#!/usr/bin/env python3
import argparse
import re
import requests
from rich import print
from urllib.parse import urlparse, urlencode
from typing import List, Dict, Union
from dataclasses import dataclass
import json
import config

# -------------------------------------------------------
# BingSearch Class
# -------------------------------------------------------
class BingSearch:
    BASE_PATH = "https://api.bing.microsoft.com/v7.0/search?{}"
    SECRET_KEY = config.BING_API_KEY  # Replace with your actual Bing API key

    # Map Bing's API fields to output fields for readability
    SELECTED_FIELDS = {
        'url': 'page_url',
        'name': 'title',
        'siteName': 'siteName',
        'snippet': 'summary',
        'datePublished': "datePublished",
        'richFacts': 'richFacts'
    }

    @classmethod
    def _query(cls, query: str, count: int):
        params = {
            "q": query,
            "textDecorations": False,
            "mkt": "en-US",
            "count": count,
            "SafeSearch": "Strict"
        }
        url = cls.BASE_PATH.format(urlencode(params))
        
        try:
            rsp = requests.get(url, headers={'Ocp-Apim-Subscription-Key': cls.SECRET_KEY})
            rsp.raise_for_status()
        except requests.exceptions.RequestException as e:
            return False, f"HTTP request failed: {e}"
        
        return True, rsp.json()

    @classmethod
    def search(cls, query: str, k: int = 1):
        ret, jdata = cls._query(query, k)
        if not ret or 'webPages' not in jdata or 'value' not in jdata['webPages']:
            return []

        items = jdata['webPages']['value']
        # Process results using SELECTED_FIELDS to rename
        data_list = [
            {cls.SELECTED_FIELDS.get(key, key): item[key] for key in cls.SELECTED_FIELDS if key in item}
            for item in items
        ]
        return data_list


# -------------------------------------------------------
# SerperSearch & SerperConfig
# -------------------------------------------------------
@dataclass
class SerperConfig:
    API_KEY: str = config.SERPER_API_KEY  ## Replace with your actual Serpstack API key
    BASE_URL: str = "https://google.serper.dev/search"
    BATCH_LIMIT: int = 100

class SerperSearch:
    def __init__(self, api_key: str = None):
        self.config = SerperConfig()
        if api_key:
            self.config.API_KEY = api_key
        
        self.headers = {
            'X-API-KEY': self.config.API_KEY,
            'Content-Type': 'application/json'
        }
    
    def search(self, query: str, k:int=5) -> Dict:
        """Single search query."""
        payload = json.dumps({"q": query, "num": k, "gl": "au"})
        try:
            response = requests.post(self.config.BASE_URL, headers=self.headers, data=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")

    def search_batch(self, queries: List[str], k:int=5) -> List[Dict]:
        """Batch search multiple queries."""
        if len(queries) > self.config.BATCH_LIMIT:
            raise ValueError(f"Batch size exceeds limit of {self.config.BATCH_LIMIT}")
        
        payload = json.dumps([{"q": q, "num": k, "gl": "au"} for q in queries])
        try:
            response = requests.post(self.config.BASE_URL, headers=self.headers, data=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")


# -------------------------------------------------------
# FireScrape Class
# -------------------------------------------------------
class FireScrape:
    API_KEY = config.FIRE_SCRAPE_API_KEY  # Replace with your actual Firecrawl API key
    API_URL = "https://api.firecrawl.dev/v1/scrape"

    @classmethod
    def is_wikipedia_url(cls, url: str) -> bool:
        """Checks if a given URL is a Wikipedia page."""
        try:
            parsed_url = urlparse(url)
            return "wikipedia.org" in parsed_url.netloc
        except Exception as e:
            print(f"Error parsing URL: {e}")
            return False
        
    @classmethod
    def crawl(cls, url: str, format_type: str = 'markdown', scrape_type: str = 'general') -> str:
        """
        Crawls a webpage using the Firecrawl API.

        Args:
            url (str): The URL of the webpage to crawl.
            format_type (str): The format of the response (default is 'markdown').
            scrape_type (str): One of ['simple','general','wiki'] controlling the cleanup style.
        """
        payload = {
            "url": url,
            "formats": [format_type],
            "onlyMainContent": True,
            "waitFor": 2
        }
        
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(cls.API_URL, headers=headers, json=payload)
            jdata = response.json()
            if jdata['success']:
                data_got = jdata['data'].get(format_type, "")
                if scrape_type == "simple":
                    return FireScrape.simple_clean(data_got)
                elif scrape_type == "general":
                    return FireScrape.clean_content_general(data_got)
                elif scrape_type == "wiki":
                    return FireScrape.clean_content_wikipedia(data_got)
            return ""
        except requests.RequestException as e:
            print(f"Error making request to Firecrawl API: {e}")
            return ""
            
    @classmethod
    def simple_clean(cls, content: str) -> str:
        # Remove Markdown-style image links
        content = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', content)
        # Remove lines starting with "More information on..."
        content = re.sub(r'^More information on.*$', '', content, flags=re.MULTILINE)
        # Replace multiple consecutive newlines with a single newline
        content = re.sub(r'\n{3,}', '\n', content)
        return content
    
    @classmethod
    def clean_content_general(cls, content: str) -> str:
        """Cleans general webpage content."""
        # Remove markdown image links
        content = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', content)
        # (Optional) remove more patterns if needed
        # e.g., content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)
        # Reduce multiple newlines
        content = re.sub(r'\n{3,}', '\n', content)
        return content.strip()

    @classmethod
    def clean_content_wikipedia(cls, content: str) -> str:
        """Cleans Wikipedia content."""
        # Pass 1: remove markdown image links
        content = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', content)
        # Pass 2: remove standard markdown links, references, etc.
        content = re.sub(r'\[(.*?)\]\(.*?\)|\[(.*?)\]', lambda m: (m.group(1) or m.group(2)), content)
        
        removal_patterns = [
            r'\[\d+\]',                  # Reference brackets like [1], [2]
            r'\s?\[edit\]\s?',
            r'!\s*<br><br>',
            r'\\?\[\d+\\?\]',
            r'\\?\[edit(?:\"\))?\\?\s*\\?\]',
            r'<br>',
            r'\bhttps?://\S+\b',
            r'\bwww\.\S+\b',
            r'(?:\.jpg\)?)?'
        ]
        for pattern in removal_patterns:
            content = re.sub(pattern, '', content)
        content = re.sub(r'\n{2,}', '\n', content)

        # (Optional) separate references
        if "the free encyclopedia" in content:
            content = content.split('the free encyclopedia', 1)[1].strip()
        if 'References\n' in content:
            content, references = map(str.strip, content.split('References\n', 1))

        return content.strip()


# -------------------------------------------------------
# Main with argparse
# -------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Demo script using BingSearch + FireScrape with optional Wikipedia cleaning."
    )
    parser.add_argument("--query", type=str, default="Artificial Intelligence (AI) will replace 50% of all human jobs by 2030.",
                        help="Search query.")
    parser.add_argument("--top_k", type=int, default=3, 
                        help="Number of search results to retrieve from Bing.")
    args = parser.parse_args()

    # Create a BingSearch instance
    searcher = BingSearch()

    # Perform search
    search_result = searcher.search(args.query, k=args.top_k)

    # Process results
    wiki_result = []
    for item in search_result:
        url = item["page_url"]
        # Decide how to scrape: if Wikipedia => 'wiki', else 'general'
        if FireScrape.is_wikipedia_url(url):
            item['text'] = FireScrape.crawl(url, scrape_type='wiki')
            wiki_result.append(item)
        else:
            item['text'] = FireScrape.crawl(url, scrape_type='general')
        
        print(item)  # Print the item dict, including 'text'
    
    print("[bold green]Done![/bold green]")


if __name__ == "__main__":
    main()

# python search_and_scrape.py \
#     --query "Impact of climate change on coastal cities" \
#     --top_k 5