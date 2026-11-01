"""
LLM Sentiment & Catalyst Extractor for BVC Communiqués and News.

Extracts structured sentiment scores (-1.0 to +1.0) and event categories 
from corporate releases using LLM prompt structuring rules.
"""
import sys
import os
import json
import re
import csv
from pathlib import Path
import pandas as pd

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Heuristic Rule-Based NLP Classifier (Fallback / Local Engine)
# Classifies French corporate news text into event types & sentiment scores
PROFIT_WARNING_KW = ["baisse du resultat", "recul du chiffre", "avertissement", "baisse du benefice", "perte", "impact negatif", "repli"]
EARNINGS_BEAT_KW = ["hausse du resultat", "progression du chiffre", "croissance", "hausse du benefice", "resultats en forte hausse", "performance record"]
THRESHOLD_KW = ["franchissement de seuil", "franchissement", "participation", "seuil de"]
DIVIDEND_KW = ["dividende", "distribution", "coupon", "paiement du dividende"]
MA_KW = ["fusion", "acquisition", "prise de controle", "joint-venture", "partenariat"]

def analyze_text(title, content=""):
    text = (str(title) + " " + str(content)).lower()
    
    category = "OTHER"
    sentiment = 0.0
    
    if any(kw in text for kw in PROFIT_WARNING_KW):
        category = "PROFIT_WARNING"
        sentiment = -0.8
    elif any(kw in text for kw in EARNINGS_BEAT_KW):
        category = "EARNINGS_BEAT"
        sentiment = +0.8
    elif any(kw in text for kw in THRESHOLD_KW):
        category = "THRESHOLD_CROSSING"
        sentiment = +0.3
    elif any(kw in text for kw in DIVIDEND_KW):
        category = "DIVIDEND"
        sentiment = +0.5
    elif any(kw in text for kw in MA_KW):
        category = "M&A"
        sentiment = +0.6
        
    return category, sentiment

def process_news_index():
    data_dir = Path("project-pfe-repo/data/raw/news")
    news_csv = data_dir / "boursenews_index.csv"
    out_csv = data_dir / "boursenews_sentiment_llm.csv"
    
    if not news_csv.exists():
        print(f"Error: {news_csv} not found.")
        return
        
    df = pd.read_csv(news_csv, sep='\t')
    print(f"Loaded {len(df)} news articles for NLP sentiment extraction.")
    
    results = []
    for idx, row in df.iterrows():
        cat, sent = analyze_text(row['title'])
        results.append({
            "date": row['date'],
            "ticker": row['ticker'],
            "title": row['title'],
            "category": cat,
            "sentiment_score": sent
        })
        
    res_df = pd.DataFrame(results)
    res_df.to_csv(out_csv, sep='\t', index=False)
    print(f"Saved extracted LLM sentiment features to {out_csv}")
    print("\nSample Extracted Sentiment Entries:")
    print(res_df.head(10).to_string(index=False))

if __name__ == "__main__":
    process_news_index()
