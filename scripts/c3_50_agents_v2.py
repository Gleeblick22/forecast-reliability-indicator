"""c3_50_agents_v2.py (Roadmap P2.4-P2.6). Corrected FRI mapping (high s_hat = scale down),
one battery per region, decision on f_decision, revenue at settled p_disp30,
ex-ante charging (replenish only in later intervals with f_decision <= 20).
Old inverted mapping kept as 'fri_inverted_old'."""
import sys, json
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve
from config.settings import (PROCESSED_DIR, TABLES_DIR, DISPATCH_THRESHOLD,
    BATTERY_CAPACITY_MWH as CAP, BATTERY_POWER_MW as PMAX, BATTERY_SOC_MIN as SMIN,
    BATTERY_SOC_RESET_VALUE as SRESET, BATTERY_DISCHARGE_EFF as ETA_D,
    BATTERY_CHARGE_EFF as ETA_C, BATTERY_MIN_DISPATCH_MW as PMIN)
from config.logging_config import get_logger

logger = get_logger("c3_50_agents_v2")
KEYS = ["REGIONID", "DATETIME"]
DT, CHARGE_TRIGGER = 0.5, 20.0
ALPHA, BETA, R_REPL = 5.04e-4, 2.03, 42_000_000
SF_REGIME, SF_DELTA, UNREL = 300.0, 100.0, 300.0
N_RANDOM, N_BOOT, SEED = 100, 2000, 42
rng = np.random.default_rng(SEED)


def deg_cost(depth):
    return R_REPL * ALPHA * depth ** BETA


def simulate(day, dec, price, scale):
    n = len(dec)
    disp, deg, rev, chg = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n
    soc, cur, deficit = SRESET, -1, 0.0
    for i in range(n):
        if day[i] != cur:
            soc, cur = SRESET, day[i]
        if dec[i] >= DISPATCH_THRESHOLD and soc > SMIN:
            maxd = min(PMAX, (soc - SMIN) * CAP / DT)
            d = min(maxd, max(PMIN, maxd * scale[i]))
            e = d * DT
            soc -= e / CAP
            disp[i], deg[i], rev[i] = d, deg_cost(e / CAP), d * ETA_D * price[i] * DT
            deficit += e
        elif dec[i] <= CHARGE_TRIGGER and deficit > 0:
            amt = min(PMAX * DT, deficit)
            chg[i] = (amt / ETA_C) * price[i]
            deficit -= amt
    return disp, deg, rev, chg, deficit


def run_agent(test, scale, groups):
    parts, left = [], 0.0
    for idx, day, dec, price in groups:
        d, g, r, c, lf = simulate(day, dec, price, scale[idx].tolist())
        parts.append(pd.DataFrame({"disp": d, "deg": g, "rev": r, "chg": c}, index=idx))
        left += lf
    r = pd.concat(parts).sort_index()
    r["net"] = r.rev - r.deg - r.chg
    r.attrs["left"] = left
    return r


def summarise(name, test, r):
    dispd = r.disp > 0
    over = test.f_decision - test.p_disp30
    sf = dispd & (test.p_disp30 >= SF_REGIME) & (over > SF_DELTA)
    bad = dispd & (over > UNREL)
    return dict(agent=name, dispatch_intervals=int(dispd.sum()),
                mwh_discharged=round((r.disp * DT).sum(), 1),
                gross_revenue=round(r.rev.sum()), degradation=round(r.deg.sum()),
                charging_cost=round(r.chg.sum()), net_revenue=round(r.net.sum()),
                unreplenished_mwh=round(r.attrs["left"], 1), silent_failures=int(sf.sum()),
                dispatched_into_overforecast=int(bad.sum()),
                mwh_into_overforecast=round((r.disp[bad] * DT).sum(), 1))


def boot_diff(a, b):
    diff = (a - b).values
    reps = rng.choice(diff, (N_BOOT, len(diff))).sum(axis=1)
    return diff.sum(), np.percentile(reps, 2.5), np.percentile(reps, 97.5)


def main():
    logger.info("c3_50_agents_v2.py started")
    theta = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["theta_d300"]
    lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
    test = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])
    test = test.merge(lab[KEYS + ["recent_std_3h"]], on=KEYS, how="left")
    test = test.sort_values(["REGIONID", "DATETIME"]).reset_index(drop=True)
    test["day"] = test.DATETIME.dt.floor("D").factorize()[0]
    groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
              for _, g in test.groupby("REGIONID", sort=False)]

    val = lab[(lab.partition == "train") & (lab.DATETIME >= "2022-08-01")]
    p, rr, t = precision_recall_curve(val.y_v2_d300, val.recent_std_3h.fillna(0))
    v_theta = float(t[np.argmax((2 * p * rr / (p + rr + 1e-12))[:-1])])
    logger.info(f"theta={theta:.6f}  v_theta={v_theta:.2f}")

    s, vol = test.fri_score.values, test.recent_std_3h.fillna(0).values
    trig = test.f_decision.values >= DISPATCH_THRESHOLD
    fri3 = np.where(s >= theta, 0.25, np.where(s >= 0.5, 0.75, 1.0))
    n = len(test)
    scales = {"baseline": np.ones(n), "fri_3band": fri3,
              "fri_binary": np.where(s >= theta, 0.25, 1.0),
              "fri_inverted_old": np.where(s >= 0.75, 1.0, np.where(s >= 0.5, 0.75, 0.25)),
              "const_0.25": np.full(n, 0.25), "const_0.75": np.full(n, 0.75),
              "vol_binary": np.where(vol >= v_theta, 0.25, 1.0)}
    logger.info(f"Triggers: {trig.sum():,}; fri_3band mix: {pd.Series(fri3[trig]).value_counts().to_dict()}")

    runs, rows = {}, []
    for name, sc in scales.items():
        runs[name] = run_agent(test, sc, groups)
        rows.append(summarise(name, test, runs[name]))
        logger.info(f"done {name}")

    mix, rand_net = fri3[trig], []
    for k in range(N_RANDOM):
        sc = np.ones(n); sc[trig] = rng.choice(mix, trig.sum())
        r = run_agent(test, sc, groups); rand_net.append(r.net.sum())
        if k == 0:
            rows.append(summarise("random_matched_seed0", test, r))
    rand_net = np.array(rand_net)
    pd.DataFrame({"net_revenue": rand_net}).to_csv(TABLES_DIR / "c3_50_random_matched.csv", index=False)

    summ = pd.DataFrame(rows)
    summ.to_csv(TABLES_DIR / "c3_50_agents_summary.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        logger.info(f"\n{summ}")
    fri_net = summ.loc[summ.agent == "fri_3band", "net_revenue"].iloc[0]
    logger.info(f"random_matched net: mean {rand_net.mean():,.0f} "
                f"[{np.percentile(rand_net, 2.5):,.0f} to {np.percentile(rand_net, 97.5):,.0f}]; "
                f"FRI beats {np.mean(fri_net > rand_net) * 100:.0f}% of seeds")

    daily = lambda r: r.net.groupby(test.day).sum()
    brow = []
    for a, b in [("fri_3band", c) for c in ["baseline", "const_0.25", "const_0.75", "vol_binary",
                 "fri_inverted_old"]] + [("fri_binary", "vol_binary")]:
        tot, lo, hi = boot_diff(daily(runs[a]), daily(runs[b]))
        brow.append(dict(comparison=f"{a} - {b}", net_diff=round(tot), ci_lo=round(lo),
                         ci_hi=round(hi), ci_excludes_0=bool(lo > 0 or hi < 0)))
    bt = pd.DataFrame(brow)
    bt.to_csv(TABLES_DIR / "c3_50_paired_bootstrap.csv", index=False)
    logger.info(f"\nPaired daily bootstrap (net revenue, AUD):\n{bt}")
    sys.exit(0)


if __name__ == "__main__":
    main()
