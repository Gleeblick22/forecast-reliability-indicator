"""r1_forecast_conditioned.py (revision B1, EXPLORATORY; reviewer R2.1, R2.8, DA.2, Ed.1).
Registered R1 uses the settled-price regime (p_disp30 >= 300). This adds, for test 2 (2023-25):
A registered R1 reproduced (check); B forecast-conditioned R1 (f_decision >= 300);
C decision-forecast MAE / naive MAE (mean settled price over the 3 h ending 30 min before t);
D medians and day-block bootstrap 95% CIs. Output: results/revision/b1_r1_forecast_conditioned.csv"""
import numpy as np
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR

TAU, SEED, NBOOT = 300.0, 42, 1000
OUT = TABLES_DIR.parent / "revision"; OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

d = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"])
d = d.sort_values(["REGIONID", "DATETIME"]).reset_index(drop=True)
for c in ("error_v2", "p_disp30", "f_decision"):
    assert c in d.columns, f"missing column {c}"


def naive_forecast(g):
    s = g.set_index("DATETIME").p_disp30
    m = s.rolling("3h", closed="right").mean().shift(freq="30min")
    return m.reindex(g.DATETIME).values


d["naive"] = np.concatenate([naive_forecast(g) for _, g in d.groupby("REGIONID", sort=True)])
d["err_naive"] = (d.naive - d.p_disp30).abs()
d["day"] = d.DATETIME.dt.floor("D")


def boot_ratio(g, num_mask, den_mask, col):
    days = g.day.values; ud = np.unique(days)
    idx = {k: np.where(days == k)[0] for k in ud}
    reps = []
    for _ in range(NBOOT):
        pick = np.concatenate([idx[k] for k in rng.choice(ud, len(ud))])
        v, nm, dm = g[col].values[pick], num_mask[pick], den_mask[pick]
        if nm.sum() and dm.sum():
            reps.append(v[nm].mean() / v[dm].mean())
    return np.percentile(reps, 2.5), np.percentile(reps, 97.5)


rows = []
for reg, g in d.groupby("REGIONID", sort=True):
    g = g.reset_index(drop=True)
    ok = g.err_naive.notna().values
    e = g.error_v2.values
    for regime, ext in (("settled (registered)", (g.p_disp30 >= TAU).values),
                        ("forecast-conditioned", (g.f_decision >= TAU).values)):
        nor = ~ext
        lo, hi = boot_ratio(g, ext, nor, "error_v2")
        rows.append(dict(region=reg, regime=regime, n_extreme=int(ext.sum()), n_normal=int(nor.sum()),
                         mae_extreme=round(e[ext].mean(), 2), mae_normal=round(e[nor].mean(), 2),
                         ratio_of_means=round(e[ext].mean() / e[nor].mean(), 2), ci_lo=round(lo, 2), ci_hi=round(hi, 2),
                         ratio_of_medians=round(np.median(e[ext]) / np.median(e[nor]), 2),
                         rel_mae_vs_naive_extreme=round(e[ext & ok].mean() / g.err_naive.values[ext & ok].mean(), 3),
                         rel_mae_vs_naive_normal=round(e[nor & ok].mean() / g.err_naive.values[nor & ok].mean(), 3)))

t = pd.DataFrame(rows)
t.to_csv(OUT / "b1_r1_forecast_conditioned.csv", index=False)
ref = pd.read_csv(TABLES_DIR / "c4_03_R1_regions.csv")
chk = t[t.regime == "settled (registered)"].merge(ref[["region", "ratio"]], on="region")
pd.set_option("display.width", 250)
print("\n=== B1: R1 by regime, test 2 (2023-25) ===")
print(t.drop(columns=["n_normal"]).to_string(index=False))
print(f"\nCHECK settled-regime ratios vs c4_03_R1_regions.csv: max |diff| = {(chk.ratio_of_means - chk.ratio).abs().max():.3f} (should be < 0.01)")
print("Saved:", OUT / "b1_r1_forecast_conditioned.csv")
