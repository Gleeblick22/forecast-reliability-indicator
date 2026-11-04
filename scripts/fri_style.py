"""fri_style.py: one colour palette and plot style for every FRI figure (import it in each figure script).
Rule: a colour always means the same thing in every figure.
  FRI blue #2a78d6 | Baseline grey #52514e | Volatility orange #eb6834 | Forecast level aqua #1baf7a
  Constant x0.75 #9085e9 | Constant x0.25 #6250d6 | Extreme/unreliable red #e34948 | Normal grey #b4b2a9
Periods are not colours: 2023-25 solid/filled, 2022 dashed/open."""
import os
import matplotlib as mpl
import matplotlib.style
from matplotlib import font_manager

# Use Times New Roman from Windows when running under WSL (no install or sudo needed)
for _f in ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"):
    _p = os.path.join("/mnt/c/Windows/Fonts", _f)
    if os.path.exists(_p):
        font_manager.fontManager.addfont(_p)

C = dict(
    fri="#2a78d6", fri_dark="#184f95", fri_light="#cde2fb",
    baseline="#52514e", vol="#eb6834", flevel="#1baf7a",
    const75="#9085e9", const25="#6250d6",
    extreme="#e34948", normal="#b4b2a9",
    feat_decision="#184f95", feat_revision="#3987e5", feat_other="#9ec5f4",
    ink="#0b0b0b", ink2="#52514e", grid="#e4e2db", axis="#888780",
    part_fit="#f1efe8", part_val="#e4e2db", part_test1="#d3d1c7", part_test2="#f7f6f3",
    box_head="#184f95", box_head_rep="#0f766e", box_fill="#f5f7fa", box_line="#9aa5b1",
)
AGENT = {"Baseline (no scaling)": C["baseline"], "FRI three-band": C["fri"], "Volatility-matched": C["vol"],
         "Forecast-level-matched*": C["flevel"], "Constant ×0.75": C["const75"], "Constant ×0.25": C["const25"]}


def use():
    """Apply the shared style. Call once at the top of every figure script."""
    mpl.style.use("seaborn-v0_8-whitegrid")
    mpl.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "legend.frameon": True, "legend.framealpha": 0.9, "legend.edgecolor": "#cccccc",
        "axes.edgecolor": "#333333", "axes.linewidth": 0.8, "axes.labelcolor": C["ink"],
        "axes.spines.top": False, "axes.spines.right": False,
        "grid.linewidth": 0.4, "grid.color": "#e0e0e0", "lines.linewidth": 1.2, "lines.markersize": 4,
        "axes.prop_cycle": mpl.cycler(color=[C["fri"], C["vol"], C["flevel"], C["const75"], C["const25"]]),
        "figure.dpi": 300, "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.facecolor": "white",
        "pdf.fonttype": 42, "svg.fonttype": "none",
    })
