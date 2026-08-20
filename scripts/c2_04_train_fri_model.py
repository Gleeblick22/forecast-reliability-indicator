"""
c2_04_train_fri_model.py
=========================
Trains XGBoost FRI model — first training
with default parameters before tuning.

Input:  data/processed/X_train.csv
        data/processed/y_train.csv
Output: results/models/fri_model_v1.pkl
        results/tables/c2_04_fri_model_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    MODELS_DIR,
    RANDOM_SEED,
    XGBOOST_PARAMS,
)
from config.logging_config import get_logger

logger = get_logger("c2_04_train_fri_model")

X_TRAIN_FILE  = PROCESSED_DIR / "X_train.csv"
Y_TRAIN_FILE  = PROCESSED_DIR / "y_train.csv"
X_TEST_FILE   = PROCESSED_DIR / "X_test.csv"
Y_TEST_FILE   = PROCESSED_DIR / "y_test.csv"
MODEL_FILE    = MODELS_DIR    / "fri_model_v1.pkl"
RESULTS_FILE  = TABLES_DIR    / "c2_04_fri_model_results.csv"


def load_data() -> tuple:
    """Load train and test splits."""
    for f in [X_TRAIN_FILE, Y_TRAIN_FILE, X_TEST_FILE, Y_TEST_FILE]:
        if not f.exists():
            logger.error(f"File not found: {f}")
            logger.error("Run c2_02_train_test_split.py first")
            sys.exit(1)

    X_train = pd.read_csv(X_TRAIN_FILE)
    y_train = pd.read_csv(Y_TRAIN_FILE)
    X_test  = pd.read_csv(X_TEST_FILE)
    y_test  = pd.read_csv(Y_TEST_FILE)

    # Calculate scale_pos_weight per Decision 3
    extreme = y_train["label"].sum()
    normal  = len(y_train) - extreme
    scale_pos_weight = normal / extreme if extreme > 0 else 1

    logger.info(f"X_train: {X_train.shape}")
    logger.info(f"X_test:  {X_test.shape}")
    logger.info(f"Train extreme: {extreme:,}  normal: {normal:,}")
    logger.info(f"scale_pos_weight: {scale_pos_weight:.2f}")

    return X_train, y_train, X_test, y_test, scale_pos_weight


def train_fri_model(
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    scale_pos_weight: float
) -> XGBClassifier:
    """Train XGBoost FRI model with default params."""
    logger.info("Training XGBoost FRI model...")
    logger.info(f"Parameters: {XGBOOST_PARAMS}")

    model = XGBClassifier(
        n_estimators=XGBOOST_PARAMS["n_estimators"],
        max_depth=XGBOOST_PARAMS["max_depth"],
        learning_rate=XGBOOST_PARAMS["learning_rate"],
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_SEED,
        eval_metric="logloss",
        use_label_encoder=False,
    )

    model.fit(X_train.values, y_train["label"].values)
    logger.info("FRI model trained")
    return model


def evaluate_model(
    model: XGBClassifier,
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame
) -> dict:
    """Evaluate FRI model on train and test sets."""
    y_train_pred  = model.predict(X_train.values)
    y_test_pred   = model.predict(X_test.values)
    y_test_proba  = model.predict_proba(X_test.values)[:, 1]

    train_f1  = f1_score(y_train["label"], y_train_pred, zero_division=0)
    test_f1   = f1_score(y_test["label"], y_test_pred, zero_division=0)
    test_pr   = precision_score(y_test["label"], y_test_pred, zero_division=0)
    test_rec  = recall_score(y_test["label"], y_test_pred, zero_division=0)
    test_auc  = roc_auc_score(y_test["label"], y_test_proba)

    logger.info(f"Train F1:     {train_f1:.4f}")
    logger.info(f"Test F1:      {test_f1:.4f}")
    logger.info(f"Test Precision: {test_pr:.4f}")
    logger.info(f"Test Recall:  {test_rec:.4f}")
    logger.info(f"Test AUC-ROC: {test_auc:.4f}")

    passes_h4 = test_f1 >= 0.60
    logger.info(f"H4 threshold (F1 >= 0.60): {'PASS' if passes_h4 else 'FAIL'}")

    return {
        "model":          "xgboost_v1_default",
        "train_f1":       round(train_f1, 4),
        "test_f1":        round(test_f1, 4),
        "test_precision": round(test_pr, 4),
        "test_recall":    round(test_rec, 4),
        "test_auc":       round(test_auc, 4),
        "passes_h4":      passes_h4,
        "note":           "default params before tuning",
    }


def save_outputs(model: XGBClassifier, results: dict) -> None:
    """Save model and results."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Saved model: {MODEL_FILE}")

    pd.DataFrame([results]).to_csv(RESULTS_FILE, index=False)
    logger.info(f"Saved results: {RESULTS_FILE}")


def main():
    logger.info("=" * 60)
    logger.info("c2_04_train_fri_model.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Random seed: {RANDOM_SEED}")
    logger.info("=" * 60)

    X_train, y_train, X_test, y_test, scale_pos_weight = load_data()

    model = train_fri_model(X_train, y_train, scale_pos_weight)

    logger.info("Evaluating FRI model...")
    results = evaluate_model(model, X_train, y_train, X_test, y_test)

    save_outputs(model, results)

    logger.info("=" * 60)
    logger.info("c2_04 COMPLETE")
    logger.info(f"Test F1 (default params): {results['test_f1']:.4f}")
    logger.info(f"H4 pre-tuning:            {'PASS' if results['passes_h4'] else 'needs tuning'}")
    logger.info("Next: ./run.sh scripts/c2_05_hyperparameter_tuning.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
