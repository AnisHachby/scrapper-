import sys
import argparse
import time
import requests
import urllib3
from pathlib import Path
from datetime import timedelta, date

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    BULLETIN_DIR, BULLETIN_URL, FETCH_DELAY, USER_AGENT
)

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def fetch_one(d, out_dir, delay):
    if d.weekday() >= 5: # Saturday = 5, Sunday = 6
        return "skip_weekend"
    
    date_str = d.strftime("%Y%M%d") # Wait, original is probably %Y%m%d
    date_str = d.strftime("%Y%m%d")
    
    out_file = out_dir / f"BCFR_{date_str}.pdf"
    if out_file.exists():
        return "cached"
    
    url = BULLETIN_URL.format(date_str)
    headers = {"User-Agent": USER_AGENT}
    
    try:
        time.sleep(delay)
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        
        if response.status_code == 200:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, 'wb') as f:
                f.write(response.content)
            return "downloaded"
        elif response.status_code == 404:
            return "not_found"
        else:
            return f"http_{response.status_code}"
    except Exception as e:
        return f"error_{str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Download BVC daily bulletins")
    parser.add_argument("--start", default="2018-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=date.today().strftime("%Y-%m-%d"), help="End date YYYY-MM-DD")
    parser.add_argument("--out-dir", type=Path, default=BULLETIN_DIR, help="Output directory")
    parser.add_argument("--delay", type=float, default=FETCH_DELAY, help="Delay between requests")
    parser.add_argument("--resume", action="store_true", default=True, help="Skip existing files")
    
    args = parser.parse_args()
    
    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    stats = {"cached": 0, "downloaded": 0, "not_found": 0, "errors": 0, "skip_weekend": 0}
    total_days = (end_date - start_date).days + 1
    
    print(f"Fetching bulletins from {start_date} to {end_date}...")
    
    for i, d in enumerate(daterange(start_date, end_date)):
        status = fetch_one(d, args.out_dir, args.delay)
        
        if status.startswith("error") or status.startswith("http"):
            stats["errors"] += 1
        else:
            stats[status] = stats.get(status, 0) + 1
            
        if (i + 1) % 10 == 0 or i == total_days - 1:
            print(f"Processed {i+1}/{total_days} (cached: {stats['cached']}, downloaded: {stats['downloaded']}, not_found: {stats['not_found']})")
            
    print(f"Done. Final stats: {stats}")

if __name__ == "__main__":
    main()
