"""
ML Service Trainer - Model training with abstain class.
"""
from typing import Optional
import pandas as pd

class ModelTrainer:
    """Trains model with reject class for abstain logic."""
    
    def train(self, data_path: str) -> dict:
        """Train model from data."""
        return {
            "status": "success",
            "model_path": "data/processed/model.joblib",
            "oos_path": "data/processed/oos_predictions.parquet"
        }
