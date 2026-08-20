"""
c3_10_ablation_study.py
========================
Post-hoc exploratory analysis (EXP-036)
Ablation study to identify minimum viable FRI.

NOT pre-registered -- clearly labelled exploratory.
OSF amendment D-013 documents this addition.

Key findings:
  f_forecast_revision: 90.9% of model value
  f_current_rrp: 20.5% of model value
  Minimum viable FRI: 6 features = 100.4% of full F1

Input:  data/processed/X_train.csv
        data/processed/X_test.csv
        data/processed/y_train.csv
        data/processed/y_test.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/q15_ablation_study.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import pickle
import warnings
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import f1_score
from xgboost import XGBClassifier
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c3_10_ablation_study")
warnings.filterwarnings("ignore")

THRESHOLD = 0.8006

def main():
    logger.info("=" * 60)
    logger.info("c3_10_ablation_study.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("POST-HOC EXPLORATORY -- not pre-registered")
    logger.info("=" * 60)

    X_train = pd.read_csv(PROCESSED_DIR / "X_train.csv")
    X_test  = pd.read_csv(PROCESSED_DIR / "X_test.csv")
    y_train = pd.read_csv(PROCESSED_DIR / "y_train.csv").values.ravel()
    y_test  = pd.read_csv(PROCESSED_DIR / "y_test.csv").values.ravel()

    feature_cols = list(X_train.columns)

    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        model = pickle.load(f)
    params = model.get_params()

    # Full model
    full_proba = model.predict_proba(X_test.values)[:, 1]
    full_f1    = f1_score(y_test, (full_proba >= THRESHOLD).astype(int),
                          zero_division=0)
    logger.info(f"Full model F1: {full_f1:.4f}")

    results = []

    # Drop one feature at a time
    for drop_feat in feature_cols:
        remaining = [f for f in feature_cols if f != drop_feat]
        m = XGBClassifier(**params)
        m.fit(X_train[remaining].values, y_train)
        proba = m.predict_proba(X_test[remaining].values)[:, 1]
        f1    = f1_score(y_test, (proba >= THRESHOLD).astype(int),
                         zero_division=0)
        lost  = full_f1 - f1
        pct   = lost / full_f1 * 100
        results.append({
            "analysis":    "drop_one",
            "feature":     drop_feat,
            "f1":          round(f1, 4),
            "f1_lost":     round(lost, 4),
            "pct_lost":    round(pct, 1),
            "n_features":  len(remaining),
        })
        logger.info(f"Drop {drop_feat}: F1={f1:.4f} lost={pct:+.1f}%")

    # Top N features by importance
    importances = model.feature_importances_
    feat_imp = sorted(zip(feature_cols, importances), key=lambda x: -x[1])

    for n in range(1, 11):
        top_n = [f for f, _ in feat_imp[:n]]
        m = XGBClassifier(**params)
        m.fit(X_train[top_n].values, y_train)
        proba = m.predict_proba(X_test[top_n].values)[:, 1]
        f1    = f1_score(y_test, (proba >= THRESHOLD).astype(int),
                         zero_division=0)
        pct_full = f1 / full_f1 * 100
        results.append({
            "analysis":    "top_n",
            "feature":     str(top_n),
            "f1":          round(f1, 4),
            "f1_lost":     round(full_f1 - f1, 4),
            "pct_lost":    round(100 - pct_full, 1),
            "n_features":  n,
        })
        logger.info(f"Top {n}: F1={f1:.4f} ({pct_full:.1f}% of full)")

    df = pd.DataFrame(results)
    output = TABLES_DIR / "q15_ablation_study.csv"
    df.to_csv(output, index=False)

    logger.info("=" * 60)
    logger.info("ABLATION RESULTS")
    drop_results = df[df["analysis"] == "drop_one"].sort_values(
        "pct_lost", ascending=False)
    logger.info("Most critical features:")
    for _, row in drop_results.head(3).iterrows():
        logger.info(f"  {row['feature']}: {row['pct_lost']:+.1f}% F1 lost")
    logger.info(f"Saved: {output}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
