"""
figure_10_h5_four_agent.py
=============================
Fig 11: H5 four-agent comparison (silent failures + net revenue
under realistic degradation economics, with R sensitivity).
PRODUCTION VERSION -- master theme compliant.
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
import numpy as np
from config.settings import FIGURES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h5_four_agent")

BLUE       = "#0072B2"
GREEN      = "#009E73"
VERMILLION = "#D55E00"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"

C_TITLE_A = "#0072B2"
C_TITLE_B = "#009E73"

AGENTS_A = ["Baseline\n(~24h lead)", "FRI-augmented\n(~24h lead)",
            "P5-timed\nbaseline", "P5-timed\n+ FRI"]
SF_VALUES = [44, 44, 3, 3]
SF_COLORS = [MUTED, MUTED, BLUE, GREEN]

R_LABELS = ["R = AUD 21M\n(half)", "R = AUD 42M\n(baseline)", "R = AUD 84M\n(double)"]
P5_BASE_NET = [240893.38, 187603.24, 81022.98]
CONTROL_NET_R42 = 226740.88  # signal-free control, R=42M only
P5_FRI_NET  = [312252.23, 299614.46, 274338.92]

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
    "axes.grid":          True,
    "grid.color":         "#E8E8E8",
    "grid.linestyle":     "-",
    "grid.linewidth":     0.5,
    "axes.axisbelow":     True,
    "axes.linewidth":     0.6,
}


def build_panel_a(ax):
    logger.info("Building Panel (a)...")
    x = np.arange(len(AGENTS_A))
    ax.bar(x, SF_VALUES, width=0.55, color=SF_COLORS,
           alpha=0.9, edgecolor="white", linewidth=0.3, zorder=3)

    for xi, v in zip(x, SF_VALUES):
        ax.text(xi, v + 1.0, f"{v}", ha="center", va="bottom",
                fontsize=8, fontweight="bold", color=BLACK, zorder=5)

    ax.plot([0, 1], [48, 48], color="#534AB7", lw=1.0, zorder=4)
    ax.text(0.5, 49, "statistically\nindistinguishable", fontsize=5.5,
            color="#534AB7", ha="center", va="bottom", style="italic", fontweight="bold", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(AGENTS_A, fontsize=6.5, color=BLACK)
    ax.set_ylabel("Silent failures (sign-aware)", fontsize=7.5, color=BLACK)
    ax.set_ylim(0, 58)
    ax.grid(axis="x", visible=False)

    ax.text(0.0, 1.05, "(a)  Silent failures by information timing and signal",
            transform=ax.transAxes, fontsize=8, fontweight="bold",
            va="bottom", ha="left", color=BLACK, zorder=11)
    logger.info("Panel (a) complete")


def build_panel_b(ax):
    logger.info("Building Panel (b)...")
    x = np.arange(len(R_LABELS))
    w = 0.32

    ax.bar(x - w/2, P5_BASE_NET, width=w, color=BLUE, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3, label="P5-timed baseline")
    ax.bar(x + w/2, P5_FRI_NET, width=w, color=GREEN, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3, label="P5-timed + FRI")

    for xi, (bv, fv) in enumerate(zip(P5_BASE_NET, P5_FRI_NET)):
        adv_pct = (fv - bv) / bv * 100
        ax.text(xi - w/2, bv + 3000, f"${bv/1000:,.0f}k", ha="center",
                va="bottom", fontsize=5.5, color=BLUE, zorder=5)
        ax.text(xi + w/2, fv + 3000, f"${fv/1000:,.0f}k", ha="center",
                va="bottom", fontsize=5.5, color=GREEN, zorder=5)
        ax.text(xi, max(bv, fv) + 16000, f"+{adv_pct:.1f}%",
                ha="center", va="bottom", fontsize=6.5,
                fontweight="bold", color=VERMILLION, zorder=5)

    # Signal-free control reference marker (R=42M only)
    ax.plot([1 - w, 1 + w], [CONTROL_NET_R42, CONTROL_NET_R42],
            color="#666666", ls=":", lw=1.2, zorder=6)
    ax.text(1, CONTROL_NET_R42 - 8000, "Signal-free control (constant 0.75x): $226.7k",
            fontsize=5.5, color="#666666", ha="center", va="top",
            style="italic", zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels(R_LABELS, fontsize=6.5, color=BLACK)
    ax.set_ylabel("Net revenue (AUD)", fontsize=7.5, color=BLACK)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    ax.set_ylim(0, 340000)
    ax.grid(axis="x", visible=False)

    leg = ax.legend(loc="upper right", fontsize=5.5, frameon=True,
                    framealpha=0.95, edgecolor=GREY_LIGHT,
                    handlelength=0.9, handletextpad=0.4, borderpad=0.35,
                    labelspacing=0.3, fancybox=False)
    leg.get_frame().set_linewidth(0.25)

    ax.text(0.0, 1.05, "(b)  Net revenue under realistic degradation economics",
            transform=ax.transAxes, fontsize=8, fontweight="bold",
            va="bottom", ha="left", color=BLACK, zorder=11)
    logger.info("Panel (b) complete")


def build_figure():
    plt.rcParams.update(STYLE)
    fig = plt.figure(figsize=(9.50, 4.50))
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.20,
                           width_ratios=[1, 1.15],
                           left=0.07, right=0.985,
                           top=0.89, bottom=0.16)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    build_panel_a(ax1)
    build_panel_b(ax2)
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig10_h5_four_agent.png")
    pdf = str(FIGURES_DIR / "fig10_h5_four_agent.pdf")
    fig.savefig(png, dpi=1200, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1200, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_10_h5_four_agent.py -- PRODUCTION")
    logger.info("=" * 60)
    fig = build_figure()
    save_figure(fig)
    logger.info("figure_10_h5_four_agent.py complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
