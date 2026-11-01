# SOURCES — Project Data Sources & Open-Sourcing Guide

This document explains what the **BVC Signal vs Noise** project is, where its data comes from, and how to make every source **variable / configurable** so the project can be reused with other stock exchanges and open-sourced safely.

---

## 1. Project Overview

**BVC Signal vs Noise** is a pipeline that distinguishes genuine price movements (signal) from unrepresentative artifacts (noise) on the **Casablanca Stock Exchange (Bourse de Casablanca, BVC)**.

The pipeline has 9 stages:

| Stage | Script | Purpose |
|-------|--------|---------|
| Config & Setup | `src/config.py` | Centralized paths, thresholds, URLs, feature columns |
| Data Collection | `src/fetch_bulletins.py` | Download official BVC daily "Bulletin de la Cote" PDFs |
| Data Collection | `src/fetch_ammc_catalysts.py` | Crawl AMMC issuer press-release digests |
| Parsing | `src/parse_bulletins.py` | Parse PDF bulletins into raw parquet |
| Parsing | `src/parse_ammc_catalysts.py` | Parse HTML AMMC articles into raw CSV |
| Features & Labels | `src/features.py` | Build a 12-feature panel |
| Features & Labels | `src/labels.py` | Label notable price moves |
| Modeling | `src/model.py` | Train a Random Forest with walk-forward CV |
| Evaluation | `src/backtest.py`, `src/baseline_rules.py`, ... | Compare vs baselines, backtest, robustness |
| Explainability | `src/explain_prediction.py`, `src/case_studies.py` | Break down predictions, extract case studies |
| Figures & Reports | `src/make_figures.py`, `dashboard/` | Generate figures and the monitoring dashboard |


## 2. Current Data Sources (Hardcoded)

All source URLs and paths currently live in **`src/config.py`**. This is the single place to edit when repointing the project.

| Source | Script | URL / Path | Notes |
|--------|--------|------------|-------|
| BVC daily bulletins (PDF) | `fetch_bulletins.py` | `https://media.casablanca-bourse.com/sites/default/files/es-auto-upload/fr/BCFR_{YYYYMMDD}.pdf` | One PDF per trading day; archive back to July 2023 |
| AMMC press releases | `fetch_ammc_catalysts.py` | `https://www.ammc.ma/fr/communiques-presse-emetteurs` | Drupal cache limits anonymous paging to ~10 recent entries |
| Boursenews sitemap | `fetch_news.py` | `https://boursenews.ma/sitemap.xml` | Matched to BVC tickers via keyword slugs |
| BVC dividend calendar | `scrape_dividends.py` | `https://www.casablanca-bourse.com/fr/calendrier-des-dividendes` | HTML table scrape |
| Price / transaction data | `features.py` | `data/processed/prices_raw.parquet`, `transactions_raw.parquet` | Produced by the parsers above |
| Market index | `features.py` | `data/processed/indices_raw.parquet` | MASI index returns |

### Ticker → ISIN mapping

`scrape_dividends.py` contains a hardcoded `TICKER_TO_ISIN` map (~45 Casablanca tickers) and a `BVC_NAME_TO_TICKER` map for issuer-name normalization. These are **BVC-specific** and would need to be replaced for another exchange.


## 3. Making Sources Variable (Open-Source Friendly)

To open-source this project so others can run it against a different exchange or data provider, **avoid hardcoding URLs in script bodies**. Instead, read them from environment variables with sensible defaults from `config.py`.

### Recommended pattern

Add a `sources` section to `config.py` that reads environment variables first:

```python
import os
from pathlib import Path

# ── Data sources (overridable via env vars) ──────────────────────────
BULLETIN_URL = os.getenv(
    "BVC_BULLETIN_URL",
    "https://media.casablanca-bourse.com/sites/default/files/es-auto-upload/fr/BCFR_{}.pdf",
)
AMMC_LISTING_URL = os.getenv(
    "BVC_AMMC_LISTING_URL",
    "https://www.ammc.ma/fr/communiques-presse-emetteurs",
)
BOURSENEWS_SITEMAP = os.getenv(
    "BVC_NEWS_SITEMAP",
    "https://boursenews.ma/sitemap.xml",
)
DIVIDEND_CALENDAR_URL = os.getenv(
    "BVC_DIVIDEND_URL",
    "https://www.casablanca-bourse.com/fr/calendrier-des-dividendes",
)
```

Then each fetch script should use the config values directly (they already do for `BULLETIN_URL` and `AMMC_LISTING_URL`; `fetch_news.py` and `scrape_dividends.py` currently inline their URLs and should be updated to import from `config`).

### Example: `.env` file (not committed)

```bash
# Copy .env.example to .env and edit
BVC_BULLETIN_URL=https://media.casablanca-bourse.com/sites/default/files/es-auto-upload/fr/BCFR_{}.pdf
BVC_AMMC_LISTING_URL=https://www.ammc.ma/fr/communiques-presse-emetteurs
BVC_NEWS_SITEMAP=https://boursenews.ma/sitemap.xml
BVC_DIVIDEND_URL=https://www.casablanca-bourse.com/fr/calendrier-des-dividendes
FETCH_DELAY=1.2
AMMC_FETCH_DELAY=2.5
```

Provide a `.env.example` in the repo (without secrets) so contributors know which variables exist.


## 4. Steps to Open-Source with Variable Sources

1. **Centralize every URL** in `src/config.py` behind `os.getenv(...)` with the current BVC URL as default.
2. **Update `fetch_news.py` and `scrape_dividends.py`** to read their URLs from `config.py` instead of inlining them.
3. **Add `sources.yaml` (optional)** for contributors who prefer YAML over env vars. `config.py` can load it if present.
4. **Add `.env.example`** documenting all overridable variables.
5. **Add `SOURCES.md`** (this file) and `CONTRIBUTING.md`.
6. **Add `.gitignore`** rules to exclude `data/`, `*.log`, `__pycache__/`, `.env`, `.venv/` (already present).
7. **Add a `LICENSE`** (already present on the remote `origin/main`).
8. **Document required Python version** (currently 3.14) and install command: `pip install -r requirements.txt`.
9. **Add CI** (GitHub Actions) that runs `src/validate.py` and `src/tests/test_validation.py` on every push.

## 5. Source Limitations to Document for Contributors

| Source | Limitation |
|--------|------------|
| AMMC press releases | Anonymous paging is cached; only ~10 most recent entries reachable — not a multi-year backfill |
| BVC bulletins | Weekend days skipped (no bulletin); 404 = non-trading day |
| Boursenews | Ticker matching is keyword-based on URL slugs; false positives possible for short keywords |
| Dividend calendar | HTML table scrape; site structure changes can break the parser |
| Price data | 6,364 rows (~19%) currently fail OHLC logic validation; `transactions_raw.parquet` may be missing |

## 6. Attribution

This project was developed as a PFE (final-year project) at Capital Trust Securities, focused on the Casablanca Stock Exchange (BVC). When reusing or adapting for another exchange, please:

- Replace the BVC-specific ticker/ISIN maps with your target exchange's mappings.
- Update the fetch scripts to match your data providers' URL patterns and HTML/PDF structure.
- Recalibrate label thresholds (`MOVE_THRESHOLD`, `CONFIRM_THRESHOLD`, `HORIZON_DAYS` in `config.py`) for your market's volatility regime.

## 7. Quick Start with Custom Sources

```bash
# 1. Clone
git clone https://github.com/AnisHachby/scrapper-.git
cd scrapper-

# 2. Create env with your sources
cp .env.example .env
# edit .env with your own URLs

# 3. Install
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 4. Run pipeline with your sources
python src/fetch_bulletins.py
python src/fetch_ammc_catalysts.py
python src/parse_bulletins.py
python src/parse_ammc_catalysts.py
python src/features.py
python src/labels.py
python src/model.py
```
