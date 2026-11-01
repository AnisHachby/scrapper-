"""
Scrapes Boursenews.ma sitemap and matches articles to BVC stock tickers.
Allows historical backfilling of news intensity signals.
"""
import sys
import ssl
import csv
import re
import urllib.request
from pathlib import Path
import xml.etree.ElementTree as ET

TICKER_KEYWORDS = {
    "ATW": ["attijariwafa", "attijari", "atw"],
    "IAM": ["maroc-telecom", "iam", "telecom", "itissalat"],
    "ADH": ["addoha", "douja", "adh"],
    "ADI": ["alliances", "adi"],
    "TQA": ["taqa-morocco", "taqa", "jlec"],
    "CSU": ["cosumar"],
    "BCP": ["banque-populaire", "bcp", "chaabi"],
    "LHC": ["lafargeholcim", "lafarge", "holcim"],
    "MLE": ["maroc-leasing"],
    "SNP": ["snep"],
    "SND": ["sonasid"],
    "HPS": ["hps", "hightech-payment"],
    "MUT": ["mutandis"],
    "PORT": ["marsa-maroc", "marsa", "sodep"],
    "MNG": ["managem"],
    "WAA": ["wafa-assurance"],
    "ASN": ["atlanta", "atlantasanlam"],
    "RDS": ["residences-dar-saada", "dar-saada"],
    "BCI": ["bmci"],
    "BOA": ["bank-of-africa", "bmce", "boa"],
    "CIH": ["cih", "credit-immobilier"],
    "CDM": ["credit-du-maroc"],
    "CMA": ["ciments-du-maroc", "cimar"],
    "SAH": ["sahams-assurance", "sahams", "sanlam"],
    "DWY": ["dari-couspate", "dari"],
    "LES": ["lesieur", "lesieur-cristal"],
    "MAB": ["maroc-carbon"],
    "IMO": ["immorente"],
    "BAL": ["balima"],
    "STR": ["stroc", "stroc-industrie"],
    "NXT": ["nextans"],
    "ATH": ["auto-hall"],
    "ALM": ["aluminium-du-maroc"],
    "RIS": ["risma"],
    "FBR": ["fenie-brossette"],
    "IB": ["ib-maroc"],
    "JET": ["jet-contractors", "jet-aluminium"],
    "M2M": ["m2m-group"],
    "MOX": ["maghreb-oxygene"],
    "SNA": ["sanam"],
    "DHO": ["doha"],
}

def parse_date(date_str):
    if not date_str:
        return ""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
    if match:
        return match.group(1)
    return ""

def main():
    out_dir = Path("project-pfe-repo/data/raw/news")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "boursenews_index.csv"
    
    url = "https://boursenews.ma/sitemap.xml"
    print(f"Fetching Boursenews sitemap: {url}")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            xml_data = r.read()
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return
        
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"Error parsing sitemap XML: {e}")
        return
        
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    articles = []
    
    for url_node in root.findall('ns:url', ns):
        loc = url_node.find('ns:loc', ns)
        lastmod = url_node.find('ns:lastmod', ns)
        
        if loc is not None:
            loc_str = loc.text.strip()
            date_str = lastmod.text.strip() if lastmod is not None else ""
            parsed_date = parse_date(date_str)
            
            if "/article/" in loc_str:
                # Normalize slug using hyphens as spaces
                slug = loc_str.split('/')[-1].lower()
                title = slug.replace('-', ' ').title()
                
                # Check for ticker matches
                matched_tickers = []
                for ticker, keywords in TICKER_KEYWORDS.items():
                    for kw in keywords:
                        # Replace hyphens with spaces for clean regex matching
                        clean_slug = slug.replace('-', ' ')
                        clean_kw = kw.replace('-', ' ')
                        
                        # Short keywords must match as exact words to avoid false positive substrings
                        if len(clean_kw) <= 4:
                            pattern = r"\b" + re.escape(clean_kw) + r"\b"
                        else:
                            pattern = re.escape(clean_kw)
                            
                        if re.search(pattern, clean_slug):
                            matched_tickers.append(ticker)
                            break
                            
                for t in matched_tickers:
                    articles.append({
                        "date": parsed_date,
                        "url": loc_str,
                        "ticker": t,
                        "title": title
                    })
                    
    print(f"Parsed {len(articles)} matched ticker articles.")
    
    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(["date", "url", "ticker", "title"])
        for art in articles:
            writer.writerow([art["date"], art["url"], art["ticker"], art["title"]])
            
    print(f"Saved matched articles index to {out_csv}")

if __name__ == "__main__":
    main()
