"""
figure_h9_temporal.py
=====================
Publication figure for Section 4.2.4 temporal warning profile.
POST-HOC EXPLORATORY (D-024) -- not pre-registered.

Design: Two-panel figure
  Panel (a): Horizontal bar chart
             Y = warning type
             X = number of spike episodes
             Clean -- no redundant annotations

  Panel (b): Bubble matrix
             Y = NEM region (NSW1, QLD1, SA1, TAS1, VIC1)
             X = lead time category (0, 30, 60, 90, 120, 150, 180 min)
             Bubble size  = number of episodes in that cell
             Bubble color = region color (Wong 2011)
             Count label inside each bubble
             0 min column = DURING-SPIKE episodes
             Separate row marker for NO-TRIGGER

Verified data (D-024):
  71 episodes: PRE=17 (23.9%), DURING=43 (60.6%), NO-TRIG=11 (15.5%)
  PRE-SPIKE lead times:
    NSW1=[30], QLD1=[60,90,90,120,120],
    SA1=[60,90,150], TAS1=[90,90,90,90,120,180], VIC1=[30,30]
  Mean lead time: 90.0 min

Output:
  results/figures/fig12_h9_temporal.png
  results/figures/fig12_h9_temporal.pdf

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from collections import Counter
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h9_temporal")

# ── COLORS (Wong 2011) ─────────────────────────────────────
COL_PRE    = "#009E73"
COL_DURING = "#D55E00"
COL_NONE   = "#999999"
BLACK      = "#222222"
MUTED      = "#666666"

REGION_COLORS = {
    "NSW1": "#0072B2",
    "VIC1": "#D55E00",
    "QLD1": "#009E73",
    "SA1" : "#E69F00",
    "TAS1": "#CC79A7",
}

# ── LOCKED VALUES (D-024) ──────────────────────────────────
TOTAL_EP  = 71
PRE_N     = 17
DURING_N  = 43
NOTRIG_N  = 11
MEAN_LEAD = 90.0
REGIONS   = ["NSW1", "QLD1", "SA1", "TAS1", "VIC1"]

# verified lead times per region (PRE-SPIKE only)
PRE_LEADS = {
    "NSW1": [30.0],
    "QLD1": [60.0, 90.0, 90.0, 120.0, 120.0],
    "SA1" : [60.0, 90.0, 150.0],
    "TAS1": [90.0, 90.0, 90.0, 90.0, 120.0, 180.0],
    "VIC1": [30.0, 30.0],
}

# lead time x-axis categories
LEAD_CATS = [0, 30, 60, 90, 120, 150, 180]

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
    "axes.grid":          False,
    "axes.linewidth":     0.6,
}


def load_and_verify() -> pd.DataFrame:
    """Load and verify D-024 temporal profiling results."""
    path = TABLES_DIR / "c1_09_temporal_profiling.csv"
    if not path.exists():
        logger.error(f"Not found: {path}")
        sys.exit(1)
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df)} episodes from {path.name}")

    assert len(df) == TOTAL_EP, \
        f"Total mismatch: {len(df)} vs {TOTAL_EP}"
    assert (df["warning_type"] == "PRE-SPIKE").sum()    == PRE_N
    assert (df["warning_type"] == "DURING-SPIKE").sum() == DURING_N
    assert (df["warning_type"] == "NO-TRIGGER").sum()   == NOTRIG_N

    pre = df[df["warning_type"] == "PRE-SPIKE"]
    for region, expected in PRE_LEADS.items():
        actual = sorted(
            pre[pre["region"] == region]["lead_time_min"].tolist()
        )
        assert actual == expected, \
            f"{region} lead mismatch: {actual} vs {expected}"

    assert abs(pre["lead_time_min"].mean() - MEAN_LEAD) < 0.01
    logger.info("All locked values verified")
    return df


def build_bubble_matrix(df: pd.DataFrame) -> dict:
    """
    Build bubble matrix data structure.

    Returns dict:
      matrix[region][lead_cat] = {
        'pre'   : count of PRE-SPIKE episodes,
        'during': count of DURING-SPIKE episodes,
        'notrig': count of NO-TRIGGER episodes,
      }
    """
    matrix = {
        r: {lc: {"pre": 0, "during": 0, "notrig": 0}
            for lc in LEAD_CATS}
        for r in REGIONS
    }

    # PRE-SPIKE: use actual lead time
    pre_df = df[df["warning_type"] == "PRE-SPIKE"]
    for _, row in pre_df.iterrows():
        lead = int(row["lead_time_min"])
        matrix[row["region"]][lead]["pre"] += 1

    # DURING-SPIKE: lead time = 0
    dur_df = df[df["warning_type"] == "DURING-SPIKE"]
    for _, row in dur_df.iterrows():
        matrix[row["region"]][0]["during"] += 1

    # NO-TRIGGER: lead time = 0 (missed entirely)
    ntr_df = df[df["warning_type"] == "NO-TRIGGER"]
    for _, row in ntr_df.iterrows():
        matrix[row["region"]][0]["notrig"] += 1

    # log matrix
    logger.info("Bubble matrix:")
    for region in REGIONS:
        row_str = "  " + region + ": "
        for lc in LEAD_CATS:
            cell = matrix[region][lc]
            total = cell["pre"] + cell["during"] + cell["notrig"]
            if total > 0:
                row_str += f"[{lc}min={total}] "
        logger.info(row_str)

    return matrix


def build_panel_a(ax) -> None:
    """
    Panel (a): Clean horizontal bar chart.
    Three bars: PRE-SPIKE, DURING-SPIKE, NO-TRIGGER.
    No redundant annotations.
    """
    logger.info("Building Panel (a)...")

    categories = ["NO-TRIGGER", "DURING-SPIKE", "PRE-SPIKE"]
    counts     = [NOTRIG_N, DURING_N, PRE_N]
    colors     = [COL_NONE, COL_DURING, COL_PRE]
    alphas     = [0.70, 0.85, 0.90]

    for i, (cnt, col, alph) in enumerate(
            zip(counts, colors, alphas)):
        ax.barh(i, cnt, 0.50,
                color=col, alpha=alph,
                edgecolor="white", linewidth=0.3,
                zorder=3)
        pct = cnt / TOTAL_EP * 100
        # percentage outside bar
        ax.text(cnt + 0.6, i,
                f"({pct:.1f}%)",
                va="center", ha="left",
                fontsize=6.5, color=BLACK,
                fontweight="bold")
        # count inside bar
        ax.text(cnt / 2, i,
                str(cnt),
                va="center", ha="center",
                fontsize=7.5, color="white",
                fontweight="bold")

    ax.set_yticks(range(len(categories)))
    ytick_labels = []
    for cat in categories:
        if cat == "PRE-SPIKE":
            ytick_labels.append(
                f"PRE-SPIKE\n(mean {int(MEAN_LEAD)} min)"
            )
        else:
            ytick_labels.append(cat)
    ax.set_yticklabels(ytick_labels,
                       fontweight="bold", fontsize=6.5)
    # italicize the mean lead sub-label for PRE-SPIKE
    for tick_label in ax.get_yticklabels():
        if "mean" in tick_label.get_text():
            tick_label.set_fontsize(6.5)
    ax.set_xlabel("Number of spike episodes (n=71)",
                  fontweight="bold")
    ax.set_xlim(0, DURING_N + 20)
    ax.set_title(
        "(a)  FRI warning type distribution",
        loc="left", fontweight="bold", pad=5,
    )
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_linewidth(0.6)
    ax.spines["left"].set_color("#AAAAAA")
    ax.spines["bottom"].set_visible(True)
    ax.xaxis.grid(True, color="#E8E8E8",
                  linewidth=0.5, zorder=0)


def build_panel_b(ax) -> None:
    """
    Panel (b): PRE-SPIKE only bubble matrix.
    Y = NEM region, X = lead time (30-180 min).
    Bubble size proportional to episode count per cell.
    Color = region color (Wong 2011).
    Count label inside each bubble.
    DURING-SPIKE and NO-TRIGGER excluded --
    already shown clearly in Panel (a).
    """
    logger.info("Building Panel (b) -- PRE-SPIKE bubble matrix...")

    pre_cats = [30, 60, 90, 120, 150, 180]
    region_y = {r: i for i, r in enumerate(REGIONS)}
    lead_x   = {lc: i for i, lc in enumerate(pre_cats)}

    # count episodes per region x lead time cell
    cell_counts = {
        r: {lc: 0 for lc in pre_cats}
        for r in REGIONS
    }
    for region, leads in PRE_LEADS.items():
        for lead in leads:
            cell_counts[region][int(lead)] += 1

    # log for verification
    for region in REGIONS:
        row = {lc: cell_counts[region][lc]
               for lc in pre_cats
               if cell_counts[region][lc] > 0}
        logger.info(f"  {region}: {row}")

    # bubble size scaling
    max_count = max(
        cell_counts[r][lc]
        for r in REGIONS for lc in pre_cats
    )
    SIZE_MAX = 900
    SIZE_MIN = 120

    def bubble_size(n):
        if n == 0:
            return 0
        return SIZE_MIN + (SIZE_MAX - SIZE_MIN) * (n / max_count)

    # draw bubbles
    for region in REGIONS:
        y   = region_y[region]
        col = REGION_COLORS[region]
        for lc in pre_cats:
            x = lead_x[lc]
            n = cell_counts[region][lc]
            if n == 0:
                continue
            sz = bubble_size(n)
            ax.scatter(x, y,
                       s          = sz,
                       c          = col,
                       alpha      = 0.82,
                       edgecolors = "white",
                       linewidths = 0.5,
                       zorder     = 3)
            ax.text(x, y, str(n),
                    ha="center", va="center",
                    fontsize=6.5,
                    color="white",
                    fontweight="bold",
                    zorder=4)

    # n= total per region on right
    for region in REGIONS:
        y     = region_y[region]
        total = len(PRE_LEADS[region])
        ax.text(len(pre_cats) - 0.3, y,
                f"n={total}",
                ha="left", va="center",
                fontsize=7.5,
                color=REGION_COLORS[region])

    # vertical gridlines at each lead time column
    for i in range(len(pre_cats)):
        ax.axvline(i, color="#E8E8E8",
                   linewidth=0.6, linestyle="--",
                   zorder=0)

    # horizontal grid lines between regions
    for i in range(len(REGIONS)):
        ax.axhline(i - 0.5, color="#F0F0F0",
                   linewidth=0.5, zorder=0)

    # y axis region labels colored
    ax.set_yticks(range(len(REGIONS)))
    ax.set_yticklabels(REGIONS,
                       fontweight="bold",
                       fontsize=6.5)
    for label, region in zip(
            ax.get_yticklabels(), REGIONS):
        label.set_color(REGION_COLORS[region])

    # x axis lead time labels
    ax.set_xticks(range(len(pre_cats)))
    ax.set_xticklabels(
        [f"{lc} min" for lc in pre_cats],
        fontsize=6.5,
    )
    ax.set_xlim(-0.6, len(pre_cats) - 0.1)
    ax.set_ylim(-0.6, len(REGIONS) - 0.3)
    ax.set_xlabel(
        "FRI advance warning lead time (min)",
        fontweight="bold",
    )
    ax.set_title(
        "(b)  PRE-SPIKE lead time by region",
        loc="left", fontweight="bold", pad=5,
    )
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_linewidth(0.6)
    ax.spines["left"].set_color("#AAAAAA")
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_linewidth(0.6)
    ax.spines["bottom"].set_color("#AAAAAA")


def main() -> None:
    logger.info("Starting figure_h9_temporal (bar + bubble matrix)")
    logger.info("POST-HOC EXPLORATORY D-024 -- not pre-registered")

    df     = load_and_verify()
    matrix = build_bubble_matrix(df)

    plt.rcParams.update(STYLE)
    fig = plt.figure(figsize=(9.0, 4.2))
    gs  = gridspec.GridSpec(
        1, 2,
        figure=fig,
        wspace=0.18,
        width_ratios=[1.0, 1.0],
        left=0.08, right=0.97,
        top=0.94,  bottom=0.14,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])

    build_panel_a(ax_a)
    build_panel_b(ax_b)

    out_png = FIGURES_DIR / "fig12_h9_temporal.png"
    out_pdf = FIGURES_DIR / "fig12_h9_temporal.pdf"
    fig.savefig(out_png, dpi=1000)
    fig.savefig(out_pdf, dpi=1000)
    plt.close(fig)

    logger.info(f"Saved: {out_png}")
    logger.info(f"Saved: {out_pdf}")
    logger.info("figure_h9_temporal complete")


if __name__ == "__main__":
    main()
