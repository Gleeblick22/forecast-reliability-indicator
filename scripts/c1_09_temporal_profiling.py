"""
c1_09_temporal_profiling.py
============================
POST-HOC EXPLORATORY ANALYSIS (D-024) — not pre-registered.
Results must be labelled as post-hoc exploratory in manuscript.
Cannot be used as hypothesis confirmation.

Tests whether FRI triggers BEFORE price spike onset or only
during/after. Determines whether FRI provides actionable
advance warning for autonomous battery dispatch agents.

Lookback window: 6 intervals (3 hours) — operationally
justified as NEM battery pre-positioning window.

Input:  results/tables/c3_02_fri_agent_results.csv
Output: results/tables/c1_09_temporal_profiling.csv
        results/tables/c1_09_temporal_summary.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from config.settings import (
    TABLES_DIR,
    NEM_REGIONS,
    DISPATCH_INTERVAL,
    TEMPORAL_LOOKBACK_INTERVALS,
    TEMPORAL_EPISODE_GAP_MIN,
    TEMPORAL_FRI_TRIGGER_BAND,
    TEMPORAL_EXTREME_LABEL,
    TEMPORAL_DEVIATION,
)
from config.logging_config import get_logger

logger = get_logger("c1_09_temporal_profiling")

# ── FILE PATHS ─────────────────────────────────────────────
AGENT_FILE   = TABLES_DIR / "c3_02_fri_agent_results.csv"
OUT_CSV      = TABLES_DIR / "c1_09_temporal_profiling.csv"
SUMMARY_CSV  = TABLES_DIR / "c1_09_temporal_summary.csv"


def load_agent_results() -> pd.DataFrame:
    """
    Load FRI agent results from Component 3.
    Contains DATETIME, REGIONID, regime, fri_band,
    fri_score, forecast_error per 30-min interval.
    """
    if not AGENT_FILE.exists():
        logger.error(f"Agent results not found: {AGENT_FILE}")
        sys.exit(1)
    df = pd.read_csv(AGENT_FILE, parse_dates=["DATETIME"])
    df = df.sort_values(["REGIONID", "DATETIME"]).reset_index(drop=True)
    logger.info(f"Loaded {len(df):,} intervals from {AGENT_FILE.name}")
    logger.info(f"Date range : {df['DATETIME'].min()} to {df['DATETIME'].max()}")
    logger.info(f"Extreme    : {(df['regime'] == TEMPORAL_EXTREME_LABEL).sum()} intervals")
    logger.info(f"FRI HIGH   : {(df['fri_band'] == TEMPORAL_FRI_TRIGGER_BAND).sum()} intervals")
    return df


def detect_episodes(reg_df: pd.DataFrame, region: str) -> pd.DataFrame:
    """
    Group consecutive extreme intervals into spike episodes.
    Episodes separated by gap > TEMPORAL_EPISODE_GAP_MIN minutes
    are treated as distinct events.
    """
    ext_df = reg_df[reg_df["regime"] == TEMPORAL_EXTREME_LABEL].copy()
    ext_df = ext_df.sort_values("DATETIME").reset_index(drop=True)

    if len(ext_df) == 0:
        logger.warning(f"{region}: no extreme events found")
        return ext_df

    ep_id  = 0
    ep_ids = [0]
    for i in range(1, len(ext_df)):
        gap = (
            ext_df.loc[i, "DATETIME"] - ext_df.loc[i - 1, "DATETIME"]
        ).total_seconds() / 60
        if gap > TEMPORAL_EPISODE_GAP_MIN:
            ep_id += 1
        ep_ids.append(ep_id)
    ext_df["ep_id"] = ep_ids

    n_ep = ext_df["ep_id"].nunique()
    logger.info(f"{region}: {len(ext_df)} extreme intervals → {n_ep} episodes")
    return ext_df


def classify_episode(
    ep: pd.DataFrame,
    reg_df: pd.DataFrame,
    onset: pd.Timestamp,
) -> dict:
    """
    Classify a single spike episode by FRI warning type.

    Returns warning_type:
      PRE-SPIKE    — FRI HIGH fired before onset (advance warning)
      DURING-SPIKE — FRI HIGH fired during episode (no advance)
      NO-TRIGGER   — FRI did not trigger at all
    """
    before   = reg_df[reg_df["DATETIME"] < onset]
    lookback = before.tail(TEMPORAL_LOOKBACK_INTERVALS)

    high_before = lookback[lookback["fri_band"] == TEMPORAL_FRI_TRIGGER_BAND]

    if len(high_before) > 0:
        last_high      = high_before["DATETIME"].max()
        lead_min       = (onset - last_high).total_seconds() / 60
        lead_intervals = int(lead_min / DISPATCH_INTERVAL)
        return {
            "warning_type"       : "PRE-SPIKE",
            "had_advance_warning": True,
            "fri_high_time"      : last_high,
            "lead_time_min"      : lead_min,
            "lead_time_intervals": lead_intervals,
        }

    during = ep[ep["fri_band"] == TEMPORAL_FRI_TRIGGER_BAND]
    if len(during) > 0:
        return {
            "warning_type"       : "DURING-SPIKE",
            "had_advance_warning": False,
            "fri_high_time"      : during["DATETIME"].min(),
            "lead_time_min"      : 0.0,
            "lead_time_intervals": 0,
        }

    return {
        "warning_type"       : "NO-TRIGGER",
        "had_advance_warning": False,
        "fri_high_time"      : None,
        "lead_time_min"      : None,
        "lead_time_intervals": None,
    }


def run_temporal_profiling(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run temporal profiling across all NEM regions.
    Returns episode-level DataFrame with lead time results.
    """
    episodes = []

    for region in sorted(df["REGIONID"].unique()):
        reg_df = df[df["REGIONID"] == region].copy()
        reg_df = reg_df.sort_values("DATETIME").reset_index(drop=True)
        ext_df = detect_episodes(reg_df, region)

        if len(ext_df) == 0:
            continue

        for eid, ep in ext_df.groupby("ep_id"):
            onset    = ep["DATETIME"].min()
            end_time = ep["DATETIME"].max()
            dur_int  = len(ep)

            classification = classify_episode(ep, reg_df, onset)

            episodes.append({
                "deviation"           : TEMPORAL_DEVIATION,
                "region"              : region,
                "episode_id"          : f"{region}_ep{eid:02d}",
                "onset_time"          : onset,
                "end_time"            : end_time,
                "duration_intervals"  : dur_int,
                "duration_min"        : dur_int * DISPATCH_INTERVAL,
                "max_forecast_error"  : ep["forecast_error"].max(),
                "mean_fri_score"      : round(ep["fri_score"].mean(), 4),
                "n_fri_high_in_ep"    : (ep["fri_band"] == TEMPORAL_FRI_TRIGGER_BAND).sum(),
                **classification,
            })

    return pd.DataFrame(episodes)


def compute_summary(ep_df: pd.DataFrame) -> dict:
    """Compute summary statistics for COMPLIANCE output."""
    total      = len(ep_df)
    pre_spike  = (ep_df["warning_type"] == "PRE-SPIKE").sum()
    during     = (ep_df["warning_type"] == "DURING-SPIKE").sum()
    no_trigger = (ep_df["warning_type"] == "NO-TRIGGER").sum()
    pre_df     = ep_df[ep_df["warning_type"] == "PRE-SPIKE"]

    return {
        "deviation"              : TEMPORAL_DEVIATION,
        "analysis_type"          : "POST-HOC EXPLORATORY",
        "run_date"               : datetime.now().strftime("%Y-%m-%d"),
        "threshold_used"         : "D-009 AUD100 via regime column",
        "lookback_intervals"     : TEMPORAL_LOOKBACK_INTERVALS,
        "lookback_minutes"       : TEMPORAL_LOOKBACK_INTERVALS * DISPATCH_INTERVAL,
        "total_episodes"         : total,
        "pre_spike_count"        : int(pre_spike),
        "pre_spike_pct"          : round(pre_spike / total * 100, 2),
        "during_spike_count"     : int(during),
        "no_trigger_count"       : int(no_trigger),
        "mean_lead_time_min"     : round(pre_df["lead_time_min"].mean(), 1) if len(pre_df) > 0 else None,
        "median_lead_time_min"   : round(pre_df["lead_time_min"].median(), 1) if len(pre_df) > 0 else None,
        "min_lead_time_min"      : int(pre_df["lead_time_min"].min()) if len(pre_df) > 0 else None,
        "max_lead_time_min"      : int(pre_df["lead_time_min"].max()) if len(pre_df) > 0 else None,
    }


def log_results(ep_df: pd.DataFrame, summary: dict) -> None:
    """Log full results to logger."""
    total     = summary["total_episodes"]
    pre_spike = summary["pre_spike_count"]
    during    = summary["during_spike_count"]
    no_trig   = summary["no_trigger_count"]

    logger.info("=" * 52)
    logger.info(f"TEMPORAL PROFILING RESULTS ({TEMPORAL_DEVIATION})")
    logger.info("POST-HOC EXPLORATORY — not pre-registered")
    logger.info("=" * 52)
    logger.info(f"Total spike episodes     : {total}")
    logger.info(f"  PRE-SPIKE warning ✓    : {pre_spike} ({pre_spike/total*100:.1f}%)")
    logger.info(f"  DURING-SPIKE           : {during} ({during/total*100:.1f}%)")
    logger.info(f"  NO-TRIGGER             : {no_trig} ({no_trig/total*100:.1f}%)")

    if summary["mean_lead_time_min"] is not None:
        logger.info(f"Lead time (pre-spike only):")
        logger.info(f"  Mean   : {summary['mean_lead_time_min']:.1f} min")
        logger.info(f"  Median : {summary['median_lead_time_min']:.1f} min")
        logger.info(f"  Min    : {summary['min_lead_time_min']} min")
        logger.info(f"  Max    : {summary['max_lead_time_min']} min")

    logger.info("By region:")
    for region, grp in ep_df.groupby("region"):
        pre = (grp["warning_type"] == "PRE-SPIKE").sum()
        tot = len(grp)
        logger.info(f"  {region}: {pre}/{tot} pre-spike ({pre/tot*100:.0f}%)")

    logger.info("Episode detail:")
    for _, row in ep_df.iterrows():
        logger.info(
            f"  {row['episode_id']} | {row['onset_time']} | "
            f"{row['warning_type']} | lead={row['lead_time_min']} min | "
            f"max_err={row['max_forecast_error']:.1f}"
        )


# ── MAIN ───────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Starting {TEMPORAL_DEVIATION} temporal profiling")
    logger.info("POST-HOC EXPLORATORY — not pre-registered")
    logger.info(f"Lookback : {TEMPORAL_LOOKBACK_INTERVALS} intervals "
                f"({TEMPORAL_LOOKBACK_INTERVALS * DISPATCH_INTERVAL} min)")
    logger.info(f"Episode gap: {TEMPORAL_EPISODE_GAP_MIN} min")

    df     = load_agent_results()
    ep_df  = run_temporal_profiling(df)
    summary = compute_summary(ep_df)

    ep_df.to_csv(OUT_CSV, index=False)
    pd.DataFrame([summary]).to_csv(SUMMARY_CSV, index=False)

    log_results(ep_df, summary)

    logger.info(f"Saved: {OUT_CSV}")
    logger.info(f"Saved: {SUMMARY_CSV}")
    logger.info("NEXT: Add D-024 to COMPLIANCE.md before using in manuscript")
