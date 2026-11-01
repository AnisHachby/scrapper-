"""
Exactitude (Accuracy) Calculator for BVC Signal vs Noise Model

Calculates various accuracy metrics for model predictions and data quality.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import PROCESSED_DIR


@dataclass
class AccuracyMetrics:
    """Container for accuracy metrics."""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    specificity: float
    false_positive_rate: float
    true_positive_rate: float
    flagged_count: int
    total_positives: int
    total_samples: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'accuracy': self.accuracy,
            'specificity': self.specificity,
            'false_positive_rate': self.false_positive_rate,
            'true_positive_rate': self.true_positive_rate,
            'flagged_count': self.flagged_count,
            'total_positives': self.total_positives,
            'total_samples': self.total_samples
        }
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"Precision: {self.precision:.2%} | "
            f"Recall: {self.recall:.2%} | "
            f"F1: {self.f1_score:.2%} | "
            f"Accuracy: {self.accuracy:.2%}\\n"
            f"Specificity: {self.specificity:.2%} | "
            f"FPR: {self.false_positive_rate:.2%} | "
            f"TPR: {self.true_positive_rate:.2%}\\n"
            f"Flagged: {self.flagged_count}/{self.total_samples} "
            f"(Positives: {self.total_positives})"
        )


class ExactitudeCalculator:
    """
    Calculates exactitude (accuracy) metrics for model predictions.
    
    Supports:
    - Binary classification metrics
    - Threshold-based analysis
    - Data quality validation
    - Comparison across different thresholds
    """
    
    def __init__(self, oos_path: Optional[Path] = None):
        """Initialize calculator."""
        self.oos_path = oos_path or (PROCESSED_DIR / "oos_predictions.parquet")
        self.oos_data: Optional[pd.DataFrame] = None
        
    def load_data(self) -> pd.DataFrame:
        """Load OOS predictions data."""
        if not self.oos_path.exists():
            raise FileNotFoundError(f"OOS predictions not found: {self.oos_path}")
        self.oos_data = pd.read_parquet(self.oos_path)
        return self.oos_data
    def calculate_metrics_at_threshold(self, threshold: float, y_true: Optional[pd.Series] = None, y_pred: Optional[pd.Series] = None, y_prob: Optional[pd.Series] = None) -> AccuracyMetrics:
        """Calculate accuracy metrics at a specific threshold."""
        if self.oos_data is None:
            self.load_data()
        if y_true is None:
            y_true = self.oos_data['label']
        if y_prob is None:
            y_prob = self.oos_data['prob']
        y_pred = (y_prob >= threshold).astype(int)
        tp = ((y_pred == 1) & (y_true == 1)).sum()
        tn = ((y_pred == 0) & (y_true == 0)).sum()
        fp = ((y_pred == 1) & (y_true == 0)).sum()
        fn = ((y_pred == 0) & (y_true == 1)).sum()
        total = len(y_true)
        flagged = y_pred.sum()
        positives = y_true.sum()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        accuracy = (tp + tn) / total if total > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return AccuracyMetrics(precision=precision, recall=recall, f1_score=f1, accuracy=accuracy, specificity=specificity, false_positive_rate=fpr, true_positive_rate=tpr, flagged_count=int(flagged), total_positives=int(positives), total_samples=int(total))
    def compare_thresholds(self, thresholds: List[float], min_flagged: int = 10) -> pd.DataFrame:
        """Compare metrics across multiple thresholds."""
        if self.oos_data is None:
            self.load_data()
        results = []
        for t in thresholds:
            metrics = self.calculate_metrics_at_threshold(t)
            status = "OK" if metrics.flagged_count >= min_flagged else "LOW"
            results.append({'threshold': t, 'flagged': metrics.flagged_count, 'precision': metrics.precision, 'recall': metrics.recall, 'f1': metrics.f1_score, 'accuracy': metrics.accuracy, 'status': status})
        return pd.DataFrame(results)
    def calculate_data_quality_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate data quality metrics."""
        metrics = {'total_rows': len(df), 'total_columns': len(df.columns), 'missing_values': int(df.isna().sum().sum()), 'missing_percentage': (df.isna().sum().sum() / (len(df) * len(df.columns))) * 100, 'duplicate_rows': int(df.duplicated().sum()), 'infinite_values': int(np.isinf(df.select_dtypes(include=[np.number])).sum().sum()), 'columns_with_missing': df.columns[df.isna().any()].tolist()}
        completeness = {}
        for col in df.columns:
            non_null = df[col].notna().sum()
            completeness[col] = (non_null / len(df)) * 100 if len(df) > 0 else 0
        metrics['column_completeness'] = completeness
        return metrics
    def print_report(self, threshold: float = 0.65):
        """Print a comprehensive accuracy report."""
        if self.oos_data is None:
            self.load_data()
        print("\n" + "="*70)
        print("EXACTITUDE (ACCURACY) REPORT")
        print("="*70)
        metrics = self.calculate_metrics_at_threshold(threshold)
        print(f"\nMetrics at threshold {threshold:.2f}:")
        print("-" * 70)
        print(metrics)
        thresholds = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
        print(f"\nThreshold Comparison (min 10 flags):")
        print("-" * 70)
        comparison = self.compare_thresholds(thresholds)
        print(comparison.to_string(index=False))
        print(f"\nData Quality Metrics:")
        print("-" * 70)
        quality = self.calculate_data_quality_metrics(self.oos_data)
        print(f"Total rows: {quality['total_rows']:,}")
        print(f"Total columns: {quality['total_columns']}")
        print(f"Missing values: {quality['missing_values']:,} ({quality['missing_percentage']:.2f}%)")
        print(f"Duplicate rows: {quality['duplicate_rows']:,}")
        print(f"Infinite values: {quality['infinite_values']:,}")
        if quality['columns_with_missing']:
            print(f"\nColumns with missing: {', '.join(quality['columns_with_missing'][:5])}")
        print("\n" + "="*70)

def calculate_model_exactitude(oos_path: Optional[Path] = None) -> AccuracyMetrics:
    """Convenience function to calculate model accuracy."""
    calculator = ExactitudeCalculator(oos_path)
    return calculator.calculate_metrics_at_threshold(0.65)

def validate_data_exactitude(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """Validate data exactitude and return errors/warnings."""
    calculator = ExactitudeCalculator()
    quality = calculator.calculate_data_quality_metrics(df)
    errors = []
    warnings = []
    if quality['missing_percentage'] > 20:
        errors.append(f"High missing data: {quality['missing_percentage']:.1f}%")
    elif quality['missing_percentage'] > 10:
        warnings.append(f"Moderate missing data: {quality['missing_percentage']:.1f}%")
    if quality['duplicate_rows'] > 0:
        warnings.append(f"Duplicate rows: {quality['duplicate_rows']}")
    if quality['infinite_values'] > 0:
        errors.append(f"Infinite values: {quality['infinite_values']}")
    for col, completeness in quality['column_completeness'].items():
        if completeness < 50:
            errors.append(f"Column '{col}' is {completeness:.1f}% complete")
        elif completeness < 80:
            warnings.append(f"Column '{col}' is {completeness:.1f}% complete")
    return errors, warnings

if __name__ == "__main__":
    try:
        calculator = ExactitudeCalculator()
        calculator.print_report(threshold=0.65)
        print("\n\n" + "="*70)
        print("DATA EXACTITUDE VALIDATION")
        print("="*70)
        if calculator.oos_data is not None:
            errors, warnings = validate_data_exactitude(calculator.oos_data)
            if errors:
                print("\nERRORS:")
                for e in errors:
                    print(f"  [X] {e}")
            if warnings:
                print("\nWARNINGS:")
                for w in warnings:
                    print(f"  [!] {w}")
            if not errors and not warnings:
                print("\n[OK] All data quality checks passed!")
    except FileNotFoundError as e:
        print(f"\n[X] Error: {e}")
        print("Please run the model first: py src/model.py")
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
