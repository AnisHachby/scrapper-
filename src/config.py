"""Centralized configuration for the BVC signal/noise pipeline.

Every script imports paths, thresholds, and column lists from here.
Nothing is hardcoded in individual modules.
"""

from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FIGURES_DIR = PROCESSED_DIR / "figures"
REPORTS_DIR = ROOT_DIR / "reports"

BULLETIN_DIR = RAW_DIR / "bulletins"
AMMC_DIR = RAW_DIR / "ammc"

# ── BVC bulletin URL pattern ─────────────────────────────────────────────────
# Public daily "Bulletin de la Cote" PDFs, archive back to July 2023.
# Format placeholder: YYYYMMDD
BULLETIN_URL = (
    "https://media.casablanca-bourse.com"
    "/sites/default/files/es-auto-upload/fr/BCFR_{}.pdf"
)

# ── AMMC catalyst URL ────────────────────────────────────────────────────────
AMMC_BASE = "https://www.ammc.ma"
AMMC_LISTING_URL = AMMC_BASE + "/fr/communiques-presse-emetteurs"

# ── Fetch settings ───────────────────────────────────────────────────────────
FETCH_DELAY = 1.2          # seconds between HTTP requests (BVC)
AMMC_FETCH_DELAY = 2.5     # seconds between HTTP requests (AMMC)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# ── ISIN pattern ─────────────────────────────────────────────────────────────
ISIN_PATTERN = r"MA[0-9A-Z]{10}"

# ── Feature engineering ──────────────────────────────────────────────────────
ROLLING_WINDOW = 20        # days for RVOL and momentum
CATALYST_WINDOW_DAYS = 2   # match catalysts within +/- this many days
RETURN_ARTIFACT_CAP = 0.15 # |return| above this treated as parsing error

# ── Labeling ─────────────────────────────────────────────────────────────────
MOVE_THRESHOLD = 0.03      # |return| >= 3% to be a "notable move"
CONFIRM_THRESHOLD = 0.02   # forward cumulative return >= 2% same direction
HORIZON_DAYS = 5           # forward look window for confirmation

# ── Model hyperparameters ────────────────────────────────────────────────────
N_ESTIMATORS = 300
MAX_DEPTH = 6
MIN_SAMPLES_LEAF = 10
N_SPLITS = 5               # TimeSeriesSplit folds
MIN_POSITIVE_PER_FOLD = 5  # skip folds with fewer positive labels
MIN_FLAGGED = 10           # minimum flags for a threshold to be considered

# ── Feature columns (single source of truth) ─────────────────────────────────
FEATURE_COLS = [
    "return_",             # trailing underscore to avoid Python keyword
    "abnormal_return",
    "momentum_5d",
    "momentum_20d",
    "volume",
    "value_mad",
    "block_share",
    "rvol_20d",
    "amihud",
    "dist_ytd_high",
    "dist_ytd_low",
    "catalyst_flag",
    "news_count_3d",
    "news_count_7d",
    "catalyst_sentiment_3d",
    "ofi_1d",
    "directional_rvol",
]

# ── Threshold sweep for precision-recall curve ───────────────────────────────
PR_THRESHOLDS = [round(t / 100, 2) for t in range(5, 100, 5)]

# ── Backtest thresholds to report ────────────────────────────────────────────
REPORT_THRESHOLDS = [0.55, 0.65, 0.70, 0.80]

# ── Robustness: alternative label definitions ────────────────────────────────
ROBUSTNESS_LABEL_DEFS = [
    {"move": 0.02, "confirm": 0.01, "horizon": 5},
    {"move": 0.02, "confirm": 0.02, "horizon": 5},
    {"move": 0.03, "confirm": 0.01, "horizon": 5},
    {"move": 0.03, "confirm": 0.02, "horizon": 5},   # baseline
    {"move": 0.04, "confirm": 0.02, "horizon": 5},
    {"move": 0.05, "confirm": 0.03, "horizon": 5},
]

# ── Case studies ─────────────────────────────────────────────────────────────
CASE_STUDIES = [
    {"name": "IB MAROC", "start": "2025-06-01", "end": "2025-07-31"},
    {"name": "STROC INDUSTRIE", "start": "2025-06-01", "end": "2025-06-30"},
    {"name": "BALIMA", "start": "2024-06-01", "end": "2024-06-30"},
    {"name": "LESIEUR CRISTAL", "start": "2025-07-01", "end": "2025-07-08"},
]
