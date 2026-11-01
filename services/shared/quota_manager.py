"""
Quota management to prevent model hallucination under quota pressure.
Enforces daily signal quotas and tracks usage per user/IP.
"""
import time
from datetime import datetime, date
from typing import Optional, Dict
from collections import defaultdict
import threading


class QuotaManager:
    """
    Thread-safe quota manager that tracks daily signal allocations.
    Prevents quota-driven hallucination by refusing requests after limit.
    """
    
    def __init__(self, daily_quota: int = 10):
        self.daily_quota = daily_quota
        self._usage: Dict[str, Dict[str, int]] = defaultdict(lambda: {"date": "", "count": 0})
        self._lock = threading.Lock()
    
    def _get_key(self, user_id: Optional[str] = None, ip: Optional[str] = None) -> str:
        """Generate unique key for quota tracking."""
        return user_id or ip or "global"
    
    def _reset_if_new_day(self, key: str):
        """Reset quota counter if it's a new day."""
        today = str(date.today())
        if self._usage[key]["date"] != today:
            self._usage[key] = {"date": today, "count": 0}
    
    def check_quota(self, user_id: Optional[str] = None, ip: Optional[str] = None) -> tuple[bool, int]:
        """
        Check if quota is available.
        
        Returns:
            (allowed: bool, remaining: int)
        """
        key = self._get_key(user_id, ip)
        
        with self._lock:
            self._reset_if_new_day(key)
            used = self._usage[key]["count"]
            remaining = max(0, self.daily_quota - used)
            return remaining > 0, remaining
    
    def consume(self, user_id: Optional[str] = None, ip: Optional[str] = None) -> int:
        """
        Consume one quota unit. Refuses if quota exhausted.
        
        Returns:
            Remaining quota after consumption
        
        Raises:
            Exception: If quota exhausted
        """
        from fastapi import HTTPException
        
        key = self._get_key(user_id, ip)
        
        with self._lock:
            self._reset_if_new_day(key)
            used = self._usage[key]["count"]
            
            if used >= self.daily_quota:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily signal quota exhausted ({self.daily_quota}/{self.daily_quota}). "
                           f"Quota resets at midnight UTC."
                )
            
            self._usage[key]["count"] += 1
            return self.daily_quota - self._usage[key]["count"]
    
    def get_remaining(self, user_id: Optional[str] = None, ip: Optional[str] = None) -> int:
        """Get remaining quota without consuming."""
        key = self._get_key(user_id, ip)
        
        with self._lock:
            self._reset_if_new_day(key)
            return max(0, self.daily_quota - self._usage[key]["count"])
    
    def reset(self, user_id: Optional[str] = None, ip: Optional[str] = None):
        """Reset quota for a specific user or global."""
        key = self._get_key(user_id, ip)
        with self._lock:
            self._usage[key] = {"date": str(date.today()), "count": 0}


# Global quota instances
# Per-user: 10 signals/day, Per-IP: 50 signals/day (for demo/multiple users)
daily_quota = QuotaManager(daily_quota=10)
ip_quota = QuotaManager(daily_quota=50)
