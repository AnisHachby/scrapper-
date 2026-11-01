"""
Model registry for versioning and managing multiple model versions.
"""
import joblib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib


class ModelRegistry:
    """
    Manages model versions, metadata, and A/B testing.
    """
    
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.models_dir / "registry.json"
        self._registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load model registry from disk."""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {"models": {}, "active_version": None}
    
    def _save_registry(self):
        """Save registry to disk."""
        with open(self.registry_file, 'w') as f:
            json.dump(self._registry, f, indent=2, default=str)
    
    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of model file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
    
    def register_model(
        self,
        model_path: Path,
        version: str,
        metadata: Dict[str, Any],
        set_active: bool = True
    ) -> str:
        """
        Register a new model version.
        
        Args:
            model_path: Path to model.joblib
            version: Version string (e.g., "v2.1.0")
            metadata: Dict with precision, recall, training_date, etc.
            set_active: Whether to set as active model
        
        Returns:
            version: The registered version string
        """
        model_hash = self._compute_hash(model_path)
        
        self._registry["models"][version] = {
            "hash": model_hash,
            "path": str(model_path),
            "registered_at": datetime.now().isoformat(),
            "metadata": metadata,
            "active": set_active,
        }
        
        if set_active:
            self._registry["active_version"] = version
            # Deactivate others
            for v in self._registry["models"]:
                if v != version:
                    self._registry["models"][v]["active"] = False
        
        self._save_registry()
        return version
    
    def get_active_model(self) -> Optional[Dict[str, Any]]:
        """Get the currently active model."""
        active_ver = self._registry.get("active_version")
        if not active_ver or active_ver not in self._registry["models"]:
            return None
        return self._registry["models"][active_ver]
    
    def load_active_model(self):
        """Load the active model from disk."""
        info = self.get_active_model()
        if not info:
            return None
        return joblib.load(info["path"])
    
    def list_models(self) -> Dict[str, Any]:
        """List all registered models."""
        return self._registry.get("models", {})
    
    def rollback(self, version: str) -> bool:
        """Rollback to a previous model version."""
        if version not in self._registry["models"]:
            return False
        
        for v in self._registry["models"]:
            self._registry["models"][v]["active"] = (v == version)
        
        self._registry["active_version"] = version
        self._save_registry()
        return True
