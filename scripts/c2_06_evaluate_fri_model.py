"""
c2_06_evaluate_fri_model.py
============================
Formal evaluation of tuned FRI model on
held-out test set. Tests H4 hypothesis.

H4: FRI model achieves F1 >= 0.60 on
    held-out chronological test set.

Input:  results/models/fri_model_v1_tuned.pkl
        data/processed/X_test.csv
        data/processed/y_test.csv
        results/tables/c2_03_baseline_results.csv
Output: results/tables/c2_06_h4_model_performance.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from sklearn.metrics import (
    f1_score, precision_score, recall_score,
    roc_auc_score, confusion_matrix,
    precision_recall_curve
)

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    MODELS_DIR,
    H4_F1_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c2_06_evaluate_fri_model")

MODEL_FILE       = MODELS_DIR / "fri_model_v1_tuned.pkl"
X_TRAIN_FILE     = PROCESSED_DIR / "X_train.csv"
Y_TRAIN_FILE     = PROCESSED_DIR / "y_train.csv"
X_TEST_FILE      = PROCESSED_DIR / "X_test.csv"
Y_TEST_FILE      = PROCESSED_DIR / "y_test.csv"
BASELINE_FILE    = TABLES_DIR / "c2_03_baseline_results.csv"
RESULTS_FILE     = TABLES_DIR / "c2_06_h4_model_performance.csv"


def load_inputs() -> tuple:
    """Load tuned model and test data."""
    for f in [MODEL_FILE, X_TRAIN_FILE, Y_TRAIN_FILE, X_TEST_FILE, Y_TEST_FILE]:
        if not f.exists():
            logger.error(f"File not found: {f}")
            sys.exit(1)

    with open(MODEL_FILE, "rb") as f:
        model = pickle.load(f)
    logger.info(f"Loaded tuned model: {MODEL_FILE}")

    X_train = pd.read_csv(X_TRAIN_FILE)
    y_train = pd.read_csv(Y_TRAIN_FILE)
    X_test  = pd.read_csv(X_TEST_FILE)
    y_test  = pd.read_csv(Y_TEST_FILE)
    logger.info(f"Train set: {X_train.shape}")
    logger.info(f"Test set:  {X_test.shape}")
    logger.info(f"Test extreme: {y_test['label'].sum():,}")

    # Load baseline for comparison
    baseline_f1 = None
    if BASELINE_FILE.exists():
        baseline = pd.read_csv(BASELINE_FILE)
        baseline_f1 = baseline["test_f1"].iloc[0]
        logger.info(f"Baseline F1: {baseline_f1:.4f}")

    return model, X_train, y_train, X_test, y_test, baseline_f1




def find_optimal_threshold(model, X_train: pd.DataFrame, y_train: pd.DataFrame) -> float:
    """
    Find optimal classification threshold using precision-recall
    curve on TRAINING data only. No test label leakage.
    Reference: Saito and Rehmsmeier 2015 PLOS ONE
    DOI: 10.1371/journal.pone.0118432
    Self-refine cycle 2 — D-004 in COMPLIANCE.md
    """
    y_proba_train = model.predict_proba(X_train.values)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(
        y_train["label"].values, y_proba_train
    )

    # Find threshold that maximises F1 on training data
    f1_scores = []
    for p, r in zip(precisions, recalls):
        if p + r > 0:
            f1_scores.append(2 * p * r / (p + r))
        else:
            f1_scores.append(0)

    best_idx       = np.argmax(f1_scores)
    best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
    best_f1_train  = f1_scores[best_idx]

    logger.info(f"Optimal threshold (train PR curve): {best_threshold:.4f}")
    logger.info(f"Best F1 on training data:           {best_f1_train:.4f}")
    logger.info("Threshold selected on training data only — no test leakage")

    return float(best_threshold)

def evaluate_h4(
    model,
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    baseline_f1: float
) -> dict:
    """
    Formal H4 evaluation on held-out test set.
    This is the PRIMARY Component 2 result.
    """
    y_proba        = model.predict_proba(X_test.values)[:, 1]
    # Default threshold evaluation
    y_pred_default = model.predict(X_test.values)
    f1_default     = f1_score(y_test["label"], y_pred_default, zero_division=0)
    logger.info(f"Default threshold (0.50) F1: {f1_default:.4f}")
    # Optimal threshold from training PR curve (D-004)
    optimal_threshold = find_optimal_threshold(model, X_train, y_train)
    y_pred = (y_proba >= optimal_threshold).astype(int)

    f1   = f1_score(y_test["label"], y_pred, zero_division=0)
    pr   = precision_score(y_test["label"], y_pred, zero_division=0)
    rec  = recall_score(y_test["label"], y_pred, zero_division=0)
    auc  = roc_auc_score(y_test["label"], y_proba)
    cm   = confusion_matrix(y_test["label"], y_pred)

    tn, fp, fn, tp = cm.ravel()

    passes_h4 = f1 >= H4_F1_THRESHOLD

    logger.info(f"=== H4 FORMAL EVALUATION ===")
    logger.info(f"F1 score:      {f1:.4f}")
    logger.info(f"Precision:     {pr:.4f}")
    logger.info(f"Recall:        {rec:.4f}")
    logger.info(f"AUC-ROC:       {auc:.4f}")
    logger.info(f"True Negative: {tn:,}")
    logger.info(f"False Positive:{fp:,}")
    logger.info(f"False Negative:{fn:,}")
    logger.info(f"True Positive: {tp:,}")

    if baseline_f1 is not None:
        improvement = ((f1 - baseline_f1) / baseline_f1 * 100
                      if baseline_f1 > 0 else 0)
        logger.info(f"Baseline F1:   {baseline_f1:.4f}")
        logger.info(f"Improvement:   {improvement:.1f}%")

    logger.info(f"H4 threshold:  F1 >= {H4_F1_THRESHOLD}")
    logger.info(f"H4 RESULT:     {'PASSED' if passes_h4 else 'FAILED'}")

    return {
        "f1_score":        round(f1, 4),
        "precision":       round(pr, 4),
        "recall":          round(rec, 4),
        "auc_roc":         round(auc, 4),
        "true_negative":   int(tn),
        "false_positive":  int(fp),
        "false_negative":  int(fn),
        "true_positive":   int(tp),
        "baseline_f1":     round(baseline_f1, 4) if baseline_f1 else None,
        "improvement_pct": round(improvement, 2) if baseline_f1 else None,
        "h4_threshold":       H4_F1_THRESHOLD,
        "passes_h4":          passes_h4,
        "optimal_threshold":   round(optimal_threshold, 4),
        "f1_default_threshold": round(f1_default, 4),
    }


def main():
    logger.info("=" * 60)
    logger.info("c2_06_evaluate_fri_model.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"H4 threshold: F1 >= {H4_F1_THRESHOLD}")
    logger.info("THIS IS THE PRIMARY COMPONENT 2 RESULT")
    logger.info("=" * 60)

    model, X_train, y_train, X_test, y_test, baseline_f1 = load_inputs()

    results = evaluate_h4(model, X_train, y_train, X_test, y_test, baseline_f1)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([results]).to_csv(RESULTS_FILE, index=False)
    logger.info(f"Saved: {RESULTS_FILE}")

    logger.info("=" * 60)
    logger.info(f"H4 RESULT: {'PASSED' if results['passes_h4'] else 'FAILED'}")
    logger.info(f"F1 score:  {results['f1_score']:.4f}")
    logger.info(f"Required:  >= {H4_F1_THRESHOLD}")

    if not results["passes_h4"]:
        logger.warning("H4 FAILED — initiate self-refine protocol")
        logger.warning("See PDD Section 4.2 for failure diagnosis")

    logger.info("Next: ./run.sh scripts/c2_07_calibrate_decision_rules.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
