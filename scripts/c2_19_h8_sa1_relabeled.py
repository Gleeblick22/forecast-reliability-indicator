"""
c2_19_h8_sa1_relabeled.py
============================
Phase 3: H8 SA1 cross-region test using the relabeled classifier
methodology. Trains on the four non-SA1 regions using the
genuine reliability label and leakage-controlled revision
feature, tests on held-out SA1.

Input:  data/processed/final_leakage_controlled_dataset.csv
Output: results/tables/c2_19_h8_sa1_relabeled_results.csv
"""
import sys
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import f1_score, roc_auc_score, precision_recall_curve
import numpy as np
from config.settings import PROCESSED_DIR, TABLES_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_19_h8_sa1_relabeled")

FEATURES = [
    "f_current_rrp", "new_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

def main():
    logger.info("=" * 60)
    logger.info("c2_19_h8_sa1_relabeled.py started")
    logger.info("=" * 60)

    df = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)

    # Train on 4 non-SA1 regions, training period only
    train = df[(df["DATETIME"] < split_date) & (df["REGIONID"] != "SA1")]
    # Test on SA1, held-out period
    test = df[(df["DATETIME"] >= split_date) & (df["REGIONID"] == "SA1")]

    logger.info(f"Train (4 regions, no SA1): {len(train):,} rows, "
                f"extreme rate {train['y_new'].mean()*100:.2f}%")
    logger.info(f"Test (SA1 only): {len(test):,} rows, "
                f"extreme rate {test['y_new'].mean()*100:.2f}%")

    X_train, y_train = train[FEATURES], train["y_new"]
    X_test, y_test = test[FEATURES], test["y_new"]

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    model = XGBClassifier(
        n_estimators=200, max_depth=9, learning_rate=0.3,
        scale_pos_weight=scale_pos_weight, random_state=42,
        eval_metric="logloss", verbosity=0,
    )
    model.fit(X_train, y_train)

    train_proba = model.predict_proba(X_train)[:, 1]
    test_proba = model.predict_proba(X_test)[:, 1]

    precisions, recalls, thresholds = precision_recall_curve(y_train, train_proba)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    optimal_threshold = thresholds[np.argmax(f1_scores[:-1])]

    y_pred = (test_proba >= optimal_threshold).astype(int)
    auc = roc_auc_score(y_test, test_proba)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    logger.info(f"SA1 F1={f1:.4f}  AUC={auc:.4f}  threshold={optimal_threshold:.4f}")

    pd.DataFrame([{"context": "SA1 (relabeled)", "f1": f1, "auc": auc,
                    "threshold": optimal_threshold}]).to_csv(
        TABLES_DIR / "c2_19_h8_sa1_relabeled_results.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR}/c2_19_h8_sa1_relabeled_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
