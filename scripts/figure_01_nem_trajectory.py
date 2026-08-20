"""
figure_01_nem_trajectory.py
===========================
Fig 1: NEM predispatch price trajectory and extreme event rate.
PRODUCTION VERSION -- master theme compliant (one-shot rewrite).

Verified data (aemo_nem_all_2021_2022_processed.csv):
  102,675 rows, 5 regions, Oct 2021 - Dec 2022
  Training (< 2022-10-01): 87,510 intervals, extreme rate 14.58%
  Test (>= 2022-10-01):     15,165 intervals, extreme rate 0.94%
  Monthly mean RRP max 4504.60 -> clipped at 500 for display
  Stacked extreme-rate peak 316.9% (Jun 2022)

Panel (a): Monthly mean pre-dispatch RRP by NEM region (lines + markers,
            crisis shading, split line, ONE compact crisis label)
Panel (b): Monthly extreme price event rate by NEM region (stacked area,
            training-rate and test-rate reference annotations)

Output:
  results/figures/fig01_nem_trajectory.png
  results/figures/fig01_nem_trajectory.pdf

Project: forecast-reliability-indicator (FRI)
OSF:      10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from config.settings import (
    FIGURES_DIR, PROCESSED_DIR,
    PRICE_THRESHOLD_NEM, H4_TRAIN_TEST_SPLIT_DATE,
)
from config.logging_config import get_logger

logger = get_logger("fig_nem_trajectory")

C_TITLE_A = "#0072B2"   # Panel (a) title -- BLUE
C_TITLE_B = "#009E73"   # Panel (b) title -- GREEN

SPLIT        = pd.Timestamp(H4_TRAIN_TEST_SPLIT_DATE)
CRISIS_START = pd.Timestamp("2022-05-01")
CRISIS_END   = pd.Timestamp("2022-07-31")
PRICE_CAP    = 500.0
TRAIN_RATE   = 14.58
TEST_RATE    = 0.94
REGIONS      = ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]

REG_COLORS = {
    "NSW1": "#0072B2", "VIC1": "#D55E00", "QLD1": "#009E73",
    "SA1": "#E69F00", "TAS1": "#CC79A7",
}
LINESTYLE_MAP = {
    "NSW1": "-", "VIC1": "--", "QLD1": "-.",
    "SA1": ":", "TAS1": (0, (1, 1)),
}
# Distinct marker per region: shape survives grayscale printing and
# colour-vision deficiency where colour+dash alone may not (item 3).
MARKER_MAP = {
    "NSW1": "o", "VIC1": "s", "QLD1": "^",
    "SA1": "D", "TAS1": "v",
}

C_SPLIT    = "#534AB7"
C_CRISIS   = "#C0392B"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "axes.labelsize":     7.5,
    "xtick.labelsize":    6,
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
    logger.info("Loading processed NEM data...")
    df = pd.read_csv(
        PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv",
        parse_dates=["DATETIME"], low_memory=False)
    logger.info(f"Loaded {len(df):,} rows")
    return df


def aggregate_monthly(df):
    df = df.copy()
    df["DATETIME"] = pd.to_datetime(df["DATETIME"], dayfirst=True)
    df["month"] = df["DATETIME"].dt.to_period("M").dt.to_timestamp()
    price = (df.groupby(["month", "REGIONID"], as_index=False)
               .agg(mean_price=("last_forecast", "mean")))
    ext = (df.groupby(["month", "REGIONID"])
             .agg(extreme=("regime", lambda x: (x == "extreme").sum()),
                  total=("regime", "count")).reset_index())
    ext["pct"] = ext["extreme"] / ext["total"] * 100
    logger.info("Monthly aggregation complete")
    return price, ext


def style_xaxis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(),
             rotation=30, ha="right", fontsize=6)


def build_panel_a(ax, price):
    logger.info("Building Panel (a)...")
    for reg in REGIONS:
        d = price[price["REGIONID"] == reg].sort_values("month")
        ax.plot(d["month"], d["mean_price"].clip(upper=PRICE_CAP),
                color=REG_COLORS[reg], lw=0.9,
                marker=MARKER_MAP[reg], markersize=2.8,
                markeredgecolor="white", markeredgewidth=0.3,
                ls=LINESTYLE_MAP[reg], zorder=4)

    ax.axvspan(CRISIS_START, CRISIS_END, alpha=0.08,
               color=C_CRISIS, zorder=1, lw=0)
    ax.axvline(SPLIT, color=C_SPLIT, lw=0.9, ls="--",
               alpha=0.7, zorder=5)


    # Crisis span bracket above the plot (modern event-window marker)
    y_brk = PRICE_CAP + 18            # 518: above clipped peak (500)
    tick  = 10
    ax.plot([CRISIS_START, CRISIS_END], [y_brk, y_brk],
            color=C_CRISIS, lw=0.9, zorder=6, clip_on=False)
    ax.plot([CRISIS_START, CRISIS_START], [y_brk - tick, y_brk],
            color=C_CRISIS, lw=0.9, zorder=6, clip_on=False)
    ax.plot([CRISIS_END, CRISIS_END], [y_brk - tick, y_brk],
            color=C_CRISIS, lw=0.9, zorder=6, clip_on=False)
    ax.text(CRISIS_START + (CRISIS_END - CRISIS_START) / 2, y_brk + 5,
            "2022 energy crisis", fontsize=6.5, color=C_CRISIS,
            fontweight="bold", ha="center", va="bottom",
            zorder=6, clip_on=False)

    # Clip note bottom-right (empty zone)
    ax.text(0.99, 0.02, "Prices above AUD 500/MWh clipped",
            transform=ax.transAxes, fontsize=5, color="#222222",
            ha="right", va="bottom", style="italic", zorder=6)

    # Unclipped Jun 2022 annotation (yellow box + arrow to $500 plateau)
    # Item 1: condensed annotation - lead with the NEM-wide peak; the
    # full per-region breakdown lives in the dataset/summary table.
    ax.annotate(
        "June 2022 crisis peak\n"
        "NEM max: NSW1 $4,504.60/MWh\n"
        "(all mainland regions > $3,600)",
        xy=(pd.Timestamp("2022-06-01"), PRICE_CAP),
        xytext=(pd.Timestamp("2022-01-15"), 400),
        fontsize=5.5, color="#222222",
        arrowprops=dict(arrowstyle="-|>", color="#222222", lw=0.8,
                        connectionstyle="arc3,rad=-0.15"),
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#FFFDE7",
                  edgecolor="#333333", linewidth=0.6, alpha=0.97),
        zorder=12)

    ax.set_ylim(-10, PRICE_CAP + 42)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(100))
    ax.set_ylabel("Mean predispatch RRP (AUD/MWh)", fontsize=7.5)
    style_xaxis(ax)

    # Legend: region lines + crisis patch, upper LEFT (early-period
    # curves stay below 210 -> upper-left is empty above them)
    handles = [Line2D([0], [0], color=REG_COLORS[r], lw=0.9,
                      linestyle=LINESTYLE_MAP[r], marker=MARKER_MAP[r],
                      markersize=2.6, markeredgecolor="white",
                      markeredgewidth=0.3, label=r) for r in REGIONS]
    handles.append(Patch(facecolor=C_CRISIS, alpha=0.15,
                         edgecolor="none", label="Crisis period"))
    handles.append(Line2D([0], [0], color=C_SPLIT, lw=0.9, ls="--",
                          label="Train/test split (1 Oct 22)"))
    leg = ax.legend(handles=handles, loc="upper left", ncol=1,
                    fontsize=5.5, frameon=True, framealpha=0.95,
                    edgecolor=GREY_LIGHT, handlelength=1.6,
                    labelspacing=0.3, borderpad=0.35,
                    handletextpad=0.4, fancybox=False)
    leg.get_frame().set_linewidth(0.25)

    # Panel label inside top, right of legend block
    ax.set_title("(a)  Monthly mean pre-dispatch RRP by NEM region",
             fontsize=9, fontweight="bold", loc="left",
             color=C_TITLE_A, pad=7)
    logger.info("Panel (a) complete")


def build_panel_b(ax, ext):
    logger.info("Building Panel (b)...")
    pivot = (ext.pivot(index="month", columns="REGIONID", values="pct")
                .fillna(0))[REGIONS]

    ax.stackplot(pivot.index, [pivot[r].values for r in REGIONS],
                 colors=[REG_COLORS[r] for r in REGIONS],
                 alpha=0.85, zorder=3)
    ax.axvline(SPLIT, color=C_SPLIT, lw=0.9, ls="--",
               alpha=0.7, zorder=6)

    y_max = pivot.sum(axis=1).max()

    # Training rate reference + annotation (left zone is empty below 60%)
    ax.axhline(TRAIN_RATE, xmax=0.74, color=C_SPLIT, lw=0.7,
               ls=":", alpha=0.6, zorder=4)
    ax.annotate(
        f"Training extreme rate: {TRAIN_RATE:.2f}%",
        xy=(pd.Timestamp("2022-02-01"), TRAIN_RATE),
        xytext=(pd.Timestamp("2021-10-10"), 75),
        fontsize=6, color=C_SPLIT, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=C_SPLIT, lw=0.7,
                        connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor=C_SPLIT, linewidth=0.5, alpha=0.95),
        zorder=10)

    # Test rate annotation (right zone empty above the tiny test bars)
    ax.annotate(
        f"Test extreme rate: {TEST_RATE:.2f}%",
        xy=(pd.Timestamp("2022-11-15"), 4),
        xytext=(pd.Timestamp("2022-10-05"), 75),
        fontsize=6, color=C_SPLIT, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=C_SPLIT, lw=0.7,
                        connectionstyle="arc3,rad=-0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor=C_SPLIT, linewidth=0.5, alpha=0.95),
        zorder=10)

    # Peak label (verified: stacked sum peaks 316.9% in Jun 2022)
    peak_month = pivot.sum(axis=1).idxmax()
    peak_val = pivot.sum(axis=1).max()
    ax.annotate(
        f"Stacked peak: {peak_val:.1f}%\n(June 2022 crisis)",
        xy=(peak_month, peak_val),
        xytext=(pd.Timestamp("2022-08-20"), peak_val * 0.88),
        fontsize=6, color=BLACK,
        arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.7,
                        connectionstyle="arc3,rad=-0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor=GREY_LIGHT, linewidth=0.5, alpha=0.95),
        zorder=10)

    ax.set_ylabel("Extreme event rate (%, cumulative across regions)",
                  fontsize=7.5)
    ax.set_ylim(0, y_max * 1.10)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
    style_xaxis(ax)

    handles = [Line2D([0], [0], color=REG_COLORS[r], lw=3, label=r)
               for r in REGIONS]
    leg = ax.legend(handles=handles, loc="upper left", ncol=1,
                    fontsize=5.5, frameon=True, framealpha=0.95,
                    edgecolor=GREY_LIGHT, handlelength=0.9,
                    labelspacing=0.3, borderpad=0.35,
                    handletextpad=0.4, fancybox=False)
    leg.get_frame().set_linewidth(0.25)

    ax.set_title("(b)  Monthly extreme price event rate by NEM region",
             fontsize=9, fontweight="bold", loc="left",
             color=C_TITLE_B, pad=7)
    logger.info("Panel (b) complete")


def build_figure(df):
    logger.info("Building figure...")
    plt.rcParams.update(STYLE)
    price, ext = aggregate_monthly(df)
    fig = plt.figure(figsize=(6.90, 5.40))
    gs = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[1.4, 1.0],
                           hspace=0.32, left=0.10, right=0.985,
                           top=0.96, bottom=0.09)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    build_panel_a(ax1, price)
    build_panel_b(ax2, ext)
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig01_nem_trajectory.png")
    pdf = str(FIGURES_DIR / "fig01_nem_trajectory.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_01_nem_trajectory.py -- PRODUCTION (master theme)")
    logger.info("=" * 60)
    df = load_data()
    fig = build_figure(df)
    save_figure(fig)
    logger.info("=" * 60)
    logger.info("figure_01_nem_trajectory.py complete")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()