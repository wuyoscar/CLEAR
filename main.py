#!/usr/bin/env python3
import os
import torch
import time
import json
import pandas as pd
import argparse
from openai import OpenAI

from utilize import extract_json_response, get_token_count, save_json
from clear.search import SerperSearch, FireScrape
from clear.prompt import (
    generate_query_prompt,
    section_community_analysis_prompt,
    section_topic_question_prompt,
    generate_image_uris_from_pdfs,
    email_report_prompt,
)
from clear.db import PolicyMatcher
from clear.load_model import load_model_and_tokenizer
import config

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_output_folder(base_path="output"):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    folder_path = os.path.join(base_path, timestamp)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def save_generation_results(output_folder, data_obj, text_obj, gen_results):
    # 保存 data_obj 和 text_obj 到 JSON 文件
    save_json(data_obj, os.path.join(output_folder, "data_object.json"))
    save_json(text_obj, os.path.join(output_folder, "text_object.json"))

    # 保存文本输出结果
    for key, value in gen_results.items():
        if isinstance(value, str):
            with open(os.path.join(output_folder, key), "w", encoding="utf-8") as file:
                file.write(value)

    print(f"Results saved to {output_folder}")


def call_gpt(prompt_messages, model="gpt-4o", temperature=0.2, top_p=0.1):
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response_payload = {
        "model": model,
        "messages": prompt_messages,
        "temperature": temperature,
        "top_p": top_p,
    }
    try:
        response = client.chat.completions.create(**response_payload)
        return response
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def generate_extraction(user_query, model, tokenizer, device, max_retries=2):
    prompt = generate_query_prompt(user_query)

    for attempt in range(max_retries + 1):
        print(f"[yellow]Attempt {attempt + 1} to process the user query...[/yellow]")
        input_tokens = tokenizer(
            prompt,
            padding=True,
            truncation=True,
            max_length=1250,
            return_tensors="pt",
        ).to(device)

        output_tokens = model.generate(
            **input_tokens,
            max_new_tokens=220,
            eos_token_id=tokenizer.eos_token_id,
        )

        raw_output = tokenizer.decode(output_tokens[0], skip_special_tokens=True)
        extracted_response = extract_json_response(raw_output)

        if extracted_response:
            print("[green]Successfully extracted the JSON response.[/green]")
            return extracted_response
        else:
            print(f"[red]Extraction failed on attempt {attempt + 1}. Retrying...[/red]\n{raw_output}")

    print("[bold red]All extraction attempts failed. Please check the model or input query.[/bold red]")
    raise RuntimeError("Failed to extract JSON response after maximum retries.")


def fetch_policy_data(query_extraction, data_object):
    db_matcher = PolicyMatcher()
    location_details = query_extraction.get('location', {})

    print("[blue]Searching the database for matching location...[/blue]")
    db_results = db_matcher.search(**location_details)

    has_lga_in_db = 'lga_info' in db_results
    has_suburb_in_db = 'suburb_info' in db_results

    data_object["has_lga_in_db"] = has_lga_in_db
    data_object["has_suburb_in_db"] = has_suburb_in_db

    if has_suburb_in_db:
        print("[green]Suburb data found and added to the data object.[/green]")
        data_object["suburb_info"] = db_results.get("suburb_info")
    else:
        print("[yellow]No suburb data found.[/yellow]")

    if has_lga_in_db:
        print("[green]LGA data found and added to the data object.[/green]")
        data_object["lga_info"] = db_results.get("lga_info")
        data_object["policies"] = db_results.get("policies", [])
    else:
        print("[yellow]No LGA data found.[/yellow]")

    return data_object


def validate_and_scrape(search_result, name, result_type):
    if (
        name in search_result['organic'][0].get('snippet', '') or
        name in search_result['organic'][0].get('title', '')
    ):
        print(f"{result_type.capitalize()} {name} found in Wikipedia result.")
        return FireScrape.crawl(search_result['organic'][0].get('link', ''), scrape_type="wiki")
    else:
        print(f"{result_type.capitalize()} {name} not found in Wikipedia result.")
        return None


def fetch_additional_variables(data_object):
    searcher = SerperSearch()

    lga_name = data_object['lga_info']['lga']
    state_name = data_object['suburb_info']['state']
    suburb_name = data_object['suburb_info']['suburb']

    lga_query = f"WIKIPEDIA local government of {lga_name} {state_name} in Australia"
    lga_result = searcher.search(lga_query, k=1)
    lga_wiki_var = validate_and_scrape(lga_result, lga_name, "lga")

    if 'organic' in lga_result:
        lga_wiki_var_reference = lga_result['organic'][0]
    else:
        lga_wiki_var_reference = None

    if data_object['has_suburb_in_db']:
        sub_query = f"WIKIPEDIA suburb of {suburb_name} {state_name} in Australia"
        sub_result = searcher.search(sub_query, k=1)
        if 'organic' in sub_result:
            suburb_wiki_var_reference = sub_result['organic'][0]
        else:
            suburb_wiki_var_reference = None
        suburb_wiki_var = validate_and_scrape(sub_result, suburb_name, "suburb")
    else:
        suburb_wiki_var = None
        suburb_wiki_var_reference = None

    lga_census_var = FireScrape.crawl(data_object['lga_info']['censusURL_2021'], scrape_type='general')

    text_var = {}
    text_var['page_var'] = {
        "lga_wiki_var": lga_wiki_var,
        "lga_wiki_var_reference": lga_wiki_var_reference,
        "suburb_wiki_var": suburb_wiki_var,
        "suburb_wiki_var_reference": suburb_wiki_var_reference,
        "lga_census_var": lga_census_var,
    }
    return text_var


def display_table(df: pd.DataFrame) -> str:
    return f"###Table in json format: {df.to_json()}"


def extract_policy_texts(policy_paths, layout):
    policy_texts = {}
    policy_name_list = []
    for i, pdf_path in enumerate(policy_paths):
        print(f"[blue]Processing PDF: {pdf_path}[/blue]")
        doc = layout(pdf_path)
        policy_name = f"policy_{i+1}_token_{get_token_count(doc.text)}"
        policy_name_list.append(policy_name)
        policy_texts[policy_name] = doc.text
    return policy_texts, policy_name_list


def main():
    parser = argparse.ArgumentParser(
        description="Extract policy data and generate analysis using LLM and crawling."
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device to use: cuda, mps, or cpu. If not provided, auto-detect."
    )
    parser.add_argument(
        "--query",
        type=str,
        default="In Oakford, WA, in the Serpentine-Jarrahdale LGA, water scarcity and extreme heat are major challenges. What programs are in place to promote water efficiency and manage climate impacts in our region?",
        help="User query for extraction."
    )
    parser.add_argument(
        "--gpt_model",
        type=str,
        default="gpt-4o",
        help="GPT model to use for API calls (default: gpt-4o)."
    )
    args = parser.parse_args()

    # 加载模型和分词器，传入设备参数（若 args.device 为 None 则自动检测）
    model, tokenizer, device = load_model_and_tokenizer(device=args.device)

    # 使用用户查询
    user_query = args.query

    # 生成提取内容
    query_extraction = generate_extraction(user_query, model, tokenizer, device)

    data_object = {
        "user_query": user_query,
        "query_extraction": query_extraction,
    }

    # 从数据库中获取匹配的 suburb、LGA 及政策信息
    data_object = fetch_policy_data(query_extraction, data_object)
    if not data_object.get("has_lga_in_db", False):
        raise RuntimeError(
            f"[red]No matching records found in the database![/red]\n{data_object.get('log_info', 'No log info available')}"
        )

    # 使用爬虫抓取额外变量信息
    text_var = fetch_additional_variables(data_object)
    lga_policy_path = [
        os.path.join(ROOT_DIR, "data", "pdf_lga", policy["pdf_path"])
        for policy in data_object.get("policies", [])
    ]
    text_var["lga_policy_path"] = lga_policy_path

    # 使用 GPT API 生成社区分析报告
    commu_prompt = section_community_analysis_prompt(data_object, text_var)
    commu_gen = call_gpt(commu_prompt, model=args.gpt_model)
    commu_gen_text = commu_gen.choices[0].message.content

    # 使用 GPT API 生成文档分析报告
    image_uris = generate_image_uris_from_pdfs(lga_policy_path)
    document_analysis_prompt = section_topic_question_prompt(data_object, text_var, image_uris)
    document_analysis_gen = call_gpt(document_analysis_prompt, model=args.gpt_model)
    document_analysis_text = document_analysis_gen.choices[0].message.content

    # 使用 GPT API 生成电子邮件报告
    email_prompt = email_report_prompt(data_object, text_var, document_analysis_text)
    email_gen = call_gpt(email_prompt, model=args.gpt_model)
    email_text = email_gen.choices[0].message.content

    # 创建输出文件夹
    output_folder = create_output_folder()

    # 保存生成结果
    gen_results = {
        "community_analysis_text": commu_gen_text,
        "document_analysis_text": document_analysis_text,
        "email_report_text": email_text,
    }
    save_generation_results(output_folder, data_object, text_var, gen_results)


if __name__ == "__main__":
    main()
