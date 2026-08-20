"""
c3_16_rolling_retraining.py
============================
Rolling window retraining analysis.

Demonstrates FRI accuracy maintained through
periodic retraining using a 12-month rolling
training window updated monthly.

This addresses the non-stationarity limitation
of the static single-split model.

Design:
  Month 13 (Oct 2022): Train Nov21-Sep22 Test Oct22
  Month 14 (Nov 2022): Train Dec21-Oct22 Test Nov22
  Month 15 (Dec 2022): Train Jan22-Nov22 Test Dec22

Comparison:
  Static model F1 (single split)
  Rolling model F1 (monthly update)

Input:  data/processed/features_all.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/rolling_retraining_results.csv
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
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_16_rolling_retraining")

THRESHOLD       = 0.8006
WINDOW_MONTHS   = 12
MIN_EXTREME     = 5
SEED            = 42


def main():
    logger.info("=" * 60)
    logger.info("c3_16_rolling_retraining.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Rolling window: {WINDOW_MONTHS} months")
    logger.info(f"Threshold: {THRESHOLD}")
    logger.info("=" * 60)

    features  = pd.read_csv(PROCESSED_DIR / "features_all.csv",
                            parse_dates=["DATETIME"])
    feat_cols = [c for c in features.columns if c.startswith("f_")]

    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        tuned = pickle.load(f)
    params = tuned.get_params()

    features = features.sort_values(
        "DATETIME").reset_index(drop=True)
    features["month"] = features["DATETIME"].dt.to_period("M")
    months = sorted(features["month"].unique())

    logger.info(f"Total months: {len(months)}")
    logger.info(f"Period: {months[0]} to {months[-1]}")

    results = []

    for i in range(WINDOW_MONTHS, len(months)):
        train_months = months[i - WINDOW_MONTHS:i]
        test_month   = months[i]

        train = features[features["month"].isin(train_months)]
        test  = features[features["month"] == test_month]

        if test["label"].sum() < MIN_EXTREME:
            logger.info(f"Skip {test_month}: "
                        f"only {test['label'].sum()} extremes")
            continue

        X_train = train[feat_cols].values
        y_train = train["label"].values
        X_test  = test[feat_cols].values
        y_test  = test["label"].values

        model = XGBClassifier(**params)
        model.fit(X_train, y_train)
        proba  = model.predict_proba(X_test)[:, 1]
        y_pred = (proba >= THRESHOLD).astype(int)

        f1  = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, proba) \
              if y_test.sum() > 0 else 0

        results.append({
            "test_month":       str(test_month),
            "train_start":      str(train_months[0]),
            "train_end":        str(train_months[-1]),
            "train_months":     WINDOW_MONTHS,
            "test_extreme":     int(y_test.sum()),
            "test_total":       len(y_test),
            "f1_rolling":       round(f1, 4),
            "auc_rolling":      round(auc, 4),
            "f1_static":        0.6207,
        })
        logger.info(f"{test_month}: F1={f1:.4f}  AUC={auc:.4f}  "
                    f"extreme={y_test.sum()}/{len(y_test)}")

    df = pd.DataFrame(results)
    output = TABLES_DIR / "rolling_retraining_results.csv"
    df.to_csv(output, index=False)

    mean_f1   = df["f1_rolling"].mean()
    std_f1    = df["f1_rolling"].std()
    static_f1 = 0.6207

    logger.info("=" * 60)
    logger.info("ROLLING RETRAINING COMPLETE")
    logger.info(f"Test months completed:  {len(df)}")
    logger.info(f"Rolling mean F1:        {mean_f1:.4f}")
    logger.info(f"Rolling std F1:         {std_f1:.4f}")
    logger.info(f"Static model F1:        {static_f1:.4f}")
    logger.info(f"Rolling vs static:      {mean_f1 - static_f1:+.4f}")
    logger.info(f"Retraining recommended: monthly")
    logger.info(f"Saved: {output}")
    logger.info("Next: ./run.sh scripts/c3_17_cluster_retraining.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
