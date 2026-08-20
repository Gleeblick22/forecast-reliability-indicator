"""
c2_20_rescore_true_dispatchprice.py
======================================
Priority 1: rebuilds the test-set label (y_new) using true
DISPATCHPRICE instead of P5MIN, and re-scores the existing
relabeled classifier (fri_model_relabeled.pkl, unchanged, not
retrained) against this corrected label, to assess whether
AUC/F1/threshold shift meaningfully.

Input:  data/processed/final_leakage_controlled_dataset.csv
        data/processed/true_dispatchprice_test_partition.csv
        results/models/fri_model_relabeled.pkl
Output: results/tables/c2_20_true_dispatchprice_rescore_results.csv
"""
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import f1_score, roc_auc_score, precision_score, recall_score, confusion_matrix, precision_recall_curve
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_20_rescore_true_dispatchprice")

FEATURES = [
    "f_current_rrp", "new_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]
DELTA = 300.0

def main():
    logger.info("=" * 60)
    logger.info("c2_20_rescore_true_dispatchprice.py started")
    logger.info("=" * 60)

    df = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date].copy()

    true_price = pd.read_csv(PROCESSED_DIR / "true_dispatchprice_test_partition.csv", parse_dates=["DATETIME"])
    test = test.merge(true_price, on=["DATETIME", "REGIONID"], how="inner")

    logger.info(f"Test rows before merge: {len(df[df['DATETIME'] >= split_date]):,}")
    logger.info(f"Test rows after merging true DISPATCHPRICE: {len(test):,}")

    # Rebuild label using true settled price instead of P5MIN
    test["y_true_price"] = (
        (test["f_current_rrp"] - test["true_dispatchprice"]).abs() > DELTA
    ).astype(int)

    logger.info(f"Old label (P5MIN-based) positive rate: {test['y_new'].mean()*100:.2f}%")
    logger.info(f"New label (true price-based) positive rate: {test['y_true_price'].mean()*100:.2f}%")
    logger.info(f"Label agreement: {(test['y_new'] == test['y_true_price']).mean()*100:.2f}%")

    X_test = test[FEATURES]
    y_test_old = test["y_new"]
    y_test_new = test["y_true_price"]

    model = joblib.load(MODELS_DIR / "fri_model_relabeled.pkl")
    proba = model.predict_proba(X_test)[:, 1]

    # Re-derive threshold on this corrected test set is not appropriate (train-only rule);
    # keep the original, training-derived threshold, applied unchanged
    THRESHOLD = 0.856818

    for label_name, y_test in [("OLD (P5MIN-based label)", y_test_old),
                                 ("NEW (true DISPATCHPRICE label)", y_test_new)]:
        pred = (proba >= THRESHOLD).astype(int)
        auc = roc_auc_score(y_test, proba)
        f1 = f1_score(y_test, pred, zero_division=0)
        precision = precision_score(y_test, pred, zero_division=0)
        recall = recall_score(y_test, pred, zero_division=0)
        tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()

        logger.info(f"\n=== {label_name} ===")
        logger.info(f"AUC={auc:.4f}  F1={f1:.4f}  Precision={precision:.4f}  Recall={recall:.4f}")
        logger.info(f"TP={tp} FP={fp} FN={fn} TN={tn}")

    pd.DataFrame([{
        "old_positive_rate": test["y_new"].mean(),
        "new_positive_rate": test["y_true_price"].mean(),
        "label_agreement": (test["y_new"] == test["y_true_price"]).mean(),
    }]).to_csv(TABLES_DIR / "c2_20_true_dispatchprice_rescore_results.csv", index=False)
    logger.info(f"\nSaved: {TABLES_DIR}/c2_20_true_dispatchprice_rescore_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
