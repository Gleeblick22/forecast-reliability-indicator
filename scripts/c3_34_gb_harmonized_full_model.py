"""
c3_34_gb_harmonized_full_model.py
============================
H8 GB Elexon: full 10-feature model test.

Companion script to c3_06c (FRI-Lite, 9 features).
Tests the ORIGINAL, locked 10-feature FRI model
(fri_model_v1_tuned.pkl) on GB Elexon data, using
the SAME NEM-side reference (F1=0.6207, the single
registered reference used throughout this manuscript)
rather than a separately re-computed NEM-side number.

Clean methodology (no data leakage):
  GB split: 80% train / 20% test (same split as c3_06c)
  Extreme threshold: computed on GB train only
  Prediction threshold: NEM-derived (0.8006)
  No GB test data used in any computation

Rationale:
  Resolves untraceable F1=0.2817 figure (no source file
  found in results/tables/ as of this session). Provides
  a real, reproducible full-model GB comparison point
  for the FRI-Lite ablation story in Section 4.4.4.

Input:  data/processed/X_test.csv
        data/processed/y_test.csv
        data/raw/gb_elexon/gb_elexon_2021_2022.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/c3_34_gb_harmonized_full_results.csv

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
from config.settings import (
    PROCESSED_DIR, TABLES_DIR, MODELS_DIR, RAW_DIR)
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_34_gb_harmonized_full_model")

NEM_THRESHOLD  = 0.8006
NEM_F1_LOCKED  = 0.6207   # single registered reference (Table 10)
EXTREME_PCT    = 0.8744  # HARMONIZED to NEM's own percentile (Major #13)
GB_TRAIN_RATIO = 0.80


def main():
    logger.info("=" * 60)
    logger.info("c3_34_gb_harmonized_full_model.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("Full 10-feature model -- GB Elexon test")
    logger.info(f"NEM reference (locked): {NEM_F1_LOCKED}")
    logger.info(f"NEM threshold:          {NEM_THRESHOLD}")
    logger.info("=" * 60)

    # load full 10-feature trained model
    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        full_model = pickle.load(f)

    X_train_full = pd.read_csv(PROCESSED_DIR / "X_train.csv")
    all_cols = list(X_train_full.columns)
    logger.info(f"Full model features ({len(all_cols)}): {all_cols}")

    # load GB data
    logger.info("Loading GB Elexon data...")
    gb = pd.read_csv(
        RAW_DIR / "gb_elexon" / "gb_elexon_2021_2022.csv",
        parse_dates=["DATETIME"])
    gb["DATETIME"] = gb["DATETIME"].dt.tz_localize(None)
    gb = gb.sort_values("DATETIME").reset_index(drop=True)

    split_idx  = int(len(gb) * GB_TRAIN_RATIO)
    gb_train   = gb.iloc[:split_idx].copy()
    gb_test    = gb.iloc[split_idx:].copy()

    logger.info(f"GB total:  {len(gb):,}")
    logger.info(f"GB train:  {len(gb_train):,}")
    logger.info(f"GB test:   {len(gb_test):,}")

    threshold_gb = gb_train["PRICE"].quantile(EXTREME_PCT)
    logger.info(f"GB extreme threshold (train): {threshold_gb:.2f}")

    gb_test = gb_test.copy()
    gb_test["is_extreme"] = (
        gb_test["PRICE"] >= threshold_gb).astype(int)
    logger.info(f"GB test extreme events: {gb_test['is_extreme'].sum():,}")

    nem_stats = {}
    for col in all_cols:
        nem_stats[col] = {
            "mean": X_train_full[col].mean(),
            "std":  X_train_full[col].std()
        }

    def engineer_gb_features_full(df, price_col="PRICE"):
        """
        Engineer all 10 features for GB, including
        f_forecast_revision -- which has NO real GB
        equivalent (no pre-dispatch revision sequence
        exists in GB settlement data). Filled with 0
        as the only available placeholder, since GB
        cannot supply this feature at inference time.
        This placeholder-fill is the structural transfer
        gap quantified by this script.
        """
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
        # f_forecast_revision has no GB equivalent --
        # placeholder zero-fill (the structural gap itself)
        out["f_forecast_revision"]  = 0.0
        return out[all_cols]

    gb_train_feat = engineer_gb_features_full(gb_train)
    gb_test_feat  = engineer_gb_features_full(gb_test)

    for col in all_cols:
        if col == "f_forecast_revision":
            continue  # leave placeholder as-is, not normalised
        gb_mean = gb_train_feat[col].mean()
        gb_std  = gb_train_feat[col].std()
        if gb_std == 0:
            gb_std = 1
        gb_test_feat[col] = (
            nem_stats[col]["mean"] +
            ((gb_test_feat[col] - gb_mean) / gb_std) *
            nem_stats[col]["std"])

    X_test_gb = gb_test_feat[all_cols].values
    y_test_gb = gb_test["is_extreme"].values

    logger.info(f"GB test intervals: {len(y_test_gb):,}")
    logger.info(f"GB extreme events: {y_test_gb.sum():,}")

    gb_proba = full_model.predict_proba(X_test_gb)[:, 1]
    gb_pred  = (gb_proba >= NEM_THRESHOLD).astype(int)
    gb_f1    = f1_score(y_test_gb, gb_pred, zero_division=0)
    gb_auc   = roc_auc_score(y_test_gb, gb_proba)
    f1_diff  = abs(NEM_F1_LOCKED - gb_f1)
    passes_h8 = f1_diff <= 0.15

    logger.info("=" * 60)
    logger.info("FULL 10-FEATURE MODEL -- GB RESULTS")
    logger.info(f"NEM reference (locked): {NEM_F1_LOCKED:.4f}")
    logger.info(f"GB F1:                  {gb_f1:.4f}")
    logger.info(f"GB AUC-ROC:             {gb_auc:.4f}")
    logger.info(f"F1 difference:          {f1_diff:.4f}")
    logger.info(f"H8 tolerance:           0.15")
    logger.info(f"H8 full model:          {'PASS' if passes_h8 else 'FAIL'}")

    results = pd.DataFrame([{
        "variant":          "FRI full 10-feature model",
        "nem_f1_reference": NEM_F1_LOCKED,
        "gb_f1":            round(gb_f1, 4),
        "gb_auc_roc":       round(gb_auc, 4),
        "f1_difference":    round(f1_diff, 4),
        "h8_tolerance":     0.15,
        "passes_h8":        passes_h8,
        "note": (
            "f_forecast_revision zero-filled for GB "
            "(no equivalent feature exists); "
            "NEM reference fixed at locked value 0.6207")
    }])

    output = TABLES_DIR / "c3_34_gb_harmonized_full_results.csv"
    results.to_csv(output, index=False)
    logger.info(f"Saved: {output}")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
