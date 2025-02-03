import json
import ast
from PyPDF2 import PdfReader
import tiktoken
import os
import re
import urllib.parse
from markdown import markdown
#from md2pdf.core import md2pdf


def count_pdf_pages(pdf_file_path):
    """
    Calculate the number of pages in a PDF file.

    Parameters:
    pdf_file_path (str): The path to the PDF file.

    Returns:
    int: The number of pages in the PDF.
    """
    try:
        reader = PdfReader(pdf_file_path)
        return len(reader.pages)  # Return the number of pages
    except Exception as e:
        print(f"Error reading {pdf_file_path}: {e}")
        return None
    

def get_unique_with_rows_and_dict(df, col_name, key_col, value_col):
    # Get unique values with complete rows
    unique_df = df.drop_duplicates(subset=col_name).reset_index(drop=True)
    
    # Convert two columns to dictionary
    result_dict = dict(zip(unique_df[key_col], unique_df[value_col]))
    
    return unique_df, result_dict





def read_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as infile:
            data = json.load(infile)
        return data
    except Exception as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return None


def save_json(data, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=4)
        print(f"JSON data successfully saved to {file_path}")
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")

def get_token_count(text: str) -> int:
    """Get number of tokens in text"""
    encoder = tiktoken.get_encoding("cl100k_base") 
    return len(encoder.encode(text))




# def convert_md_to_pdf(text: str, filename: str = "output", output_dir: str = "outputPDF") -> dict:
#     # Ensure output directory exists
#     os.makedirs(output_dir, exist_ok=True)

#     # Set file paths
#     pdf_path = os.path.join(output_dir, f"{filename[:60]}.pdf")
#     html_path = os.path.join(output_dir, f"{filename[:60]}.html")

#     try:
#         # Convert Markdown to HTML
#         html_content = markdown(text)

#         # Save the HTML file
#         with open(html_path, "w") as html_file:
#             html_file.write(html_content)
#         print(f"HTML report written to {html_path}")

#         # Convert Markdown to PDF
#         md2pdf(
#             pdf_path,
#             md_content=text,
#             css_file_path="frontend/pdf_style.css",
#             base_url=None
#         )
#         print(f"PDF report written to {pdf_path}")

#     except Exception as e:
#         print(f"Error in converting Markdown to outputs: {e}")
#         return {"pdf_path": "", "html_path": ""}

#     # Encode file paths
#     encoded_pdf_path = urllib.parse.quote(pdf_path)
#     encoded_html_path = urllib.parse.quote(html_path)

#     return {"pdf_path": encoded_pdf_path, "html_path": encoded_html_path}



def extract_json_response(text: str) -> dict:
    # 查找 "### Response" 的位置（注意可能存在附加说明，例如 "### Response (valid JSON only):"）
    marker = "### Response"
    marker_index = text.find(marker)
    if marker_index == -1:
        print("未找到 '### Response' 标记")
        return None

    # 从 marker 后查找第一个冒号 (:)
    colon_index = text.find(":", marker_index)
    if colon_index == -1:
        print("未找到冒号 ':' 分隔符")
        return None

    # 获取冒号后面的全部文本
    response_text = text[colon_index + 1:].strip()

    # 查找第一个左大括号和最后一个右大括号，提取中间部分作为 JSON 字符串
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        print("未能在响应中找到完整的 JSON 对象")
        return None

    json_str = response_text[start:end + 1].strip()

    # 尝试解析 JSON 字符串
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # 如果标准解析失败，尝试用 ast.literal_eval 解析（适用于使用单引号的情况）
            data = ast.literal_eval(json_str)
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            return None

    # 确保 location 字段包含所需的键，如果缺失则补充 None
    if "location" in data and isinstance(data["location"], dict):
        data["location"] = {
            "query_suburb": data["location"].get("query_suburb", None),
            "query_state": data["location"].get("query_state", None),
            "query_lga": data["location"].get("query_lga", None)
        }
    return data


if __name__ == "__main__":
    with open("finalgenration", "r", encoding="utf-8") as file:
        content = file.read()