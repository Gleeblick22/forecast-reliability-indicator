"""
c2_16_isotonic_recalibration_check.py
========================================
Round 2 Reviewer 2 concern: calibration consequences (Minor #16
originally, now Major #8 in Round 2) are asserted but not
demonstrated. Applies isotonic regression to FRI's raw scores
and checks whether the resulting recalibrated scores would
reassign intervals across the HIGH/MEDIUM/LOW band boundaries
used in H5/H6's dispatch-scaling agent.
"""
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.isotonic import IsotonicRegression
from config.settings import PROCESSED_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c2_16_isotonic_recalibration_check")

FEATURES = [
    "f_current_rrp", "f_forecast_revision", "f_rolling_mean_30min",
    "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
    "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
]

X_train = pd.read_csv(PROCESSED_DIR / "X_train.csv")
y_train = pd.read_csv(PROCESSED_DIR / "y_train.csv").values.ravel()
X_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")
y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").values.ravel()

model = joblib.load(MODELS_DIR / "fri_model_v1_tuned.pkl")

# Fit isotonic regression on training predictions
train_proba = model.predict_proba(X_train)[:, 1]
iso = IsotonicRegression(out_of_bounds="clip")
iso.fit(train_proba, y_train)

# Apply to test set
test_proba_raw = model.predict_proba(X_test)[:, 1]
test_proba_calibrated = iso.predict(test_proba_raw)

def band(s):
    if s >= 0.75: return "HIGH"
    elif s >= 0.50: return "MEDIUM"
    else: return "LOW"

bands_raw = pd.Series(test_proba_raw).apply(band)
bands_calibrated = pd.Series(test_proba_calibrated).apply(band)

logger.info("Raw band distribution:")
logger.info(bands_raw.value_counts())
logger.info("\nCalibrated band distribution:")
logger.info(bands_calibrated.value_counts())

changed = (bands_raw.values != bands_calibrated.values).sum()
logger.info(f"\nIntervals that changed band assignment: {changed} of {len(bands_raw)} ({100*changed/len(bands_raw):.2f}%)")

# Cross-tab
crosstab = pd.crosstab(bands_raw, bands_calibrated, rownames=["Raw"], colnames=["Calibrated"])
logger.info(f"\nCross-tabulation:\n{crosstab}")

sys.exit(0)
