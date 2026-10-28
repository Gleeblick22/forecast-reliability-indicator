"""c3_51_gateA_checks.py (Gate A follow-ups)
1) vol_matched: same factor counts as fri_3band, assigned by highest recent_std_3h.
2) E6 degradation-shape sensitivity: beta in {1.0, 1.5, 2.03}; scale k calibrated so the
   BASELINE agent's total degradation equals the c3_50 value; only curvature changes.
Reuses simulate/run_agent/summarise from c3_50_agents_v2.py.
Output: results/tables/c3_51_gateA_checks.csv, c3_51_gateA_bootstrap.csv"""
import sys, json, importlib.util
import numpy as np
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR, DISPATCH_THRESHOLD
from config.logging_config import get_logger

spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
logger = get_logger("c3_51_gateA_checks")
KEYS = ["REGIONID", "DATETIME"]
BETAS = [1.0, 1.5, 2.03]


def main():
    theta = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["theta_d300"]
    lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
    test = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])
    test = test.merge(lab[KEYS + ["recent_std_3h"]], on=KEYS, how="left")
    test = test.sort_values(["REGIONID", "DATETIME"]).reset_index(drop=True)
    test["day"] = test.DATETIME.dt.floor("D").factorize()[0]
    groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
              for _, g in test.groupby("REGIONID", sort=False)]
    n, s = len(test), test.fri_score.values
    vol = test.recent_std_3h.fillna(0).values
    fri3 = np.where(s >= theta, 0.25, np.where(s >= 0.5, 0.75, 1.0))

    order = np.argsort(-vol, kind="stable")
    n25, n75 = int((fri3 == 0.25).sum()), int((fri3 == 0.75).sum())
    volm = np.ones(n); volm[order[:n25]] = 0.25; volm[order[n25:n25 + n75]] = 0.75
    logger.info(f"Flag counts matched: x0.25={n25}, x0.75={n75}")
    scales = {"baseline": np.ones(n), "fri_3band": fri3, "vol_matched": volm,
              "const_0.25": np.full(n, 0.25), "const_0.75": np.full(n, 0.75)}

    target = None
    rows, brow = [], []
    for beta in [2.03, 1.0, 1.5]:
        k = 1.0
        A.deg_cost = lambda d, b=beta, kk=k: A.R_REPL * A.ALPHA * kk * d ** b
        base = A.run_agent(test, scales["baseline"], groups)
        if target is None:
            target = base.deg.sum()
        k = target / base.deg.sum()
        A.deg_cost = lambda d, b=beta, kk=k: A.R_REPL * A.ALPHA * kk * d ** b
        runs = {name: A.run_agent(test, sc, groups) for name, sc in scales.items()}
        for name, r in runs.items():
            rows.append({"beta": beta, "k_calibration": round(k, 4), **A.summarise(name, test, r)})
        daily = lambda r: r.net.groupby(test.day).sum()
        for ctrl in ["baseline", "vol_matched", "const_0.25", "const_0.75"]:
            tot, lo, hi = A.boot_diff(daily(runs["fri_3band"]), daily(runs[ctrl]))
            brow.append(dict(beta=beta, comparison=f"fri_3band - {ctrl}", net_diff=round(tot),
                             ci_lo=round(lo), ci_hi=round(hi), ci_excludes_0=bool(lo > 0 or hi < 0)))
        logger.info(f"done beta={beta} (k={k:.4f})")

    res = pd.DataFrame(rows).sort_values(["beta", "agent"])
    bt = pd.DataFrame(brow)
    res.to_csv(TABLES_DIR / "c3_51_gateA_checks.csv", index=False)
    bt.to_csv(TABLES_DIR / "c3_51_gateA_bootstrap.csv", index=False)
    cols = ["beta", "agent", "net_revenue", "degradation", "gross_revenue", "mwh_into_overforecast"]
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        logger.info(f"\n{res[cols]}")
        logger.info(f"\nPaired daily bootstrap:\n{bt}")
    sys.exit(0)


if __name__ == "__main__":
    main()
