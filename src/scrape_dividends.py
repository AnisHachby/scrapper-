"""
Scrapes the Casablanca Stock Exchange (BVC) official dividend calendar.
Overwrites project-pfe-repo/data/raw/dividends/dividend_calendar.csv with real-world data.
"""
import ssl
import csv
import re
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

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
    "ASN": ["atlanta", "atlantasanlam", "atlantasanad"],
    "RDS": ["residences-dar-saada", "dar-saada"],
    "BCI": ["bmci"],
    "BOA": ["bank-of-africa", "bmce", "boa"],
    "CIH": ["cih", "credit-immobilier"],
    "CDM": ["credit-du-maroc"],
    "CMA": ["ciments-du-maroc", "cimar"],
    "SAH": ["sahams-assurance", "sahams", "sanlam"],
    "DWY": ["dari-couspate", "dari", "disway"],
    "LES": ["lesieur", "lesieur-cristal"],
    "MAB": ["maroc-carbon"],
    "IMO": ["immorente"],
    "BAL": ["balima"],
    "STR": ["stroc", "stroc-industrie"],
    "NXT": ["nextans"],
    "ATH": ["auto-hall", "auto hall"],
    "ALM": ["aluminium-du-maroc"],
    "RIS": ["risma"],
    "FBR": ["fenie-brossette"],
    "IB": ["ib-maroc"],
    "JET": ["jet-contractors", "jet-aluminium"],
    "M2M": ["m2m-group"],
    "MOX": ["maghreb-oxygene"],
    "SNA": ["sanam"],
    "DHO": ["doha", "delta-holding", "delta holding"],
}

# Inverse mapper for ISINs
TICKER_TO_ISIN = {
    "ATW": "MA0000012247",
    "IAM": "MA0000011488",
    "ADH": "MA0000011512",
    "ADI": "MA0000012015",
    "TQA": "MA0000012205",
    "CSU": "MA0000012163",
    "BCP": "MA0000011884",
    "LHC": "MA0000012320",
    "MLE": "MA0000010969",
    "SNP": "MA0000011322",
    "SND": "MA0000011306",
    "HPS": "MA0000011991",
    "MUT": "MA0000012148",
    "PORT": "MA0000012221",
    "MNG": "MA0000011033",
    "WAA": "MA0000010621",
    "ASN": "MA0000011702",
    "RDS": "MA0000012049",
    "BOA": "MA0000010019",
    "CIH": "MA0000012114",
    "CDM": "MA0000010266",
    "CMA": "MA0000010530",
    "SAH": "MA0000011124",
    "DWY": "MA0000011876",
    "LES": "MA0000011009",
    "IMO": "MA0000012304",
    "BAL": "MA0000010639",
    "STR": "MA0000011793",
    "NXT": "MA0000011421",
    "ATH": "MA0000010092",
    "ALM": "MA0000010241",
    "RIS": "MA0000011504",
    "FBR": "MA0000010159",
    "IB": "MA0000010464",
    "JET": "MA0000011868",
    "M2M": "MA0000011637",
    "MOX": "MA0000011942",
    "SNA": "MA0000010589",
    "DHO": "MA0000011967",
}

BVC_NAME_TO_TICKER = {
    "MAGHREB OXYGENE": "MOX",
    "AFRIQUIA GAZ": "AGAZ",
    "IMMORENTE INVEST": "IMO",
    "AUTO NEJMA": "NEJ",
    "AUTO HALL": "ATH",
    "CREDIT DU MAROC": "CDM",
    "DELTA HOLDING": "DHO",
    "SOCIETE DES BOISSONS DU MAROC": "SBM",
    "CASH PLUS S.A": "CASH",
    "SALAFIN": "SLF",
    "CFG BANK": "CFG",
    "ATLANTASANAD": "ASN",
    "VICENNE": "VICE",
    "ITISSALAT AL-MAGHRIB": "IAM",
    "HOLCIM MAROC S.A": "LHC",
    "LAFARGEHOLCIM MAROC": "LHC",
    "WAFA ASSURANCE": "WAA",
    "ARADEI CAPITAL": "ARADEI",
    "DISWAY": "DWY",
}

def clean_date(date_str):
    # DD/MM/YYYY to YYYY-MM-DD
    parts = date_str.strip().split('/')
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return date_str

def main():
    out_dir = Path("project-pfe-repo/data/raw/dividends")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "dividend_calendar.csv"
    
    url = "https://www.casablanca-bourse.com/fr/calendrier-des-dividendes"
    print(f"Scraping BVC official dividend calendar: {url}")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9',
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=25) as r:
            soup = BeautifulSoup(r.read(), 'html.parser')
    except Exception as e:
        print(f"Error downloading page: {e}")
        return
        
    table = soup.find('table')
    if not table:
        print("Error: Could not locate table tag in HTML body.")
        return
        
    rows = table.find_all('tr')
    print(f"Found {len(rows)} table rows.")
    
    dividends = []
    
    for i, row in enumerate(rows):
        tds = [td.get_text().strip() for td in row.find_all('td')]
        if len(tds) < 5 or i == 0:
            # Skip header or short rows
            continue
            
        issuer_name = tds[0]
        amount_str = tds[1].replace(',', '.')
        ex_date_str = tds[2]
        pay_date_str = tds[3]
        div_type = tds[4]
        
        # Parse amount
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0
            
        # Parse ex_date
        ex_date = clean_date(ex_date_str)
        
        # Map issuer_name to ticker
        matched_ticker = BVC_NAME_TO_TICKER.get(issuer_name.strip())
        if not matched_ticker:
            norm_name = issuer_name.lower()
            for ticker, keywords in TICKER_KEYWORDS.items():
                for kw in keywords:
                    if kw in norm_name:
                        matched_ticker = ticker
                        break
                if matched_ticker:
                    break
                    
        if not matched_ticker:
            # Fallback matching on first token
            matched_ticker = issuer_name.split()[0].upper()[:4]
            
        isin = TICKER_TO_ISIN.get(matched_ticker, "MA_UNKNOWN")
        
        # Determine status (upcoming vs paid) based on ex_date comparison
        # Let's say if ex_date is in the future relative to today (we use 2026-07-21 as local time)
        status = "UPCOMING"
        if ex_date < "2026-07-21":
            status = "PAID"
            
        dividends.append({
            "isin": isin,
            "ticker": matched_ticker,
            "ex_date": ex_date,
            "amount_mad": amount,
            "status": status
        })
        
    # Write to CSV
    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(["isin", "ticker", "ex_date", "amount_mad", "status"])
        for div in dividends:
            writer.writerow([div["isin"], div["ticker"], div["ex_date"], div["amount_mad"], div["status"]])
            
    print(f"Scraped and saved {len(dividends)} real dividend events to {out_csv}")

if __name__ == "__main__":
    main()
