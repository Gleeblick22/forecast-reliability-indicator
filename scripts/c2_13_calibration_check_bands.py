"""
c2_13_calibration_check_bands.py
===================================
Targeted calibration check within the FRI band ranges
(0.50-1.00), where the classifier's probability output is
actually used operationally (Minor review item #16).
"""
import sys
import pandas as pd
import numpy as np
import joblib
from config.settings import PROCESSED_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c2_13_calibration_check_bands")

FEATURES = [
    "f_current_rrp", "f_forecast_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

df = pd.read_csv(PROCESSED_DIR / "features_all.csv", parse_dates=["DATETIME"])
test = df[df["DATETIME"] >= "2022-10-01"]
X_test = test[FEATURES]
y_test = test["label"].values

model = joblib.load(MODELS_DIR / "fri_model_v1_tuned.pkl")
y_proba = model.predict_proba(X_test)[:, 1]

bands = [(0.0, 0.5, "LOW"), (0.5, 0.75, "MEDIUM"), (0.75, 1.01, "HIGH")]
logger.info("Calibration within operational bands:")
logger.info(f"{'Band':<10} {'n':>8} {'mean_predicted':>16} {'observed_freq':>16}")
for lo, hi, name in bands:
    mask = (y_proba >= lo) & (y_proba < hi)
    n = mask.sum()
    if n > 0:
        mean_pred = y_proba[mask].mean()
        obs_freq = y_test[mask].mean()
        logger.info(f"{name:<10} {n:>8} {mean_pred:>16.4f} {obs_freq:>16.4f}")

sys.exit(0)
