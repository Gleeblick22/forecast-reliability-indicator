"""
c3_19_h7_overlay_redesign.py
==============================
H7 Revenue -- Redesigned simulation (post-hoc exploratory).
NOT pre-registered. Deviation D-019 recorded in COMPLIANCE.md.

Implements five methods from external review:

  Method 1: Risk-adjusted metrics
            Revenue per MWh discharged
            Net revenue after degradation cost

  Method 2: Transaction costs and penalties
            Wrong-way penalty (data-driven price-gap based)
            Opportunity cost when SOC depleted by false positives

  Method 3: FRI as decision overlay (not just size modifier)
            HIGH band forces dispatch overriding baseline
            LOW band vetoes dispatch overriding baseline
            MEDIUM band keeps baseline with graduated size

  Method 4: Heterogeneous battery sizes
            Small 20 MWh / Medium 100 MWh / Large 300 MWh

  Method 5: Continuous graduated dispatch
            HIGH=1.00 MEDIUM=0.75 LOW=0.25
            Direction matches Component 2 D-009

Additional statistical rigour:
  Three baseline variants (naive persistence trend)
  Bootstrap CIs on revenue difference (n=1000)
  McNemar test on dispatch decisions
  Regional breakdown in output
  FRI coverage validation

Pre-registered H7 result (-3.17%) reported separately.
This analysis addresses: Under what conditions does
FRI create economic value?

Input:  results/tables/c3_01_baseline_agent_results.csv
        results/tables/c3_02_fri_agent_results.csv
Output: results/tables/h7_overlay_results.csv
        results/tables/h7_overlay_regional.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from config.settings import TABLES_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_19_h7_overlay_redesign")


BATTERY_SIZES = {
    "small":  {"capacity_mwh": 20,  "power_mw": 10},
    "medium": {"capacity_mwh": 100, "power_mw": 50},
    "large":  {"capacity_mwh": 300, "power_mw": 150},
}

SOC_MIN                  = 0.10
SOC_MAX                  = 0.90
SOC_RESET                = 0.50
EFFICIENCY               = 0.90
INTERVAL_HRS             = 5 / 60
DISPATCH_THRESH          = 100.0
DEGRADATION_COST_PER_MWH = 10.0
WRONG_WAY_PRICE_THRESH   = 50.0
OPPORTUNITY_COST_PRICE   = 1000.0

# Band factors -- graduated dispatch not binary veto
# HIGH = extreme likely (58.68% rate) -- full dispatch
# MEDIUM = moderate (11.27% rate) -- 75% dispatch
# LOW = reliable signal (0.24% rate) -- 25% dispatch
# Note: LOW=0.25 not 0.0 because 98.4% of intervals
# are LOW band -- veto would make FRI non-operational
BAND_FACTORS = {
    "HIGH":   1.00,
    "MEDIUM": 0.75,
    "LOW":    0.25,
}


def run_simulation(df, capacity_mwh, power_mw,
                   battery_name, agent_mode):
    reg_results = []
    regions = sorted(df["REGIONID"].unique())

    for region in regions:
        reg = df[df["REGIONID"] == region].copy()
        reg = reg.sort_values("DATETIME").reset_index(drop=True)
        reg["forecast_rolling"] = (
            reg["first_forecast"]
            .rolling(window=3, min_periods=1).mean())
        reg["forecast_diff"] = (
            reg["first_forecast"].diff().fillna(0))

        soc = SOC_RESET
        prev_date = None
        depletion_caused_by_dispatch = False

        for _, row in reg.iterrows():
            dt = pd.to_datetime(row["DATETIME"])

            if prev_date is None or dt.date() != prev_date:
                soc = SOC_RESET
                prev_date = dt.date()
                depletion_caused_by_dispatch = False

            is_extreme = (row["regime"] == "extreme")
            forecast = row["first_forecast"]

            should_dispatch = False
            factor = 1.00

            if agent_mode == "baseline":
                should_dispatch = forecast >= DISPATCH_THRESH

            elif agent_mode == "persistence":
                should_dispatch = (
                    row["forecast_rolling"] >= DISPATCH_THRESH)

            elif agent_mode == "trend":
                should_dispatch = (
                    forecast >= DISPATCH_THRESH and
                    row["forecast_diff"] > 0)

            elif agent_mode == "fri_overlay":
                base_decision = forecast >= DISPATCH_THRESH
                band = row.get("fri_band", None)
                if pd.isna(band) or band is None:
                    should_dispatch = base_decision
                    factor = 1.00
                else:
                    band = str(band)
                    if band == "HIGH":
                        should_dispatch = True
                        factor = 1.00
                    elif band == "LOW":
                        # Graduated reduction not veto
                        # 98.4% LOW band -- veto is non-operational
                        should_dispatch = base_decision
                        factor = BAND_FACTORS["LOW"]
                    else:
                        should_dispatch = base_decision
                        factor = BAND_FACTORS["MEDIUM"]

            if should_dispatch and factor > 0:
                max_by_soc = (
                    (soc - SOC_MIN) * capacity_mwh / INTERVAL_HRS)
                dispatch_mw = max(
                    0.0,
                    min(max_by_soc, power_mw) * factor)
            else:
                dispatch_mw = 0.0

            mwh_out = dispatch_mw * EFFICIENCY * INTERVAL_HRS
            actual_price = row.get(
                "actual_rrp", row["last_forecast"])
            revenue = (dispatch_mw * EFFICIENCY *
                       actual_price * INTERVAL_HRS)

            wrong_way_penalty = 0.0
            wrong_way_flag = False
            if dispatch_mw > 0 and                     actual_price < WRONG_WAY_PRICE_THRESH:
                price_gap = WRONG_WAY_PRICE_THRESH - actual_price
                wrong_way_penalty = mwh_out * price_gap
                revenue -= wrong_way_penalty
                wrong_way_flag = True

            soc -= mwh_out / capacity_mwh
            soc = max(SOC_MIN, min(SOC_MAX, soc))

            if dispatch_mw > 0 and soc <= SOC_MIN + 0.05:
                depletion_caused_by_dispatch = True

            opportunity_cost = 0.0
            if (depletion_caused_by_dispatch and
                    is_extreme and dispatch_mw == 0):
                potential_mwh = power_mw * EFFICIENCY * INTERVAL_HRS
                opportunity_cost = (
                    potential_mwh *
                    (OPPORTUNITY_COST_PRICE - WRONG_WAY_PRICE_THRESH))
                revenue -= opportunity_cost

            is_sf = is_extreme and (dispatch_mw == 0)

            reg_results.append({
                "DATETIME":          dt,
                "REGIONID":          region,
                "regime":            row["regime"],
                "fri_band":          row.get("fri_band", "N/A"),
                "agent":             agent_mode,
                "battery":           battery_name,
                "should_dispatch":   should_dispatch,
                "dispatch_factor":   round(factor, 4),
                "dispatch_mw":       round(dispatch_mw, 4),
                "mwh_discharged":    round(mwh_out, 4),
                "actual_price":      round(actual_price, 4),
                "revenue":           round(revenue, 4),
                "wrong_way_penalty": round(wrong_way_penalty, 4),
                "wrong_way_flag":    wrong_way_flag,
                "opportunity_cost":  round(opportunity_cost, 4),
                "soc":               round(soc, 4),
                "is_silent_failure": is_sf,
                "is_extreme":        is_extreme,
            })

    return pd.DataFrame(reg_results)


def aggregate_metrics(df, region=None):
    if region is not None:
        df = df[df["REGIONID"] == region]
    total_rev   = df["revenue"].sum()
    total_mwh   = df["mwh_discharged"].sum()
    total_ww    = df["wrong_way_penalty"].sum()
    total_opp   = df["opportunity_cost"].sum()
    deg_cost    = total_mwh * DEGRADATION_COST_PER_MWH
    net_rev     = total_rev - deg_cost
    rev_per_mwh = total_rev / total_mwh if total_mwh > 0 else 0
    net_per_mwh = net_rev   / total_mwh if total_mwh > 0 else 0
    return {
        "total_revenue":     round(total_rev, 2),
        "total_mwh":         round(total_mwh, 4),
        "degradation_cost":  round(deg_cost, 2),
        "wrong_way_total":   round(total_ww, 2),
        "wrong_way_count":   int(df["wrong_way_flag"].sum()),
        "opportunity_total": round(total_opp, 2),
        "net_revenue":       round(net_rev, 2),
        "rev_per_mwh":       round(rev_per_mwh, 4),
        "net_per_mwh":       round(net_per_mwh, 4),
        "silent_failures":   int(df["is_silent_failure"].sum()),
        "dispatch_count":    int((df["dispatch_mw"] > 0).sum()),
    }


def pct_change(new, old):
    if old == 0 or pd.isna(old) or pd.isna(new):
        return 0.0
    return round((new - old) / abs(old) * 100, 4)


def bootstrap_rpm(df, n_iter=1000, seed=42):
    """Bootstrap 95% CI for revenue per MWh."""
    rng = np.random.default_rng(seed)
    ratios = []
    for _ in range(n_iter):
        sample = df.sample(len(df), replace=True,
                           random_state=int(rng.integers(1e9)))
        total_rev = sample["revenue"].sum()
        total_mwh = sample["mwh_discharged"].sum()
        if total_mwh > 0:
            ratios.append(total_rev / total_mwh)
    ratios = np.array(ratios)
    return {
        "rpm_point": round(df["revenue"].sum() /
                     df["mwh_discharged"].sum(), 4),
        "rpm_ci_low":  round(float(np.percentile(ratios, 2.5)), 4),
        "rpm_ci_high": round(float(np.percentile(ratios, 97.5)), 4),
    }


def bootstrap_revenue_diff(df_a, df_b, n_iter=1000, seed=42):
    rng = np.random.default_rng(seed)
    merged = df_a[["DATETIME", "REGIONID", "revenue"]].rename(
        columns={"revenue": "rev_a"}).merge(
        df_b[["DATETIME", "REGIONID", "revenue"]].rename(
            columns={"revenue": "rev_b"}),
        on=["DATETIME", "REGIONID"])
    diffs = (merged["rev_b"] - merged["rev_a"]).values
    n = len(diffs)
    boot_means = [
        rng.choice(diffs, size=n, replace=True).mean()
        for _ in range(n_iter)]
    boot_means = np.array(boot_means)
    p_value = 2 * min(
        (boot_means >= 0).mean(),
        (boot_means <= 0).mean())
    return {
        "mean_diff": round(diffs.mean(), 4),
        "ci_low":    round(np.percentile(boot_means, 2.5), 4),
        "ci_high":   round(np.percentile(boot_means, 97.5), 4),
        "p_value":   round(float(p_value), 6),
        "n":         n,
    }


def mcnemar_dispatch(df_a, df_b):
    merged = df_a[["DATETIME", "REGIONID",
                   "should_dispatch"]].rename(
        columns={"should_dispatch": "disp_a"}).merge(
        df_b[["DATETIME", "REGIONID",
              "should_dispatch"]].rename(
            columns={"should_dispatch": "disp_b"}),
        on=["DATETIME", "REGIONID"])
    a_only = int(
        (merged["disp_a"] & ~merged["disp_b"]).sum())
    b_only = int(
        (~merged["disp_a"] & merged["disp_b"]).sum())
    if (a_only + b_only) == 0:
        return {"a_only": 0, "b_only": 0,
                "chi2": 0.0, "p_value": 1.0}
    chi2 = (abs(a_only - b_only) - 1) ** 2 / (a_only + b_only)
    p = float(1 - stats.chi2.cdf(chi2, df=1))
    return {"a_only": a_only, "b_only": b_only,
            "chi2": round(chi2, 4),
            "p_value": round(p, 6)}


def report_battery(battery_name, capacity_mwh, results_dict):
    logger.info("")
    logger.info(f"  {battery_name.upper()} BATTERY ({capacity_mwh} MWh)")
    logger.info(f"  {chr(45)*80}")
    logger.info(
        f"  {chr(39)+chr(39)+chr(39)+chr(39)}Metric{chr(39)+chr(39)+chr(39)+chr(39):<26} "
        f"{'Baseline':>12} {'Persist':>12} "
        f"{'Trend':>12} {'FRI Overlay':>12}")
    logger.info(f"  {chr(45)*80}")
    for label, key in [
        ("Total Revenue ($)",   "total_revenue"),
        ("Net Revenue ($)",     "net_revenue"),
        ("Rev per MWh ($)",     "rev_per_mwh"),
        ("Net per MWh ($)",     "net_per_mwh"),
        ("MWh Discharged",      "total_mwh"),
        ("Wrong-way ($)",       "wrong_way_total"),
        ("Opportunity ($)",     "opportunity_total"),
        ("Silent Failures",     "silent_failures"),
        ("Dispatch Events",     "dispatch_count"),
    ]:
        b = results_dict["baseline"][key]
        p = results_dict["persistence"][key]
        t = results_dict["trend"][key]
        f = results_dict["fri_overlay"][key]
        logger.info(
            f"  {label:<30} {b:>12,.2f} {p:>12,.2f} "
            f"{t:>12,.2f} {f:>12,.2f}")


def main():
    logger.info("=" * 60)
    logger.info("c3_19_h7_overlay_redesign.py started")
    logger.info("POST-HOC EXPLORATORY ANALYSIS -- D-019")
    logger.info("Band: HIGH=1.00 MED=0.75 LOW=0.25 (D-009)")
    logger.info("=" * 60)

    base_raw = pd.read_csv(
        TABLES_DIR / "c3_01_baseline_agent_results.csv",
        parse_dates=["DATETIME"])
    fri_raw  = pd.read_csv(
        TABLES_DIR / "c3_02_fri_agent_results.csv",
        parse_dates=["DATETIME"])

    if "actual_rrp" not in base_raw.columns:
        logger.warning(
            "actual_rrp not found -- using last_forecast "
            "as proxy for settled RRP (per D-008/D-009)")

    # Drop existing NaN fri columns from baseline before merge
    base_clean = base_raw.drop(
        columns=["fri_score", "fri_band"], errors="ignore")
    fri_scores = fri_raw[[
        "DATETIME", "REGIONID", "fri_score", "fri_band"]].copy()
    base_with_fri = base_clean.merge(
        fri_scores, on=["DATETIME", "REGIONID"], how="left")

    n_total   = len(base_with_fri)
    n_with    = base_with_fri["fri_score"].notna().sum()
    coverage  = 100 * n_with / n_total if n_total > 0 else 0
    logger.info(f"Intervals: {n_total:,}")
    logger.info(f"FRI coverage: {n_with:,} ({coverage:.1f}%)")
    if coverage < 80:
        logger.warning(
            f"FRI coverage {coverage:.1f}% below 80% -- "
            "results dominated by fallback behaviour")

    summary_rows  = []
    regional_rows = []

    for battery_name, params in BATTERY_SIZES.items():
        cap = params["capacity_mwh"]
        pwr = params["power_mw"]
        logger.info(
            f"Simulating {battery_name} ({cap} MWh / {pwr} MW)...")

        sims = {}
        for mode in ["baseline", "persistence",
                     "trend", "fri_overlay"]:
            src = base_with_fri if mode == "fri_overlay"                   else base_raw
            sims[mode] = run_simulation(
                src, cap, pwr, battery_name, mode)

        results = {m: aggregate_metrics(s)
                   for m, s in sims.items()}
        report_battery(battery_name, cap, results)

        boot = bootstrap_revenue_diff(
            sims["baseline"], sims["fri_overlay"],
            n_iter=1000, seed=42)
        mcn  = mcnemar_dispatch(
            sims["baseline"], sims["fri_overlay"])

        # Bootstrap CI on revenue per MWh
        rpm_base = bootstrap_rpm(sims["baseline"])
        rpm_fri  = bootstrap_rpm(sims["fri_overlay"])

        logger.info(
            f"  Bootstrap: mean_diff={boot['mean_diff']:.4f} "
            f"CI=[{boot['ci_low']:.4f},{boot['ci_high']:.4f}] "
            f"p={boot['p_value']:.4f}")
        logger.info(
            f"  Rev/MWh baseline: "
            f"{rpm_base['rpm_point']:.2f} "
            f"[{rpm_base['rpm_ci_low']:.2f}, "
            f"{rpm_base['rpm_ci_high']:.2f}]")
        logger.info(
            f"  Rev/MWh overlay:  "
            f"{rpm_fri['rpm_point']:.2f} "
            f"[{rpm_fri['rpm_ci_low']:.2f}, "
            f"{rpm_fri['rpm_ci_high']:.2f}]")
        ci_overlap = (rpm_fri['rpm_ci_low'] < rpm_base['rpm_ci_high'])

        logger.info(
            f"  CIs overlap: {ci_overlap} "
            f"({'NOT significant' if ci_overlap else 'SIGNIFICANT'})")
        logger.info(
            f"  McNemar: chi2={mcn['chi2']:.2f} "
            f"p={mcn['p_value']:.6f} "
            f"base_only={mcn['a_only']} "
            f"overlay_only={mcn['b_only']}")

        b = results["baseline"]
        f = results["fri_overlay"]
        summary_rows.append({
            "battery":            battery_name,
            "capacity_mwh":       cap,
            "baseline_revenue":   b["total_revenue"],
            "overlay_revenue":    f["total_revenue"],
            "revenue_pct":
                pct_change(f["total_revenue"],
                           b["total_revenue"]),
            "baseline_net":       b["net_revenue"],
            "overlay_net":        f["net_revenue"],
            "net_pct":
                pct_change(f["net_revenue"],
                           b["net_revenue"]),
            "baseline_rpm":       b["rev_per_mwh"],
            "overlay_rpm":        f["rev_per_mwh"],
            "rpm_pct":
                pct_change(f["rev_per_mwh"],
                           b["rev_per_mwh"]),
            "baseline_npm":       b["net_per_mwh"],
            "overlay_npm":        f["net_per_mwh"],
            "npm_pct":
                pct_change(f["net_per_mwh"],
                           b["net_per_mwh"]),
            "baseline_mwh":       b["total_mwh"],
            "overlay_mwh":        f["total_mwh"],
            "mwh_pct":
                pct_change(f["total_mwh"],
                           b["total_mwh"]),
            "baseline_sf":        b["silent_failures"],
            "overlay_sf":         f["silent_failures"],
            "sf_pct":
                pct_change(f["silent_failures"],
                           b["silent_failures"]),
            "baseline_ww":        b["wrong_way_total"],
            "overlay_ww":         f["wrong_way_total"],
            "baseline_opp":       b["opportunity_total"],
            "overlay_opp":        f["opportunity_total"],
            "boot_mean_diff":     boot["mean_diff"],
            "boot_ci_low":        boot["ci_low"],
            "boot_ci_high":       boot["ci_high"],
            "boot_p_value":       boot["p_value"],
            "baseline_rpm_point": rpm_base["rpm_point"],
            "baseline_rpm_ci_low": rpm_base["rpm_ci_low"],
            "baseline_rpm_ci_high": rpm_base["rpm_ci_high"],
            "overlay_rpm_point":  rpm_fri["rpm_point"],
            "overlay_rpm_ci_low": rpm_fri["rpm_ci_low"],
            "overlay_rpm_ci_high": rpm_fri["rpm_ci_high"],
            "mcnemar_chi2":       mcn["chi2"],
            "mcnemar_p":          mcn["p_value"],
            "base_only_disp":     mcn["a_only"],
            "overlay_only_disp":  mcn["b_only"],
        })

        for region in sorted(
                sims["baseline"]["REGIONID"].unique()):
            b_r = aggregate_metrics(
                sims["baseline"], region=region)
            f_r = aggregate_metrics(
                sims["fri_overlay"], region=region)
            regional_rows.append({
                "battery":          battery_name,
                "region":           region,
                "baseline_revenue": b_r["total_revenue"],
                "overlay_revenue":  f_r["total_revenue"],
                "revenue_pct":
                    pct_change(f_r["total_revenue"],
                               b_r["total_revenue"]),
                "baseline_sf":      b_r["silent_failures"],
                "overlay_sf":       f_r["silent_failures"],
                "baseline_mwh":     b_r["total_mwh"],
                "overlay_mwh":      f_r["total_mwh"],
                "baseline_rpm":     b_r["rev_per_mwh"],
                "overlay_rpm":      f_r["rev_per_mwh"],
            })

    df_summary  = pd.DataFrame(summary_rows)
    df_regional = pd.DataFrame(regional_rows)
    df_summary.to_csv(
        TABLES_DIR / "h7_overlay_results.csv", index=False)
    df_regional.to_csv(
        TABLES_DIR / "h7_overlay_regional.csv", index=False)

    logger.info("=" * 60)
    logger.info("H7 OVERLAY REDESIGN COMPLETE")
    cols = ["battery", "revenue_pct", "net_pct",
            "rpm_pct", "npm_pct", "sf_pct",
            "boot_p_value"]
    logger.info(df_summary[cols].to_string(index=False))
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
