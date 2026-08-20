"""
figure_h1_amplification.py
==========================
Fig 3: H1 forecast error amplification.
PRODUCTION VERSION -- master theme compliant (one-shot rewrite).

Verified data (c1_04_h1_amplification_results.csv + confidence_intervals.csv):
  NSW1 19.7826, VIC1 23.4979, QLD1 12.9949, SA1 4.3881, TAS1 7.9690
  NEM mean 13.7265 CI[7.5418, 19.9112]; all p<0.001

Panel (a): A_r per region, descending, criterion 1.5 dashed, NEM mean box.
Panel (b): MAE normal vs extreme per region (log x), ratio annotations.

Output: results/figures/fig05_h1_amplification.png/.pdf
Project: forecast-reliability-indicator (FRI)  OSF: 10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h1_amplification")

BLUE       = "#0072B2"
BLUE_LIGHT = "#56B4E9"
VERMILLION = "#D55E00"
GREEN      = "#009E73"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"

CRITERION = 1.5
NEM_MEAN  = 13.73
NEM_CI    = (7.54, 19.91)

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "axes.labelsize":     7.5,
    "xtick.labelsize":    6.5,
    "ytick.labelsize":    7,
    "legend.fontsize":    5.5,
    "figure.dpi":         1200,
    "savefig.dpi":        1200,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.04,
    "axes.facecolor":     "white",
    "figure.facecolor":   "white",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.spines.left":   False,
    "axes.grid":          True,
    "grid.color":         "#E8E8E8",
    "grid.linestyle":     "-",
    "grid.linewidth":     0.5,
    "axes.axisbelow":     True,
    "axes.linewidth":     0.6,
    "ytick.major.size":   0,
}


def load_data():
    logger.info("Loading H1 data...")
    h1 = pd.read_csv(TABLES_DIR / "c1_04_h1_amplification_results.csv")
    h1 = h1.sort_values("ratio", ascending=True).reset_index(drop=True)
    for _, r in h1.iterrows():
        logger.info(f"  {r['region']}: A_r={r['ratio']:.4f} "
                    f"norm={r['mae_normal']:.2f} ext={r['mae_extreme']:.2f}")
    return h1


def build_panel_a(ax, h1):
    """A_r bars, ascending bottom-to-top (descending visual order)."""
    logger.info("Building Panel (a)...")
    y = np.arange(len(h1))
    ax.barh(y, h1["ratio"], height=0.62, color=BLUE, alpha=0.9,
            edgecolor="white", linewidth=0.3, zorder=3)

    # Value labels inside bars (white) or beside short bars
    for yi, v in zip(y, h1["ratio"]):
        ax.text(v - 0.3, yi, f"{v:.2f}x", ha="right", va="center",
                fontsize=6.5, color="white", fontweight="bold", zorder=5)

    # Criterion line
    ax.axvline(CRITERION, color="#D55E00", ls="--", lw=0.9, alpha=0.8, zorder=4)
    ax.text(CRITERION + 0.35, (len(h1) - 1) / 2.0,
            "criterion $\\geq$1.5x",
            fontsize=5.5, color="#D55E00", style="italic",
            ha="left", va="center", rotation=90, zorder=5)

    # NEM mean box: bottom-right empty zone (bars shrink toward bottom)
    ax.text(0.97, 0.05,
            f"NEM mean = {NEM_MEAN:.2f}x\n"
            f"95% CI [{NEM_CI[0]:.2f}, {NEM_CI[1]:.2f}]\n"
            f"p < 0.001 (all regions)",
            transform=ax.transAxes, fontsize=6, ha="right", va="bottom",
            color=BLACK,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor=GREY_LIGHT, linewidth=0.5, alpha=0.95),
            zorder=10)

    ax.set_yticks(y)
    ax.set_yticklabels(h1["region"], fontsize=7, color=BLACK)
    ax.set_xlim(0, 25.5)
    ax.set_xlabel("Amplification ratio ($A_r$)", fontsize=7.5,
                  color=BLACK, labelpad=3)
    ax.grid(axis="y", visible=False)

    ax.text(0.0, 1.05, "(a)  Amplification ratio by region", transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="left", color=BLACK, zorder=11)
    logger.info("Panel (a) complete")


def build_panel_b(ax, h1):
    """Grouped MAE bars, log x, ratio annotations on right margin."""
    logger.info("Building Panel (b)...")
    y = np.arange(len(h1))
    bh = 0.30

    ax.barh(y + bh/2 + 0.02, h1["mae_normal"], height=bh,
            color=BLUE_LIGHT, alpha=0.9, edgecolor="white",
            linewidth=0.3, zorder=3)
    ax.barh(y - bh/2 - 0.02, h1["mae_extreme"], height=bh,
            color=VERMILLION, alpha=0.9, edgecolor="white",
            linewidth=0.3, zorder=3)

    for yi, (nv, ev, r) in enumerate(zip(h1["mae_normal"],
                                         h1["mae_extreme"],
                                         h1["ratio"])):
        ax.text(nv * 1.12, yi + bh/2 + 0.02, f"${nv:,.0f}",
                fontsize=5.5, ha="left", va="center",
                color="#3690C0", fontweight="bold", zorder=5)
        ax.text(ev * 1.12, yi - bh/2 - 0.02, f"${ev:,.0f}",
                fontsize=5.5, ha="left", va="center",
                color=VERMILLION, fontweight="bold", zorder=5)
        # Fold-difference annotation at right margin
        ax.text(15000, yi, f"{r:.1f}x", fontsize=6, ha="right",
                va="center", color=MUTED, fontweight="bold", zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(h1["region"], fontsize=7, color=BLACK)
    ax.set_xscale("log")
    ax.set_xlim(40, 16000)
    ax.set_xticks([50, 100, 500, 1000, 5000, 10000])
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"${v:,.0f}" if v >= 1000 else f"${v:.0f}"))
    ax.set_xlabel("MAE (AUD/MWh, log scale)", fontsize=7.5,
                  color=BLACK, labelpad=3)
    ax.grid(axis="y", visible=False)

    # Legend inside lower right (short normal bars leave that zone clear)
    handles = [Patch(color=BLUE_LIGHT, label="Normal regime MAE"),
               Patch(color=VERMILLION, label="Extreme regime MAE")]
    leg = ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 1.02), ncol=1, fontsize=5.5,
                    frameon=True, framealpha=0.95, edgecolor=GREY_LIGHT,
                    handlelength=0.9, handletextpad=0.4, borderpad=0.35,
                    labelspacing=0.3, fancybox=False)
    leg.get_frame().set_linewidth(0.25)

    ax.text(0.0, 1.05, "(b)  MAE by price regime", transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="left", color=BLACK, zorder=11)
    logger.info("Panel (b) complete")


def build_figure(h1):
    plt.rcParams.update(STYLE)
    fig = plt.figure(figsize=(9.50, 4.50))
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.15,
                           width_ratios=[1, 1],
                           left=0.065, right=0.985,
                           top=0.89, bottom=0.14)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    build_panel_a(ax1, h1)
    build_panel_b(ax2, h1)
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig05_h1_amplification.png")
    pdf = str(FIGURES_DIR / "fig05_h1_amplification.pdf")
    fig.savefig(png, dpi=1200, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1200, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_h1_amplification.py -- PRODUCTION (master theme)")
    logger.info("=" * 60)
    h1 = load_data()
    fig = build_figure(h1)
    save_figure(fig)
    logger.info("figure_h1_amplification.py complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
