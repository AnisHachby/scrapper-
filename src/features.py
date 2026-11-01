import sys
import argparse
import re
import unicodedata
from pathlib import Path
import pandas as pd
import numpy as np

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    PROCESSED_DIR, FEATURE_COLS, ROLLING_WINDOW, 
    CATALYST_WINDOW_DAYS, RETURN_ARTIFACT_CAP
)

def normalize_name(name):
    if not isinstance(name, str):
        return ""
    # Remove accents, uppercase
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    return n.upper().strip()

def load_prices(path):
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    
    # Clean and numeric close
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df = df.dropna(subset=['close'])
    df = df[~df['designation'].str.contains(r'- - - -', na=False)]
    
    # Sort and clean
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['isin', 'date']).reset_index(drop=True)
    
    # Calculate return per ISIN
    df['return_'] = df.groupby('isin')['close'].pct_change()
    
    # Cap artifacts
    df.loc[df['return_'].abs() > RETURN_ARTIFACT_CAP, 'return_'] = np.nan
    return df

def load_volume(path):
    if not path.exists():
        return pd.DataFrame(columns=['date', 'isin', 'total_value', 'total_quantity', 'block_share'])
    df = pd.read_parquet(path)
    if df.empty:
        return pd.DataFrame(columns=['date', 'isin', 'total_value', 'total_quantity', 'block_share'])
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Pivot by market
    pivoted = df.pivot_table(
        index=['date', 'isin'], 
        columns='market_type', 
        values=['quantity', 'value'], 
        aggfunc='sum'
    ).fillna(0)
    
    # Flatten columns
    pivoted.columns = [f"{col[1].lower()}_{col[0]}" for col in pivoted.columns]
    pivoted = pivoted.reset_index()
    
    # Ensure columns exist
    if 'central_value' not in pivoted.columns: pivoted['central_value'] = 0
    if 'blocs_value' not in pivoted.columns: pivoted['blocs_value'] = 0
    if 'central_quantity' not in pivoted.columns: pivoted['central_quantity'] = 0
    if 'blocs_quantity' not in pivoted.columns: pivoted['blocs_quantity'] = 0
    
    pivoted['total_value'] = pivoted['central_value'] + pivoted['blocs_value']
    pivoted['total_quantity'] = pivoted['central_quantity'] + pivoted['blocs_quantity']
    pivoted['block_share'] = np.where(pivoted['total_value'] > 0, pivoted['blocs_value'] / pivoted['total_value'], 0)
    
    return pivoted

def load_masi(path):
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df['date'] = pd.to_datetime(df['date'])
    
    df = df[df['index_name'] == 'MASI'].copy()
    
    # Deduplicate: keep first per date
    df = df.drop_duplicates(subset=['date'], keep='first')
    
    df = df.sort_values('date').reset_index(drop=True)
    df['masi_return'] = df['value'].pct_change()
    
    return df[['date', 'masi_return']]

def load_catalysts(path):
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    df['issuer_norm'] = df['issuer'].apply(normalize_name)
    return df

def add_catalyst_flag(panel, catalysts):
    panel['catalyst_flag'] = 0
    if catalysts.empty:
        return panel
        
    for isin, grp in panel.groupby('isin'):
        issuer_name = grp['designation'].iloc[0]
        issuer_norm = normalize_name(issuer_name)
        
        # Simple substring match
        matched_cats = catalysts[catalysts['issuer_norm'].apply(lambda x, norm=issuer_norm: norm in x or x in norm)]
        
        if matched_cats.empty:
            continue
            
        for idx, row in grp.iterrows():
            obs_date = row['date']
            
            # Anti-look-ahead: published ON or BEFORE obs_date
            # Window: within CATALYST_WINDOW_DAYS
            valid_cats = matched_cats[
                (matched_cats['date'] <= obs_date) & 
                (obs_date - matched_cats['date']).dt.days <= CATALYST_WINDOW_DAYS
            ]
            
            if not valid_cats.empty:
                panel.at[idx, 'catalyst_flag'] = 1
                
    return panel

ISIN_TO_NEWS_TICKER = {
    "MA0000012247": "ATW",  # Attijariwafa Bank
    "MA0000011488": "IAM",  # Maroc Telecom (TCO)
    "MA0000011512": "ADH",  # Addoha (IMM)
    "MA0000012015": "ADI",  # Alliances
    "MA0000012205": "TQA",  # Taqa Morocco
    "MA0000012163": "CSU",  # Cosumar (SFA)
    "MA0000011884": "BCP",  # BCP (BAN)
    "MA0000012320": "LHC",  # LafargeHolcim (LH)
    "MA0000010969": "MLE",  # Maroc Leasing
    "MA0000011322": "SNP",  # Snep
    "MA0000011306": "SND",  # Sonasid
    "MA0000011991": "HPS",  # HPS (SPI)
    "MA0000012148": "MUT",  # Mutandis (LSI)
    "MA0000012221": "PORT", # Marsa Maroc
    "MA0000011033": "MNG",  # Managem (MIN)
    "MA0000010621": "WAA",  # Wafa Assurance
    "MA0000011702": "ASN",  # AtlantaSanlam
    "MA0000012049": "RDS",  # Résidences Dar Saada
    "MA0000010019": "BOA",  # Bank of Africa (BMC)
    "MA0000012114": "CIH",  # CIH Bank
    "MA0000010266": "CDM",  # Crédit du Maroc
    "MA0000010530": "CMA",  # Ciments du Maroc
    "MA0000011124": "SAH",  # Sanlam (SAH)
    "MA0000011876": "DWY",  # Dari Couspate
    "MA0000011009": "LES",  # Lesieur Cristal (DIS)
    "MA0000012304": "IMO",  # Immorente
    "MA0000010639": "BAL",  # Balima
    "MA0000011793": "STR",  # Stroc Industrie
    "MA0000011421": "NXT",  # Nexans Maroc
    "MA0000010092": "ATH",  # Auto Hall
    "MA0000010241": "ALM",  # Aluminium du Maroc
    "MA0000011504": "RIS",  # Risma
    "MA0000010159": "FBR",  # Fenie Brossette
    "MA0000010464": "IB",   # IB Maroc
    "MA0000011868": "JET",  # Jet Contractors
    "MA0000011637": "M2M",  # M2M Group
    "MA0000011942": "MOX",  # Maghreb Oxygène
    "MA0000010589": "SNA",  # Sanam
    "MA0000011967": "DHO",  # Doha
}

def add_news_features(panel, news_df):
    panel['news_count_3d'] = 0
    panel['news_count_7d'] = 0
    panel['catalyst_sentiment_3d'] = 0.0
    if news_df.empty:
        return panel
        
    news_df['date'] = pd.to_datetime(news_df['date'])
    if 'sentiment_score' not in news_df.columns:
        news_df['sentiment_score'] = 0.0
        
    for isin, grp in panel.groupby('isin'):
        ticker = ISIN_TO_NEWS_TICKER.get(isin)
        if not ticker:
            tokens = str(grp['designation'].iloc[0]).split()
            for i, t in enumerate(tokens):
                if t in ['C', 'F', 'V'] and i > 0:
                    cand = tokens[i-1]
                    if cand.isupper() and len(cand) >= 2:
                        ticker = cand
                        break
                        
        if not ticker:
            continue
            
        ticker_news = news_df[news_df['ticker'] == ticker]
        if ticker_news.empty:
            continue
            
        for idx, row in grp.iterrows():
            obs_date = row['date']
            
            # Slices using pandas datetime arithmetic with correct operator precedence
            n_3d = ticker_news[
                (ticker_news['date'] <= obs_date) & 
                ((obs_date - ticker_news['date']).dt.days <= 3)
            ]
            n_7d = ticker_news[
                (ticker_news['date'] <= obs_date) & 
                ((obs_date - ticker_news['date']).dt.days <= 7)
            ]
            
            panel.at[idx, 'news_count_3d'] = len(n_3d)
            panel.at[idx, 'news_count_7d'] = len(n_7d)
            if not n_3d.empty:
                panel.at[idx, 'catalyst_sentiment_3d'] = float(n_3d['sentiment_score'].mean())
            
    return panel

def build_features(data_dir):
    prices = load_prices(data_dir / "prices_raw.parquet")
    volume = load_volume(data_dir / "transactions_raw.parquet")
    masi = load_masi(data_dir / "indices_raw.parquet")
    catalysts = load_catalysts(data_dir / "catalysts_raw.csv")
    
    if prices.empty:
        print("No price data to build features from.")
        return pd.DataFrame()
        
    # Merge
    merged = pd.merge(prices, volume, on=['date', 'isin'], how='left')
    merged = pd.merge(merged, masi, on=['date'], how='left')
    
    merged['total_value'] = merged['total_value'].fillna(0)
    merged['total_quantity'] = merged['total_quantity'].fillna(0)
    merged['block_share'] = merged['block_share'].fillna(0)
    
    # Compute features
    merged = merged.sort_values(['isin', 'date'])
    
    # Returns and distance
    merged['abnormal_return'] = merged['return_'] - merged['masi_return'].fillna(0)
    
    # Rolling features per ISIN
    def rolling_feats(g):
        isin_val = g.name
        g['momentum_5d'] = (1 + g['return_'].fillna(0)).rolling(5).apply(np.prod, raw=True) - 1
        g['momentum_20d'] = (1 + g['return_'].fillna(0)).rolling(20).apply(np.prod, raw=True) - 1
        g['rvol_20d'] = g['total_value'] / (g['total_value'].rolling(ROLLING_WINDOW, min_periods=1).mean().replace(0, np.nan))
        
        ytd_high = g['close'].rolling(252, min_periods=1).max()
        ytd_low = g['close'].rolling(252, min_periods=1).min()
        g['dist_ytd_high'] = g['close'] / ytd_high - 1
        g['dist_ytd_low'] = np.where(ytd_low > 0, g['close'] / ytd_low - 1, 0.0)
        g['isin'] = isin_val
        return g
        
    merged = merged.groupby('isin', group_keys=False).apply(rolling_feats)
    
    # Amihud (value_mad is total_value)
    merged['value_mad'] = merged['total_value']
    merged['volume'] = merged['total_quantity']
    
    # avoid div by 0
    safe_val = np.where(merged['value_mad'] > 0, merged['value_mad'] / 1e6, np.nan)
    merged['amihud'] = merged['return_'].abs() / safe_val
    
    # Catalysts
    merged = add_catalyst_flag(merged, catalysts)
    
    # News features from Boursenews (LLM Sentiment)
    sentiment_path = data_dir.parent / "raw" / "news" / "boursenews_sentiment_llm.csv"
    news_path = data_dir.parent / "raw" / "news" / "boursenews_index.csv"
    if sentiment_path.exists():
        news_df = pd.read_csv(sentiment_path, sep='\t')
    elif news_path.exists():
        news_df = pd.read_csv(news_path, sep='\t')
    else:
        news_df = pd.DataFrame()
    merged = add_news_features(merged, news_df)
    
    # Select columns
    keep_cols = ['date', 'isin', 'designation', 'close', 'reference_price'] + FEATURE_COLS
    
    # Ensure all exist
    for col in keep_cols:
        if col not in merged.columns:
            merged[col] = np.nan
            
    return merged[keep_cols]

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    print("Building features...")
    features = build_features(PROCESSED_DIR)
    
    if not features.empty:
        out_path = PROCESSED_DIR / "features.parquet"
        features.to_parquet(out_path)
        print(f"Saved {len(features)} rows to {out_path}")
        
if __name__ == "__main__":
    main()
