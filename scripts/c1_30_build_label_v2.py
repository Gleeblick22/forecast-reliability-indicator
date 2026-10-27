"""
c1_30_build_label_v2.py  (Roadmap P2.1 - label redesign)
Decision run: pre-dispatch run closest to 45 min lead within [30, 60] -> f_decision
Outcome:      mean of six 5-min DISPATCHPRICE RRPs (INTERVENTION=0), interval-ending
Label:        y_v2 = 1[|f_decision - p_disp30| > delta], delta = 300 (also 150, 500)
Features:     only from runs issued at or before the decision run.
Output:       data/processed/aemo_nem_label_v2.csv
"""
import sys
import numpy as np
import pandas as pd
from config.settings import AEMO_RAW_DIR, PROCESSED_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

logger = get_logger("c1_30_build_label_v2")

PD_FILE = AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv"
DISP_DIR = AEMO_RAW_DIR / "dispatchprice"
OUT_FILE = PROCESSED_DIR / "aemo_nem_label_v2.csv"

WIN_LO, WIN_HI, WIN_MID = 30, 60, 45
RECENT_WINDOW_MIN = 180
PRIMARY_DELTA = 300.0
DELTAS = [150.0, 300.0, 500.0]
KEYS = ["REGIONID", "DATETIME"]


def load_dispatch_30min():
    files = sorted(DISP_DIR.glob("PUBLIC_DVD_DISPATCHPRICE_*.CSV"))
    if not files:
        logger.error(f"No DISPATCHPRICE files in {DISP_DIR}. Run c1_29 first.")
        sys.exit(1)
    logger.info(f"DISPATCHPRICE files: {len(files)}")
    parts = []
    for f in files:
        d = pd.read_csv(f, skiprows=1, low_memory=False)
        d = d[d.iloc[:, 0] == "D"]
        parts.append(d[["SETTLEMENTDATE", "REGIONID", "INTERVENTION", "RRP"]])
    d = pd.concat(parts, ignore_index=True)
    d["SETTLEMENTDATE"] = pd.to_datetime(d["SETTLEMENTDATE"])
    d["INTERVENTION"] = pd.to_numeric(d["INTERVENTION"])
    d["RRP"] = pd.to_numeric(d["RRP"])
    d = d[d["INTERVENTION"] == 0].drop_duplicates(["SETTLEMENTDATE", "REGIONID"])
    d["DATETIME"] = d["SETTLEMENTDATE"].dt.ceil("30min")
    g = d.groupby(KEYS)["RRP"].agg(p_disp30="mean", n5="count").reset_index()
    logger.info(f"30-min periods: {len(g):,}; incomplete dropped: {(g['n5'] != 6).sum():,}")
    return g[g["n5"] == 6].drop(columns="n5")


def build_pd_features():
    logger.info("Loading pre-dispatch runs (large file)...")
    df = pd.read_csv(PD_FILE, usecols=["REGIONID", "RRP", "DATETIME", "PREDISPATCH_RUN_DATETIME"])
    df["DATETIME"] = pd.to_datetime(df["DATETIME"])
    df["PREDISPATCH_RUN_DATETIME"] = pd.to_datetime(df["PREDISPATCH_RUN_DATETIME"])
    df["lead_minutes"] = (df["DATETIME"] - df["PREDISPATCH_RUN_DATETIME"]).dt.total_seconds() / 60
    df = df[df["lead_minutes"] >= 0]
    logger.info(f"Pre-dispatch rows: {len(df):,}")

    win = df[(df["lead_minutes"] >= WIN_LO) & (df["lead_minutes"] <= WIN_HI)].copy()
    win["dist"] = (win["lead_minutes"] - WIN_MID).abs()
    dec = (win.sort_values("dist").groupby(KEYS, as_index=False).first()
              [KEYS + ["RRP", "lead_minutes"]]
              .rename(columns={"RRP": "f_decision", "lead_minutes": "decision_lead_min"}))
    logger.info(f"Intervals with a decision run: {len(dec):,}")

    h = df.merge(dec[KEYS + ["decision_lead_min"]], on=KEYS, how="inner")
    h = h[h["lead_minutes"] >= h["decision_lead_min"]]
    h = h.sort_values(KEYS + ["lead_minutes"], ascending=[True, True, False])
    h["step"] = h.groupby(KEYS)["RRP"].diff()
    h["abs_step"] = h["step"].abs()
    h["sgn"] = np.sign(h["step"])
    prev = h.groupby(KEYS)["sgn"].shift()
    h["flip"] = ((h["sgn"] * prev) < 0).astype(int)
    h["recent"] = h["lead_minutes"] <= (h["decision_lead_min"] + RECENT_WINDOW_MIN)

    agg = h.groupby(KEYS).agg(
        f_first=("RRP", "first"),
        first_lead_min=("lead_minutes", "first"),
        n_runs=("RRP", "size"),
        max_abs_step=("abs_step", "max"),
        n_sign_flips=("flip", "sum"),
        run_std=("RRP", "std"),
    ).reset_index()
    recent = h[h["recent"]].groupby(KEYS)["RRP"].std().rename("recent_std_3h").reset_index()

    feat = dec.merge(agg, on=KEYS, how="left").merge(recent, on=KEYS, how="left")
    feat["rev_signed"] = feat["f_decision"] - feat["f_first"]
    feat["rev_abs"] = feat["rev_signed"].abs()
    for c in ["max_abs_step", "run_std", "recent_std_3h"]:
        feat[c] = feat[c].fillna(0.0)

    assert (feat["decision_lead_min"] >= WIN_LO).all(), "decision run later than 30 min lead"
    assert (feat["first_lead_min"] >= feat["decision_lead_min"]).all(), "history after decision"
    return feat


def main():
    logger.info("=" * 60)
    logger.info("c1_30_build_label_v2.py started")
    disp = load_dispatch_30min()
    feat = build_pd_features()
    df = feat.merge(disp, on=KEYS, how="inner")
    logger.info(f"Rows with features AND settled outcome: {len(df):,}")

    df["error_v2"] = (df["f_decision"] - df["p_disp30"]).abs()
    for d in DELTAS:
        df[f"y_v2_d{int(d)}"] = (df["error_v2"] > d).astype(int)
    df["y_v2"] = df[f"y_v2_d{int(PRIMARY_DELTA)}"]

    split = pd.to_datetime(TRAIN_TEST_SPLIT)
    df["partition"] = np.where(df["DATETIME"] < split, "train", "test")

    rates = df.groupby("partition")[[f"y_v2_d{int(d)}" for d in DELTAS]].mean() * 100
    logger.info(f"\nPositive rate (%) by partition and delta:\n{rates.round(3)}")
    logger.info(f"\nBy region/partition:\n{df.groupby(['partition', 'REGIONID'])['y_v2'].agg(['mean', 'sum', 'count'])}")
    logger.info(f"\nDecision lead stats:\n{df['decision_lead_min'].describe()}")
    tr = df[df["partition"] == "train"]
    logger.info(f"\nrev_abs vs y_v2 correlation (train): {tr['rev_abs'].corr(tr['y_v2']):.4f}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)
    logger.info(f"Saved: {OUT_FILE}")
    sys.exit(0)


if __name__ == "__main__":
    main()
