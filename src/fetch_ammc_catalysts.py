"""
Crawls AMMC website for issuer communique digests.

CRITICAL LIMITATION: The AMMC listing page is served from a full-page Drupal cache
that ignores `?page=N` and date-range filters for anonymous requests. 
Only the most recent ~10 entries are reachable via this script.
This gives a real but tiny recent catalyst sample, NOT a multi-year backfill.
"""
import sys
import argparse
import time
import csv
from pathlib import Path
from urllib.parse import urljoin
import requests
import urllib3
from bs4 import BeautifulSoup

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    AMMC_DIR, AMMC_BASE, AMMC_LISTING_URL, AMMC_FETCH_DELAY, USER_AGENT
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_with_retry(session, url, delay, max_retries=4):
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(max_retries):
        try:
            time.sleep(delay)
            response = session.get(url, headers=headers, verify=False, timeout=15)
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                return None
            time.sleep(delay * (2 ** attempt)) # exponential backoff
    return None

def crawl_index(session, out_dir, delay, max_pages=1):
    out_dir.mkdir(parents=True, exist_ok=True)
    index_file = out_dir / "index.csv"
    
    # Load existing to avoid re-fetching
    seen_urls = set()
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                if len(row) >= 2:
                    seen_urls.add(row[1])
                    
    results = []
    
    # Due to AMMC cache limitations, pagination often doesn't work.
    # But we try anyway based on max_pages.
    for page in range(max_pages):
        url = f"{AMMC_LISTING_URL}?page={page}"
        print(f"Crawling index page {page}: {url}")
        
        resp = get_with_retry(session, url, delay)
        if not resp:
            break
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        articles = soup.select('.views-row')
        
        if not articles:
            break
            
        for article in articles:
            date_elem = article.select_one('.date-display-single')
            link_elem = article.select_one('a')
            
            if date_elem and link_elem:
                date_str = date_elem.text.strip()
                article_url = urljoin(AMMC_BASE, link_elem.get('href'))
                
                if article_url not in seen_urls:
                    results.append((date_str, article_url))
                    seen_urls.add(article_url)
                    
    if results:
        mode = 'a' if index_file.exists() else 'w'
        with open(index_file, mode, encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            for row in results:
                writer.writerow(row)
        print(f"Added {len(results)} new articles to index.")
    else:
        print("No new articles found in index.")
        
    return index_file

def fetch_articles(session, index_file, out_dir, delay):
    articles_dir = out_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    
    with open(index_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        rows = list(reader)
        
    for i, row in enumerate(rows):
        if len(row) < 2:
            continue
            
        date_str, url = row[0], row[1]
        filename = url.split('/')[-1] + ".html"
        if not filename.endswith(".html"):
            filename += ".html"
            
        out_file = articles_dir / filename
        if out_file.exists():
            continue
            
        print(f"Fetching article {i+1}/{len(rows)}: {url}")
        resp = get_with_retry(session, url, delay)
        
        if resp:
            with open(out_file, 'w', encoding='utf-8') as fout:
                fout.write(resp.text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=AMMC_DIR)
    parser.add_argument("--delay", type=float, default=AMMC_FETCH_DELAY)
    parser.add_argument("--max-pages", type=int, default=1)
    
    args = parser.parse_args()
    session = requests.Session()
    
    index_file = crawl_index(session, args.out_dir, args.delay, args.max_pages)
    fetch_articles(session, index_file, args.out_dir, args.delay)
    
if __name__ == "__main__":
    main()
