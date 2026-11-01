"""
Conformal prediction for statistically guaranteed signal quality.
Provides prediction sets with coverage guarantees (e.g., 90% coverage).
"""
import numpy as np
from typing import Tuple, Optional


def conformal_prediction_sets(
    model,
    X_calibration: np.ndarray,
    y_calibration: np.ndarray,
    X_test: np.ndarray,
    alpha: float = 0.1,
    classes: list = [0, 1, 2]  # 0=bruit, 1=signal, 2=reject/abstain
) -> Tuple[np.ndarray, float]:
    """
    Generate conformal prediction sets with (1-alpha) coverage guarantee.
    
    Args:
        model: Classifier with predict_proba method
        X_calibration: Calibration feature matrix (n_calib, n_features)
        y_calibration: Calibration labels (n_calib,)
        X_test: Test feature matrix (n_test, n_features)
        alpha: Miscoverage rate (0.1 = 90% coverage)
        classes: List of class labels
    
    Returns:
        prediction_sets: Array of shape (n_test, len(classes)) with 0/1 membership
        threshold: Calibrated threshold used
    """
    # Get calibration probabilities
    calib_probs = model.predict_proba(X_calibration)
    
    # Handle case where calibration set might not have all classes
    if calib_probs.shape[1] < len(classes):
        full_probs = np.zeros((len(calib_probs), len(classes)))
        full_probs[:, :calib_probs.shape[1]] = calib_probs
        calib_probs = full_probs
    
    # Compute conformity scores: 1 - P(y|x) for true class
    calib_scores = 1.0 - calib_probs[np.arange(len(y_calibration)), y_calibration]
    
    # Get test probabilities
    test_probs = model.predict_proba(X_test)
    if test_probs.shape[1] < len(classes):
        full_test = np.zeros((len(test_probs), len(classes)))
        full_test[:, :test_probs.shape[1]] = test_probs
        test_probs = full_test
    
    # Compute quantile threshold (1-alpha coverage)
    n_calib = len(y_calibration)
    q_level = min(np.ceil((n_calib + 1) * (1 - alpha)) / n_calib, 1.0)
    threshold = np.quantile(calib_scores, q_level, method='higher')
    
    # Build prediction sets: include class if 1 - prob <= threshold
    prediction_sets = (1.0 - test_probs) <= threshold
    
    return prediction_sets, threshold


def conformal_classification(
    model,
    X_calibration: np.ndarray,
    y_calibration: np.ndarray,
    X_test: np.ndarray,
    alpha: float = 0.1
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get conformal class predictions with abstention option.
    
    Returns:
        predictions: Predicted class for each test sample (-1 = abstain)
        confidence: Conformal confidence score
    """
    pred_sets, threshold = conformal_prediction_sets(
        model, X_calibration, y_calibration, X_test, alpha
    )
    
    predictions = []
    confidences = []
    
    for i, pred_set in enumerate(pred_sets):
        n_classes_in_set = pred_set.sum()
        
        if n_classes_in_set == 1:
            # Single class prediction - high confidence
            pred_class = np.argmax(pred_set)
            predictions.append(pred_class)
            confidences.append(1.0 - threshold)
        elif n_classes_in_set == len(pred_set):
            # All classes included - abstain (too uncertain)
            predictions.append(-1)
            confidences.append(0.0)
        else:
            # Multiple classes - pick most probable
            pred_class = np.argmax(pred_set)
            predictions.append(pred_class)
            confidences.append(0.5)
    
    return np.array(predictions), np.array(confidences)


def compute_calibration_curve(
    model,
    X_calibration: np.ndarray,
    y_calibration: np.ndarray,
    n_bins: int = 10
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute reliability curve for probability calibration assessment.
    """
    probs = model.predict_proba(X_calibration)[:, 1]
    
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(probs, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    accuracies = np.zeros(n_bins)
    confidences = np.zeros(n_bins)
    counts = np.zeros(n_bins)
    
    for i in range(len(probs)):
        b = bin_indices[i]
        confidences[b] += probs[i]
        counts[b] += 1
        if y_calibration[i] == 1:
            accuracies[b] += 1
    
    # Avoid division by zero
    nonzero = counts > 0
    accuracies[nonzero] /= counts[nonzero]
    confidences[nonzero] /= counts[nonzero]
    
    return accuracies, confidences
