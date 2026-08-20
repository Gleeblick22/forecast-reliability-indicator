"""
c2_12_calibration_check.py
=============================
Checks probability calibration of the FRI classifier,
addressing Minor review item #16: scores are banded at fixed
cutpoints (0.50, 0.75) as if calibrated, but no calibration
analysis has been performed to verify this.

Computes a calibration curve (predicted probability vs.
observed frequency, binned) and Brier score on the held-out
test set, using the original, confirmed model.
"""
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss
from config.settings import PROCESSED_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c2_12_calibration_check")

FEATURES = [
    "f_current_rrp", "f_forecast_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

df = pd.read_csv(PROCESSED_DIR / "features_all.csv", parse_dates=["DATETIME"])
test = df[df["DATETIME"] >= "2022-10-01"]
X_test = test[FEATURES]
y_test = test["label"]

model = joblib.load(MODELS_DIR / "fri_model_v1_tuned.pkl")
y_proba = model.predict_proba(X_test)[:, 1]

brier = brier_score_loss(y_test, y_proba)
logger.info(f"Brier score: {brier:.4f} (lower is better; 0=perfect, 0.25=uninformative)")

frac_pos, mean_pred = calibration_curve(y_test, y_proba, n_bins=10, strategy="quantile")
logger.info("\nCalibration curve (10 quantile bins):")
logger.info(f"{'Mean predicted':>18} {'Observed frequency':>20}")
for mp, fp in zip(mean_pred, frac_pos):
    logger.info(f"{mp:>18.4f} {fp:>20.4f}")

sys.exit(0)
