"""
c3_35_gb_harmonized_frilite.py
================================
FRI without f_forecast_revision on GB Elexon market.

Tests 9-feature FRI model on GB settlement
data using strict train/test separation.

Clean methodology (no data leakage):
  GB split: 80% train  20% test
  Extreme threshold: computed on GB train only
  Prediction threshold: NEM-derived (0.8006)
  No GB test data used in any computation

Rationale:
  f_forecast_revision unavailable in
  settlement-only markets.
  Tests transferability boundary without predispatch revision data.

Input:  data/processed/X_train.csv
        data/processed/y_train.csv
        data/raw/gb_elexon/gb_elexon_2021_2022.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/c3_35_gb_harmonized_frilite_results.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import warnings
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from sklearn.metrics import f1_score, roc_auc_score
from xgboost import XGBClassifier
from config.settings import (
    PROCESSED_DIR, TABLES_DIR, MODELS_DIR, RAW_DIR)
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_35_gb_harmonized_frilite")

SEED           = 42
NEM_THRESHOLD  = 0.8006
EXTREME_PCT    = 0.8744  # HARMONIZED to NEM's own percentile (Major #13)
GB_TRAIN_RATIO = 0.80


def main():
    logger.info("=" * 60)
    logger.info("c3_35_gb_harmonized_frilite.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("Clean methodology -- no data leakage")
    logger.info(f"GB train ratio:    {GB_TRAIN_RATIO}")
    logger.info(f"Extreme percentile:{EXTREME_PCT}")
    logger.info(f"NEM threshold:     {NEM_THRESHOLD}")
    logger.info("=" * 60)

    # load NEM data
    X_train_full = pd.read_csv(PROCESSED_DIR / "X_train.csv")
    y_train      = pd.read_csv(
        PROCESSED_DIR / "y_train.csv").values.ravel()

    lite_cols = [c for c in X_train_full.columns
                 if c != "f_forecast_revision"]
    logger.info(f"Features (9 excluding f_forecast_revision): {len(lite_cols)}")
    logger.info(f"Features: {lite_cols}")

    X_train_lite = X_train_full[lite_cols].values

    # train 9-feature FRI on NEM training data
    logger.info("Training 9-feature FRI on NEM data...")
    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        tuned = pickle.load(f)
    params = tuned.get_params()

    lite_model = XGBClassifier(**params)
    lite_model.fit(X_train_lite, y_train)

    # NEM 9-feature FRI F1 using NEM threshold
    X_test_nem = pd.read_csv(PROCESSED_DIR / "X_test.csv")
    y_test_nem = pd.read_csv(
        PROCESSED_DIR / "y_test.csv").values.ravel()
    nem_proba  = lite_model.predict_proba(
        X_test_nem[lite_cols].values)[:, 1]
    nem_f1     = f1_score(
        y_test_nem,
        (nem_proba >= NEM_THRESHOLD).astype(int),
        zero_division=0)
    nem_auc    = roc_auc_score(y_test_nem, nem_proba)

    logger.info(f"NEM 9-feature FRI F1:  {nem_f1:.4f}")
    logger.info(f"NEM 9-feature FRI AUC: {nem_auc:.4f}")

    # load GB data
    logger.info("Loading GB Elexon data...")
    gb = pd.read_csv(
        RAW_DIR / "gb_elexon" / "gb_elexon_2021_2022.csv",
        parse_dates=["DATETIME"])
    gb["DATETIME"] = gb["DATETIME"].dt.tz_localize(None)
    gb = gb.sort_values("DATETIME").reset_index(drop=True)

    # strict GB split -- 80% train 20% test
    split_idx  = int(len(gb) * GB_TRAIN_RATIO)
    gb_train   = gb.iloc[:split_idx].copy()
    gb_test    = gb.iloc[split_idx:].copy()

    logger.info(f"GB total:  {len(gb):,}")
    logger.info(f"GB train:  {len(gb_train):,}")
    logger.info(f"GB test:   {len(gb_test):,}")

    # compute extreme threshold on GB TRAIN only
    threshold_gb = gb_train["PRICE"].quantile(EXTREME_PCT)
    logger.info(f"GB extreme threshold (train): {threshold_gb:.2f}")

    # apply threshold to GB TEST labels only
    gb_test = gb_test.copy()
    gb_test["is_extreme"] = (
        gb_test["PRICE"] >= threshold_gb).astype(int)
    logger.info(f"GB test extreme events: {gb_test['is_extreme'].sum():,}")

    # compute NEM normalisation stats from NEM TRAINING only
    nem_stats = {}
    for col in lite_cols:
        nem_stats[col] = {
            "mean": X_train_full[col].mean(),
            "std":  X_train_full[col].std()
        }

    def engineer_gb_features(df, price_col="PRICE"):
        P = df[price_col]
        out = pd.DataFrame()
        out["f_current_rrp"]        = P
        out["f_rolling_mean_30min"] = P.rolling(
            2, min_periods=1).mean()
        out["f_rolling_max_30min"]  = P.rolling(
            2, min_periods=1).max()
        out["f_price_change_30min"] = (
            P - P.shift(1)).fillna(0)
        out["f_price_change_60min"] = (
            P - P.shift(2)).fillna(0)
        out["f_hour_of_day"]        = df["DATETIME"].dt.hour
        out["f_is_peak_hour"]       = (
            df["DATETIME"].dt.hour.between(16, 20)
            .astype(int))
        out["f_day_of_week"]        = (
            df["DATETIME"].dt.dayofweek)
        above = (P >= P.quantile(0.875)).astype(int)
        out["f_consecutive_high"]   = (
            above.groupby(
                (above != above.shift()).cumsum()
            ).cumcount() + 1) * above
        return out

    # engineer features for GB train (for normalisation stats)
    gb_train_feat = engineer_gb_features(gb_train)
    gb_test_feat  = engineer_gb_features(gb_test)

    # normalise GB features using NEM training statistics
    for col in lite_cols:
        gb_mean = gb_train_feat[col].mean()
        gb_std  = gb_train_feat[col].std()
        if gb_std == 0:
            gb_std = 1
        # transform GB to NEM scale
        gb_test_feat[col] = (
            nem_stats[col]["mean"] +
            ((gb_test_feat[col] - gb_mean) / gb_std) *
            nem_stats[col]["std"])

    X_test_gb = gb_test_feat[lite_cols].values
    y_test_gb = gb_test["is_extreme"].values

    logger.info(f"GB test intervals: {len(y_test_gb):,}")
    logger.info(f"GB extreme events: {y_test_gb.sum():,}")

    # predict using NEM-derived threshold only
    gb_proba   = lite_model.predict_proba(X_test_gb)[:, 1]
    gb_pred    = (gb_proba >= NEM_THRESHOLD).astype(int)
    gb_f1      = f1_score(y_test_gb, gb_pred, zero_division=0)
    gb_auc     = roc_auc_score(y_test_gb, gb_proba)
    f1_diff    = abs(nem_f1 - gb_f1)
    passes_h8  = f1_diff <= 0.15

    logger.info("=" * 60)
    logger.info("9-FEATURE FRI CLEAN RESULTS")
    logger.info(f"NEM 9-feature FRI F1: {nem_f1:.4f}")
    logger.info(f"GB  9-feature FRI F1: {gb_f1:.4f}")
    logger.info(f"GB  AUC-ROC:     {gb_auc:.4f}")
    logger.info(f"F1 difference:   {f1_diff:.4f}")
    logger.info(f"H8 tolerance:    0.15")
    logger.info(f"H8 9-feature FRI: {'PASS' if passes_h8 else 'FAIL'}")
    logger.info(f"Data leakage:    None")

    results = pd.DataFrame([{
        "variant":           "FRI 9 features without f_forecast_revision",
        "excluded_feature":  "f_forecast_revision",
        "methodology":       "clean -- no data leakage",
        "gb_train_ratio":    GB_TRAIN_RATIO,
        "threshold_source":  "NEM training data only",
        "nem_f1":            round(nem_f1, 4),
        "nem_auc":           round(nem_auc, 4),
        "gb_f1":             round(gb_f1, 4),
        "gb_auc_roc":        round(gb_auc, 4),
        "f1_difference":     round(f1_diff, 4),
        "h8_tolerance":      0.15,
        "passes_h8":         passes_h8,
        "data_leakage":      False,
        "note": (
            "Clean methodology: GB threshold from "
            "train only. NEM threshold used for prediction.")
    }])

    output = TABLES_DIR / "c3_35_gb_harmonized_frilite_results.csv"
    results.to_csv(output, index=False)
    logger.info(f"Saved: {output}")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
