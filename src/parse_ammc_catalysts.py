import sys
import argparse
import csv
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import AMMC_DIR, PROCESSED_DIR, AMMC_BASE

def parse_article(html_text, date_str):
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # Try to find the content body
    body = soup.select_one('div.text_with_summary.body')
    if not body:
        body = soup.select_one('.field-name-body')
        
    if not body:
        return []
        
    results = []
    
    # Look for paragraphs containing links (which usually hold the communique PDF)
    for p in body.find_all('p'):
        a_tag = p.find('a')
        if a_tag:
            text = p.text.strip()
            pdf_url = a_tag.get('href', '')
            if pdf_url and not pdf_url.startswith('http'):
                pdf_url = urljoin(AMMC_BASE, pdf_url)
                
            # Usually format is "ISSUER NAME - Description of the communique"
            parts = text.split(' - ', 1)
            if len(parts) == 2:
                issuer = parts[0].strip()
                description = parts[1].strip()
            else:
                issuer = text
                description = text
                
            results.append({
                'date': date_str,
                'issuer': issuer,
                'description': description,
                'pdf_url': pdf_url
            })
            
    return results

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    index_file = AMMC_DIR / "index.csv"
    articles_dir = AMMC_DIR / "articles"
    out_file = PROCESSED_DIR / "catalysts_raw.csv"
    
    if not index_file.exists():
        print(f"No index file found at {index_file}")
        return
        
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    all_catalysts = []
    
    with open(index_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) < 2:
                continue
            date_str, url = row[0], row[1]
            
            filename = url.split('/')[-1] + ".html"
            if not filename.endswith(".html"):
                filename += ".html"
                
            article_path = articles_dir / filename
            if article_path.exists():
                with open(article_path, 'r', encoding='utf-8') as html_file:
                    catalysts = parse_article(html_file.read(), date_str)
                    all_catalysts.extend(catalysts)
                    
    print(f"Parsed {len(all_catalysts)} catalysts.")
    
    if all_catalysts:
        keys = ['date', 'issuer', 'description', 'pdf_url']
        with open(out_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_catalysts)
            
if __name__ == "__main__":
    main()
