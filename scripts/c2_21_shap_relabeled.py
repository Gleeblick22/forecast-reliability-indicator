"""
c2_21_shap_relabeled.py
==========================
Priority 2: SHAP feature-importance analysis for the relabeled
classifier (fri_model_relabeled.pkl), never previously computed.
Replaces the original classifier's SHAP values (34.94%/30.70%/
65.64%) currently cited in Results 4.D and Introduction
Contribution 2.

Input:  data/processed/final_leakage_controlled_dataset.csv
        results/models/fri_model_relabeled.pkl
Output: results/tables/c2_21_shap_relabeled_results.csv
"""
import sys
import pandas as pd
import numpy as np
import joblib
import shap
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_21_shap_relabeled")

FEATURES = [
    "f_current_rrp", "new_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

def main():
    logger.info("=" * 60)
    logger.info("c2_21_shap_relabeled.py started")
    logger.info("=" * 60)

    df = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date]
    X_test = test[FEATURES]

    model = joblib.load(MODELS_DIR / "fri_model_relabeled.pkl")

    logger.info("Computing SHAP values (TreeExplainer)...")
    explainer = shap.PermutationExplainer(model.predict_proba, X_test.sample(min(500, len(X_test)), random_state=42))
    shap_values_full = explainer(X_test)
    shap_values = shap_values_full.values[:, :, 1]  # positive class

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    total = mean_abs_shap.sum()
    pct = 100 * mean_abs_shap / total

    results = pd.DataFrame({
        "feature": FEATURES,
        "mean_abs_shap": mean_abs_shap,
        "pct_contribution": pct,
        "direction": ["positive" if np.mean(shap_values[:, i]) > 0 else "negative"
                      for i in range(len(FEATURES))],
    }).sort_values("pct_contribution", ascending=False)

    logger.info(f"\n{results.to_string(index=False)}")

    top2_pct = results.head(2)["pct_contribution"].sum()
    logger.info(f"\nTop 2 features combined: {top2_pct:.2f}%")

    results.to_csv(TABLES_DIR / "c2_21_shap_relabeled_results.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR}/c2_21_shap_relabeled_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
