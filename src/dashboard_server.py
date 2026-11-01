# MIGRATED: Thin wrapper - actual implementation in migrated_dashboard.py
import sys
from pathlib import Path

# Ensure the src directory is on the path so relative imports resolve
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from migrated_dashboard import app
