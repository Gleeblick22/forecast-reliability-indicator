"""
figure_h5_silent.py
===================
Publication figure for H5 hypothesis result (silent failure reduction).
PRODUCTION VERSION -- master theme compliant.

Verified data:
  c3_03_h5_silent_failure_results.csv: baseline=55, FRI=21,
    reduction=61.82% (threshold 20%), rates 0.3627% -> 0.1385%
  confidence_intervals.csv H5: 61.82 CI[48.78, 74.58]
  h5_mcnemar_test.csv: both=21, baseline_only=34, fri_only=0,
    chi2=32.0294, p<0.001

Panel (a): Silent failure counts baseline vs FRI, per region + total,
           with 61.82% reduction annotation and CI.
Panel (b): McNemar discordant pair breakdown (34 / 0 / 21).

Output:
  results/figures/fig08_h5_silent.png
  results/figures/fig08_h5_silent.pdf

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h5_silent")

BLUE       = "#0072B2"
GREY       = "#999999"
GREEN      = "#009E73"
VERMILLION = "#D55E00"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"

# Locked values
SF_BASE, SF_FRI   = 55, 21
RED_PCT           = 61.82
RED_CI            = (48.78, 74.58)
MCN_BOTH          = 21
MCN_BASE_ONLY     = 34
MCN_FRI_ONLY      = 0
MCN_CHI2          = 32.03
REGIONS           = ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "axes.labelsize":     7.5,
    "xtick.labelsize":    6.5,
    "ytick.labelsize":    6.5,
    "legend.fontsize":    5.5,
    "figure.dpi":         1000,
    "savefig.dpi":        1000,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.04,
    "axes.facecolor":     "white",
    "figure.facecolor":   "white",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.color":         "#E8E8E8",
    "grid.linestyle":     "-",
    "grid.linewidth":     0.5,
    "axes.axisbelow":     True,
    "axes.linewidth":     0.6,
}


def load_data():
    logger.info("Loading H5 per-interval agent results...")
    base = pd.read_csv(TABLES_DIR / "c3_01_baseline_agent_results.csv",
                       usecols=["REGIONID", "is_silent_failure"])
    fri = pd.read_csv(TABLES_DIR / "c3_02_fri_agent_results.csv",
                      usecols=["REGIONID", "is_silent_failure"])
    base_sf = (base[base["is_silent_failure"] == True]
               .groupby("REGIONID").size())
    fri_sf = (fri[fri["is_silent_failure"] == True]
              .groupby("REGIONID").size())
    logger.info("Per-region silent failures (baseline / FRI):")
    tot_b, tot_f = 0, 0
    rows = []
    for r in REGIONS:
        b = int(base_sf.get(r, 0))
        f = int(fri_sf.get(r, 0))
        tot_b += b
        tot_f += f
        rows.append((r, b, f))
        logger.info(f"  {r}: {b} / {f}")
    logger.info(f"  TOTAL: {tot_b} / {tot_f}  (locked: {SF_BASE}/{SF_FRI})")
    assert tot_b == SF_BASE and tot_f == SF_FRI, \
        "Per-region totals do not match locked H5 values!"
    return rows


def build_panel_a(ax, rows):
    """Grouped bars per region + total, reduction annotation."""
    logger.info("Building Panel (a)...")
    labels = [r[0] for r in rows] + ["Total"]
    base_v = [r[1] for r in rows] + [SF_BASE]
    fri_v  = [r[2] for r in rows] + [SF_FRI]
    x = np.arange(len(labels))
    w = 0.36

    ax.bar(x - w/2, base_v, w, color=GREY, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3, label="Baseline agent")
    ax.bar(x + w/2, fri_v, w, color=BLUE, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3, label="FRI agent")

    for xi, b, f in zip(x, base_v, fri_v):
        ax.text(xi - w/2, b + 0.8, str(b), ha="center", va="bottom",
                fontsize=6, color=MUTED, fontweight="bold", zorder=5)
        ax.text(xi + w/2, f + 0.8, str(f), ha="center", va="bottom",
                fontsize=6, color=BLUE, fontweight="bold", zorder=5)

    # Reduction annotation pointing at Total pair
    ax.annotate(
        f"{RED_PCT:.2f}% reduction\n95% CI [{RED_CI[0]:.2f}%, {RED_CI[1]:.2f}%]\n"
        f"55 \u2192 21 silent failures",
        xy=(x[-1], SF_BASE),
        xytext=(x[-1] - 2.6, SF_BASE - 6),
        fontsize=6, color="#534AB7", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#534AB7", lw=0.8,
                        connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor="#534AB7", linewidth=0.5, alpha=0.95),
        zorder=10,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.5, color=BLACK)
    ax.set_ylabel("Silent failures (count)", fontsize=7.5, color=BLACK)
    ax.set_ylim(0, SF_BASE * 1.22)
    ax.grid(axis="x", visible=False)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.90),
                    fontsize=5.5, frameon=True,
                    framealpha=0.95, edgecolor=GREY_LIGHT,
                    handlelength=0.9, handletextpad=0.4, borderpad=0.35,
                    labelspacing=0.3, fancybox=False)
    leg.get_frame().set_linewidth(0.25)

    ax.set_title("(a)  Silent failures by region",
                 fontsize=8, fontweight="bold", loc="left",
                 pad=7, color=BLACK)
    logger.info("Panel (a) complete")


def build_panel_b(ax):
    """McNemar discordant pair breakdown."""
    logger.info("Building Panel (b)...")
    cats = ["Baseline only\n(FRI prevented)", "Both agents", "FRI only"]
    vals = [MCN_BASE_ONLY, MCN_BOTH, MCN_FRI_ONLY]
    cols = [GREEN, GREY, VERMILLION]
    x = np.arange(len(cats))

    ax.bar(x, vals, width=0.55, color=cols, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.8, str(v), ha="center", va="bottom",
                fontsize=7, color=BLACK, fontweight="bold", zorder=5)

    # McNemar annotation
    ax.text(
        0.97, 0.82,
        "McNemar $\\chi^2$ = 32.03\np < 0.001\n34 discordant pairs,\nall favouring FRI",
        transform=ax.transAxes,
        fontsize=6, ha="right", va="top", color=BLACK,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor="#534AB7", linewidth=0.8, alpha=0.95),
        zorder=10,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=6, color=BLACK)
    ax.set_ylabel("Silent failure intervals (count)",
                  fontsize=7.5, color=BLACK)
    ax.set_ylim(0, MCN_BASE_ONLY * 1.15)
    ax.grid(axis="x", visible=False)

    ax.set_title("(b)  Paired outcome breakdown",
                 fontsize=8, fontweight="bold", loc="left",
                 pad=7, color=BLACK)
    logger.info("Panel (b) complete")


def build_figure(rows):
    logger.info("Building figure...")
    plt.rcParams.update(STYLE)
    fig = plt.figure(figsize=(6.90, 3.00))
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.26,
                           width_ratios=[1.45, 1.0],
                           left=0.075, right=0.985,
                           top=0.97, bottom=0.13)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    build_panel_a(ax1, rows)
    build_panel_b(ax2)
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig08_h5_silent.png")
    pdf = str(FIGURES_DIR / "fig08_h5_silent.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_h5_silent.py -- PRODUCTION (master theme)")
    logger.info("=" * 60)
    rows = load_data()
    fig = build_figure(rows)
    save_figure(fig)
    logger.info("=" * 60)
    logger.info("figure_h5_silent.py complete")
    logger.info(f"Output: {FIGURES_DIR}/fig08_h5_silent.png/.pdf")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
