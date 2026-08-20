"""
c3_46_h8_gb_relabeled.py
===========================
Phase 3: H8 GB transfer test using the relabeled classifier
(trained on NEM's genuine reliability label). GB has no
predispatch forecast sequence, so a true reliability label
cannot be constructed there (structural constraint, per
Discussion Section C); GB's label remains price-level-based,
as in the original H8 methodology, tested at both the original
(99.06th pct) and harmonized (87.44th pct) thresholds.
f_forecast_revision is zero-filled for GB (no equivalent
feature exists), matching the original H8 methodology exactly.

Input:  data/raw/gb_elexon/gb_elexon_2021_2022.csv
        results/models/fri_model_relabeled.pkl
Output: results/tables/c3_46_h8_gb_relabeled_results.csv
"""
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import f1_score, roc_auc_score
from config.settings import RAW_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c3_46_h8_gb_relabeled")

NEM_THRESHOLD = 0.856818
GB_TRAIN_RATIO = 0.80

def engineer_gb_features(df, price_col="PRICE"):
    P = df[price_col]
    out = pd.DataFrame()
    out["f_current_rrp"]        = P
    out["f_rolling_mean_30min"] = P.rolling(2, min_periods=1).mean()
    out["f_rolling_max_30min"]  = P.rolling(2, min_periods=1).max()
    out["f_price_change_30min"] = (P - P.shift(1)).fillna(0)
    out["f_price_change_60min"] = (P - P.shift(2)).fillna(0)
    out["f_hour_of_day"]        = df["DATETIME"].dt.hour
    out["f_is_peak_hour"]       = df["DATETIME"].dt.hour.between(16, 20).astype(int)
    out["f_day_of_week"]        = df["DATETIME"].dt.dayofweek
    above = (P >= P.quantile(0.875)).astype(int)
    out["f_consecutive_high"] = (above.groupby((above != above.shift()).cumsum()).cumcount() + 1) * above
    out["new_revision"] = 0.0  # zero-filled, no GB equivalent
    return out[["f_current_rrp", "new_revision", "f_rolling_mean_30min",
                "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
                "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]]

def test_gb(extreme_pct, label):
    gb = pd.read_csv(RAW_DIR / "gb_elexon" / "gb_elexon_2021_2022.csv", parse_dates=["DATETIME"])
    gb["DATETIME"] = gb["DATETIME"].dt.tz_localize(None)
    gb = gb.sort_values("DATETIME").reset_index(drop=True)
    split_idx = int(len(gb) * GB_TRAIN_RATIO)
    gb_train, gb_test = gb.iloc[:split_idx].copy(), gb.iloc[split_idx:].copy()

    threshold_gb = gb_train["PRICE"].quantile(extreme_pct)
    gb_test["is_extreme"] = (gb_test["PRICE"] >= threshold_gb).astype(int)

    feat = engineer_gb_features(gb_test)
    model = joblib.load(MODELS_DIR / "fri_model_relabeled.pkl")
    proba = model.predict_proba(feat)[:, 1]
    pred = (proba >= NEM_THRESHOLD).astype(int)

    f1 = f1_score(gb_test["is_extreme"], pred, zero_division=0)
    auc = roc_auc_score(gb_test["is_extreme"], proba)

    logger.info(f"\n=== GB relabeled, {label} (pct={extreme_pct}) ===")
    logger.info(f"Threshold price: {threshold_gb:.2f}")
    logger.info(f"Extreme events: {gb_test['is_extreme'].sum():,} of {len(gb_test):,}")
    logger.info(f"F1={f1:.4f}  AUC={auc:.4f}")
    logger.info(f"F1 diff from NEM reference (0.8898): {abs(0.8898-f1):.4f}")
    logger.info(f"Passes tolerance: {abs(0.8898-f1) <= 0.15}")

    return {"label": label, "extreme_pct": extreme_pct, "f1": f1, "auc": auc}

def main():
    logger.info("=" * 60)
    logger.info("c3_46_h8_gb_relabeled.py started")
    logger.info("=" * 60)

    results = []
    results.append(test_gb(0.9906, "Original (99.06th pct)"))
    results.append(test_gb(0.8744, "Harmonized (87.44th pct)"))

    pd.DataFrame(results).to_csv(TABLES_DIR / "c3_46_h8_gb_relabeled_results.csv", index=False)
    logger.info(f"\nSaved: {TABLES_DIR}/c3_46_h8_gb_relabeled_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
