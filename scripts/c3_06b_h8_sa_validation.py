"""
c3_06b_h8_sa_validation.py
===========================
H8 Cross-region validation -- South Australia.

Trains FRI on NSW1 VIC1 QLD1 TAS1.
Tests on SA1 (60%+ renewable penetration).
Applies NEM threshold 0.8006 -- no retraining.
H8 passes if F1 difference <= 0.15.

Input:  data/processed/features_all.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/c3_06b_h8_sa_validation_results.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
Deviation: D-014 (SA substituted for ERCOT/GB)
           D-023 (threshold corrected to 0.8006)
"""
import sys
import pickle
import warnings
import numpy as np
import pandas as pd
from sklearn.metrics import (
    f1_score, roc_auc_score, confusion_matrix)
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_06b_h8_sa_validation")

NEM_F1        = 0.6207
NEM_THRESHOLD = 0.8006
H8_MAX_DIFF   = 0.15
TRAIN_REGIONS = ["NSW1", "VIC1", "QLD1", "TAS1"]
TEST_REGION   = "SA1"

FEATURES = [
    "f_current_rrp",
    "f_forecast_revision",
    "f_rolling_max_30min",
    "f_rolling_mean_30min",
    "f_price_change_60min",
    "f_day_of_week",
    "f_consecutive_high",
    "f_hour_of_day",
    "f_price_change_30min",
    "f_is_peak_hour",
]


def main():
    logger.info("=" * 60)
    logger.info("c3_06b_h8_sa_validation.py started")
    logger.info("H8 Cross-region validation -- South Australia")
    logger.info("Train: %s", TRAIN_REGIONS)
    logger.info("Test:  %s", TEST_REGION)
    logger.info("NEM F1=%.4f  threshold=%.4f", NEM_F1, NEM_THRESHOLD)
    logger.info("H8 passes if diff <= %.2f", H8_MAX_DIFF)
    logger.info("=" * 60)

    logger.info("Loading features_all.csv...")
    fa = pd.read_csv(PROCESSED_DIR / "features_all.csv")
    logger.info("Total rows: %d", len(fa))
    logger.info("Regions: %s", sorted(fa["REGIONID"].unique()))

    # SA test partition
    sa = fa[fa["REGIONID"] == TEST_REGION].copy()
    logger.info("SA rows:    %d", len(sa))
    logger.info("SA extreme: %d (%.2f%%)",
                int(sa["label"].sum()),
                100 * sa["label"].mean())

    # check features
    missing = [f for f in FEATURES if f not in sa.columns]
    if missing:
        logger.error("Missing features: %s", missing)
        sys.exit(1)

    # load NEM-trained model
    logger.info("Loading NEM-trained FRI model...")
    model = pickle.load(
        open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb"))
    logger.info("Model loaded: %s", type(model).__name__)

    # apply NEM model to SA -- no retraining
    X = sa[FEATURES].fillna(0)
    y = sa["label"].astype(int)

    logger.info("Applying NEM threshold %.4f to SA data...",
                NEM_THRESHOLD)
    y_prob = model.predict_proba(X)[:, 1]
    y_pred = (y_prob >= NEM_THRESHOLD).astype(int)

    f1      = f1_score(y, y_pred, zero_division=0)
    auc     = roc_auc_score(y, y_prob)
    f1_diff = abs(f1 - NEM_F1)
    h8_pass = f1_diff <= H8_MAX_DIFF

    cm = confusion_matrix(y, y_pred)
    tn, fp, fn, tp = cm.ravel()

    logger.info("")
    logger.info("=" * 60)
    logger.info("H8 SA VALIDATION RESULTS")
    logger.info("=" * 60)
    logger.info("  NEM F1:    %.4f", NEM_F1)
    logger.info("  SA F1:     %.4f", f1)
    logger.info("  F1 diff:   %.4f", f1_diff)
    logger.info("  Threshold: %.4f", H8_MAX_DIFF)
    logger.info("  H8 RESULT: %s", "PASS" if h8_pass else "FAIL")
    logger.info("  AUC:       %.4f", auc)
    logger.info("  TP=%-6d FP=%d", tp, fp)
    logger.info("  FN=%-6d TN=%d", fn, tn)
    logger.info("=" * 60)

    results = pd.DataFrame([{
        "market":             "SA1_cross_region",
        "train_regions":      str(TRAIN_REGIONS),
        "nem_f1":             NEM_F1,
        "sa_f1":              round(f1, 6),
        "sa_auc_roc":         round(auc, 6),
        "f1_difference":      round(f1_diff, 6),
        "h8_tolerance":       H8_MAX_DIFF,
        "optimal_threshold":  NEM_THRESHOLD,
        "train_n":            len(fa[fa["REGIONID"].isin(
                                  TRAIN_REGIONS)]),
        "test_n":             len(sa),
        "test_extreme":       int(y.sum()),
        "passes_h8":          h8_pass,
        "deviation":          "D-014 D-023",
    }])

    out = TABLES_DIR / "c3_06b_h8_sa_validation_results.csv"
    results.to_csv(out, index=False)
    logger.info("Saved: %s", out)
    sys.exit(0)


if __name__ == "__main__":
    main()