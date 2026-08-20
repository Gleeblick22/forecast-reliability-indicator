"""
settings.py
===========
Central configuration for the FRI project.
All project-wide settings are defined here.
No script should hardcode any of these values.

Project: forecast-reliability-indicator (FRI)
Author:  Dhan Prasad Ghale
Date:    April 2026
"""

from pathlib import Path

# ============================================================
# PROJECT PATHS
# ============================================================

ROOT_DIR        = Path(__file__).resolve().parent.parent
DATA_DIR        = ROOT_DIR / "data"
RAW_DIR         = DATA_DIR / "raw"
AEMO_RAW_DIR    = RAW_DIR / "aemo_nem"
ERCOT_RAW_DIR   = RAW_DIR / "ercot"
PROCESSED_DIR   = DATA_DIR / "processed"
EXTERNAL_DIR    = DATA_DIR / "external"
RESULTS_DIR     = ROOT_DIR / "results"
TABLES_DIR      = RESULTS_DIR / "tables"
FIGURES_DIR     = RESULTS_DIR / "figures"
MODELS_DIR      = RESULTS_DIR / "models"
LOGS_DIR        = ROOT_DIR / "logs"
ANALYSIS_DIR    = ROOT_DIR / "analysis"

# ============================================================
# REPRODUCIBILITY
# ============================================================

RANDOM_SEED = 42

# ============================================================
# NEM SETTINGS
# ============================================================

NEM_REGIONS          = ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]
DISPATCH_INTERVAL    = 30       # minutes (30-min pre-dispatch resolution; corrected from legacy 5)
PREDISPATCH_HORIZONS = ["P5", "P30"]

# ============================================================
# DATA PERIOD
# ============================================================

AEMO_START_DATE  = "2021-10-01"
AEMO_END_DATE    = "2022-12-31"
TRAIN_TEST_SPLIT = "2022-10-01"

# ============================================================
# ERCOT SETTINGS
# ============================================================

ERCOT_START_DATE = "2021-01-01"
ERCOT_END_DATE   = "2022-12-31"

# ============================================================
# DECISION 1 — FORECAST ERROR DEFINITION
# Locked: April 29, 2026
# Method: earliest predispatch forecast vs latest predispatch
# forecast for each interval. Captures real-time signal
# volatility experienced by autonomous agents.
# OSF Registration: 10.17605/OSF.IO/Z89HD
# ============================================================

FORECAST_ERROR_METHOD  = "earliest_vs_latest"
FORECAST_ERROR_COLUMN  = "forecast_error"

# ============================================================
# DECISION 2 — EXTREME EVENT DEFINITION
# Locked: April 29, 2026
# Method: single interval where latest predispatch RRP
# >= $300/MWh. Consistent with PDD Section 3.2 and OSF
# pre-registration. Sensitivity tested at $150 and $500.
# ============================================================

PRICE_THRESHOLD_NEM      = 300.0    # AUD/MWh primary threshold
EXTREME_DEFINITION       = "single_interval"
SENSITIVITY_THRESHOLDS   = [150.0, 500.0]

# ============================================================
# DECISION 3 — TRIGGER WEIGHTS
# Locked: April 29, 2026
# Rule: Component 2 uses ONLY features identified and ranked
# in Component 1 trigger weight analysis. No new features
# may be added in Component 2 without deviation log entry
# in COMPLIANCE.md.
# ============================================================

TRIGGER_WEIGHT_FILE      = "trigger_weights.csv"
MIN_FEATURES_PER_REGION  = 5
FEATURE_LOCK_RULE        = "component1_only"

# ============================================================
# DECISION 4 — BASELINE AGENT
# Locked: April 29, 2026
# Logic: Discharge at full power when latest predispatch
# forecast >= $300/MWh. Idle otherwise. No FRI input.
# Represents naive forecast-following strategy.
# ============================================================

BASELINE_AGENT_THRESHOLD = 300.0    # AUD/MWh dispatch trigger
BASELINE_DISPATCH_FACTOR = 1.0      # 100% of rated power

# ============================================================
# DECISION 5 — FRI AGENT DECISION BANDS
# Locked: April 29, 2026
# Pre-registered on OSF: 10.17605/OSF.IO/Z89HD
# Three confidence bands map FRI score to dispatch factor.
# ============================================================

FRI_DECISION_BANDS = {
    "high":   {"min": 0.75, "max": 1.00, "dispatch_factor": 1.00},
    "medium": {"min": 0.50, "max": 0.75, "dispatch_factor": 0.75},
    "low":    {"min": 0.00, "max": 0.50, "dispatch_factor": 0.25},
}

FRI_THRESHOLD_HIGH   = 0.75
FRI_THRESHOLD_MEDIUM = 0.50

# ============================================================
# DECISION 6 — MISSING DATA RULES
# Locked: April 29, 2026
# Rules applied during c1_02_validate_data.py and
# c1_03_preprocess_data.py before any analysis begins.
# ============================================================

MISSING_GAP_FILL_LIMIT      = 30    # minutes — forward fill if gap <= this
MISSING_GAP_EXCLUDE_LIMIT   = 30    # minutes — exclude trading day if gap > this
MISSING_RATE_FLAG_THRESHOLD = 0.01  # 1% — flag region if missing rate exceeds
DUPLICATE_KEEP_RULE         = "latest_lastchanged"

# ============================================================
# BATTERY SIMULATION SETTINGS
# ============================================================

BATTERY_CAPACITY_MWH     = 100.0   # MWh total energy capacity
BATTERY_POWER_MW         = 50.0    # MW rated discharge power
BATTERY_SOC_MIN          = 0.10    # minimum state of charge (10%)
BATTERY_SOC_MAX          = 0.90    # maximum state of charge (90%)
BATTERY_SOC_INITIAL      = 0.50    # starting state of charge (50%)
BATTERY_DISCHARGE_EFF    = 0.90    # discharge efficiency (90%)
BATTERY_CHARGE_EFF       = 0.90    # charge efficiency (90%)
BATTERY_MIN_DISPATCH_MW  = 1.0     # minimum dispatch size (MW)

# Revenue calculation
# Revenue = dispatch_MW * actual_RRP * (interval_minutes / 60)
INTERVAL_HOURS           = 0.5     # 30-minute interval in hours (agents define locally; corrected from legacy 5/60)

# ============================================================
# HYPOTHESIS THRESHOLDS
# All pre-registered on OSF: 10.17605/OSF.IO/Z89HD
# ============================================================

H1_AMPLIFICATION_THRESHOLD = 1.5
H1_PVALUE_THRESHOLD        = 0.05
H1_MIN_REGIONS_PASSING     = 4

H2_MASKING_THRESHOLD       = 0.50

H3_PVALUE_THRESHOLD        = 0.05

H4_F1_THRESHOLD            = 0.60
H4_TRAIN_TEST_SPLIT_DATE   = "2022-10-01"

H5_REDUCTION_THRESHOLD     = 0.20
H6_PVALUE_THRESHOLD        = 0.05
H7_REVENUE_THRESHOLD       = 0.15
H8_F1_TOLERANCE            = 0.15

# ============================================================
# FRI MODEL SETTINGS
# ============================================================

XGBOOST_PARAMS = {
    "n_estimators":  100,
    "max_depth":     6,
    "learning_rate": 0.1,
    "subsample":     0.8,
    "random_state":  RANDOM_SEED,
    "eval_metric":   "logloss",
}

# ============================================================
# OSF REGISTRATION
# ============================================================

OSF_DOI           = "10.17605/OSF.IO/Z89HD"
OSF_URL           = "https://doi.org/10.17605/OSF.IO/Z89HD"
REGISTRATION_DATE = "2026-04-28"

# ============================================================
# DECISION 7 — H3 HORIZON CLASSIFICATION
# Locked: April 29, 2026
# P5  = final forecast run before interval dispatches
# P30 = forecast run closest to 30 minutes before interval
# Tolerance: +/- 5 minutes for P30 classification
# ============================================================

H3_P5_DEFINITION   = "final_run_before_dispatch"
H3_P30_WINDOW_MIN  = 25    # minutes before interval
H3_P30_WINDOW_MAX  = 35    # minutes before interval
H3_P30_DEFINITION  = "run_closest_to_30min_before"

# ============================================================
# DECISION 8 — FRI PREDICTION TARGET
# Locked: April 29, 2026
# FRI predicts whether the CURRENT predispatch forecast
# for the current interval is reliable or unreliable.
# This enables real-time dispatch decision modification.
# ============================================================

FRI_PREDICTION_TARGET = "current_interval_reliability"
FRI_LABEL_DEFINITION  = "extreme_if_last_forecast_gte_threshold"

# ============================================================
# DECISION 9 — BATTERY DISPATCH THRESHOLD
# Locked: April 29, 2026
# Agent dispatches when forecast >= $100/MWh
# Lower than extreme threshold to create meaningful contrast
# between normal high-price and extreme event dispatch
# ============================================================

DISPATCH_THRESHOLD        = 100.0   # AUD/MWh agent dispatch trigger

# ============================================================
# DECISION 10 — REVENUE CALCULATION FORMULA
# Locked: April 29, 2026
# revenue = dispatch_MW * efficiency * actual_RRP * (5/60)
# Charging cost excluded — identical for both agents
# Simplification stated in manuscript limitations
# ============================================================

REVENUE_FORMULA           = "dispatch_MW * efficiency * RRP * interval_hours"

# ============================================================
# DECISION 11 — SIMULATION PERIOD
# Locked: April 29, 2026
# Test partition only — data FRI model never saw
# Prevents look-ahead bias in agent evaluation
# ============================================================

SIMULATION_START          = "2022-10-01"
SIMULATION_END            = "2022-12-31"

# ============================================================

# ============================================================
# GB ELEXON SETTINGS (H8 Cross Market Validation)
# ============================================================
# Great Britain electricity balancing market
# Source: Elexon BMRS API (data.elexon.co.uk)
# Replaces ERCOT which is geographically blocked from Australia
# Deviation D-006 recorded in COMPLIANCE.md

GB_RAW_DIR              = RAW_DIR / "gb_elexon"
GB_START_DATE           = "2021-01-01"
GB_END_DATE             = "2022-12-31"
GB_PRICE_COLUMN         = "systemBuyPrice"
GB_INTERVAL_MINUTES     = 30
GB_THRESHOLD_METHOD     = "percentile_0.9906_train_only"  # corrected: matches c3_06c (was stale 6x_average_price)
GB_THRESHOLD_PERCENTILE = 0.9906  # corrected from legacy multiplier
GB_RETRAIN              = False  # No retraining per Decision 12
GB_DATA_FILE            = GB_RAW_DIR / "gb_elexon_2021_2022.csv"

# DECISION 12 — ERCOT DATA ALIGNMENT
# Locked: April 29, 2026
# Resample ERCOT 15-min to 5-min via linear interpolation
# Extreme threshold = 6x average ERCOT price
# Primary validation hub = North
# No retraining on ERCOT data
# ============================================================

ERCOT_RESAMPLE_METHOD     = "linear_interpolation"
ERCOT_THRESHOLD_METHOD    = "6x_average_price"
ERCOT_THRESHOLD_MULTIPLIER = 6.0
ERCOT_PRIMARY_HUB         = "North"
ERCOT_RETRAIN             = False

# ============================================================
# DECISION 13 — STATE OF CHARGE MANAGEMENT
# Locked: April 29, 2026
# Daily SOC reset to 50% at 00:00 each trading day
# No charging strategy modelled — both agents reset equally
# Stated as limitation in manuscript
# ============================================================

BATTERY_SOC_RESET_DAILY   = True
BATTERY_SOC_RESET_VALUE   = 0.50
SOC_RESET_TIME            = "00:00"

# ============================================================
# DECISION 24 — TEMPORAL LEAD TIME ANALYSIS
# Locked: 2026-06-17
# POST-HOC EXPLORATORY — not pre-registered
# Tests whether FRI triggers before price spike onset.
# Lookback window = 6 intervals (3 hours) — justified as
# NEM battery pre-positioning window for dispatch agents.
# Episode gap = 60 min to split consecutive spike clusters.
# Threshold: regime == 'extreme' (consistent with D-009
# AUD 100 via c3_02_fri_agent_results.csv regime column).
# Framing: Exploratory supporting evidence only.
# Cannot be used as hypothesis confirmation.
# Manuscript: Section 4.2.3, labelled post-hoc.
# ============================================================

TEMPORAL_LOOKBACK_INTERVALS = 6     # 6 x 30 min = 3 hours
TEMPORAL_EPISODE_GAP_MIN    = 60    # minutes gap to split episodes
TEMPORAL_FRI_TRIGGER_BAND   = "HIGH"
TEMPORAL_EXTREME_LABEL      = "extreme"
TEMPORAL_DEVIATION          = "D-024"
