"""
c2_03_train_baseline_model.py
==============================
Trains logistic regression baseline model
for comparison against XGBoost FRI model.

Input:  data/processed/X_train.csv
        data/processed/y_train.csv
Output: results/models/baseline_model_v1.pkl
        results/tables/c2_03_baseline_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, precision_score, recall_score

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    MODELS_DIR,
    RANDOM_SEED,
)
from config.logging_config import get_logger

logger = get_logger("c2_03_train_baseline_model")

X_TRAIN_FILE  = PROCESSED_DIR / "X_train.csv"
Y_TRAIN_FILE  = PROCESSED_DIR / "y_train.csv"
X_TEST_FILE   = PROCESSED_DIR / "X_test.csv"
Y_TEST_FILE   = PROCESSED_DIR / "y_test.csv"
MODEL_FILE    = MODELS_DIR    / "baseline_model_v1.pkl"
RESULTS_FILE  = TABLES_DIR    / "c2_03_baseline_results.csv"


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

    logger.info(f"X_train: {X_train.shape}")
    logger.info(f"X_test:  {X_test.shape}")
    logger.info(f"Train extreme: {y_train['label'].sum():,}")
    logger.info(f"Test extreme:  {y_test['label'].sum():,}")

    return X_train, y_train, X_test, y_test


def train_baseline(
    X_train: pd.DataFrame,
    y_train: pd.DataFrame
) -> Pipeline:
    """Train logistic regression baseline."""
    logger.info("Training logistic regression baseline...")

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            random_state=RANDOM_SEED,
            max_iter=1000,
            class_weight="balanced",
        ))
    ])

    pipeline.fit(X_train.values, y_train["label"].values)
    logger.info("Baseline model trained")
    return pipeline


def evaluate_model(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame
) -> dict:
    """Evaluate baseline on train and test sets."""
    y_train_pred = pipeline.predict(X_train.values)
    y_test_pred  = pipeline.predict(X_test.values)

    train_f1  = f1_score(y_train["label"], y_train_pred, zero_division=0)
    train_pr  = precision_score(y_train["label"], y_train_pred, zero_division=0)
    train_rec = recall_score(y_train["label"], y_train_pred, zero_division=0)

    test_f1   = f1_score(y_test["label"], y_test_pred, zero_division=0)
    test_pr   = precision_score(y_test["label"], y_test_pred, zero_division=0)
    test_rec  = recall_score(y_test["label"], y_test_pred, zero_division=0)

    logger.info(f"Train F1: {train_f1:.4f}  Precision: {train_pr:.4f}  Recall: {train_rec:.4f}")
    logger.info(f"Test  F1: {test_f1:.4f}  Precision: {test_pr:.4f}  Recall: {test_rec:.4f}")

    return {
        "model":          "logistic_regression",
        "train_f1":       round(train_f1, 4),
        "train_precision": round(train_pr, 4),
        "train_recall":   round(train_rec, 4),
        "test_f1":        round(test_f1, 4),
        "test_precision": round(test_pr, 4),
        "test_recall":    round(test_rec, 4),
    }


def save_outputs(pipeline: Pipeline, results: dict) -> None:
    """Save model and results."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump(pipeline, f)
    logger.info(f"Saved model: {MODEL_FILE}")

    pd.DataFrame([results]).to_csv(RESULTS_FILE, index=False)
    logger.info(f"Saved results: {RESULTS_FILE}")


def main():
    logger.info("=" * 60)
    logger.info("c2_03_train_baseline_model.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Random seed: {RANDOM_SEED}")
    logger.info("=" * 60)

    X_train, y_train, X_test, y_test = load_data()

    pipeline = train_baseline(X_train, y_train)

    logger.info("Evaluating baseline...")
    results = evaluate_model(pipeline, X_train, y_train, X_test, y_test)

    save_outputs(pipeline, results)

    logger.info("=" * 60)
    logger.info("c2_03 COMPLETE")
    logger.info(f"Baseline test F1: {results['test_f1']:.4f}")
    logger.info("This is the benchmark for XGBoost to beat")
    logger.info("Next: ./run.sh scripts/c2_04_train_fri_model.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
