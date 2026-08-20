"""
c2_23_roc_pr_curves_relabeled.py
===================================
Priority 6: generates full ROC and precision-recall curve data
points for the relabeled classifier, needed to rebuild Figure 8,
never previously computed during Phase 3's H4 rebuild.

Input:  data/processed/final_leakage_controlled_dataset.csv
        results/models/fri_model_relabeled.pkl
Output: results/tables/c2_23_roc_curve_relabeled.csv
        results/tables/c2_23_pr_curve_relabeled.csv
"""
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import roc_curve, precision_recall_curve, roc_auc_score, average_precision_score
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_23_roc_pr_curves_relabeled")

FEATURES = [
    "f_current_rrp", "new_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

def main():
    logger.info("=" * 60)
    logger.info("c2_23_roc_pr_curves_relabeled.py started")
    logger.info("=" * 60)

    df = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date]
    X_test, y_test = test[FEATURES], test["y_new"]

    model = joblib.load(MODELS_DIR / "fri_model_relabeled.pkl")
    proba = model.predict_proba(X_test)[:, 1]

    fpr, tpr, roc_thresholds = roc_curve(y_test, proba)
    precision, recall, pr_thresholds = precision_recall_curve(y_test, proba)

    auc = roc_auc_score(y_test, proba)
    ap = average_precision_score(y_test, proba)
    prevalence = y_test.mean()

    logger.info(f"AUC = {auc:.4f}")
    logger.info(f"AP = {ap:.4f}")
    logger.info(f"Prevalence = {prevalence*100:.2f}%")
    logger.info(f"ROC curve points: {len(fpr)}")
    logger.info(f"PR curve points: {len(precision)}")

    # Operating point at the locked threshold
    THRESHOLD = 0.856818
    idx = np.argmin(np.abs(roc_thresholds - THRESHOLD)) if len(roc_thresholds) > 0 else 0
    op_fpr, op_tpr = fpr[idx], tpr[idx]
    logger.info(f"Operating point at threshold={THRESHOLD}: FPR={op_fpr:.4f}, TPR={op_tpr:.4f}")

    pd.DataFrame({"fpr": fpr, "tpr": tpr}).to_csv(
        TABLES_DIR / "c2_23_roc_curve_relabeled.csv", index=False)
    pd.DataFrame({"precision": precision, "recall": recall}).to_csv(
        TABLES_DIR / "c2_23_pr_curve_relabeled.csv", index=False)

    pd.DataFrame([{"auc": auc, "ap": ap, "prevalence": prevalence,
                    "op_fpr": op_fpr, "op_tpr": op_tpr}]).to_csv(
        TABLES_DIR / "c2_23_roc_pr_summary_relabeled.csv", index=False)

    logger.info(f"Saved ROC/PR curves and summary")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
