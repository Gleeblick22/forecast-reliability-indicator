"""
c2_11_retrain_no_june2022.py
===============================
Retrains XGBoost with June 2022 (the NEM market suspension
period) excluded from the training partition, addressing
Major review item #10: 35.78% of training extreme events
come from this single, administratively unprecedented month.
Test partition (already entirely post-October 2022) is
unaffected. Same hyperparameters, same features, same
methodology as the original model -- only the training data
composition differs.

Original model and results are NOT overwritten; this produces
a new, separate model and results file for direct comparison.

Input:  data/processed/features_all.csv
Output: results/models/fri_model_v2_no_june2022.pkl
        results/tables/c2_11_no_june2022_results.csv
"""
import sys
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import (
    f1_score, roc_auc_score, precision_score, recall_score,
    precision_recall_curve, confusion_matrix
)
import joblib
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_11_retrain_no_june2022")

FEATURES = [
    "f_current_rrp", "f_forecast_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

def main():
    logger.info("=" * 60)
    logger.info("c2_11_retrain_no_june2022.py started")
    logger.info("Major review item #10: June 2022 exclusion robustness check")
    logger.info("=" * 60)

    df = pd.read_csv(PROCESSED_DIR / "features_all.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)

    train_full = df[df["DATETIME"] < split_date]
    test = df[df["DATETIME"] >= split_date]

    june_mask = (train_full["DATETIME"] >= "2022-06-01") & (train_full["DATETIME"] < "2022-07-01")
    train_no_june = train_full[~june_mask]

    logger.info(f"Original training set: {len(train_full):,} rows")
    logger.info(f"June 2022 rows removed: {june_mask.sum():,}")
    logger.info(f"New training set (no June 2022): {len(train_no_june):,} rows")
    logger.info(f"Test set (unchanged): {len(test):,} rows")

    X_train = train_no_june[FEATURES]
    y_train = train_no_june["label"]
    X_test = test[FEATURES]
    y_test = test["label"]

    logger.info(f"Train extreme rate: {y_train.mean()*100:.2f}%")
    logger.info(f"Test extreme rate: {y_test.mean()*100:.2f}%")

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    logger.info(f"scale_pos_weight: {scale_pos_weight:.4f}")

    model = XGBClassifier(
        n_estimators=200, max_depth=9, learning_rate=0.3,
        scale_pos_weight=scale_pos_weight, random_state=42,
        eval_metric="logloss", verbosity=0,
    )
    logger.info("Training model (no June 2022)...")
    model.fit(X_train, y_train)

    y_proba_train = model.predict_proba(X_train)[:, 1]
    y_proba_test = model.predict_proba(X_test)[:, 1]

    precisions, recalls, thresholds = precision_recall_curve(y_train, y_proba_train)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    best_idx = np.argmax(f1_scores[:-1])
    optimal_threshold = thresholds[best_idx]

    y_pred = (y_proba_test >= optimal_threshold).astype(int)

    auc = roc_auc_score(y_test, y_proba_test)
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    logger.info("=" * 60)
    logger.info("NO-JUNE-2022 MODEL RESULTS")
    logger.info(f"AUC-ROC:   {auc:.4f}")
    logger.info(f"F1:        {f1:.4f}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall:    {recall:.4f}")
    logger.info(f"Threshold: {optimal_threshold:.4f}")
    logger.info(f"TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    logger.info("=" * 60)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_DIR / "fri_model_v2_no_june2022.pkl")
    logger.info(f"Model saved: {MODELS_DIR / 'fri_model_v2_no_june2022.pkl'}")

    results = pd.DataFrame([{
        "model": "no_june2022", "auc_roc": auc, "f1_score": f1,
        "precision": precision, "recall": recall, "threshold": optimal_threshold,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "train_rows": len(train_no_june), "train_extreme_rate": y_train.mean(),
    }])
    results.to_csv(TABLES_DIR / "c2_11_no_june2022_results.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR / 'c2_11_no_june2022_results.csv'}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
