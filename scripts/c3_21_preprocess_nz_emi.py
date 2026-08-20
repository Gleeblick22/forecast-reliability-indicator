"""
c3_21_preprocess_nz_emi.py
===========================
Preprocess New Zealand EMI data for H8 cross-market validation.
Secondary Dataset 2 -- NZ NZEM predispatch prices.

Steps:
  1. Extract PRSS revision sequences per island per trading period
  2. Compute first_forecast last_forecast forecast_error run_count
  3. Merge with nodal final prices for actual_rrp
  4. Aggregate by island (NI/SI) like NEM regions
  5. Apply NZD 300/MWh extreme threshold
  6. Engineer same 10 features as NEM model

Input:  data/raw/nz_emi/prss_2021/
        data/raw/nz_emi/prss_2022/
        data/raw/nz_emi/nodal_2021/
        data/raw/nz_emi/nodal_2022/
Output: data/processed/nz_emi_processed.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import zipfile
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from config.settings import RAW_DIR, PROCESSED_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_21_preprocess_nz_emi")

NZ_DIR         = RAW_DIR / "nz_emi"
EXTREME_THRESH = 300.0
PEAK_HOURS     = range(7, 22)

PRSS_COLS = [
    "node", "trading_date", "trading_period",
    "price", "run_datetime", "price_type"
]


def load_prss_zip(zip_path):
    rows = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if not name.endswith(".csv"):
                    continue
                with zf.open(name) as f:
                    try:
                        df = pd.read_csv(
                            f, header=None,
                            names=PRSS_COLS,
                            dtype={"trading_period": int,
                                   "price": float}
                        )
                        rows.append(df)
                    except Exception:
                        continue
    except Exception as e:
        logger.warning("Failed " + str(zip_path.name) + ": " + str(e))
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    df = pd.concat(rows, ignore_index=True)
    df["run_datetime"] = pd.to_datetime(
        df["run_datetime"], dayfirst=True, errors="coerce"
    )
    df["trading_date"] = pd.to_datetime(
        df["trading_date"], dayfirst=True, errors="coerce"
    )
    return df


def build_revision_sequences(prss_df):
    if prss_df.empty:
        return pd.DataFrame()

    agg = (
        prss_df
        .groupby(["trading_date", "trading_period",
                  "run_datetime"])["price"]
        .mean()
        .reset_index()
    )

    agg_sorted = agg.sort_values("run_datetime")
    first_last = (
        agg_sorted
        .groupby(["trading_date", "trading_period"])
        .agg(
            first_forecast=("price", lambda x: x.iloc[0]),
            last_forecast=("price",  lambda x: x.iloc[-1]),
            run_count=("price", "count"),
        )
        .reset_index()
    )

    first_last["forecast_error"] = (
        first_last["last_forecast"] - first_last["first_forecast"]
    )
    return first_last


def load_nodal_prices(csv_path):
    try:
        df = pd.read_csv(csv_path)
        df["TradingDate"] = pd.to_datetime(
            df["TradingDate"], errors="coerce"
        )
        agg = (
            df
            .groupby(["TradingDate", "TradingPeriod",
                      "Island"])["DollarsPerMegawattHour"]
            .mean()
            .reset_index()
            .rename(columns={
                "TradingDate": "trading_date",
                "TradingPeriod": "trading_period",
                "Island": "island",
                "DollarsPerMegawattHour": "actual_rrp",
            })
        )
        return agg
    except Exception as e:
        logger.warning("Failed " + str(csv_path.name) + ": " + str(e))
        return pd.DataFrame()


def trading_period_to_datetime(date, period):
    minutes = (period - 1) * 30
    return pd.Timestamp(date) + pd.Timedelta(minutes=minutes)


def engineer_features(df):
    df = df.sort_values(["REGIONID", "DATETIME"]).reset_index(drop=True)

    features = pd.DataFrame()
    features["DATETIME"] = df["DATETIME"]
    features["REGIONID"] = df["REGIONID"]
    # f_current_rrp = first_forecast per D-003 fix
    features["f_current_rrp"] = df["first_forecast"]
    features["f_forecast_revision"] = df["forecast_error"]

    for region in df["REGIONID"].unique():
        mask = df["REGIONID"] == region
        prices = df.loc[mask, "last_forecast"]
        features.loc[mask, "f_rolling_max_30min"] = (
            prices.rolling(1, min_periods=1).max().values
        )
        features.loc[mask, "f_rolling_mean_30min"] = (
            prices.rolling(1, min_periods=1).mean().values
        )
        features.loc[mask, "f_price_change_30min"] = (
            prices.diff(1).fillna(0).values
        )
        features.loc[mask, "f_price_change_60min"] = (
            prices.diff(2).fillna(0).values
        )
        is_high = (prices >= EXTREME_THRESH)
        features.loc[mask, "f_consecutive_high"] = (
            is_high
            .groupby(is_high.ne(is_high.shift()).cumsum())
            .cumcount()
            .values
        )

    features["f_hour_of_day"] = df["DATETIME"].dt.hour
    features["f_day_of_week"] = df["DATETIME"].dt.dayofweek
    features["f_is_peak_hour"] = (
        df["DATETIME"].dt.hour.isin(PEAK_HOURS).astype(int)
    )
    return features


def main():
    bar = "=" * 60
    logger.info(bar)
    logger.info("c3_21_preprocess_nz_emi.py started")
    logger.info("Preprocessing NZ EMI for H8 validation")
    logger.info("Extreme threshold: NZD " + str(EXTREME_THRESH) + "/MWh")
    logger.info(bar)

    all_prss  = []
    all_nodal = []

    for year in [2021, 2022]:
        prss_dir  = NZ_DIR / ("prss_"  + str(year))
        nodal_dir = NZ_DIR / ("nodal_" + str(year))

        prss_files  = sorted(prss_dir.glob("*.zip"))
        nodal_files = sorted(nodal_dir.glob("*_F.csv"))

        logger.info("")
        logger.info("Year " + str(year) + ":")
        logger.info("  PRSS files:  " + str(len(prss_files)))
        logger.info("  Nodal files: " + str(len(nodal_files)))

        prss_rows = []
        for i, zf in enumerate(prss_files):
            raw = load_prss_zip(zf)
            if not raw.empty:
                rev = build_revision_sequences(raw)
                if not rev.empty:
                    prss_rows.append(rev)
            if (i + 1) % 60 == 0:
                logger.info(
                    "  PRSS " + str(year) + ": " +
                    str(i + 1) + "/" + str(len(prss_files))
                )

        if prss_rows:
            year_prss = pd.concat(prss_rows, ignore_index=True)
            all_prss.append(year_prss)
            logger.info(
                "  PRSS " + str(year) + ": " +
                str(len(year_prss)) + " intervals"
            )

        nodal_rows = []
        for i, cf in enumerate(nodal_files):
            nd = load_nodal_prices(cf)
            if not nd.empty:
                nodal_rows.append(nd)
            if (i + 1) % 60 == 0:
                logger.info(
                    "  Nodal " + str(year) + ": " +
                    str(i + 1) + "/" + str(len(nodal_files))
                )

        if nodal_rows:
            year_nodal = pd.concat(nodal_rows, ignore_index=True)
            all_nodal.append(year_nodal)
            logger.info(
                "  Nodal " + str(year) + ": " +
                str(len(year_nodal)) + " intervals"
            )

    if not all_prss or not all_nodal:
        logger.error("No data loaded -- check input directories")
        sys.exit(1)

    prss_df  = pd.concat(all_prss,  ignore_index=True)
    nodal_df = pd.concat(all_nodal, ignore_index=True)

    logger.info("")
    logger.info("Total PRSS rows:  " + str(len(prss_df)))
    logger.info("Total Nodal rows: " + str(len(nodal_df)))

    merged_rows = []
    for island in ["NI", "SI"]:
        nodal_island = nodal_df[nodal_df["island"] == island].copy()
        merged = prss_df.merge(
            nodal_island[["trading_date", "trading_period",
                          "actual_rrp"]],
            on=["trading_date", "trading_period"],
            how="inner"
        )
        merged["island"] = island
        merged_rows.append(merged)

    df = pd.concat(merged_rows, ignore_index=True)
    logger.info("Merged rows: " + str(len(df)))

    df["DATETIME"] = df.apply(
        lambda r: trading_period_to_datetime(
            r["trading_date"], r["trading_period"]
        ),
        axis=1
    )
    df["REGIONID"] = df["island"]

    df["regime"] = np.where(
        df["actual_rrp"] >= EXTREME_THRESH, "extreme", "normal"
    )

    n_extreme = int((df["regime"] == "extreme").sum())
    pct_extreme = 100 * n_extreme / len(df) if len(df) > 0 else 0
    logger.info(
        "Extreme intervals: " + str(n_extreme) +
        " (" + ("%.2f" % pct_extreme) + "%)"
    )

    logger.info("Engineering features...")
    features = engineer_features(df)

    out = df[[
        "DATETIME", "REGIONID", "regime",
        "first_forecast", "last_forecast",
        "forecast_error", "run_count",
        "actual_rrp"
    ]].copy()
    for col in features.columns:
        if col.startswith("f_"):
            out[col] = features[col].values

    out_path = PROCESSED_DIR / "nz_emi_processed.csv"
    out.to_csv(out_path, index=False)

    logger.info("")
    logger.info(bar)
    logger.info("PREPROCESSING COMPLETE")
    logger.info("Output: " + str(out_path))
    logger.info("Rows: " + str(len(out)))
    logger.info("Columns: " + str(out.columns.tolist()))
    logger.info("Regions: " + str(sorted(out["REGIONID"].unique())))
    logger.info(
        "Extreme: " + str(n_extreme) +
        " (" + ("%.2f" % pct_extreme) + "%)"
    )
    logger.info(
        "Date range: " + str(out["DATETIME"].min()) +
        " to " + str(out["DATETIME"].max())
    )
    logger.info(bar)
    sys.exit(0)


if __name__ == "__main__":
    main()
