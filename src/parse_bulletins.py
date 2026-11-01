import sys
import argparse
import re
from pathlib import Path
import pandas as pd
import pdfplumber

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import BULLETIN_DIR, PROCESSED_DIR, ISIN_PATTERN

def to_number(s):
    if not s or s.strip() == '-' or s.strip() == '- - - -':
        return None
    try:
        # Remove spaces, replace comma with dot
        s_clean = s.replace(' ', '').replace(',', '.')
        return float(s_clean)
    except ValueError:
        return None

# French bulletin prices use a SPACE as thousands separator
# (e.g. "3 653,00" == 3653.00).  Splitting on whitespace shatters them
# into "3" and "653,00", which silently corrupts every price >= 1000 MAD.
# This regex keeps grouped numbers as a single token.
NUMBER_RE = re.compile(r'\d{1,3}(?: \d{3})*(?:,\d+)?')
# BVC bulletins print 2-digit years (e.g. "17/07/26"); accept both.
DATE_RE = re.compile(r'\d{2}/\d{2}/\d{2,4}')


def to_number_grouped(s):
    """Parse a French-formatted, space-grouped number ('3 653,00' -> 3653.0)."""
    if not s:
        return None
    return to_number(s)

def page_text(page):
    # Some older PDFs have text rendered twice (bolding artifact)
    # pdfplumber's dedupe_chars can help, but we'll try extract_text first.
    # If it looks completely garbled (lots of duplicate chars), we could use dedupe.
    # For now, standard extraction works for most BCFRs.
    text = page.extract_text(layout=True)
    if not text:
        text = page.extract_text()
    return text or ""

def parse_prices_page(text, session_date):
    """Parse MARCHE PRINCIPAL / DEVELOPPEMENT / CROISSANCE pages."""
    results = []
    
    # We look for ISIN lines
    isin_regex = re.compile(f"({ISIN_PATTERN})")
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        match = isin_regex.search(line)
        if match:
            # Check for suspended stock placeholder: '- - - -'
            if '- - - -' in line:
                continue # Skip suspended stocks
                
            isin = match.group(1)
            parts = line.split(isin)
            
            if len(parts) != 2:
                continue
                
            left_part = parts[0].strip()
            right_part = parts[1].strip()
            
            # Left part holds the share-quantity, sector code, previous date
            # and reference price. BVC prints 2-digit years ("17/07/26").
            dates = DATE_RE.findall(left_part)

            reference_price = None
            if len(dates) >= 2:
                # Reference price is the number AFTER the LAST date.
                last_date = dates[-1]
                idx = left_part.rfind(last_date)
                if idx >= 0:
                    after_last_date = left_part[idx + len(last_date):].strip()
                    # Grouped regex so "3 700,00" stays one token (3700.0)
                    grp = NUMBER_RE.search(after_last_date)
                    if grp:
                        reference_price = to_number(grp.group(0))

            # Right part begins with the company NAME, then OHLC numbers.
            # French prices use a SPACE thousands separator ("3 653,00" == 3653.00).
            # Naive whitespace splitting shatters them, so parse grouped numbers.
            r_tokens = right_part.split()
            designation = ""
            for t in r_tokens:
                if NUMBER_RE.fullmatch(t):
                    break
                designation += t + " "
            designation = designation.strip()

            numerics = [to_number(x) for x in NUMBER_RE.findall(right_part)]
            open_p, high_p, low_p, close_p = None, None, None, None
            if len(numerics) >= 4:
                # PDF column order: Open, Close, High, Low
                open_p = numerics[0]
                close_p = numerics[1]
                high_p = numerics[2]
                low_p = numerics[3]
            elif numerics:
                close_p = numerics[-1]
            # (results.append below uses these locals)
                
            results.append({
                'date': session_date,
                'isin': isin,
                'designation': designation,
                'reference_price': reference_price,
                'open': open_p,
                'high': high_p,
                'low': low_p,
                'close': close_p
            })
            
    return results

def split_qty_value(blob, price):
    """
    Disambiguate quantity and value from a blob of text.
    Uses the identity: value = price * quantity
    """
    # ... Simplified parsing logic ...
    pass

def parse_transactions_page(text, session_date):
    """Parse PHYSIONOMIE DES TRANSACTIONS."""
    results = []
    current_market = None
    
    for line in text.split('\n'):
        line = line.strip()
        
        if "MARCHE CENTRAL" in line:
            current_market = "CENTRAL"
        elif "MARCHE DE BLOCS" in line:
            current_market = "BLOCS"
        elif "TRANSFERTS" in line or "OPA" in line or "OFFRE PUBLIQUE" in line:
            current_market = "OTHER" # Skip these
            
        if current_market in ["CENTRAL", "BLOCS"]:
            # Look for lines starting with an ISIN
            match = re.match(f"^({ISIN_PATTERN})", line)
            if match:
                isin = match.group(1)
                remainder = line[len(isin):].strip()
                
                # Format is usually: ISIN Designation Volume Value
                # Since Designation can have spaces, extract from right to left
                # A robust parsing uses regex to find the rightmost numbers
                # Let's extract the last two numeric blobs
                num_matches = re.findall(r'(\d+(?: \d{3})*(?:,\d+)?)', remainder)
                
                if len(num_matches) >= 2:
                    qty_str = num_matches[-2]
                    val_str = num_matches[-1]
                    
                    qty = to_number(qty_str)
                    val = to_number(val_str)
                    
                    # Designation is everything before the qty
                    idx = remainder.rfind(qty_str)
                    designation = remainder[:idx].strip() if idx > 0 else ""
                    
                    results.append({
                        'date': session_date,
                        'isin': isin,
                        'designation': designation,
                        'market_type': current_market,
                        'quantity': qty,
                        'value': val
                    })
    return results

def parse_indices_page(text, session_date):
    """Parse MASI and sector indices."""
    results = []
    
    masi_found = False # To deduplicate MASI 20 ambiguity
    
    for line in text.split('\n'):
        line = line.strip()
        
        if "MASI " in line or "MASI20" in line or "MASI.ESG" in line or line.startswith("MASI"):
            # If MASI alone
            if "MASI 20" in line:
                pass # Handled differently to avoid confusion
                
            tokens = line.split()
            nums = [to_number(t) for t in tokens if to_number(t) is not None]
            
            if nums:
                idx_val = nums[0] # Usually the first number is the index value
                name = "MASI" if "MASI" in line and not "20" in line else "OTHER"
                
                if name == "MASI" and not masi_found:
                    results.append({
                        'date': session_date,
                        'index_name': 'MASI',
                        'value': idx_val
                    })
                    masi_found = True
                    
    return results

def session_date_from_filename(path):
    m = re.search(r"BCFR_(\d{8})\.pdf", path.name)
    if m:
        ds = m.group(1)
        return f"{ds[:4]}-{ds[4:6]}-{ds[6:]}"
    return None

def parse_one(path):
    session_date = session_date_from_filename(path)
    if not session_date:
        return [], [], []
        
    prices = []
    transactions = []
    indices = []
    
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page_text(page)
                
                if "MARCHE PRINCIPAL" in text or "MARCHE DE DEVELOPPEMENT" in text:
                    prices.extend(parse_prices_page(text, session_date))
                    
                if "PHYSIONOMIE DES TRANSACTIONS" in text:
                    transactions.extend(parse_transactions_page(text, session_date))
                    
                if "INDICES DE SECTEURS" in text or "MASI" in text:
                    indices.extend(parse_indices_page(text, session_date))
                    
    except Exception as e:
        print(f"Error parsing {path}: {e}")
        
    return prices, transactions, indices

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    if not BULLETIN_DIR.exists():
        print(f"Bulletin dir {BULLETIN_DIR} not found.")
        return
        
    pdf_files = list(BULLETIN_DIR.glob("BCFR_*.pdf"))
    total = len(pdf_files)
    
    all_prices = []
    all_transactions = []
    all_indices = []
    
    print(f"Parsing {total} PDF bulletins...")
    
    for i, path in enumerate(pdf_files):
        p, t, idx = parse_one(path)
        all_prices.extend(p)
        all_transactions.extend(t)
        all_indices.extend(idx)
        
        if (i+1) % 50 == 0 or i == total - 1:
            print(f"Parsed {i+1}/{total} bulletins")
            
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    df_p = pd.DataFrame(all_prices)
    df_t = pd.DataFrame(all_transactions)
    df_i = pd.DataFrame(all_indices)
    
    print(f"Prices: {len(df_p)} rows")
    print(f"Transactions: {len(df_t)} rows")
    print(f"Indices: {len(df_i)} rows")
    
    if not df_p.empty:
        df_p.to_parquet(PROCESSED_DIR / "prices_raw.parquet")
    if not df_t.empty:
        df_t.to_parquet(PROCESSED_DIR / "transactions_raw.parquet")
    if not df_i.empty:
        df_i.to_parquet(PROCESSED_DIR / "indices_raw.parquet")
        
if __name__ == "__main__":
    main()
