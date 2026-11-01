"""
Worker Service Tasks - Background jobs for scraping and maintenance.
"""
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parent.parent.parent.parent / "project-pfe-repo"
_SRC = _REPO / "src"


def scrape_bvc_bulletins(date: Optional[str] = None) -> dict:
    """Scrape BVC bulletins for a specific date or today."""
    try:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Scraping BVC bulletins for {date}")
        
        script = _SRC / "fetch_bulletins.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"BVC scraping failed: {result.stderr}")
            return {"status": "error", "error": result.stderr}
        
        logger.info(f"BVC scraping completed")
        return {"status": "success", "output": result.stdout}
        
    except subprocess.TimeoutExpired:
        logger.error("BVC scraping timeout")
        return {"status": "timeout"}
    except Exception as e:
        logger.error(f"BVC scraping error: {e}")
        return {"status": "error", "error": str(e)}


def scrape_ammc_catalysts() -> dict:
    """Scrape AMMC press releases and catalysts."""
    try:
        logger.info("Scraping AMMC catalysts")
        
        script = _SRC / "fetch_ammc_catalysts.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"AMMC scraping failed: {result.stderr}")
            return {"status": "error", "error": result.stderr}
        
        logger.info(f"AMMC scraping completed")
        return {"status": "success", "output": result.stdout}
        
    except Exception as e:
        logger.error(f"AMMC scraping error: {e}")
        return {"status": "error", "error": str(e)}


def retrain_model(version: str = "auto") -> dict:
    """Retrain model with latest data."""
    try:
        logger.info(f"Starting model retraining (version: {version})")
        
        steps = [
            ("features.py", 600),
            ("labels.py", 300),
            ("model.py", 900),
            ("backtest.py", 300)
        ]
        
        results = {}
        for step, timeout in steps:
            logger.info(f"Running {step}...")
            script = _SRC / step
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            results[step] = {
                "returncode": result.returncode,
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500] if result.stderr else None
            }
            
            if result.returncode != 0:
                logger.error(f"{step} failed: {result.stderr}")
                break
        
        logger.info(f"Model retraining completed")
        return {
            "status": "completed",
            "results": results,
            "version": version,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Model retraining error: {e}")
        return {"status": "error", "error": str(e)}


def cleanup_old_data(days: int = 90) -> dict:
    """Clean up old intraday data and logs."""
    try:
        logger.info(f"Cleaning up data older than {days} days")
        
        data_dir = _REPO / "data" / "intraday"
        cutoff = datetime.now() - timedelta(days=days)
        
        deleted_files = 0
        if data_dir.exists():
            for file in data_dir.glob("*.csv"):
                try:
                    date_str = file.stem.split("_")[1]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff:
                        file.unlink()
                        deleted_files += 1
                except Exception:
                    continue
        
        logger.info(f"Deleted {deleted_files} old files")
        return {"status": "success", "deleted": deleted_files}
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return {"status": "error", "error": str(e)}
