#!/usr/bin/env python3
"""Utility script to search and download judgments from Indian Kanoon.

Usage:
  # To search for judgments about a topic:
  python scripts/download_kanoon.py --query "anticipatory bail BNS"

  # To download a specific judgment by ID (TID):
  python scripts/download_kanoon.py --doc 1739097
"""

import os
import sys
import argparse
import httpx
from dotenv import load_dotenv

# Load env file
load_dotenv()

API_KEY = os.getenv("INDIANKANOON_API_KEY")
API_BASE = os.getenv("INDIANKANOON_API_BASE", "https://api.indiankanoon.org").rstrip("/")

if not API_KEY:
    print("\033[91mError: INDIANKANOON_API_KEY is not set in backend/.env file.\033[0m")
    sys.exit(1)


def get_headers():
    return {
        "Accept": "application/json",
        "Authorization": f"Token {API_KEY}"
    }


def search_judgments(query: str):
    print(f"Searching Indian Kanoon for: '{query}'...")
    url = f"{API_BASE}/search/"
    params = {
        "formInput": query,
        "pagenum": 0
    }
    
    try:
        response = httpx.get(url, params=params, headers=get_headers(), timeout=20.0)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("docs", [])
        if not results:
            print("No matching judgments found.")
            return
            
        print(f"\nFound {len(results)} matches:")
        print("-" * 80)
        for idx, doc in enumerate(results):
            title = doc.get("title", "No Title")
            doc_id = doc.get("tid")
            publish_date = doc.get("publishdate", "N/A")
            print(f"[{idx + 1}] Title: {title}")
            print(f"    Document ID (TID): \033[92m{doc_id}\033[0m")
            print(f"    Published: {publish_date}")
            print("-" * 80)
            
        print("\nTo download any of these, run:")
        print("  python scripts/download_kanoon.py --doc <TID>")
        
    except Exception as e:
        print(f"\033[91mSearch error: {e}\033[0m")


def download_judgment(doc_id: str):
    print(f"Fetching document ID {doc_id} from Indian Kanoon...")
    url = f"{API_BASE}/doc/{doc_id}/"
    
    try:
        response = httpx.get(url, headers=get_headers(), timeout=20.0)
        response.raise_for_status()
        data = response.json()
        
        title = data.get("title", f"judgment_{doc_id}")
        raw_html_or_text = data.get("doc", "")
        
        # Clean HTML tags if present for plain text readability
        import re
        clean_text = re.sub(r'<[^>]+>', '', raw_html_or_text)
        
        # Format filename
        safe_title = re.sub(r'[^\w\-_.]', '_', title)[:60]
        filename = f"{safe_title}_{doc_id}.txt"
        
        # Save to output file
        os.makedirs("downloads", exist_ok=True)
        filepath = os.path.join("downloads", filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\n")
            f.write(f"Source ID: {doc_id}\n")
            f.write("=" * 80 + "\n\n")
            f.write(clean_text)
            
        print(f"\n\033[92mSuccess!\033[0m Judgment saved to: \033[94mbackend/{filepath}\033[0m")
        print("You can now upload this text file directly into the Web UI to test analysis.")
        
    except Exception as e:
        print(f"\033[91mDownload error: {e}\033[0m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indian Kanoon Judgment Tool")
    parser.add_argument("--query", type=str, help="Search query string to search for legal judgments")
    parser.add_argument("--doc", type=str, help="Document ID (TID) to download text file")
    
    args = parser.parse_args()
    
    if args.query:
        search_judgments(args.query)
    elif args.doc:
        download_judgment(args.doc)
    else:
        parser.print_help()
