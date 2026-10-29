"""c4_08_auc_block_bootstrap.py (exploratory, added 29 Oct 2026 after registration)
Daily-block bootstrap CIs for the FRI AUC, to check that the stratified interval bootstrap
(Section III.H) is not too narrow when unreliable intervals cluster in time.
Whole days (all five regions together) are resampled with replacement, 2,000 times.
Input:  results/tables/c2_31_test_scores.csv (2022 test 1), results/tables/c4_03_scores.csv (2023-25 test 2)
Output: results/tables/c4_08_auc_block_bootstrap.csv"""
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import roc_auc_score

T = Path("results/tables")
FILES = {"test1_2022": T / "c2_31_test_scores.csv", "test2_2023_25": T / "c4_03_scores.csv"}
B, SEED = 2000, 42


def pick(cols, starts, contains):
    for c in cols:
        if any(c.lower().startswith(s) for s in starts):
            return c
    for c in cols:
        if any(k in c.lower() for k in contains):
            return c
    raise KeyError(f"no column for {starts}/{contains} in {list(cols)}")


rows = []
for name, f in FILES.items():
    df = pd.read_csv(f)
    ycol = pick(df.columns, ["y_v2", "y_"], ["label", "unreliable"])
    scol = pick(df.columns, ["fri_score"], ["score", "prob"])
    tcol = pick(df.columns, ["datetime"], ["time", "date"])
    df["T"] = pd.to_datetime(df[tcol], format="mixed")
    print(f"\n{name}: file={f.name} label={ycol} score={scol} rows={len(df):,} "
          f"from {df['T'].min()} to {df['T'].max()} positives={int(df[ycol].sum())}")
    auc = roc_auc_score(df[ycol], df[scol])
    df["day"] = df["T"].dt.floor("D")
    days = df["day"].unique()
    idx = {d: g.index.values for d, g in df.groupby("day")}
    y, s = df[ycol].values, df[scol].values
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(B):
        pick_days = rng.choice(days, size=len(days), replace=True)
        ii = np.concatenate([idx[d] for d in pick_days])
        if y[ii].min() == y[ii].max():
            continue
        boots.append(roc_auc_score(y[ii], s[ii]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"AUC = {auc:.3f}   daily-block 95% CI [{lo:.3f}, {hi:.3f}]   (valid resamples {len(boots)}/{B}, days {len(days)})")
    rows.append(dict(sample=name, n=len(df), positives=int(y.sum()), days=len(days), auc=round(auc, 4),
                     block_ci_lo=round(lo, 4), block_ci_hi=round(hi, 4), resamples=len(boots)))
out = T / "c4_08_auc_block_bootstrap.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print("\nSaved", out)
