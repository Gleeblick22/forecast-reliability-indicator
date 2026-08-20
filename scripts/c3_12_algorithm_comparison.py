"""
c3_12_algorithm_comparison.py
==============================
Compares XGBoost against alternative ML algorithms
to justify algorithm selection for FRI model.

Algorithms compared:
  Logistic Regression  (sklearn)
  Random Forest        (sklearn)
  LightGBM             (lightgbm)
  MLP Neural Network   (sklearn)
  XGBoost              (xgboost) -- primary model

All algorithms use same features same split
same threshold 0.8006 for fair comparison.

Statistical decision: SD-005
  XGBoost selected based on empirical comparison
  Tree ensembles known to outperform on tabular data
  Reference: Grinsztajn et al 2022 NeurIPS

Input:  data/processed/X_train.csv
        data/processed/X_test.csv
        data/processed/y_train.csv
        data/processed/y_test.csv
Output: results/tables/algorithm_comparison.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import time
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import f1_score, roc_auc_score, precision_score, recall_score
from xgboost import XGBClassifier
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_12_algorithm_comparison")

THRESHOLD = 0.8006
SEED      = 42


def evaluate(name, model, X_train, y_train, X_test, y_test):
    logger.info(f"Training {name}...")
    t0 = time.time()
    model.fit(X_train, y_train)
    train_time = round(time.time() - t0, 2)

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_test)[:, 1]
    else:
        proba = model.decision_function(X_test)
        proba = (proba - proba.min()) / (proba.max() - proba.min())

    y_pred = (proba >= THRESHOLD).astype(int)

    f1   = round(f1_score(y_test, y_pred, zero_division=0), 4)
    auc  = round(roc_auc_score(y_test, proba), 4)
    prec = round(precision_score(y_test, y_pred, zero_division=0), 4)
    rec  = round(recall_score(y_test, y_pred, zero_division=0), 4)

    logger.info(f"  F1={f1}  AUC={auc}  "
                f"Precision={prec}  Recall={rec}  "
                f"Time={train_time}s")

    return {
        "algorithm":      name,
        "f1":             f1,
        "auc_roc":        auc,
        "precision":      prec,
        "recall":         rec,
        "train_time_sec": train_time,
        "threshold":      THRESHOLD,
        "selected":       name == "XGBoost",
    }


def main():
    logger.info("=" * 60)
    logger.info("c3_12_algorithm_comparison.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Threshold: {THRESHOLD}")
    logger.info("Reference: Grinsztajn et al 2022 NeurIPS")
    logger.info("=" * 60)

    X_train = pd.read_csv(PROCESSED_DIR / "X_train.csv").values
    X_test  = pd.read_csv(PROCESSED_DIR / "X_test.csv").values
    y_train = pd.read_csv(PROCESSED_DIR / "y_train.csv").values.ravel()
    y_test  = pd.read_csv(PROCESSED_DIR / "y_test.csv").values.ravel()

    logger.info(f"Train: {len(X_train):,}  Test: {len(X_test):,}")
    logger.info(f"Train extreme: {y_train.sum():,}  "
                f"Test extreme: {y_test.sum():,}")

    algorithms = [
        ("Logistic Regression",
         LogisticRegression(
             max_iter=1000,
             class_weight="balanced",
             random_state=SEED)),
        ("Random Forest",
         RandomForestClassifier(
             n_estimators=200,
             max_depth=9,
             class_weight="balanced",
             random_state=SEED,
             n_jobs=-1)),
        ("MLP Neural Network",
         MLPClassifier(
             hidden_layer_sizes=(100, 50),
             max_iter=500,
             random_state=SEED)),
        ("XGBoost",
         XGBClassifier(
             n_estimators=200,
             max_depth=9,
             learning_rate=0.3,
             scale_pos_weight=5.86,
             use_label_encoder=False,
             eval_metric="logloss",
             random_state=SEED,
             verbosity=0)),
    ]

    # add LightGBM if available
    try:
        from lightgbm import LGBMClassifier
        algorithms.insert(3, (
            "LightGBM",
            LGBMClassifier(
                n_estimators=200,
                max_depth=9,
                learning_rate=0.3,
                scale_pos_weight=5.86,
                random_state=SEED,
                verbose=-1)))
        logger.info("LightGBM available -- included")
    except ImportError:
        logger.info("LightGBM not available -- skipped")

    results = []
    for name, model in algorithms:
        result = evaluate(name, model,
                          X_train, y_train,
                          X_test, y_test)
        results.append(result)

    df = pd.DataFrame(results).sort_values("f1", ascending=False)
    output = TABLES_DIR / "algorithm_comparison.csv"
    df.to_csv(output, index=False)

    logger.info("=" * 60)
    logger.info("ALGORITHM COMPARISON COMPLETE")
    logger.info(f"{'Algorithm':<25} {'F1':>8} {'AUC':>8} {'Time':>8}")
    for _, row in df.iterrows():
        marker = " <-- SELECTED" if row["selected"] else ""
        logger.info(f"  {row['algorithm']:<23} "
                    f"{row['f1']:>8} "
                    f"{row['auc_roc']:>8} "
                    f"{row['train_time_sec']:>7}s"
                    f"{marker}")
    xgb_f1 = df[df["selected"]]["f1"].values[0]
    best_f1 = df["f1"].max()
    logger.info(f"XGBoost F1: {xgb_f1}  Best F1: {best_f1}")
    logger.info(f"XGBoost justified: {xgb_f1 >= best_f1 * 0.99}")
    logger.info(f"Saved: {output}")
    logger.info("Next: ./run.sh scripts/c3_13_shap_analysis.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
