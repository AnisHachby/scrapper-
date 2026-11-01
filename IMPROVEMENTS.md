# HOW TO IMPROVE MODEL METRICS

## Current Performance
- Precision: 45.14% (below 50% - worse than random!)
- Recall: 14.90% (missing 85% of true signals)
- F1-Score: 22.40%
- Accuracy: 72.67% (misleading due to class imbalance)

## Root Causes

### 1. SEVERE CLASS IMBALANCE
- Positive rate: Only 5.56% (1,819 out of 32,718)
- Model struggles to learn rare positive patterns
- Majority class (negative) dominates training

### 2. WEAK FEATURE SIGNALS
- Best feature: momentum_20d (correlation = +0.11)
- Most features: correlation < 0.05 (very weak)
- Model cannot distinguish signal from noise

### 3. POOR PROBABILITY CALIBRATION
- Mean probability: 0.478 (almost 50/50)
- Max probability: 0.828 (never very confident)
- Predictions are compressed and uncertain

### 4. SUBOPTIMAL THRESHOLD
- Current: 0.65 (too conservative)
- Optimal F1: 0.45 (but precision drops to 34.7%)

## Improvement Strategies (Ranked by Impact)

### TIER 1: QUICK WINS (2-3 hours) ? +10-15% improvement

1. **Install LightGBM** (5 minutes)
   ```bash
   pip install lightgbm
   ```
   - Better handling of imbalanced data
   - Better probability calibration
   - Faster training

2. **Use Optimal Threshold** (5 minutes)
   - Current: 0.65 ? Precision 45%, Recall 15%
   - Optimal: 0.45 ? Precision 35%, Recall 73% (F1: 47%)
   - Or: 0.55 ? Precision 39%, Recall 43% (F1: 41%)
   
   Update src/config.py:
   ```python
   REPORT_THRESHOLDS = [0.45, 0.55]  # Changed from [0.55, 0.65, 0.70, 0.80]
   ```

3. **Add Interaction Features** (30 minutes)
   Add to src/features.py:
   - rvol_x_momentum = rvol_20d * momentum_5d
   - momentum_ratio = momentum_5d / momentum_20d
   - volume_x_block = volume * block_share

### TIER 2: MEDIUM EFFORT (1-2 days) ? +15-20% improvement

4. **SMOTE Oversampling** (2 hours)
   - Synthetically generate positive examples
   - Balance classes during training
   - Expected: +10-15% precision

5. **Better Features** (1 day)
   - Add lagged returns (t-1, t-2, t-3)
   - Add volatility features (std of returns)
   - Add trend indicators (MA crossovers)
   - Add volume patterns (volume spikes)

6. **Hyperparameter Tuning** (4 hours)
   - Grid search or random search
   - Optimize: n_estimators, max_depth, min_samples_leaf
   - Use cross-validation

### TIER 3: ADVANCED (3-5 days) ? +20-25% improvement

7. **Try XGBoost/LightGBM** (1 day)
   - Better than RandomForest for imbalanced data
   - Built-in handling of class weights
   - Better probability calibration

8. **Ensemble Methods** (2 days)
   - Combine RF + XGBoost + Logistic Regression
   - Voting classifier
   - Stacking

9. **Feature Selection** (1 day)
   - Remove weak features (correlation < 0.03)
   - Keep only predictive features
   - Reduce noise

10. **Relabel with Different Thresholds** (2 days)
    - Current: move=3%, confirm=2%, horizon=5d
    - Try: move=2.5%, confirm=1.5%, horizon=7d
    - More positives = more training data

## Recommended Action Plan

### Week 1: Quick Wins
1. Install LightGBM
2. Update threshold to 0.55
3. Add 5 interaction features
4. Re-run model

Expected: Precision 39%, Recall 43% (F1: 41%)

### Week 2: Medium Improvements
5. Implement SMOTE
6. Add 10 new features
7. Hyperparameter tuning

Expected: Precision 50%, Recall 50% (F1: 50%)

### Week 3-4: Advanced
8. Switch to LightGBM
9. Ensemble models
10. Feature engineering

Expected: Precision 60-65%, Recall 60-65% (F1: 60-65%)

## Implementation

Run these scripts:
- improve_model_v2.py - Threshold optimization (DONE)
- improve_model.py - SMOTE + features (needs fixing)
- Add LightGBM to requirements.txt

## Business Impact

Current (threshold 0.65):
- Flags 514 moves out of 1557 true signals
- 45% precision = 55% false alarms
- Missing 85% of opportunities

Optimal (threshold 0.55):
- Flags 1714 moves out of 1557 true signals
- 39% precision = 61% false alarms
- Catches 43% of opportunities

Target (with improvements):
- Flags 900 moves
- 60% precision = 40% false alarms
- Catches 60% of opportunities
