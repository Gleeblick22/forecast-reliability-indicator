"""c1_31_rebuild_price_features.py  (leakage fix)
c1_07 built the price-dynamics features from latest_rrp INCLUDING the current interval;
in 21.5% of intervals that run has lead < 30 min (issued after the decision point).
Rebuild the same nine features from the EARLIEST run q = f(1), as the manuscript (Table II)
defines them, on a complete 30-min grid per region (time-correct shifts).
Windows: 6 intervals = 3 h, 12 intervals = 6 h. Guard: q set to NaN if earliest lead < 30 min.
Output: data/processed/price_features_earliest.csv"""
import sys
import numpy as np
import pandas as pd
from config.settings import AEMO_RAW_DIR, PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_31_rebuild_price_features")
KEYS = ["REGIONID", "DATETIME"]
df = pd.read_csv(AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv",
                 usecols=["REGIONID", "RRP", "DATETIME", "PREDISPATCH_RUN_DATETIME"],
                 parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"])
df["lead"] = (df.DATETIME - df.PREDISPATCH_RUN_DATETIME).dt.total_seconds() / 60
df = df[df.lead >= 0]
e = (df.sort_values("lead", ascending=False).groupby(KEYS, as_index=False).first()
       [KEYS + ["RRP", "lead"]].rename(columns={"RRP": "q", "lead": "q_lead"}))
bad = e.q_lead < 30
logger.info(f"Earliest-run lead stats:\n{e.q_lead.describe()}\nIntervals with earliest lead < 30 min (q -> NaN): {bad.sum():,}")
e.loc[bad, "q"] = np.nan

out = []
for reg, g in e.groupby("REGIONID"):
    grid = pd.date_range(g.DATETIME.min(), g.DATETIME.max(), freq="30min")
    r = g.set_index("DATETIME").reindex(grid)
    r.index.name = "DATETIME"
    q = r["q"]
    f = pd.DataFrame(index=r.index)
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
    out.append(f.reset_index()[f.reset_index().DATETIME.isin(g.DATETIME)])
res = pd.concat(out, ignore_index=True)
res.to_csv(PROCESSED_DIR / "price_features_earliest.csv", index=False)
logger.info(f"Saved {len(res):,} rows -> price_features_earliest.csv")
sys.exit(0)
