import sys
import argparse
import json
from pathlib import Path
import pandas as pd

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import PROCESSED_DIR, CASE_STUDIES, FEATURE_COLS

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    features_path = PROCESSED_DIR / "features.parquet"
    oos_path = PROCESSED_DIR / "oos_predictions.parquet"
    
    if not features_path.exists() or not oos_path.exists():
        print("Features or OOS predictions not found.")
        return
        
    features = pd.read_parquet(features_path)
    oos = pd.read_parquet(oos_path)
    
    features['date'] = pd.to_datetime(features['date'])
    oos['date'] = pd.to_datetime(oos['date'])
    
    results = {}
    md_lines = ["# Études de Cas - Data Extraction\n"]
    
    for case in CASE_STUDIES:
        name = case['name']
        start = pd.to_datetime(case['start'])
        end = pd.to_datetime(case['end'])
        
        print(f"Extracting {name}...")
        
        # Get ISIN
        subset = features[features['designation'].str.contains(name, case=False, na=False)]
        if subset.empty:
            print(f"  Warning: {name} not found.")
            continue
            
        isin = subset['isin'].iloc[0]
        
        # Filter dates
        mask = (features['isin'] == isin) & (features['date'] >= start) & (features['date'] <= end)
        case_data = features[mask].copy()
        
        # Get OOS probs
        case_oos = oos[(oos['isin'] == isin) & (oos['date'] >= start) & (oos['date'] <= end)]
        
        if case_data.empty:
            continue
            
        # Merge prob
        case_data = pd.merge(case_data, case_oos[['date', 'prob', 'label', 'forward_return']], on='date', how='left')
        
        # Format for JSON
        prices = []
        for _, r in case_data.iterrows():
            prices.append({
                'date': r['date'].strftime('%Y-%m-%d'),
                'close': r['close'],
                'return': r['return_'] if pd.notna(r['return_']) else None,
                'volume': r['volume'],
                'prob': r['prob'] if pd.notna(r['prob']) else None,
                'is_flagged': bool(r['prob'] >= 0.65) if pd.notna(r['prob']) else False
            })
            
        flags = case_data[case_data['prob'] >= 0.65]
        
        results[name] = {
            'prices': prices,
            'flags_count': len(flags)
        }
        
        # Markdown summary
        md_lines.append(f"## {name} ({case['start']} to {case['end']})")
        if not flags.empty:
            md_lines.append(f"Flagged {len(flags)} times. First flag:")
            first_flag = flags.iloc[0]
            md_lines.append(f"- Date: {first_flag['date'].strftime('%Y-%m-%d')}")
            md_lines.append(f"- Close: {first_flag['close']}")
            md_lines.append(f"- Probability: {first_flag['prob']:.1%}")
            fwd = first_flag.get('forward_return')
            if pd.notna(fwd):
                md_lines.append(f"- Forward 5d Return: {fwd:.1%}")
        else:
            md_lines.append("No flags in this period.")
            # Check max prob
            if not case_oos.empty:
                max_row = case_oos.loc[case_oos['prob'].idxmax()]
                md_lines.append(f"- Max probability was {max_row['prob']:.1%} on {max_row['date'].strftime('%Y-%m-%d')}")
        md_lines.append("\n")
        
    with open(PROCESSED_DIR / "case_studies.json", 'w') as f:
        json.dump(results, f, indent=2)
        
    with open(PROCESSED_DIR / "case_studies.md", 'w') as f:
        f.write("\n".join(md_lines))
        
    print("Done extracting case studies.")

if __name__ == "__main__":
    main()
