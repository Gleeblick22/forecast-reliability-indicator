"""make_figures.py (Roadmap v3, B3): Figs. 1, 3-9 in black and white (300 dpi) + captions.md.
Reads results/numbers.json and the label/score files; recomputed AUC/AP must match numbers.json.
Fig. 2 (architecture) is drawn by hand (B4)."""
import json, re, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.patches import Patch
from sklearn.metrics import roc_curve, precision_recall_curve, roc_auc_score, average_precision_score
from config.settings import TABLES_DIR, PROCESSED_DIR

R = TABLES_DIR.parent
FIG = R / "figures"; FIG.mkdir(exist_ok=True)
N = json.load(open(R / "numbers.json")); h, S = N["headline"], N["sources"]
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
                     "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.edgecolor": "black",
                     "axes.linewidth": 0.6, "grid.color": "0.88", "grid.linewidth": 0.5, "lines.linewidth": 1.2,
                     "savefig.dpi": 300, "mathtext.fontset": "dejavuserif", "pdf.fonttype": 42, "svg.fonttype": "none", "legend.frameon": True, "legend.edgecolor": "0.7", "hatch.linewidth": 0.5})
import fri_style as FS
FS.use()
C = FS.C
W1, W2 = 3.5, 7.0
CAP = {}
KEYS = ["DATETIME", "REGIONID"]
YC = ["y_v2", "y_v2_d300", "y_true", "y", "label"]
SC = ["fri_score", "score", "y_score", "proba", "pred_proba", "p"]


def save(fig, n, caption):
    fig.tight_layout()
    for ext in ("png", "svg", "pdf"):
        fig.savefig(FIG / f"fig_{n}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    CAP[n] = caption
    print(f"Fig. {n} saved")


def pick(df, cands, what):
    for c in cands:
        if c in df.columns:
            return c
    sys.exit(f"{what}: none of {cands} in columns {list(df.columns)}")


def check(name, got, want, tol=0.002):
    ok = abs(got - want) <= tol
    print(f"  check {name}: recomputed {got:.4f} vs numbers.json {want:.4f} -> {'OK' if ok else 'MISMATCH'}")
    if not ok:
        sys.exit("Stop: figure data do not match numbers.json")


lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", usecols=["DATETIME", "partition", "y_v2"], parse_dates=["DATETIME"])
s22 = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv")
Y22, P22 = pick(s22, YC, "2022 label"), pick(s22, SC, "2022 score")
y22, p22 = s22[Y22].values, s22[P22].values
rep = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"])
sc = pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])
rep = rep.merge(sc[KEYS + ["fri_score"]], on=KEYS, how="left")
assert rep.fri_score.notna().all()
y25, p25 = rep[pick(rep, YC, "2023-25 label")].values, rep["fri_score"].values
R2_AUC = float(S["R"][1]["result"].split()[1])
check("AUC 2022", roc_auc_score(y22, p22), h["det2022"]["auc"])
check("AP 2022", average_precision_score(y22, p22), h["det2022"]["ap"])
check("AUC 2023-25 (R2)", roc_auc_score(y25, p25), R2_AUC)

# ---------- Fig. 1: monthly share of unreliable decision forecasts (single panel; fri_style.py) ----------
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
per = np.where(lab.partition == "test", "test", np.where(lab.DATETIME < "2022-08-01", "fit", "val"))
m = pd.concat([pd.DataFrame({"DATETIME": lab.DATETIME, "y": lab.y_v2.values, "period": per}),
               pd.DataFrame({"DATETIME": rep.DATETIME, "y": y25, "period": "replication"})])
tot = m.groupby("period").y.agg(n="size", pos="sum", rate="mean")
m["month"] = (m.DATETIME - pd.Timedelta(minutes=30)).dt.to_period("M")
g = m.groupby(["period", "month"]).agg(n=("y", "size"), rate=("y", "mean")).reset_index()
drop = m.groupby(["period", "month"]).y.size().reset_index(name="n")
drop = drop[drop.n < 1000]
g = g[g.n >= 1000].reset_index(drop=True)
# ---- data checks for Fig. 1: stop if anything differs from numbers.json ----
for key, p_ in (("n_fit", "fit"), ("n_val", "val"), ("n_test", "test"), ("rep_lead30", "replication")):
    got, want = int(tot.loc[p_, "n"]), int(h[key])
    print(f"  check Fig.1 observations {p_:<11}: {got:>7,} vs numbers.json {want:>7,} -> {'OK' if got == want else 'MISMATCH'}")
    if got != want: sys.exit("Stop: Fig. 1 data do not match numbers.json")
got = int(tot.loc["test", "pos"])
print(f"  check Fig.1 unreliable in test 1: {got} vs numbers.json {int(h['n_test_pos'])} -> {'OK' if got == int(h['n_test_pos']) else 'MISMATCH'}")
if got != int(h["n_test_pos"]): sys.exit("Stop: Fig. 1 data do not match numbers.json")
print(f"  check Fig.1 rows left out of monthly points (day edges only): {int(drop.n.sum())} in {len(drop)} part-months, "
      f"largest {int(drop.n.max()) if len(drop) else 0} -> {'OK' if (len(drop) == 0 or drop.n.max() < 100) else 'MISMATCH'}")
if len(drop) and drop.n.max() >= 100: sys.exit("Stop: a real month would be dropped from Fig. 1")
print("  Fig.1 totals:", {p_: (int(tot.loc[p_, 'n']), int(tot.loc[p_, 'pos']), round(tot.loc[p_, 'rate'] * 100, 2)) for p_ in tot.index})
print(f"  Fig.1 peak: {g.loc[g.rate.idxmax(), 'month']} {g.rate.max() * 100:.2f}%")
T = pd.Timestamp
ORDER = ["fit", "val", "test", "replication"]
SHADE = {"fit": C["part_fit"], "val": C["part_val"], "test": C["part_test1"], "replication": C["part_test2"]}
SPAN = {"fit": ("2021-10-01", "2022-08-01"), "val": ("2022-08-01", "2022-10-01"), "test": ("2022-11-01", "2023-01-01"),
        "replication": ("2023-01-01", "2026-01-01")}
OCT = (T("2022-10-01"), T("2022-11-01"))
num = lambda p_: f"{int(tot.loc[p_, 'n']):,} obs., {tot.loc[p_, 'rate'] * 100:.2f}%"

fig, (axs, ax) = plt.subplots(2, 1, figsize=(7.2, 3.3), sharex=True,
                              gridspec_kw={"height_ratios": [1.35, 4.2], "hspace": 0.05})
# timeline strip: parts of the data with their size and unreliable share
axs.set_ylim(0, 4.2); axs.axis("off")
for p_ in ORDER:
    axs.axvspan(T(SPAN[p_][0]), T(SPAN[p_][1]), ymin=0, ymax=0.45, color=SHADE[p_], ec="white", lw=1.2)
axs.axvspan(*OCT, ymin=0, ymax=0.45, facecolor="white", edgecolor=C["axis"], hatch="////", lw=0)
mid = lambda a, b: T(a) + (T(b) - T(a)) / 2
axs.text(mid(*SPAN["fit"]), 0.95, f"Fit\n{num('fit')}", ha="center", va="center", fontsize=7.5, linespacing=1.1)
axs.text(mid(*SPAN["replication"]), 0.95, f"Test 2 (replication, model frozen)\n{num('replication')}",
         ha="center", va="center", fontsize=7.5, linespacing=1.1)
def lead(x_bar, x_txt, y_txt, text, ha):
    axs.annotate(text, xy=(x_bar, 1.92), xytext=(x_txt, y_txt), ha=ha, va="center", fontsize=8,
                 arrowprops=dict(arrowstyle="-", lw=0.5, color=C["ink2"], shrinkA=1, shrinkB=0))
lead(T("2022-09-01"), T("2022-06-20"), 2.75, f"Validation: {num('val')}", "right")
lead(T("2022-10-16"), T("2022-10-16"), 3.75, "Oct 2022 excluded", "center")
lead(T("2022-12-01"), T("2023-03-10"), 2.75, f"Test 1: {num('test')}", "left")

# main panel
for p_ in ORDER:
    ax.axvspan(T(SPAN[p_][0]), T(SPAN[p_][1]), color=SHADE[p_], lw=0, zorder=0)
ax.axvspan(*OCT, facecolor="white", edgecolor=C["axis"], hatch="////", lw=0, zorder=0)
ax.set_yscale("log"); ax.set_ylim(0.04, 60)
ax.yaxis.set_major_locator(mticker.FixedLocator([0.1, 0.3, 1, 3, 10, 30]))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}%"))
ax.yaxis.set_minor_locator(mticker.NullLocator())
for k_, p_ in enumerate(ORDER):
    d_ = g[g.period == p_]
    ax.plot(d_.month.dt.to_timestamp() + pd.Timedelta(days=14), d_.rate * 100, color=C["extreme"], marker="o",
            ms=3, lw=1.2, zorder=3, label="Monthly share of unreliable intervals" if k_ == 0 else None)
pk = g.loc[g.rate.idxmax()]
xp = pk.month.to_timestamp() + pd.Timedelta(days=14)
ax.annotate(f"{pk.month.strftime('%b %Y')}: {pk.rate * 100:.1f}%\n(administered pricing)", xy=(xp, pk.rate * 100),
            xytext=(T("2022-09-10"), 14.0), fontsize=8, va="center", ha="left",
            bbox=dict(boxstyle="square,pad=0.25", fc="white", ec="none", alpha=0.9),
            arrowprops=dict(arrowstyle="-", lw=0.5, color=C["ink2"], shrinkA=0, shrinkB=3), zorder=5)
ax.legend(loc="upper right")
ax.set_ylabel("Unreliable intervals (%, log scale)")
ax.set_xlim(T("2021-10-01"), T("2026-01-01"))
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
save(fig, 1, f"Fig. 1. Monthly share of unreliable decision forecasts (|f(w_t) − p̄_t| > AUD 300/MWh) across the five NEM regions "
     f"(log scale). The strip above gives each part of the data (Table I) with its number of interval-region observations and "
     f"share of unreliable ones. October 2022 is excluded because the AEMO archive holds only the latest pre-dispatch run for "
     f"that month; the {pk.month.strftime('%B %Y')} peak ({pk.rate * 100:.1f}%) falls in the administered-pricing period.")

# ---------- Fig. 3: one real interval (TAS1, interval ending 24 Dec 2022 17:00), colour, fri_style.py ----------
REG3, END3 = "TAS1", pd.Timestamp("2022-12-24 17:00")
row3 = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
row3 = row3[(row3.REGIONID == REG3) & (row3.DATETIME == END3)].iloc[0]
parts3 = []
for ch in pd.read_csv(PROCESSED_DIR.parent / "raw" / "aemo_nem" / "aemo_nem_all_2021_2022_raw.csv", chunksize=2_000_000,
                      usecols=["REGIONID", "DATETIME", "RRP", "INTERVENTION", "LASTCHANGED", "PREDISPATCH_RUN_DATETIME"]):
    ch = ch[(ch.REGIONID == REG3) & (ch.DATETIME.astype(str).str.startswith(END3.strftime("%Y-%m-%d %H:%M")))]
    if len(ch): parts3.append(ch)
r3 = pd.concat(parts3)
for c_ in ("DATETIME", "LASTCHANGED", "PREDISPATCH_RUN_DATETIME"): r3[c_] = pd.to_datetime(r3[c_])
r3 = r3[r3.INTERVENTION == 0].sort_values("PREDISPATCH_RUN_DATETIME").drop_duplicates("PREDISPATCH_RUN_DATETIME", keep="last")
r3["lead_min"] = (r3.DATETIME - r3.PREDISPATCH_RUN_DATETIME).dt.total_seconds() / 60
r3 = r3[r3.lead_min >= row3.decision_lead_min]                       # runs available up to the decision run
dec3 = r3[r3.lead_min == row3.decision_lead_min].iloc[0]
pub3 = (dec3.LASTCHANGED - dec3.PREDISPATCH_RUN_DATETIME).total_seconds() / 60
# ---- data checks for Fig. 3 ----
for name_, got_, want_ in (("first forecast", r3.RRP.iloc[0], row3.f_first), ("decision forecast", dec3.RRP, row3.f_decision),
                           ("runs up to decision", len(r3), row3.n_runs)):
    ok_ = abs(float(got_) - float(want_)) < 1e-6
    print(f"  check Fig.3 {name_}: raw {float(got_):.4f} vs label file {float(want_):.4f} -> {'OK' if ok_ else 'MISMATCH'}")
    if not ok_: sys.exit("Stop: Fig. 3 data do not match the label file")
gap3 = row3.f_decision - row3.p_disp30
print(f"  Fig.3: settled {row3.p_disp30:.2f}, gap {gap3:.1f}, unreliable={int(row3.y_v2)}, decision run published {pub3:.1f} min after its run time")

YTOP = max(540.0, float(r3.RRP.max()) * 1.12)                       # adapts if any run forecast is higher
BRK = -4.0                                                            # axis break: compressed early runs, expanded last hours
fig, (axL, ax) = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True, gridspec_kw={"width_ratios": [1.6, 3], "wspace": 0.06})
x3 = -r3.lead_min.values / 60                                        # hours relative to the end of interval t
xd = -row3.decision_lead_min / 60
for a_ in (axL, ax):
    a_.axvspan(x3[0], xd, color="#eaf2fc", lw=0, zorder=0)
    a_.step(x3, r3.RRP.values, where="post", color=C["fri"], lw=1.2, zorder=3)
    a_.plot(x3, r3.RRP.values, "o", color=C["fri"], ms=2.2, zorder=3)
axL.set_xlim(x3[0] - 0.8, BRK); ax.set_xlim(BRK, 1.45); ax.set_xticks([-3, -2, -1, 0])
axL.spines["right"].set_visible(False); ax.spines["left"].set_visible(False); ax.tick_params(left=False)
for a_, x0 in ((axL, 1), (ax, 0)):
    for y0 in (0,):
        a_.plot([x0 - 0.015, x0 + 0.015], [y0 - 0.03, y0 + 0.03], transform=a_.transAxes, color=C["axis"], lw=0.7, clip_on=False)
ax.axvspan(-0.5, 0, color=C["part_test1"], lw=0, zorder=0)
ax.step([], [], color=C["fri"], lw=1.2, label="Forecast for interval $t$ (each run)")
ax.plot([xd], [row3.f_decision], "D", color=C["fri_dark"], ms=6, zorder=5)
ax.hlines(row3.p_disp30, -0.5, 0, color=C["extreme"], lw=2.4, zorder=4, label=r"Settled price $\bar{p}_t$")
ax.annotate("", xy=(-0.25, row3.p_disp30), xytext=(-0.25, row3.f_decision),
            arrowprops=dict(arrowstyle="<->", lw=0.8, color=C["ink"], shrinkA=0, shrinkB=0), zorder=6)
ax.text(0.12, (row3.p_disp30 + row3.f_decision) / 2, f"$|f-\\bar{{p}}_t|$ = {abs(gap3):.0f}\n> 300: unreliable",
        ha="left", va="center", fontsize=8, color="#a32d2d")
ax.annotate(f"Decision forecast $f(w_t)$ = {row3.f_decision:.0f}\n(run at the start of interval $t$)",
            xy=(xd, row3.f_decision), xytext=(-3.85, row3.f_decision * 0.97), ha="left", va="center",
            fontsize=8, color=C["fri_dark"], arrowprops=dict(arrowstyle="-", lw=0.5, color=C["ink2"], shrinkA=0, shrinkB=4))
axL.annotate(f"First forecast {r3.RRP.iloc[0]:.0f}\n({r3.lead_min.iloc[0] / 60:.1f} h ahead)", xy=(x3[0], r3.RRP.iloc[0]),
             xytext=(x3[0] + 0.5, 175), ha="left", va="center", fontsize=8,
             arrowprops=dict(arrowstyle="-", lw=0.5, color=C["ink2"], shrinkA=0, shrinkB=3))
axL.text((x3[0] + BRK) / 2, 300, "Revision path:\nruns available before\nthe decision (FRI features)", ha="center", fontsize=8,
         color=C["fri_dark"], style="italic", linespacing=1.15)
ax.text(-0.25, YTOP * 0.955, "Interval $t$", ha="center", fontsize=8)
axL.set_ylim(min(0.0, float(r3.RRP.min()) * 1.1), YTOP)
axL.set_ylabel("Price (AUD/MWh)")
fig.supxlabel("Hours relative to the end of trading interval $t$ (AEMO timestamp); the axis is broken at 4 h", fontsize=9, y=-0.03)
ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.47))
save(fig, 3, f"Fig. 3. Information available for one unreliable interval ({REG3}, trading interval ending "
     f"{END3.strftime('%d %B %Y %H:%M')}). The {len(r3)} pre-dispatch runs published before the decision (shaded blue) form the "
     f"revision path used as features; the decision run, issued at the start of the interval, forecast AUD {row3.f_decision:.0f}/MWh. "
     f"The settled price, the mean of the six 5-min DISPATCHPRICE values (INTERVENTION = 0), was AUD {row3.p_disp30:.0f}/MWh, so "
     f"|f(w_t) − p̄_t| = {abs(gap3):.0f} > δ_Y = 300 and the interval is labelled unreliable. The time axis is broken at 4 h. Runs are plotted at their run time; "
     f"AEMO published the decision run {pub3:.0f} min later.")

# ---------- Fig. 5 (file fig_5): error amplification (R1), colour, fri_style.py ----------
r1 = pd.DataFrame(S["R1_regions"])
print(f"  check Fig.5 R1 ratios: {r1.ratio.min():.2f}-{r1.ratio.max():.2f} vs numbers.json {h['R1_ratio_min']:.2f}-{h['R1_ratio_max']:.2f} -> "
      f"{'OK' if abs(r1.ratio.min() - h['R1_ratio_min']) < 0.01 and abs(r1.ratio.max() - h['R1_ratio_max']) < 0.01 else 'MISMATCH'}")
if abs(r1.ratio.min() - h["R1_ratio_min"]) >= 0.01 or abs(r1.ratio.max() - h["R1_ratio_max"]) >= 0.01: sys.exit("Stop: Fig. 5 data")
print("  Fig.5 per region:", r1[["region", "mean_err_extreme", "mean_err_normal", "ratio"]].round(1).to_dict("records"))
x = np.arange(len(r1)); w = 0.36
fig, ax = plt.subplots(figsize=(3.5, 2.8))
ax.set_axisbelow(True); ax.grid(axis="x", visible=False)
ax.bar(x - w / 2 - 0.01, r1.mean_err_extreme, w, color=C["extreme"], label="Extreme interval ($\\bar{p}_t$ ≥ 300)")
ax.bar(x + w / 2 + 0.01, r1.mean_err_normal, w, color=C["normal"], label="Normal interval ($\\bar{p}_t$ < 300)")
for i, r in r1.iterrows():
    xe, xn = i - w / 2 - 0.01, i + w / 2 + 0.01
    ax.text(xe, r.mean_err_extreme * 0.86, f"{r.mean_err_extreme:,.0f}", ha="center", va="top", fontsize=5.9, color="white")
    ax.text(xn, r.mean_err_normal * 1.08, f"{r.mean_err_normal:.0f}", ha="center", va="bottom", fontsize=6.3, color=C["ink2"])
    ax.text(i, r.mean_err_extreme * 1.15, f"×{r.ratio:.0f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color=C["ink"])
ax.set_yscale("log")
ax.set_yticks([10, 30, 100, 300, 1000, 3000]); ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.set_xticks(x); ax.set_xticklabels(r1.region.str.replace("1", "", regex=False))
ax.set_ylabel(r"Mean $|f(w_t) - \bar{p}_t|$ (AUD/MWh)")
ax.set_ylim(10, max(4000, r1.mean_err_extreme.max() * 2.2)); ax.set_xlim(-0.6, len(r1) - 0.4)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7, handlelength=1.2, columnspacing=1.0)
save(fig, 5, f"Fig. 5. Mean absolute error of the decision forecast against the settled price in extreme and normal intervals, "
     f"test 2 (2023–25; R1; log scale). Bars show the mean error (AUD/MWh); bold labels give the ratio of means ({h['R1_ratio_min']:.0f}–{h['R1_ratio_max']:.0f}); Welch p < 10⁻⁷ in every region.")

# ---------- Fig. 6 (file fig_6): ROC and PR, colour, one shared legend ----------
from matplotlib.lines import Line2D
S6 = [("fri25", y25, p25, dict(color=C["fri"], ls="-", lw=1.5), 5),
      ("fri22", y22, p22, dict(color=C["fri"], ls="--", lw=1.3), 4)]
if "f_decision" in rep.columns:
    fa = np.abs(rep.f_decision.values)
    check("AP |f| 2023-25 (c4_05)", average_precision_score(y25, fa), h["fdec"]["2023-25"]["ap"])
    S6.append(("flev", y25, fa, dict(color=C["flevel"], ls="-", lw=1.1), 3))
if "recent_std_3h" in rep.columns:
    v = rep.recent_std_3h.values.astype(float); v = np.where(np.isnan(v), np.nanmin(v) - 1, v)
    check("dAP 2023-25 (R4)", average_precision_score(y25, p25) - average_precision_score(y25, v), float(S["R"][3]["result"].split()[1]))
    S6.append(("vol", y25, v, dict(color=C["vol"], ls="-", lw=1.1), 2))
fig = plt.figure(figsize=(7.2, 4.1))
gs6 = fig.add_gridspec(2, 2, height_ratios=[1, 0.17])
a, b = fig.add_subplot(gs6[0, 0]), fig.add_subplot(gs6[0, 1])
lax = fig.add_subplot(gs6[1, :]); lax.axis("off")             # legend row: tight_layout keeps it clear of the axis labels
met = {}
for k, y_, s_, st, z_ in S6:
    f_, t_, _ = roc_curve(y_, s_); pr, rc, _ = precision_recall_curve(y_, s_)
    met[k] = (roc_auc_score(y_, s_), average_precision_score(y_, s_))
    if k != "vol": a.plot(f_, t_, zorder=z_, **st)
    b.step(rc, pr, where="post", zorder=z_, **st)
print("  Fig.6 AUC/AP:", {k: (round(x_, 3), round(y__, 3)) for k, (x_, y__) in met.items()})
a.plot([0, 1], [0, 1], color=C["axis"], ls=":", lw=0.8)
a.text(0.62, 0.55, "Chance", rotation=38, fontsize=7, color=C["axis"], ha="center")
prev = float(y25.mean()); b.axhline(prev, color=C["axis"], ls=":", lw=0.8)
b.text(0.06, prev + 0.012, f"No skill, test 2 (AP = {prev:.3f})", fontsize=7, color=C["axis"], ha="left", va="bottom")
for ax_, t_, xl, yl in [(a, "(a) ROC", "False positive rate", "True positive rate"), (b, "(b) Precision–recall", "Recall", "Precision")]:
    ax_.set_title(t_, loc="left", fontstyle="italic"); ax_.set_xlabel(xl); ax_.set_ylabel(yl)
    ax_.set_xlim(0, 1); ax_.set_ylim(0, 1.02); ax_.set_box_aspect(1)
LAB = {"fri25": "FRI, test 2 (2023–25): AUC {0:.3f}, AP {1:.3f}", "fri22": "FRI, test 1 (2022): AUC {0:.3f}, AP {1:.3f}",
       "flev": "$|f(w_t)|$ alone*, test 2: AUC {0:.3f}, AP {1:.3f}", "vol": "Recent volatility, test 2: AP {1:.3f} (R4)"}
H6 = [Line2D([], [], label=LAB[k].format(*met[k]), **st) for k, _, _, st, _ in S6]
lax.legend(handles=H6, loc="center", ncol=2, fontsize=7.5, columnspacing=1.5)
save(fig, 6, f"Fig. 6. ROC (a) and precision–recall (b) curves of the FRI model, fitted on 2021–22 and then held fixed, on test 2 (2023–25, "
     f"{h['rep_lead30']:,} intervals; solid) and test 1 (2022, {h['n_test']:,} intervals, {h['n_test_pos']} unreliable; dashed). "
     f"Orange: intervals ranked by raw recent volatility (recent_std_3h), the R4 comparison. *Aqua: ranked by the decision forecast "
     f"alone, |f(w_t)| (exploratory, not registered). Dotted lines: chance (a) and the no-skill precision, equal to the share of "
     f"unreliable intervals (b).")

FEAT_LABEL = {
    "f_decision": "Decision forecast $f(w_t)$",
    "rev_abs": "Revision since earliest run (abs.)", "rev_signed": "Revision since earliest run (signed)",
    "n_runs": "Number of runs", "n_sign_flips": "Revision direction changes",
    "max_abs_step": "Largest run-to-run change", "run_std": "Std. of all runs",
    "recent_std_3h": "Std. of runs, last 3 h before decision",
    "f_current_rrp": "Earliest-run price $q_t$", "f_rolling_mean_30min": "Mean of $q$, past 3 h",
    "f_rolling_max_30min": "Max of $q$, past 3 h", "f_price_change_30min": "Change in $q$ over 3 h",
    "f_price_change_60min": "Change in $q$ over 6 h", "f_consecutive_high": "Consecutive $q$ > AUD 100/MWh",
    "f_hour_of_day": "Hour of day", "f_day_of_week": "Day of week", "f_is_peak_hour": "Peak hour (16–20 h)"}
IMP_MEASURE = "mean |SHAP value| (TreeSHAP) on the 2022 test set, as % of the total"   # c2_31 step 4, pred_contribs=True

# ---------- Fig. 7 (file fig_7): feature attribution, colour ----------
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]
imp = pd.Series(S["importance"]).sort_values()
sd, sp = float(imp["f_decision"]), float(imp[[k for k in PATH if k in imp.index]].sum())
for nm_, got_, want_ in (("decision forecast share", sd, h["attr_f_decision"]), ("revision-path share", sp, h["attr_path_group"]),
                         ("total of shares", float(imp.sum()), 100.0)):
    ok_ = abs(got_ - want_) < 0.15
    print(f"  check Fig.7 {nm_}: {got_:.2f} vs {want_:.2f} -> {'OK' if ok_ else 'MISMATCH'}")
    if not ok_: sys.exit("Stop: Fig. 7 data")
fig, ax = plt.subplots(figsize=(3.5, 3.8))
ax.set_axisbelow(True)
for i, (k, v) in enumerate(imp.items()):
    col = C["feat_decision"] if k == "f_decision" else (C["feat_revision"] if k in PATH else C["feat_other"])
    ax.barh(i, v, height=0.7, color=col); ax.text(v + 0.6, i, f"{v:.1f}", va="center", fontsize=7)
ax.set_yticks(range(len(imp))); ax.set_yticklabels([FEAT_LABEL.get(k, k) for k in imp.index], fontsize=7)
ax.set_xlabel("Share of mean |SHAP value| (%)"); ax.set_xlim(0, imp.max() * 1.2); ax.grid(axis="y", visible=False)
ax.legend(handles=[Patch(color=C["feat_decision"], label=f"Decision forecast ({sd:.1f}%)"),
                   Patch(color=C["feat_revision"], label=f"Revision path ({sp:.1f}%)"),
                   Patch(color=C["feat_other"], label=f"Earliest-run price,\ncalendar ({100 - sd - sp:.1f}%)")],
          loc="center right", bbox_to_anchor=(1.0, 0.42), fontsize=7, handlelength=1.4, borderpad=0.5)
save(fig, 7, f"Fig. 7. Feature importance of the FRI model ({len(imp)} features; {IMP_MEASURE}). The decision forecast accounts for {h['attr_f_decision']:.1f}% "
     f"and the revision-path group for {h['attr_path_group']:.1f}%.")

# ---------- Fig. 8 (file fig_8): exposure by agent, colour ----------
ORDER = [("baseline", "Baseline"), ("vol_matched", "Volatility-matched"), ("fdec_matched", "Forecast-level-matched*"), ("const_0.75", "Constant ×0.75"),
         ("const_0.25", "Constant ×0.25"), ("fri_3band", "FRI three-band")]
COL = {"baseline": C["baseline"], "vol_matched": C["vol"], "fdec_matched": C["flevel"], "const_0.75": C["const75"],
       "const_0.25": C["const25"], "fri_3band": C["fri"]}
g22 = {r["agent"]: r for r in S["gateA"] if abs(r["beta"] - 2.03) < 1e-9}
g25 = {r["agent"]: r for r in S["agents_2325"]}
for r in S["fdec_ctrl"]:
    if r["agent"] == "fdec_matched":
        (g22 if r["period"] == "2022 test" else g25)["fdec_matched"] = r
for nm_, g_, want_ in (("2022", g22, h["exposure_reduction_2022_pct"]), ("2023-25", g25, h["rep_exposure_reduction_pct"])):
    got_ = (1 - g_["fri_3band"]["mwh_into_overforecast"] / g_["baseline"]["mwh_into_overforecast"]) * 100
    print(f"  check Fig.8 exposure reduction {nm_}: {got_:.1f}% vs numbers.json {want_}% -> {'OK' if abs(got_ - want_) < 0.06 else 'MISMATCH'}")
    if abs(got_ - want_) >= 0.06: sys.exit("Stop: Fig. 8 data")
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7), sharey=True)
for ax_, g_, t_ in [(axs[0], g22, "(a) Test 1 (2022)"), (axs[1], g25, "(b) Test 2 (2023–25)")]:
    ax_.set_axisbelow(True)
    vals = [g_[k]["mwh_into_overforecast"] for k, _ in ORDER]
    base_ = g_["baseline"]["mwh_into_overforecast"]
    for i, (k, _) in enumerate(ORDER):
        ax_.barh(i, vals[i], height=0.65, color=COL[k], hatch="////" if k == "fdec_matched" else None,
                 edgecolor="white" if k == "fdec_matched" else None, lw=0)
        pc_ = (vals[i] / base_ - 1) * 100
        lbl_ = f"{vals[i]:,.1f}" if k == "baseline" else f"{vals[i]:,.1f} ({pc_:+.1f}%)".replace("-", "−")
        ax_.text(vals[i] + max(vals) * 0.02, i, lbl_, va="center", fontsize=7.5,
                 fontweight="bold" if k == "fri_3band" else "normal")
    ax_.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax_.set_title(t_, loc="left", fontstyle="italic"); ax_.set_xlim(0, max(vals) * 1.42)
    ax_.set_xlabel("MWh into over-forecast intervals"); ax_.grid(axis="y", visible=False)
axs[0].set_yticks(range(len(ORDER))); axs[0].set_yticklabels([l for _, l in ORDER]); axs[0].invert_yaxis()
a2 = re.findall(r"\[[-\d., ]+\]", h["h5_h7"]["A2 exposure 2022"]["result"])[-1]
r3 = [r for r in S["hypotheses"] if r["id"] == "R3"][0]["result"].split("; ", 1)[1]
save(fig, 8, f"Fig. 8. Energy discharged into over-forecast intervals (f(w_t) − p̄_t > AUD 300/MWh) by agent, β = 2.03. "
     f"FRI reduces exposure against the baseline by {h['exposure_reduction_2022_pct']}% in test 1 (95% CI {a2} MWh) and by "
     f"{h['rep_exposure_reduction_pct']}% in test 2 ({r3}; R3). * Exploratory control, not registered (hatched): same band counts as FRI, assigned by highest f(w_t).")

# ---------- Fig. 9 (file fig_9): R6 degradation curvature, colour ----------
B = [1.0, 1.5, 2.03]
gb = lambda b_, a_: next(r for r in S["gateA"] if abs(r["beta"] - b_) < 1e-9 and r["agent"] == a_)["net_revenue"]
r6 = {round(r["beta"], 2): r for r in S["R6"]}
adv22 = [(gb(b_, "const_0.25") / gb(b_, "fri_3band") - 1) * 100 for b_ in B]
adv25 = [(r6[b_]["net_const025"] / r6[b_]["net_fri"] - 1) * 100 for b_ in B]
fb = [abs(gb(b_, "fri_3band") / gb(b_, "baseline") - 1) * 100 for b_ in B] + \
     [abs(r6[b_]["net_fri"] / r6[b_]["net_baseline"] - 1) * 100 for b_ in B]
print("  Fig.9 constant x0.25 advantage (%): 2022", [round(v, 1) for v in adv22], "| 2023-25", [round(v, 1) for v in adv25])
fig, ax = plt.subplots(figsize=(3.5, 2.8))
lo_, hi_ = min(adv22 + adv25) - 22, max(adv22 + adv25) * 1.18
ax.axhspan(0, hi_, color="#efedfc", lw=0, zorder=0)                    # constant x0.25 ahead (violet tint)
ax.axhspan(lo_, 0, color=C["fri_light"], lw=0, zorder=0)               # FRI ahead (blue tint)
ax.axhline(0, color=C["axis"], lw=0.8, zorder=1)
ax.text(0.84, hi_ * 0.97, "Constant ×0.25 earns more", fontsize=7, color=C["const25"], ha="left", va="top", style="italic")
ax.text(2.1, lo_ * 0.5, "FRI earns more", fontsize=7, color=C["fri_dark"], ha="right", va="center", style="italic")
ax.plot(B, adv25, color=C["const25"], ls="-", marker="o", ms=5, lw=1.5, zorder=3, label="Test 2 (2023–25)")
ax.plot(B, adv22, color=C["const25"], ls="--", marker="s", ms=5, mfc="white", lw=1.5, zorder=3, label="Test 1 (2022)")
pm = lambda v: f"{v:+.0f}%".replace("-", "−")
for k_, (b_, v) in enumerate(zip(B, adv22)):
    ax.annotate(pm(v), (b_, v), textcoords="offset points", xytext=(-9, 6) if k_ == 0 else (0, 7), ha="center", fontsize=7.5)
for k_, (b_, v) in enumerate(zip(B, adv25)):
    ax.annotate(pm(v), (b_, v), textcoords="offset points", xytext=(9, -12) if k_ == 0 else (0, -13), ha="center", fontsize=7.5)
ax.set_xticks(B); ax.set_xticklabels(["1.0", "1.5", "2.03"]); ax.set_xlim(0.8, 2.13); ax.set_xlabel(r"Degradation exponent $\beta$")
ax.set_ylim(lo_, hi_); ax.grid(axis="x", visible=False)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}".replace("-", "−")))
ax.set_ylabel("Constant ×0.25 advantage\n(% of FRI net revenue)")
ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.88), fontsize=7.5)
save(fig, 9, f"Fig. 9. Net-revenue advantage of constant ×0.25 dispatch over FRI as degradation becomes less convex (R6), as a "
     f"percentage of FRI net revenue. α is rescaled at each β so that baseline degradation cost is unchanged. The advantage falls "
     f"from {pm(adv22[2])} (test 1) and {pm(adv25[2])} (test 2) at β = 2.03 to {pm(adv22[0])} and {pm(adv25[0])} at β = 1.0. "
     f"FRI and baseline net revenue differ by at most {max(fb):.1f}% at any β (Table VII).")

# ---------- Fig. A.1 (file fig_A1): per-region AUC, colour ----------
MIN_POS = 10
reg = []
for r in S["R_exploratory"]:
    mm = re.match(r"AUC d300 (\w+) \(positives (\d+)\)", r["item"])
    if mm:
        reg.append((mm.group(1), float(r["value"]), int(mm.group(2))))
reg = pd.DataFrame(reg, columns=["region", "auc", "pos"]).sort_values("region").reset_index(drop=True)
print(f"  check Fig.A1 regions: {len(reg)}, positives sum {int(reg.pos.sum()):,} (2023-25 total 1,684) -> {'OK' if int(reg.pos.sum()) == 1684 else 'CHECK'}")
rc22 = next((c for c in ["REGIONID", "region"] if c in s22.columns), None)
n22, a22 = [None] * len(reg), [np.nan] * len(reg)
if rc22:
    a22, n22 = [], []
    for r_ in reg.region:
        d_ = s22[s22[rc22] == r_]; yv = d_[Y22].values; n_ = int(yv.sum()); n22.append(n_)
        a22.append(roc_auc_score(yv, d_[P22].values) if MIN_POS <= n_ < len(yv) else np.nan)
    print(f"  check Fig.A1 test-1 positives sum {sum(n22)} (2022 test total {h['n_test_pos']}) -> {'OK' if sum(n22) == h['n_test_pos'] else 'CHECK'}")
yy = np.arange(len(reg))[::-1]                                         # NSW at the top, same order as Fig. 5
OFF = 0.14 if rc22 else 0.0
fig, ax = plt.subplots(figsize=(3.5, 2.7))
ax.axvline(R2_AUC, color=C["axis"], ls="--", lw=0.8, zorder=1, label=f"Pooled, test 2 ({R2_AUC:.3f})")
ax.scatter(reg.auc, yy + OFF, marker="o", s=34, color=C["fri"], zorder=3, label="Test 2 (2023–25)")
if rc22:
    ax.scatter(a22, yy - OFF, marker="s", s=30, facecolor="white", edgecolor=C["fri"], linewidths=1.2, zorder=3,
               label="Test 1 (2022)")
print("  Fig.A1 AUC by region, test 2:", dict(zip(reg.region, reg.auc.round(3))), "| test 1:",
      {r_: round(v_, 3) for r_, v_ in zip(reg.region, a22) if v_ == v_})
ax.set_yticks(yy); ax.set_yticklabels(reg.region.str.replace("1", "", regex=False))
lo_ = np.floor((min(v_ for v_ in list(reg.auc) + list(a22) if v_ == v_) - 0.03) * 20) / 20
ax.set_xlabel("AUC"); ax.set_xlim(lo_, 1.0); ax.set_ylim(-0.6, len(reg) - 0.4); ax.grid(axis="y", visible=False)
tr = ax.get_yaxis_transform()
ax.text(1.03, len(reg) - 0.45, "$n^+$\n(test 2 / test 1)", transform=tr, fontsize=7, ha="left", va="bottom")
for y_, p_, q_ in zip(yy, reg.pos, n22):
    ax.text(1.03, y_, f"{p_:,} / {q_}" if q_ is not None else f"{p_:,}", transform=tr, fontsize=7, ha="left", va="center")
ax.legend(loc="upper left", fontsize=7, borderpad=0.4, handletextpad=0.4)
save(fig, "A1", f"Fig. A.1. AUC by region for the fixed FRI model (exploratory). n⁺ is the number of unreliable intervals in test 2 (2023–25) "
     f"and test 1 (2022). 2022 AUC is shown only for regions with at least {MIN_POS} unreliable intervals. "
     f"The dashed line is the pooled test-2 AUC (R2).")

(FIG / "captions.md").write_text("# Figure captions (generated by make_figures.py)\n\n" + "\n\n".join(CAP[k] for k in sorted(CAP, key=lambda k: (isinstance(k, str), str(k).zfill(3)))) + "\n")
print(f"Saved {len(CAP)} figures and captions.md to {FIG}")
