"""
figure_h4_shap.py
=================
Publication figure for H4 SHAP attribution.
PRODUCTION VERSION -- master theme compliant.

Verified data (shap_importance.csv), matches Table 10:
  f_current_rrp 34.94%, f_forecast_revision 30.70% (top-2 = 65.64%),
  f_rolling_max_30min 8.83%, f_rolling_mean_30min 7.23%,
  f_price_change_60min 4.22% (top-5 = 85.92%).
  Negative direction: f_day_of_week (3.71%), f_price_change_30min (2.80%).

Single panel: horizontal bars by mean |SHAP|, orange=positive direction,
blue=negative direction, dashed separator under top-2 dominant features.
Matches locked Fig caption (orange positive / blue negative / dashed line).

Output:
  results/figures/fig09_h4_shap.png
  results/figures/fig09_h4_shap.pdf

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h4_shap")

BLUE       = "#0072B2"
ORANGE     = "#E69F00"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"

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
    "axes.spines.left":   False,
    "axes.grid":          True,
    "grid.color":         "#E8E8E8",
    "grid.linestyle":     "-",
    "grid.linewidth":     0.5,
    "axes.axisbelow":     True,
    "axes.linewidth":     0.6,
    "ytick.major.size":   0,
}

# Display names (italic feature codes preserved)
NAME_MAP = {
    "f_current_rrp":        "Current RRP",
    "f_forecast_revision":  "Forecast revision",
    "new_revision":         "Forecast revision",
    "f_rolling_max_30min":  "Rolling max 30 min",
    "f_rolling_mean_30min": "Rolling mean 30 min",
    "f_price_change_60min": "Price change 60 min",
    "f_day_of_week":        "Day of week",
    "f_consecutive_high":   "Consecutive high",
    "f_hour_of_day":        "Hour of day",
    "f_price_change_30min": "Price change 30 min",
    "f_is_peak_hour":       "Is peak hour",
}


def load_data():
    logger.info("Loading SHAP importance data...")
    df = pd.read_csv(TABLES_DIR / "c2_21_shap_relabeled_results.csv")
    df = df.rename(columns={"pct_contribution": "shap_pct"})
    df = df.sort_values("mean_abs_shap", ascending=True).reset_index(drop=True)
    logger.info(f"Loaded {len(df)} features")
    for _, r in df.iterrows():
        logger.info(f"  {r['feature']}: {r['mean_abs_shap']:.4f} "
                    f"({r['shap_pct']:.2f}%) {r['direction']}")
    return df


def build_figure(df):
    logger.info("Building figure...")
    plt.rcParams.update(STYLE)

    fig, ax = plt.subplots(figsize=(6.90, 3.30))
    fig.subplots_adjust(left=0.20, right=0.96, top=0.97, bottom=0.13)

    y = np.arange(len(df))
    colors = [ORANGE if d == "positive" else BLUE
              for d in df["direction"]]

    ax.barh(y, df["mean_abs_shap"], height=0.62, color=colors,
            alpha=0.9, edgecolor="white", linewidth=0.3, zorder=3)

    # Value + percentage labels at bar ends
    for yi, (v, pct) in enumerate(zip(df["mean_abs_shap"], df["shap_pct"])):
        ax.text(v + 0.0004, yi, f"{v:.4f}  ({pct:.2f}%)",
                fontsize=5.5, va="center", ha="left",
                color=BLACK, fontweight="bold", zorder=5)

    # Dashed separator under top-2 dominant features
    ax.axhline(len(df) - 2.5, color="#534AB7", ls="--", lw=0.7,
               alpha=0.7, zorder=2)
    ax.text(0.0295, len(df) - 2.78,
            "Top 2 features: 70.36% of total attribution",
            fontsize=5.5, color="#534AB7", style="normal",
            fontweight="bold", ha="right", va="top", zorder=5)

    # Y labels
    ax.set_yticks(y)
    ax.set_yticklabels([NAME_MAP.get(f, f) for f in df["feature"]],
                       fontsize=6.5, color=BLACK, fontweight="bold")

    ax.set_xlabel("Mean |SHAP| value", fontsize=7.5, color=BLACK,
                  labelpad=3, fontweight="bold")
    ax.set_xlim(0, 0.0365)
    ax.grid(axis="y", visible=False)

    # Legend inside lower right (bars shrink toward bottom -> space free)
    handles = [
        Patch(color=ORANGE, label="Positive effect on extreme probability"),
        Patch(color=BLUE,   label="Negative effect on extreme probability"),
    ]
    leg = ax.legend(handles=handles, loc="lower right", fontsize=5.5,
                    frameon=True, framealpha=0.95, edgecolor=GREY_LIGHT,
                    handlelength=0.9, handletextpad=0.4, borderpad=0.35,
                    labelspacing=0.3, fancybox=False)
    leg.get_frame().set_linewidth(0.25)

    logger.info("Figure complete")
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig09_h4_shap.png")
    pdf = str(FIGURES_DIR / "fig09_h4_shap.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_h4_shap.py -- PRODUCTION (master theme)")
    logger.info("=" * 60)
    df = load_data()
    fig = build_figure(df)
    save_figure(fig)
    logger.info("=" * 60)
    logger.info("figure_h4_shap.py complete")
    logger.info(f"Output: {FIGURES_DIR}/fig09_h4_shap.png/.pdf")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
