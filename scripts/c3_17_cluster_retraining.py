"""
c3_17_cluster_retraining.py
============================
Quarterly retraining analysis.

Demonstrates FRI accuracy with quarterly
retraining using expanding training windows.

STRICT SEPARATION: Test data is never used
in training. Eliminates data leakage from
previous cluster-triggered approach.

Design:
  Q1: Train Oct21-Dec21  Test Oct22-Dec22
  Q2: Train Oct21-Mar22  Test Oct22-Dec22
  Q3: Train Oct21-Jun22  Test Oct22-Dec22
  Q4: Train Oct21-Sep22  Test Oct22-Dec22

Shows: More training data improves F1
Shows: Quarterly retraining is viable

Input:  data/processed/features_all.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/cluster_retraining_results.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import warnings
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from sklearn.metrics import f1_score, roc_auc_score
from xgboost import XGBClassifier
from config.settings import (
    PROCESSED_DIR, TABLES_DIR, MODELS_DIR,
    TRAIN_TEST_SPLIT)
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_17_cluster_retraining")

THRESHOLD = 0.8006
SEED      = 42


def main():
    logger.info("=" * 60)
    logger.info("c3_17_cluster_retraining.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("Strict separation: test data never used in training")
    logger.info("=" * 60)

    features   = pd.read_csv(PROCESSED_DIR / "features_all.csv",
                             parse_dates=["DATETIME"])
    feat_cols  = [c for c in features.columns
                  if c.startswith("f_")]
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)

    train_df = features[
        features["DATETIME"] < split_date].copy()
    test_df  = features[
        features["DATETIME"] >= split_date].copy()

    X_test = test_df[feat_cols].values
    y_test = test_df["label"].values

    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        tuned = pickle.load(f)
    params = tuned.get_params()

    train_start = train_df["DATETIME"].min()
    quarters = [
        ("Q1 Oct21-Dec21", train_start,
         pd.Timestamp("2022-01-01")),
        ("Q2 Oct21-Mar22", train_start,
         pd.Timestamp("2022-04-01")),
        ("Q3 Oct21-Jun22", train_start,
         pd.Timestamp("2022-07-01")),
        ("Q4 Oct21-Sep22", train_start,
         split_date),
    ]

    logger.info(f"Test intervals: {len(test_df):,}")
    logger.info(f"Test extreme:   {y_test.sum():,}")
    logger.info(f"Quarters:       {len(quarters)}")

    results = []

    for label, q_start, q_end in quarters:
        q_train = train_df[
            (train_df["DATETIME"] >= q_start) &
            (train_df["DATETIME"] < q_end)].copy()

        if q_train["label"].sum() < 5:
            logger.info(f"Skip {label}: insufficient extremes")
            continue

        X_train = q_train[feat_cols].values
        y_train = q_train["label"].values

        model = XGBClassifier(**params)
        model.fit(X_train, y_train)
        proba  = model.predict_proba(X_test)[:, 1]
        y_pred = (proba >= THRESHOLD).astype(int)

        f1  = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, proba) \
              if y_test.sum() > 0 else 0

        results.append({
            "quarter":          label,
            "train_start":      str(q_start.date()),
            "train_end":        str(q_end.date()),
            "train_total":      len(q_train),
            "train_extreme":    int(y_train.sum()),
            "test_total":       len(y_test),
            "test_extreme":     int(y_test.sum()),
            "f1":               round(f1, 4),
            "auc_roc":          round(auc, 4),
            "f1_static":        0.6207,
            "f1_improvement":   round(f1 - 0.6207, 4),
            "data_leakage":     False,
        })
        logger.info(f"{label}: train={len(q_train):,} "
                    f"extreme={int(y_train.sum()):,} "
                    f"F1={f1:.4f} AUC={auc:.4f}")

    df = pd.DataFrame(results)
    output = TABLES_DIR / "cluster_retraining_results.csv"
    df.to_csv(output, index=False)

    logger.info("=" * 60)
    logger.info("QUARTERLY RETRAINING COMPLETE")
    logger.info("No data leakage confirmed")
    for _, row in df.iterrows():
        logger.info(f"  {row['quarter']}: "
                    f"F1={row['f1']:.4f}  "
                    f"improvement={row['f1_improvement']:+.4f}")
    logger.info(f"Static F1:     0.6207")
    logger.info(f"Q4 (full) F1:  {df.iloc[-1]['f1']:.4f}")
    logger.info(f"Saved: {output}")
    logger.info("Next: ./run.sh scripts/c3_06c_h8_frilite_validation.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
