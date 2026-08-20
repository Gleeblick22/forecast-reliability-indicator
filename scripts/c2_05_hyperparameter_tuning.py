"""
c2_05_hyperparameter_tuning.py
================================
Grid search hyperparameter tuning for
XGBoost FRI model. Uses cross-validation
on training data only — no test data used.

Input:  data/processed/X_train.csv
        data/processed/y_train.csv
Output: results/models/fri_model_v1_tuned.pkl
        results/tables/c2_05_tuning_results.csv

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
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import f1_score, make_scorer

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    MODELS_DIR,
    RANDOM_SEED,
)
from config.logging_config import get_logger

logger = get_logger("c2_05_hyperparameter_tuning")

X_TRAIN_FILE  = PROCESSED_DIR / "X_train.csv"
Y_TRAIN_FILE  = PROCESSED_DIR / "y_train.csv"
X_TEST_FILE   = PROCESSED_DIR / "X_test.csv"
Y_TEST_FILE   = PROCESSED_DIR / "y_test.csv"
MODEL_FILE    = MODELS_DIR    / "fri_model_v1_tuned.pkl"
RESULTS_FILE  = TABLES_DIR    / "c2_05_tuning_results.csv"

# Grid search parameter space
PARAM_GRID = {
    "n_estimators":  [50, 100, 200],
    "max_depth":     [3, 6, 9],
    "learning_rate": [0.01, 0.1, 0.3],
}


def load_data() -> tuple:
    """Load train and test splits."""
    for f in [X_TRAIN_FILE, Y_TRAIN_FILE, X_TEST_FILE, Y_TEST_FILE]:
        if not f.exists():
            logger.error(f"File not found: {f}")
            sys.exit(1)

    X_train = pd.read_csv(X_TRAIN_FILE)
    y_train = pd.read_csv(Y_TRAIN_FILE)
    X_test  = pd.read_csv(X_TEST_FILE)
    y_test  = pd.read_csv(Y_TEST_FILE)

    extreme          = y_train["label"].sum()
    normal           = len(y_train) - extreme
    scale_pos_weight = normal / extreme if extreme > 0 else 1

    logger.info(f"X_train: {X_train.shape}")
    logger.info(f"scale_pos_weight: {scale_pos_weight:.2f}")

    return X_train, y_train, X_test, y_test, scale_pos_weight


def run_grid_search(
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    scale_pos_weight: float
) -> tuple:
    """
    Run grid search with TimeSeriesSplit CV.
    TimeSeriesSplit respects temporal order —
    no data leakage from future to past.
    """
    logger.info("Running grid search with TimeSeriesSplit CV...")
    logger.info(f"Parameter grid: {PARAM_GRID}")
    logger.info("This may take 20-40 minutes...")

    base_model = XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_SEED,
        eval_metric="logloss",
        use_label_encoder=False,
    )

    tscv    = TimeSeriesSplit(n_splits=5)
    scorer  = make_scorer(f1_score, zero_division=0)

    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=PARAM_GRID,
        cv=tscv,
        scoring=scorer,
        n_jobs=-1,
        verbose=1,
        refit=True,
    )

    grid_search.fit(X_train.values, y_train["label"].values)

    logger.info(f"Best params: {grid_search.best_params_}")
    logger.info(f"Best CV F1:  {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_, grid_search


def evaluate_tuned(
    model: XGBClassifier,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    best_params: dict,
    best_cv_f1: float
) -> dict:
    """Evaluate tuned model on test set."""
    y_pred = model.predict(X_test.values)
    test_f1 = f1_score(y_test["label"], y_pred, zero_division=0)

    logger.info(f"Tuned model test F1: {test_f1:.4f}")
    logger.info(f"H4 threshold (F1 >= 0.60): {'PASS' if test_f1 >= 0.60 else 'FAIL'}")

    return {
        "best_n_estimators":  best_params.get("n_estimators"),
        "best_max_depth":     best_params.get("max_depth"),
        "best_learning_rate": best_params.get("learning_rate"),
        "best_cv_f1":         round(best_cv_f1, 4),
        "test_f1":            round(test_f1, 4),
        "passes_h4":          test_f1 >= 0.60,
    }


def save_outputs(model: XGBClassifier, results: dict, grid_search) -> None:
    """Save tuned model and results."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Saved tuned model: {MODEL_FILE}")

    pd.DataFrame([results]).to_csv(RESULTS_FILE, index=False)
    logger.info(f"Saved results: {RESULTS_FILE}")

    # Save full CV results
    cv_results = pd.DataFrame(grid_search.cv_results_)
    cv_file    = TABLES_DIR / "c2_05_cv_results.csv"
    cv_results.to_csv(cv_file, index=False)
    logger.info(f"Saved CV results: {cv_file}")


def main():
    logger.info("=" * 60)
    logger.info("c2_05_hyperparameter_tuning.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Random seed: {RANDOM_SEED}")
    logger.info(f"Param grid size: {len(PARAM_GRID['n_estimators']) * len(PARAM_GRID['max_depth']) * len(PARAM_GRID['learning_rate'])} combinations")
    logger.info("=" * 60)

    X_train, y_train, X_test, y_test, scale_pos_weight = load_data()

    tuned_model, grid_search = run_grid_search(
        X_train, y_train, scale_pos_weight
    )

    results = evaluate_tuned(
        tuned_model, X_test, y_test,
        grid_search.best_params_,
        grid_search.best_score_
    )

    save_outputs(tuned_model, results, grid_search)

    logger.info("=" * 60)
    logger.info("c2_05 COMPLETE")
    logger.info(f"Best params:     {grid_search.best_params_}")
    logger.info(f"Best CV F1:      {results['best_cv_f1']:.4f}")
    logger.info(f"Tuned test F1:   {results['test_f1']:.4f}")
    logger.info(f"H4 status:       {'PASS' if results['passes_h4'] else 'needs self-refine'}")
    logger.info("Next: ./run.sh scripts/c2_06_evaluate_fri_model.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
