"""
c2_22_ablation_relabeled.py
==============================
Priority 2: drop-one ablation study for the relabeled classifier,
replacing the original classifier's ablation results (Table 8:
f_forecast_revision 90.9% loss, f_current_rrp 20.5% loss),
which were computed pre-Phase-3 and never recomputed.

Input:  data/processed/final_leakage_controlled_dataset.csv
Output: results/tables/c2_22_ablation_relabeled_results.csv
"""
import sys
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import f1_score, precision_recall_curve
import numpy as np
from config.settings import PROCESSED_DIR, TABLES_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_22_ablation_relabeled")

FULL_FEATURES = [
    "f_current_rrp", "new_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

def train_and_eval(features, train, test, label_name):
    X_train, y_train = train[features], train["y_new"]
    X_test, y_test = test[features], test["y_new"]

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    model = XGBClassifier(
        n_estimators=200, max_depth=9, learning_rate=0.3,
        scale_pos_weight=scale_pos_weight, random_state=42,
        eval_metric="logloss", verbosity=0,
    )
    model.fit(X_train, y_train)

    train_proba = model.predict_proba(X_train)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_train, train_proba)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    optimal_threshold = thresholds[np.argmax(f1_scores[:-1])]

    test_proba = model.predict_proba(X_test)[:, 1]
    test_pred = (test_proba >= optimal_threshold).astype(int)
    f1 = f1_score(y_test, test_pred, zero_division=0)

    logger.info(f"{label_name}: F1={f1:.4f}")
    return f1

def main():
    logger.info("=" * 60)
    logger.info("c2_22_ablation_relabeled.py started")
    logger.info("=" * 60)

    df = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    train = df[df["DATETIME"] < split_date]
    test = df[df["DATETIME"] >= split_date]

    full_f1 = train_and_eval(FULL_FEATURES, train, test, "Full model (10 features)")

    results = []
    for feature_to_drop in ["new_revision", "f_current_rrp"]:
        remaining = [f for f in FULL_FEATURES if f != feature_to_drop]
        f1_dropped = train_and_eval(remaining, train, test, f"Without {feature_to_drop}")
        pct_loss = (full_f1 - f1_dropped) / full_f1 * 100
        logger.info(f"  -> % loss from removing {feature_to_drop}: {pct_loss:.1f}%")
        results.append({"feature_removed": feature_to_drop, "f1_after_removal": f1_dropped,
                         "pct_loss": pct_loss})

    logger.info(f"\nFull model F1 (reference): {full_f1:.4f}")
    pd.DataFrame(results).to_csv(TABLES_DIR / "c2_22_ablation_relabeled_results.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR}/c2_22_ablation_relabeled_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
