"""
figure_h7_revenue.py — Fig 15: RPM by NEM region, baseline vs FRI overlay agent.
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h7_revenue")

COLOR_BASE = "#999999"
COLOR_OVL  = "#0072B2"
COLOR_POS  = "#009E73"
COLOR_NEG  = "#D55E00"
BLACK      = "#222222"
REGION_ORDER = ["VIC1", "SA1", "NSW1", "QLD1", "TAS1"]

STYLE = {
    "font.family": "Latin Modern Roman", "font.size": 6,
    "axes.labelsize": 7, "xtick.labelsize": 5.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 5.5, "figure.dpi": 1000, "savefig.dpi": 1000,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
    "axes.facecolor": "white", "figure.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.grid": True,
    "grid.color": "#E8E8E8", "grid.linestyle": "-",
    "grid.linewidth": 0.5, "axes.axisbelow": True,
    "axes.linewidth": 0.6, "xtick.major.size": 3, "ytick.major.size": 0,
}

def load_data():
    reg   = pd.read_csv(TABLES_DIR / "h7_overlay_regional.csv")
    small = reg[reg["battery"] == "small"].copy()
    return small.set_index("region")

def build_figure(small):
    plt.rcParams.update(STYLE)
    fig, ax = plt.subplots(figsize=(4.80, 3.20))
    fig.subplots_adjust(left=0.16, right=0.72, top=0.88, bottom=0.14)

    n, y, bar_h, gap = len(REGION_ORDER), np.arange(len(REGION_ORDER)), 0.22, 0.06

    for i, region in enumerate(REGION_ORDER):
        row     = small.loc[region]
        base    = row["baseline_rpm"]
        overlay = row["overlay_rpm"]
        rev_pct = row["revenue_pct"]
        y_base  = y[i] + gap/2 + bar_h/2
        y_ovl   = y[i] - gap/2 - bar_h/2

        ax.barh(y_base, base,    height=bar_h, color=COLOR_BASE, edgecolor="white", linewidth=0.3, zorder=3)
        ax.barh(y_ovl,  overlay, height=bar_h, color=COLOR_OVL,  edgecolor="white", linewidth=0.3, zorder=3)

        ax.text(base    + 1.5, y_base, f"${base:.0f}",    va="center", ha="left", fontsize=5, color=COLOR_BASE, fontweight="bold", zorder=5)
        ax.text(overlay + 1.5, y_ovl,  f"${overlay:.0f}", va="center", ha="left", fontsize=5, color=COLOR_OVL,  fontweight="bold", zorder=5)

        col  = COLOR_POS if rev_pct > 0 else COLOR_NEG
        sign = "+" if rev_pct > 0 else ""
        ax.text(175, y[i], f"{sign}{rev_pct:.2f}%", va="center", ha="left", fontsize=5.5, color=col, fontweight="bold", zorder=5)

    ax.text(175, n - 0.3, "Total revenue\nchange (%)", va="bottom", ha="left", fontsize=5, color=BLACK, fontweight="bold", zorder=5)
    ax.set_yticks(y)
    ax.set_yticklabels(REGION_ORDER, fontsize=7, color=BLACK, fontweight="bold")
    ax.set_xlabel("Revenue per MWh dispatched (AUD/MWh)", fontsize=7, color=BLACK, fontweight="bold", labelpad=4)
    ax.set_xlim(0, 170)
    ax.tick_params(axis="x", colors=BLACK)
    for label in ax.get_xticklabels():
        label.set_fontweight("bold")
    ax.spines["bottom"].set_color("#CCCCCC")

    # Title top left
    ax.text(0.0, 1.12, "RPM by region: baseline vs FRI overlay",
            transform=ax.transAxes, fontsize=7, fontweight="bold",
            va="bottom", ha="left", color=BLACK)

    # Legend single line directly below title
    handles = [Patch(color=COLOR_BASE, label="Baseline agent"),
               Patch(color=COLOR_OVL,  label="FRI overlay")]
    leg = ax.legend(handles=handles,
                    loc="upper left", bbox_to_anchor=(0.0, 1.07),
                    ncol=2, fontsize=5.5, frameon=True, framealpha=0.95,
                    edgecolor="#CCCCCC", handlelength=0.8,
                    handletextpad=0.3, borderpad=0.3,
                    columnspacing=0.8, fancybox=False)
    leg.get_frame().set_linewidth(0.5)

    return fig

def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig15_rpm_by_region.png")
    pdf = str(FIGURES_DIR / "fig15_rpm_by_region.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    plt.close()

def main():
    small = load_data()
    fig   = build_figure(small)
    save_figure(fig)
    sys.exit(0)

if __name__ == "__main__":
    main()
