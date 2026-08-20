"""
figure_h3_horizon.py
====================
Publication figure for H3 hypothesis result (horizon sweep).
PRODUCTION VERSION -- master theme compliant.

Verified data (h3_horizon_sweep.csv):
  Amplification ratio of forecast revision (extreme vs normal)
  across predispatch horizons P30 to P1440, per NEM region.
  Onset (h3_horizon_onset.csv): NSW1 rho=0.9762 p<0.001 monotonic,
  VIC1 rho=0.9524 p=0.0003 monotonic.

Single panel: amplification ratio vs horizon (log x), 5 region lines,
1x reference line, onset annotation.

Output:
  results/figures/fig07_h3_horizon.png
  results/figures/fig07_h3_horizon.pdf

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h3_horizon")

# --- Wong 2011 palette (consistent with Fig 1) ---
REG_COLORS = {
    "NSW1": "#0072B2",
    "VIC1": "#D55E00",
    "QLD1": "#009E73",
    "SA1" : "#E69F00",
    "TAS1": "#CC79A7",
}
LINESTYLE_MAP = {
    "NSW1": "-",
    "VIC1": "--",
    "QLD1": "-.",
    "SA1" : ":",
    "TAS1": (0, (1, 1)),
}
REGIONS    = ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"
VERMILLION = "#D55E00"

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "axes.labelsize":     7.5,
    "xtick.labelsize":    6.5,
    "ytick.labelsize":    6.5,
    "legend.fontsize":    5.5,
    "figure.dpi":         1200,
    "savefig.dpi":        1200,
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
    logger.info("Loading H3 horizon sweep data...")
    sweep = pd.read_csv(TABLES_DIR / "h3_horizon_sweep.csv")
    onset = pd.read_csv(TABLES_DIR / "h3_horizon_onset.csv")
    logger.info(f"Sweep rows: {len(sweep)}  Onset rows: {len(onset)}")
    for _, r in onset.iterrows():
        logger.info(f"  {r['region']}: rho={r['spearman_rho']:.4f} "
                    f"p={r['spearman_p']:.4f} monotonic={r['monotonic']}")
    return sweep, onset


def build_figure(sweep, onset):
    logger.info("Building figure...")
    plt.rcParams.update(STYLE)

    fig, ax = plt.subplots(figsize=(9.50, 4.50))
    fig.subplots_adjust(left=0.10, right=0.985, top=0.97, bottom=0.12)

    for reg in REGIONS:
        d = sweep[sweep["region"] == reg].sort_values("horizon_min")
        ax.plot(
            d["horizon_min"], d["amplification_ratio"],
            color=REG_COLORS[reg], lw=0.9,
            ls=LINESTYLE_MAP[reg],
            marker="o", markersize=2.5,
            label=reg, zorder=4,
        )
        # CI band clipped at 0 to prevent P30 flooding
        ax.fill_between(
            d["horizon_min"],
            d["ci_lower"].clip(lower=0),
            d["ci_upper"],
            color=REG_COLORS[reg], alpha=0.08, lw=0, zorder=2,
        )

    # 1x reference line (no amplification)
    ax.axhline(1.0, color=MUTED, ls=":", lw=0.8, alpha=0.8, zorder=3)
    ax.text(33, 1.25, "No amplification (1x)", fontsize=5.5,
            color=MUTED, style="italic", fontweight="bold",
            ha="left", va="bottom", zorder=5)

    # Strategic annotation: monotonic rise (verified onset stats)
    ax.text(
        0.985, 0.04,
        "Monotonic rise: NSW1 ($\\rho$=0.976, p<0.001)\n"
        "and VIC1 ($\\rho$=0.952, p<0.001)\n"
        "Flat or declining: QLD1, SA1, TAS1",
        transform=ax.transAxes,
        fontsize=6.5, ha="right", va="bottom", color="#534AB7",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor="#534AB7", linewidth=0.8, alpha=0.95),
        zorder=10,
    )

    # Axes
    ax.set_xscale("log")
    horizons = sorted(sweep["horizon_min"].unique())
    ax.set_xticks(horizons)
    ax.set_xticklabels([f"P{h}" for h in horizons], fontsize=6.5,
                       fontweight="bold")
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xlabel("Pre-dispatch horizon (minutes ahead)",
                  fontsize=8, color=BLACK, labelpad=6,
                  fontweight="bold")
    ax.set_ylabel("Amplification ratio (x)",
                  fontsize=8, color=BLACK, labelpad=6,
                  fontweight="bold")
    ax.set_ylim(bottom=0)

    # Legend inside, upper left (curves rise to the right)
    handles = [
        Line2D([0], [0], color=REG_COLORS[r], lw=0.9,
               linestyle=LINESTYLE_MAP[r], marker="o",
               markersize=2.5, label=r)
        for r in REGIONS
    ]
    leg = ax.legend(handles=handles, loc="upper left", fontsize=7,
                    frameon=True, framealpha=0.95, edgecolor=GREY_LIGHT,
                    handlelength=2.0, labelspacing=0.4, borderpad=0.5,
                    handletextpad=0.5, fancybox=False, markerscale=1.4)
    leg.get_frame().set_linewidth(0.25)

    logger.info("Figure complete")
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig07_h3_horizon.png")
    pdf = str(FIGURES_DIR / "fig07_h3_horizon.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_h3_horizon.py -- PRODUCTION (master theme)")
    logger.info("=" * 60)
    sweep, onset = load_data()
    fig = build_figure(sweep, onset)
    save_figure(fig)
    logger.info("=" * 60)
    logger.info("figure_h3_horizon.py complete")
    logger.info(f"Output: {FIGURES_DIR}/fig07_h3_horizon.png/.pdf")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
