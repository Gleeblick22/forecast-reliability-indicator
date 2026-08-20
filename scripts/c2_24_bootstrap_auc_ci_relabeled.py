"""
c2_24_bootstrap_auc_ci_relabeled.py
======================================
Bootstraps a 95% CI for the relabeled classifier's AUC,
10,000 resamples, consistent with the project's established
methodology (Methods 3.G).
"""
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import roc_auc_score
from config.settings import PROCESSED_DIR, MODELS_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_24_bootstrap_auc_ci_relabeled")

FEATURES = [
    "f_current_rrp", "new_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

def main():
    logger.info("=" * 60)
    df = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date].reset_index(drop=True)
    X_test, y_test = test[FEATURES], test["y_new"].values

    model = joblib.load(MODELS_DIR / "fri_model_relabeled.pkl")
    proba = model.predict_proba(X_test)[:, 1]

    rng = np.random.default_rng(42)
    n = len(y_test)
    aucs = []
    for i in range(10000):
        idx = rng.integers(0, n, n)
        if len(np.unique(y_test[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y_test[idx], proba[idx]))

    aucs = np.array(aucs)
    ci_low, ci_high = np.percentile(aucs, [2.5, 97.5])
    logger.info(f"AUC point estimate: {roc_auc_score(y_test, proba):.4f}")
    logger.info(f"Bootstrap 95% CI: [{ci_low:.4f}, {ci_high:.4f}]  (n={len(aucs)} valid resamples)")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
