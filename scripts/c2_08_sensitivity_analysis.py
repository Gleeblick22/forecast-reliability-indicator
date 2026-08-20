"""
c2_08_sensitivity_analysis.py
===============================
Sensitivity analysis for H4 FRI model.
Tests F1 at alternative train/test split
dates to confirm robustness of H4 result.

Input:  data/processed/features_all.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/c2_08_sensitivity_results.csv

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
from sklearn.metrics import f1_score, roc_auc_score, precision_recall_curve

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    MODELS_DIR,
    RANDOM_SEED,
    H4_F1_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c2_08_sensitivity_analysis")

FEATURES_FILE = PROCESSED_DIR / "features_all.csv"
MODEL_FILE    = MODELS_DIR    / "fri_model_v1_tuned.pkl"
RESULTS_FILE  = TABLES_DIR    / "c2_08_sensitivity_results.csv"

# Alternative split dates for sensitivity
ALTERNATIVE_SPLITS = [
    "2022-07-01",
    "2022-09-01",
]


def load_inputs() -> tuple:
    """Load features and tuned model."""
    if not FEATURES_FILE.exists():
        logger.error(f"Features file not found: {FEATURES_FILE}")
        sys.exit(1)

    df = pd.read_csv(FEATURES_FILE, parse_dates=["DATETIME"])
    logger.info(f"Loaded features: {len(df):,} intervals")

    with open(MODEL_FILE, "rb") as f:
        model = pickle.load(f)
    logger.info("Loaded tuned model")

    return df, model


def find_optimal_threshold_sensitivity(
    model, X_train: np.ndarray, y_train: np.ndarray
) -> float:
    """
    Find optimal threshold on training partition only.
    Consistent with c2_06 approach (D-004 D-005).
    Reference: Saito and Rehmsmeier 2015 PLOS ONE
    """
    y_proba_train = model.predict_proba(X_train)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(
        y_train, y_proba_train
    )
    f1_scores = []
    for p, r in zip(precisions, recalls):
        if p + r > 0:
            f1_scores.append(2 * p * r / (p + r))
        else:
            f1_scores.append(0)

    best_idx       = np.argmax(f1_scores)
    best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
    return float(best_threshold)


def test_split(
    df: pd.DataFrame,
    split_date: str,
    scale_pos_weight: float
) -> dict:
    """
    Test H4 at alternative split date.
    Uses optimal threshold from training PR curve.
    Consistent with c2_06 method (D-004 D-005).
    """
    split_ts     = pd.Timestamp(split_date)
    feature_cols = [c for c in df.columns if c.startswith("f_")]

    train = df[df["DATETIME"] < split_ts]
    test  = df[df["DATETIME"] >= split_ts]

    if len(train) == 0 or len(test) == 0:
        logger.warning(f"Split {split_date}: insufficient data")
        return {
            "split_date":       split_date,
            "train_count":      0,
            "test_count":       0,
            "f1_default":       None,
            "f1_optimal":       None,
            "auc_roc":          None,
            "optimal_threshold": None,
            "passes_h4":        False,
            "note":             "insufficient_data",
        }

    X_train = train[feature_cols].values
    y_train = train["label"].values
    X_test  = test[feature_cols].values
    y_test  = test["label"].values

    extreme = y_train.sum()
    normal  = len(y_train) - extreme
    spw     = normal / extreme if extreme > 0 else 1

    model = XGBClassifier(
        scale_pos_weight=spw,
        random_state=RANDOM_SEED,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    y_proba = model.predict_proba(X_test)[:, 1]

    # Default threshold F1
    y_pred_default = model.predict(X_test)
    f1_default     = f1_score(y_test, y_pred_default, zero_division=0)

    # Optimal threshold from training PR curve
    optimal_threshold = find_optimal_threshold_sensitivity(
        model, X_train, y_train
    )
    y_pred_optimal = (y_proba >= optimal_threshold).astype(int)
    f1_optimal     = f1_score(y_test, y_pred_optimal, zero_division=0)

    # AUC-ROC — threshold independent
    try:
        auc = roc_auc_score(y_test, y_proba)
    except Exception:
        auc = None

    passes = f1_optimal >= H4_F1_THRESHOLD

    logger.info(
        f"Split {split_date}: train={len(train):,} test={len(test):,} "
        f"F1_default={f1_default:.4f} F1_optimal={f1_optimal:.4f} "
        f"threshold={optimal_threshold:.4f} AUC={auc:.4f} "
        f"{'ROBUST' if passes else 'NOT ROBUST'}"
    )

    return {
        "split_date":        split_date,
        "train_count":       len(train),
        "test_count":        len(test),
        "f1_default":        round(f1_default, 4),
        "f1_optimal":        round(f1_optimal, 4),
        "auc_roc":           round(auc, 4) if auc else None,
        "optimal_threshold": round(optimal_threshold, 4),
        "passes_h4":         passes,
        "note":              "",
    }


def main():
    logger.info("=" * 60)
    logger.info("c2_08_sensitivity_analysis.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Alternative splits: {ALTERNATIVE_SPLITS}")
    logger.info(f"H4 threshold: F1 >= {H4_F1_THRESHOLD}")
    logger.info("=" * 60)

    df, model = load_inputs()

    feature_cols     = [c for c in df.columns if c.startswith("f_")]
    extreme          = df["label"].sum()
    normal           = len(df) - extreme
    scale_pos_weight = normal / extreme if extreme > 0 else 1

    results = []

    for split_date in ALTERNATIVE_SPLITS:
        logger.info(f"Testing split: {split_date}")
        result = test_split(df, split_date, scale_pos_weight)
        results.append(result)

    all_robust = all(r["passes_h4"] for r in results if r["f1_optimal"] is not None)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df_results = pd.DataFrame(results)
    df_results["all_splits_robust"] = all_robust
    df_results.to_csv(RESULTS_FILE, index=False)
    logger.info(f"Saved: {RESULTS_FILE}")

    logger.info("=" * 60)
    logger.info(f"SENSITIVITY: {'ALL ROBUST' if all_robust else 'NOT ALL ROBUST'}")
    for r in results:
        logger.info(
            f"  Split {r['split_date']}: "
            f"F1_default={r['f1_default']} "
            f"F1_optimal={r['f1_optimal']} "
            f"AUC={r['auc_roc']} "
            f"{'ROBUST' if r['passes_h4'] else 'NOT ROBUST'}"
        )
    logger.info("Next: ./run.sh scripts/c2_09_replication_check.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
