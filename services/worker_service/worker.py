#!/usr/bin/env python3
"""
Worker Service Entry Point - Runs background tasks with scheduling.
"""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add to path
_WORKER = Path(__file__).resolve().parent
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))

from tasks import (
    scrape_bvc_bulletins,
    scrape_ammc_catalysts,
    retrain_model,
    cleanup_old_data
)


class WorkerScheduler:
    """
    Simple scheduler for background tasks.
    In production, replace with Celery Beat or Prefect.
    """
    
    def __init__(self):
        self.running = False
        self.tasks = {}
    
    def schedule_daily(self, task_func, hour: int, minute: int = 0):
        """Schedule a task to run daily at specific time."""
        self.tasks[task_func.__name__] = {
            "func": task_func,
            "schedule": "daily",
            "hour": hour,
            "minute": minute,
            "last_run": None
        }
    
    def schedule_interval(self, task_func, hours: int):
        """Schedule a task to run every N hours."""
        self.tasks[task_func.__name__] = {
            "func": task_func,
            "schedule": "interval",
            "hours": hours,
            "last_run": None
        }
    
    def should_run(self, task_config: dict) -> bool:
        """Check if task should run now."""
        now = datetime.now()
        last_run = task_config.get("last_run")
        
        if last_run is None:
            return True
        
        if task_config["schedule"] == "daily":
            target = now.replace(hour=task_config["hour"], minute=task_config["minute"], second=0)
            # Run if we passed the target time since last run
            return last_run < target <= now
        
        elif task_config["schedule"] == "interval":
            elapsed = (now - last_run).total_seconds() / 3600
            return elapsed >= task_config["hours"]
        
        return False
    
    def run_pending(self):
        """Run all pending tasks."""
        for name, config in self.tasks.items():
            if self.should_run(config):
                logger.info(f"Running scheduled task: {name}")
                try:
                    result = config["func"]()
                    logger.info(f"Task {name} completed: {result.get('status', 'unknown')}")
                except Exception as e:
                    logger.error(f"Task {name} failed: {e}")
                
                self.tasks[name]["last_run"] = datetime.now()
    
    def start(self):
        """Start the scheduler loop."""
        self.running = True
        logger.info("Worker scheduler started")
        
        # Configure tasks
        self.schedule_daily(scrape_bvc_bulletins, hour=8, minute=0)  # Morning scrape
        self.schedule_daily(scrape_ammc_catalysts, hour=8, minute=30)  # Afternoon scrape
        self.schedule_interval(cleanup_old_data, hours=24)  # Daily cleanup
        
        # Run loop
        while self.running:
            try:
                self.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Worker shutting down...")
                self.running = False
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)


def main():
    """Run worker with scheduler."""
    scheduler = WorkerScheduler()
    scheduler.start()


if __name__ == "__main__":
    main()
