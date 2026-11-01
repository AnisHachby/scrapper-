import argparse, csv, json, ssl, subprocess, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.casablanca-bourse.com/api/bourse_data/last_market_watches/action"
REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "intraday"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
           "Accept": "application/json, text/plain, */*", "Referer": "https://www.casablanca-bourse.com/"}
FIELDS = {"code":"code","etatCotVal":"state","staticReferencePrice":"ref_static","dynamicReferencePrice":"ref_dynamic",
          "openingPrice":"open","highPrice":"high","lowPrice":"low","lastTradedPrice":"last","coursCourant":"current",
          "closingPrice":"close","varVeille":"var_veille","cumulTitresEchanges":"cum_shares","cumulVolumeEchange":"cum_value_mad",
          "totalTrades":"n_trades","bestBidPrice":"bid","bestBidSize":"bid_size","bestAskPrice":"ask","bestAskSize":"ask_size","transactTime":"transact_time"}
COLUMNS = ["capture_ts","ticker"] + list(FIELDS.values())

def clean(v):
    if v is None or v in ("-",""): return ""
    if isinstance(v,str):
        try: return f"{float(v):.4f}".rstrip("0").rstrip(".")
        except ValueError: return v
    return v

def fetch(retries=2, timeout=10):
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req = urllib.request.Request(API, headers=HEADERS)
    last = None
    data = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:
            last = e
            if attempt < retries - 1: time.sleep(2)
    if not data or "data" not in data or "data" not in data["data"]:
        print(f"BVC API fetch skipped (market closed / timeout): {last}")
        return None, [], []
    recs = data["data"]["data"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, trades = [], []
    for rec in recs:
        a = rec.get("attributes", {})
        ticker = str(a.get("code","")).split("-")[0]
        row = {"capture_ts": now, "ticker": ticker}
        for src, dst in FIELDS.items(): row[dst] = clean(a.get(src))
        rows.append(row)
        bid, ask = clean(a.get("bestBidPrice")), clean(a.get("bestAskPrice"))
        for t in a.get("lastTransactions") or []:
            trades.append({"capture_ts": now, "ticker": ticker, "trade_time": t.get("transactTime",""),
                           "price": clean(t.get("executedPrice")), "size": clean(t.get("executedSize")), "bid": bid, "ask": ask})
    return now, rows, trades

def git(*a): subprocess.run(["git","-C",str(REPO),*a], check=False)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--commit",action="store_true"); args=ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now, rows, trades = fetch()
    if not now or not rows:
        print("Data collection skipped: No response from BVC API.")
        return
    path = OUT_DIR / f"intraday_{now[:10]}.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new: w.writeheader()
        w.writerows(rows)
    tpath = OUT_DIR / f"trades_{now[:10]}.csv"
    tcols = ["capture_ts","ticker","trade_time","price","size","bid","ask"]
    new_t = not tpath.exists()
    seen = set()
    if not new_t:
        with tpath.open(encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                p = line.rstrip("\n").split(",")
                if len(p) >= 5: seen.add((p[1],p[2],p[3],p[4]))
    fresh = [t for t in trades if (t["ticker"],t["trade_time"],str(t["price"]),str(t["size"])) not in seen]
    with tpath.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=tcols)
        if new_t: w.writeheader()
        w.writerows(fresh)
    traded = sum(1 for r in rows if r["state"] not in ("N.T","","S"))
    print(f"{now}: {len(rows)} stocks ({traded} traded), {len(fresh)} new trades -> {path.name}")
    if args.commit:
        git("add", str(OUT_DIR)); git("commit","-m",f"Intraday {now[:10]}"); git("push")

if __name__ == "__main__":
    main()
