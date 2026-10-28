"""c4_02 (Phase 4, P4.2): build 2023-25 labels + features with FROZEN code.
- Combines PD_*.csv (dedup on DATETIME, REGIONID, RUN; keep first), intervals 2023-01-01 00:30 .. 2026-01-01 00:00.
- Label + revision-path features: c1_30 functions imported unchanged (paths overridden only).
- Price-dynamics features: same logic as c1_31 (earliest run, 30-min grid, guard lead < 30 -> NaN).
- Two decision leads: 30 min (primary; R1-R4, R6) and 60 min (R5).
- Coverage report only; no hypothesis tests here (c4_03).
Outputs: data/processed/replication_2023_2025_lead30.csv, _lead60.csv, coverage_2023_2025.csv"""
import sys, importlib.util
import numpy as np
import pandas as pd
from config.settings import AEMO_RAW_DIR, PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c4_02_build_2023_2025")
KEYS = ["REGIONID", "DATETIME"]
PD_DIR = AEMO_RAW_DIR / "predispatch_2023_2025"
RAW_OUT = AEMO_RAW_DIR / "aemo_nem_all_2023_2025_raw.csv"
LO, HI = pd.Timestamp("2023-01-01 00:30"), pd.Timestamp("2026-01-01 00:00")

spec = importlib.util.spec_from_file_location("c1_30", "scripts/c1_30_build_label_v2.py")
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
L.PD_FILE, L.DISP_DIR = RAW_OUT, AEMO_RAW_DIR / "dispatchprice_2023_2025"


def combine():
    parts = [pd.read_csv(f, parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"])
             for f in sorted(PD_DIR.glob("PD_*.csv"))]
    df = pd.concat(parts, ignore_index=True)
    n0 = len(df)
    df = df.drop_duplicates(["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"], keep="first")
    df = df[(df.DATETIME >= LO) & (df.DATETIME <= HI)]
    df[["REGIONID", "RRP", "DATETIME", "PREDISPATCH_RUN_DATETIME"]].to_csv(RAW_OUT, index=False)
    logger.info(f"Combined {len(parts)} files: {n0:,} rows -> {len(df):,} after dedup and window")
    return df


def price_features(df):
    d = df.assign(lead=(df.DATETIME - df.PREDISPATCH_RUN_DATETIME).dt.total_seconds() / 60)
    d = d[d.lead >= 0]
    e = (d.sort_values("lead", ascending=False).groupby(KEYS, as_index=False).first()
           [KEYS + ["RRP", "lead"]].rename(columns={"RRP": "q", "lead": "q_lead"}))
    bad = e.q_lead < 30
    logger.info(f"Earliest-run lead median {e.q_lead.median():.0f} min; lead < 30 -> NaN: {bad.sum():,}")
    e.loc[bad, "q"] = np.nan
    out = []
    for reg, g in e.groupby("REGIONID"):
        grid = pd.date_range(g.DATETIME.min(), g.DATETIME.max(), freq="30min")
        q = g.set_index("DATETIME").reindex(grid)["q"]
        f = pd.DataFrame(index=grid)
        f["f_current_rrp"] = q
        f["f_rolling_mean_30min"] = q.rolling(6, min_periods=1).mean()
        f["f_rolling_max_30min"] = q.rolling(6, min_periods=1).max()
        f["f_price_change_30min"] = (q - q.shift(6)).fillna(0)
        f["f_price_change_60min"] = (q - q.shift(12)).fillna(0)
        f["f_hour_of_day"] = f.index.hour
        f["f_is_peak_hour"] = f["f_hour_of_day"].between(16, 20).astype(int)
        f["f_day_of_week"] = f.index.dayofweek
        above = (q >= 100).astype(int)
        f["f_consecutive_high"] = (above.groupby((above != above.shift()).cumsum()).cumcount() + 1) * above
        f["REGIONID"] = reg
        f = f.rename_axis("DATETIME").reset_index()
        out.append(f[f.DATETIME.isin(g.DATETIME)])
    return pd.concat(out, ignore_index=True)


def build_lead(lead, disp, pf):
    L.WIN_LO, L.WIN_HI, L.WIN_MID = (30, 60, 45) if lead == 30 else (60, 60, 60)
    feat = L.build_pd_features()
    df = feat.merge(disp, on=KEYS, how="inner").merge(pf, on=KEYS, how="left")
    df["error_v2"] = (df.f_decision - df.p_disp30).abs()
    for dlt in L.DELTAS:
        df[f"y_v2_d{int(dlt)}"] = (df.error_v2 > dlt).astype(int)
    df["y_v2"] = df["y_v2_d300"]
    df["partition"] = "replication"
    df.to_csv(PROCESSED_DIR / f"replication_2023_2025_lead{lead}.csv", index=False)
    logger.info(f"lead {lead}: {len(df):,} rows saved")
    return df


def main():
    raw = combine()
    pf = price_features(raw)
    disp = L.load_dispatch_30min()
    disp = disp[(disp.DATETIME >= LO) & (disp.DATETIME <= HI)]
    d30 = build_lead(30, disp, pf)
    d60 = build_lead(60, disp, pf)

    grid = pd.MultiIndex.from_product([sorted(raw.REGIONID.unique()),
                                       pd.date_range(LO, HI, freq="30min")], names=KEYS).to_frame(index=False)
    grid["month"] = grid.DATETIME.dt.to_period("M").astype(str)
    cov = grid.groupby(["REGIONID", "month"]).size().rename("expected").to_frame()
    for name, src in [("settled", disp), ("lead30_rows", d30), ("lead60_rows", d60)]:
        s = src.assign(month=src.DATETIME.dt.to_period("M").astype(str)).groupby(["REGIONID", "month"]).size()
        cov[name] = s
    cov = cov.fillna(0).astype(int).reset_index()
    cov["lead30_pct"] = (cov.lead30_rows / cov.expected * 100).round(2)
    cov.to_csv(PROCESSED_DIR / "coverage_2023_2025.csv", index=False)
    low = cov[cov.lead30_pct < 98]
    logger.info(f"Coverage: total expected {cov.expected.sum():,}, lead30 {cov.lead30_rows.sum():,}, "
                f"lead60 {cov.lead60_rows.sum():,}; region-months below 98%: {len(low)}")
    if len(low):
        logger.info(f"\n{low}")
    sys.exit(0)


if __name__ == "__main__":
    main()
