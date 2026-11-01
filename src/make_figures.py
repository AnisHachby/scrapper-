import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import PROCESSED_DIR, FIGURES_DIR, FEATURE_COLS

def set_style():
    sns.set_theme(style="whitegrid", palette="muted")
    plt.rcParams.update({
        'font.size': 12,
        'axes.labelsize': 14,
        'axes.titlesize': 16,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 12,
        'figure.titlesize': 18,
        'figure.figsize': (10, 6),
        'figure.dpi': 300
    })

def plot_pr_curve():
    pr_path = PROCESSED_DIR / "precision_recall_curve.csv"
    if not pr_path.exists():
        return
        
    df = pd.read_csv(pr_path)
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    color1 = 'tab:blue'
    ax1.set_xlabel('Probability Threshold')
    ax1.set_ylabel('Precision', color=color1)
    ax1.plot(df['threshold'], df['precision'], color=color1, marker='o', linewidth=2)
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_ylim(0, 1.0)
    ax1.axhline(y=0.70, color='r', linestyle='--', alpha=0.5, label='70% Target')
    
    ax2 = ax1.twinx()
    color2 = 'tab:orange'
    ax2.set_ylabel('Recall', color=color2)
    ax2.plot(df['threshold'], df['recall'], color=color2, marker='s', linestyle='--', linewidth=2)
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(0, 1.0)
    
    plt.title('Precision-Recall Tradeoff Across Thresholds')
    fig.tight_layout()
    plt.savefig(FIGURES_DIR / "fig1_pr_curve.png")
    plt.close()

def plot_feature_importance():
    model_path = PROCESSED_DIR / "model.joblib"
    if not model_path.exists():
        return
        
    import joblib
    model = joblib.load(model_path)
    
    importances = model.feature_importances_
    
    df = pd.DataFrame({
        'Feature': FEATURE_COLS,
        'Importance': importances
    }).sort_values('Importance', ascending=True)
    
    # Rename features for readability
    rename_map = {
        'momentum_5d': 'Momentum (5d)',
        'momentum_20d': 'Momentum (20d)',
        'dist_ytd_high': 'Dist to YTD High',
        'dist_ytd_low': 'Dist to YTD Low',
        'rvol_20d': 'Relative Vol (20d)',
        'amihud': 'Amihud Ratio',
        'value_mad': 'Value (MAD)',
        'volume': 'Volume (Shares)',
        'return_': 'Daily Return',
        'abnormal_return': 'Abnormal Return',
        'block_share': 'Block Vol Share',
        'catalyst_flag': 'AMMC Catalyst'
    }
    df['Feature Name'] = df['Feature'].map(rename_map).fillna(df['Feature'])
    
    plt.figure(figsize=(10, 8))
    sns.barplot(x='Importance', y='Feature Name', data=df, color='tab:blue')
    plt.title('Feature Importance (Random Forest)')
    plt.xlabel('Mean Decrease in Impurity')
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig2_feature_importance.png")
    plt.close()

def plot_drift():
    rob_path = PROCESSED_DIR / "robustness_results.csv"
    if not rob_path.exists():
        return
        
    # Hacky parse of the multi-table csv
    with open(rob_path, 'r') as f:
        content = f.read()
        
    if "--- By Year ---" in content:
        year_block = content.split("--- By Year ---")[1].split("---")[0].strip()
        from io import StringIO
        df = pd.read_csv(StringIO(year_block))
        
        plt.figure(figsize=(8, 5))
        sns.lineplot(x='Year', y='Precision', data=df, marker='o', color='tab:red', linewidth=3, markersize=10)
        plt.title('Temporal Drift: Precision at Threshold 0.65')
        plt.ylim(0, 1.0)
        plt.xticks(df['Year'].astype(int))
        
        for i, row in df.iterrows():
            plt.text(row['Year'], row['Precision'] + 0.05, f"{row['Precision']:.1%}", ha='center', fontsize=12)
            
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "fig5_temporal_drift.png")
        plt.close()

def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    set_style()
    print("Generating figures...")
    plot_pr_curve()
    plot_feature_importance()
    plot_drift()
    print(f"Figures saved to {FIGURES_DIR}")

if __name__ == "__main__":
    main()
