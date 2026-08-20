"""
c2_15_overfitting_check_v2.py
================================
Corrected version of c2_14: uses X_train.csv/y_train.csv/
X_test.csv/y_test.csv directly (the exact files the original
model was trained and evaluated on) instead of features_all.csv,
to avoid any column-alignment discrepancy.
"""
import sys
import pandas as pd
import joblib
from sklearn.metrics import f1_score, roc_auc_score
from config.settings import PROCESSED_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c2_15_overfitting_check_v2")

THRESHOLD = 0.8006

X_train = pd.read_csv(PROCESSED_DIR / "X_train.csv")
y_train = pd.read_csv(PROCESSED_DIR / "y_train.csv").values.ravel()
X_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")
y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").values.ravel()

logger.info(f"X_train columns: {list(X_train.columns)}")

model = joblib.load(MODELS_DIR / "fri_model_v1_tuned.pkl")

for name, X, y in [("TRAIN", X_train, y_train), ("TEST", X_test, y_test)]:
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= THRESHOLD).astype(int)
    f1 = f1_score(y, pred, zero_division=0)
    auc = roc_auc_score(y, proba)
    logger.info(f"{name}: n={len(X):,}  F1={f1:.4f}  AUC={auc:.4f}  extreme_rate={y.mean()*100:.2f}%")

sys.exit(0)
