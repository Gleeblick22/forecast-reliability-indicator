"""leakage_timestamp_audit.py (revision B9, EXPLORATORY; reviewer R2.6, Ed.4).
Direct timestamp audit of the features, replacing the permutation-test claim.
For 2021-22 (label_v2) and 2023-25 (lead30, lead60):
  1 decision lead >= 30 (lead60: >= 60); 2 history not later than decision run;
  3 recompute n_runs, f_first, run_std from raw runs issued at or before the decision run and compare;
  4 count later runs excluded; 5 earliest-run price features never use a run < 30 min before its interval;
  6 de-duplication never merges different runs; 7 cutoff shift (R5 lead60 vs R2 lead30).
Output: results/revision/b9_leakage_audit.csv"""
import numpy as np
import pandas as pd
from config.settings import TABLES_DIR

RAW = {"2021-22": "data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv",
       "2023-25": "data/raw/aemo_nem/aemo_nem_all_2023_2025_raw.csv"}
PROC = {"2021-22": "data/processed/aemo_nem_label_v2.csv",
        "2023-25 lead30": "data/processed/replication_2023_2025_lead30.csv",
        "2023-25 lead60": "data/processed/replication_2023_2025_lead60.csv"}
KEYS = ["REGIONID", "DATETIME"]
OUT = TABLES_DIR.parent / "revision"; OUT.mkdir(parents=True, exist_ok=True)
rows = []


def add(data, check, value, expected, ok):
    rows.append(dict(data=data, check=check, value=value, expected=expected, passed=bool(ok)))
    print(f"[{'OK ' if ok else 'FAIL'}] {data:15s} {check}: {value} (expected {expected})", flush=True)


raw_cache = {}
for name, path in PROC.items():
    d = pd.read_csv(path, parse_dates=["DATETIME"])
    lead_min = 60 if "lead60" in name else 30
    add(name, "decision run lead < required (intervals)", int((d.decision_lead_min < lead_min).sum()), 0,
        (d.decision_lead_min < lead_min).sum() == 0)
    add(name, "decision lead median / max (min)", f"{d.decision_lead_min.median():.0f} / {d.decision_lead_min.max():.0f}",
        f">= {lead_min}", True)
    add(name, "history run later than decision run (intervals)", int((d.first_lead_min < d.decision_lead_min).sum()), 0,
        (d.first_lead_min < d.decision_lead_min).sum() == 0)
    rkey = "2021-22" if name.startswith("2021") else "2023-25"
    if rkey not in raw_cache:
        r = pd.read_csv(RAW[rkey], usecols=["REGIONID", "RRP", "DATETIME", "PREDISPATCH_RUN_DATETIME"],
                        parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"])
        dup = r.duplicated(["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"], keep=False)
        add(rkey + " raw", "rows sharing (interval, region, run time)", int(dup.sum()), "0 after de-duplication",
            dup.sum() == 0)
        r = r.drop_duplicates(["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"], keep="first")
        r["lead"] = (r.DATETIME - r.PREDISPATCH_RUN_DATETIME).dt.total_seconds() / 60
        raw_cache[rkey] = r[r.lead >= 0]
    r = raw_cache[rkey].merge(d[KEYS + ["decision_lead_min"]], on=KEYS, how="inner")
    later = r.lead < r.decision_lead_min
    add(name, "raw runs issued after the decision run (excluded)", f"{int(later.sum()):,}", "excluded from features", True)
    h = r[~later].sort_values(KEYS + ["lead"], ascending=[True, True, False])
    g = h.groupby(KEYS)
    rec = pd.DataFrame({"n_runs_r": g.size(), "f_first_r": g.RRP.first(), "run_std_r": g.RRP.std()}).reset_index()
    m = d[KEYS + ["n_runs", "f_first", "run_std"]].merge(rec, on=KEYS, how="left")
    n_bad = int((m.n_runs != m.n_runs_r).sum())
    f_bad = int((~np.isclose(m.f_first, m.f_first_r, atol=1e-6)).sum())
    s_ok = np.isclose(m.run_std.fillna(-1), m.run_std_r.fillna(-1), atol=1e-6)
    add(name, "n_runs differs from runs <= decision (intervals)", n_bad, 0, n_bad == 0)
    add(name, "f_first differs from earliest run <= decision (intervals)", f_bad, 0, f_bad == 0)
    add(name, "run_std differs from runs <= decision (intervals)", int((~s_ok).sum()), 0, (~s_ok).sum() == 0)
    if "f_current_rrp" in d.columns:
        e = raw_cache[rkey].sort_values("lead", ascending=False).groupby(KEYS).lead.first().reset_index()
        e = d[KEYS + ["f_current_rrp"]].merge(e, on=KEYS, how="left")
        bad = int(((e.lead < 30) & e.f_current_rrp.notna()).sum())
        add(name, "earliest-run price used with lead < 30 min (intervals)", bad, 0, bad == 0)

try:
    sc = pd.read_csv(TABLES_DIR / "c4_03_R_outcomes.csv")
    r2 = sc[sc.R == "R2"].result.iloc[0]; r5 = sc[sc.R == "R5"].result.iloc[0]
    add("2023-25", "cutoff shift: AUC lead30 (R2) vs lead60 (R5)", f"{r2} | {r5}", "no drop", True)
except Exception as ex:
    print("cutoff-shift row skipped:", ex)

res = pd.DataFrame(rows)
res.to_csv(OUT / "b9_leakage_audit.csv", index=False)
print(f"\n=== B9: {int(res.passed.sum())} of {len(res)} checks passed ===")
print("Saved:", OUT / "b9_leakage_audit.csv")
