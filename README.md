# BVC Signal vs Noise Model

This repository contains the code and analysis for my PFE at Capital Trust Securities. The project aims to distinguish genuine price movements (signal) from unrepresentative artifacts (noise) on the Casablanca Stock Exchange.

## Pipeline Overview
The pipeline consists of 9 stages:
1. **Config & Setup**: Centralized configuration (`src/config.py`).
2. **Data Collection**: Fetch official BVC bulletins (`src/fetch_bulletins.py`) and AMMC catalysts (`src/fetch_ammc_catalysts.py`).
3. **Parsing**: Parse PDF bulletins (`src/parse_bulletins.py`) and HTML AMMC articles (`src/parse_ammc_catalysts.py`) into raw parquets and CSVs.
4. **Features & Labels**: Generate a 12-feature panel (`src/features.py`) and label notable moves (`src/labels.py`).
5. **Modeling**: Train a Random Forest with walk-forward CV (`src/model.py`).
6. **Evaluation**: Compare with baselines (`src/baseline_rules.py`), evaluate backtest (`src/backtest.py`), run k-fold comparisons (`src/kfold_comparison.py`), and test robustness (`src/robustness.py`).
7. **Explainability & Case Studies**: Breakdown predictions (`src/explain_prediction.py`) and extract specific case studies (`src/case_studies.py`).
8. **Figures & Reports**: Generate figures (`src/make_figures.py`) and view the dashboard (`dashboard/moniteur_bvc.html`).

## Setup Instructions

```bash
# 1. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the pipeline sequentially
python src/fetch_bulletins.py
python src/fetch_ammc_catalysts.py
python src/parse_bulletins.py
python src/parse_ammc_catalysts.py
python src/features.py
python src/labels.py
python src/model.py
python src/backtest.py
python src/baseline_rules.py
python src/kfold_comparison.py
python src/robustness.py
python src/explain_prediction.py
python src/case_studies.py
python src/make_figures.py
```

## Dashboard
Open `dashboard/moniteur_bvc.html` in your browser.
