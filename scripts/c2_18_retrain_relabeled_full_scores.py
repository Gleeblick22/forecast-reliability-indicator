"""
c2_18_retrain_relabeled_full_scores.py
=========================================
Phase 3 (Option A): retrains the FRI classifier on the genuine
reliability label (y_new) and leakage-controlled revision
feature, reproducing the confirmed leakage_controlled_h4_results
(AUC=0.9666, F1=0.8898), and saves BOTH the trained model AND
full per-interval predicted probabilities for every test-
partition interval, needed to rebuild H5-H8's downstream agent
simulations on the relabeled classifier.

Input:  data/processed/final_leakage_controlled_dataset.csv
Output: results/models/fri_model_relabeled.pkl
        results/tables/c2_18_relabeled_full_scores.csv
"""
import sys
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import f1_score, roc_auc_score, precision_score, recall_score, precision_recall_curve, confusion_matrix
import joblib
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c2_18_retrain_relabeled_full_scores")

FEATURES = [
    "f_current_rrp", "new_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

def main():
    logger.info("=" * 60)
    logger.info("c2_18_retrain_relabeled_full_scores.py started")
    logger.info("Phase 3 Option A: relabeled classifier, full scores")
    logger.info("=" * 60)

    df = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)

    train = df[df["DATETIME"] < split_date].copy()
    test = df[df["DATETIME"] >= split_date].copy()
    logger.info(f"Train: {len(train):,} rows, extreme rate {train['y_new'].mean()*100:.2f}%")
    logger.info(f"Test:  {len(test):,} rows, extreme rate {test['y_new'].mean()*100:.2f}%")

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
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    logger.info("=" * 60)
    logger.info(f"AUC={auc:.4f}  F1={f1:.4f}  Precision={precision:.4f}  Recall={recall:.4f}")
    logger.info(f"Threshold={optimal_threshold:.6f}")
    logger.info(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    logger.info("=" * 60)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_DIR / "fri_model_relabeled.pkl")
    logger.info(f"Model saved: {MODELS_DIR / 'fri_model_relabeled.pkl'}")

    # Bands
    def band(s):
        if s >= 0.75: return "HIGH"
        elif s >= 0.50: return "MEDIUM"
        else: return "LOW"

    test_out = test[["DATETIME", "REGIONID", "y_new"]].copy()
    test_out["fri_score"] = test_proba
    test_out["fri_band"] = pd.Series(test_proba, index=test_out.index).apply(band)

    test_out.to_csv(TABLES_DIR / "c2_18_relabeled_full_scores.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR / 'c2_18_relabeled_full_scores.csv'}")
    logger.info(f"Band distribution:\n{test_out['fri_band'].value_counts()}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
