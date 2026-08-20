"""
figure_h2_masking.py
====================
Publication figure for H2 hypothesis result (masking effect).
PRODUCTION VERSION -- master theme compliant.

Verified data (c1_05_h2_masking_results.csv):
  OVERALL_NEM masking = 77.28%
  Regional: VIC1=84.54, TAS1=81.25, NSW1=81.02, QLD1=77.71, SA1=66.76
  NEM mean across 5 regions = 78.256 CI[72.506, 82.52] (confidence_intervals.csv)

Panel (a): Masking % bar chart per region + 50% criterion + NEM mean annotation
Panel (b): Dumbbell aggregate vs extreme MAE + legend inside panel

Output:
  results/figures/fig06_h2_masking.png
  results/figures/fig06_h2_masking.pdf

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h2_masking")

# --- Wong 2011 palette ---
BLUE       = "#0072B2"
VERMILLION = "#D55E00"
GREY       = "#999999"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"

THRESHOLD  = 50.0   # H2 criterion (%)
NEM_MASK   = 77.28  # OVERALL_NEM masking
NEM_MEAN   = 78.256
NEM_CI_LO  = 72.506
NEM_CI_HI  = 82.52

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
    logger.info("Loading H2 masking data...")
    df = pd.read_csv(TABLES_DIR / "c1_05_h2_masking_results.csv")
    regs = df[df["label"] != "OVERALL_NEM"].copy()
    regs = regs.sort_values("masking_pct", ascending=False).reset_index(drop=True)
    logger.info(f"Loaded {len(regs)} regions:")
    for _, r in regs.iterrows():
        logger.info(f"  {r['label']}: masking={r['masking_pct']:.2f}%  "
                    f"agg=${r['aggregate_mae']:.0f}  ext=${r['extreme_mae']:.0f}")
    return regs


def build_panel_a(ax, regs):
    """Panel (a): masking % bars, 50% criterion, NEM mean annotation."""
    logger.info("Building Panel (a)...")

    labels = regs["label"].values
    pcts   = regs["masking_pct"].values
    x = np.arange(len(labels))

    ax.bar(x, pcts, width=0.62, color=BLUE, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3)

    # Value labels above bars
    for xi, v in zip(x, pcts):
        ax.text(xi, v + 1.5, f"{v:.2f}%", ha="center", va="bottom",
                fontsize=6, color=BLUE, fontweight="bold", zorder=5)

    # NEM overall masking dotted reference
    ax.axhline(NEM_MASK, color="#534AB7", ls=":", lw=0.8, alpha=0.8, zorder=2)
    ax.text(len(labels) - 0.05, NEM_MASK + 3.5,
            f"Overall NEM={NEM_MASK:.2f}%",
            fontsize=5.5, color="#534AB7", ha="right", va="bottom",
            style="normal", clip_on=False, zorder=5)

    # Strategic annotation: NEM mean + CI (placed lower-left, clear of bars)
    ax.text(
        0.02, 0.06,
        f"NEM mean = {NEM_MEAN:.2f}%\n95% CI [{NEM_CI_LO:.2f}%, {NEM_CI_HI:.2f}%]\nAll regions p<0.001",
        transform=ax.transAxes,
        fontsize=6, ha="left", va="bottom", color="#534AB7",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor="#534AB7", linewidth=0.8, alpha=0.95),
        zorder=10,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7, color=BLACK)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylabel("Masking (%)", fontsize=7.5, color=BLACK)
    ax.grid(axis="x", visible=False)

    # Panel label inside, safe position (no annotation overlap)
    ax.text(-0.07, 1.04, "(a)  Masking percentage by region",
            transform=ax.transAxes, fontsize=9, fontweight="bold",
            va="bottom", ha="left", color=BLACK)

    logger.info("Panel (a) complete")


def build_panel_b(ax, regs):
    """Vertical connected dots: Normal -> Aggregate -> Extreme per region.
    Grey connector line shows escalation gap. Log y-axis.
    X-axis matches Panel (a) region order.
    """
    logger.info("Building Panel (b)...")

    regions      = regs["label"].values
    normal_vals  = regs["normal_mae"].values
    agg_vals     = regs["aggregate_mae"].values
    extreme_vals = regs["extreme_mae"].values

    n = len(regions)
    x = np.arange(n)

    C_NORMAL = "#56B4E9"   # light blue  -- calm baseline
    C_AGG    = "#E69F00"   # orange      -- mixed/masked signal
    C_EXT    = "#D55E00"   # dark vermillion -- crisis peak

    for xi, (nv, av, ev) in enumerate(zip(normal_vals, agg_vals, extreme_vals)):
        # Grey connector line bottom to top
        ax.plot([xi, xi], [nv, ev], color=GREY_LIGHT, lw=2.5,
                solid_capstyle="round", zorder=2)

        # Three dots
        ax.scatter(xi, nv, s=60, color=C_NORMAL, edgecolors="white",
                   linewidth=0.5, zorder=4)
        ax.scatter(xi, av, s=60, color=C_AGG, edgecolors="white",
                   linewidth=0.5, zorder=4)
        ax.scatter(xi, ev, s=60, color=C_EXT, edgecolors="white",
                   linewidth=0.5, zorder=4)

        # Value labels beside each dot
        ax.text(xi + 0.10, nv, f"${nv:,.0f}",
                fontsize=5.5, va="center", color=C_NORMAL,
                fontweight="bold", zorder=5)
        ax.text(xi + 0.10, av, f"${av:,.0f}",
                fontsize=5.5, va="center", color=C_AGG,
                fontweight="bold", zorder=5)
        ax.text(xi + 0.10, ev, f"${ev:,.0f}",
                fontsize=5.5, va="center", color=C_EXT,
                fontweight="bold", zorder=5)

    # Axes
    ax.set_yscale("log")
    ax.set_ylim(70, 3800)
    ax.set_xticks(x)
    ax.set_xticklabels(regions, fontsize=7, color=BLACK)
    ax.set_xlim(-0.6, n - 0.3)
    ax.set_yticks([80, 400, 800, 1200, 1600, 2000, 2400, 2800, 3200, 3600, 4000])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"${v:,.0f}" if v >= 1000 else f"${v:.0f}"))
    ax.set_ylabel("MAE (AUD/MWh)", fontsize=7.5,
                  color=BLACK, labelpad=3)
    ax.grid(axis="x", visible=False)

    # Legend upper left
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0],[0], marker="o", color="none",
               markerfacecolor=C_NORMAL, markeredgecolor="white",
               markersize=5, label="Normal MAE"),
        Line2D([0],[0], marker="o", color="none",
               markerfacecolor=C_AGG, markeredgecolor="white",
               markersize=5, label="Aggregate MAE"),
        Line2D([0],[0], marker="o", color="none",
               markerfacecolor=C_EXT, markeredgecolor="white",
               markersize=5, label="Extreme MAE"),
    ]
    leg = ax.legend(handles=handles, loc="lower right", ncol=1,
                    fontsize=5.5, frameon=True, framealpha=0.95,
                    edgecolor=GREY_LIGHT, handletextpad=0.4,
                    borderpad=0.35, labelspacing=0.3, fancybox=False)
    leg.get_frame().set_linewidth(0.25)

    ax.set_title("(b)  MAE by price regime",
                 fontsize=9, fontweight="bold", loc="left", pad=7, color=BLACK)
    logger.info("Panel (b) complete")

def build_figure(regs):
    logger.info("Building figure...")
    plt.rcParams.update(STYLE)

    fig = plt.figure(figsize=(9.50, 4.00))
    gs = gridspec.GridSpec(
        1, 2, figure=fig,
        width_ratios=[1, 1],
        wspace=0.32,
        left=0.07, right=0.985,
        top=0.93, bottom=0.13,
    )
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    build_panel_a(ax1, regs)
    build_panel_b(ax2, regs)
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig06_h2_masking.png")
    pdf = str(FIGURES_DIR / "fig06_h2_masking.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_h2_masking.py -- PRODUCTION (master theme)")
    logger.info("=" * 60)
    regs = load_data()
    fig = build_figure(regs)
    save_figure(fig)
    logger.info("=" * 60)
    logger.info("figure_h2_masking.py complete")
    logger.info(f"Output: {FIGURES_DIR}/fig06_h2_masking.png/.pdf")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
