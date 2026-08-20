"""
c2_17_regularization_sweep.py
================================
Round 2 Reviewer 4 concern #13: overfitting disclosed (train
F1=0.9998, AUC=1.0) but no regularization sweep offered.
Retrains the classifier at several more conservative
hyperparameter settings (reduced max_depth, added L2
regularization, subsampling) and compares test-set performance
against the original, confirming whether reducing overfitting
changes test-set results meaningfully.
"""
import sys
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import f1_score, roc_auc_score
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c2_17_regularization_sweep")

X_train = pd.read_csv(PROCESSED_DIR / "X_train.csv")
y_train = pd.read_csv(PROCESSED_DIR / "y_train.csv").values.ravel()
X_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")
y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").values.ravel()

THRESHOLD = 0.8006
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

configs = {
    "original (max_depth=9, no reg)": dict(
        n_estimators=200, max_depth=9, learning_rate=0.3,
        scale_pos_weight=scale_pos_weight, random_state=42),
    "shallow (max_depth=4)": dict(
        n_estimators=200, max_depth=4, learning_rate=0.3,
        scale_pos_weight=scale_pos_weight, random_state=42),
    "L2 regularized (reg_lambda=10)": dict(
        n_estimators=200, max_depth=9, learning_rate=0.3,
        scale_pos_weight=scale_pos_weight, random_state=42,
        reg_lambda=10),
    "subsampled (subsample=0.7, colsample=0.7)": dict(
        n_estimators=200, max_depth=9, learning_rate=0.3,
        scale_pos_weight=scale_pos_weight, random_state=42,
        subsample=0.7, colsample_bytree=0.7),
    "combined conservative": dict(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        scale_pos_weight=scale_pos_weight, random_state=42,
        reg_lambda=10, subsample=0.7, colsample_bytree=0.7),
}

results = []
for name, params in configs.items():
    model = XGBClassifier(**params, eval_metric="logloss", verbosity=0)
    model.fit(X_train, y_train)

    train_proba = model.predict_proba(X_train)[:, 1]
    train_pred = (train_proba >= THRESHOLD).astype(int)
    train_f1 = f1_score(y_train, train_pred, zero_division=0)
    train_auc = roc_auc_score(y_train, train_proba)

    test_proba = model.predict_proba(X_test)[:, 1]
    test_pred = (test_proba >= THRESHOLD).astype(int)
    test_f1 = f1_score(y_test, test_pred, zero_division=0)
    test_auc = roc_auc_score(y_test, test_proba)

    logger.info(f"{name}:")
    logger.info(f"  Train: F1={train_f1:.4f}  AUC={train_auc:.4f}")
    logger.info(f"  Test:  F1={test_f1:.4f}  AUC={test_auc:.4f}")

    results.append({"config": name, "train_f1": train_f1, "train_auc": train_auc,
                     "test_f1": test_f1, "test_auc": test_auc})

pd.DataFrame(results).to_csv(TABLES_DIR / "c2_17_regularization_sweep_results.csv", index=False)
logger.info(f"\nSaved: {TABLES_DIR}/c2_17_regularization_sweep_results.csv")
sys.exit(0)
