"""make_figures.py (Roadmap v3, B3): Figs. 1, 3-9 in black and white (300 dpi) + captions.md.
Reads results/numbers.json and the label/score files; recomputed AUC/AP must match numbers.json.
Fig. 2 (architecture) is drawn by hand (B4)."""
import json, re, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
                     "savefig.dpi": 300, "pdf.fonttype": 42, "svg.fonttype": "none", "legend.frameon": True, "legend.edgecolor": "0.7", "hatch.linewidth": 0.5})
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

# ---------- Fig. 1: data overview ----------
per = np.where(lab.partition == "test", "test", np.where(lab.DATETIME < "2022-08-01", "fit", "val"))
m = pd.concat([pd.DataFrame({"DATETIME": lab.DATETIME, "y": lab.y_v2.values, "period": per}),
               pd.DataFrame({"DATETIME": rep.DATETIME, "y": y25, "period": "replication"})])
m["month"] = (m.DATETIME - pd.Timedelta(minutes=30)).dt.to_period("M")
g = m.groupby(["period", "month"]).agg(n=("y", "size"), rate=("y", "mean")).reset_index()
g = g[g.n >= 1000]
fig, ax = plt.subplots(figsize=(W2, 2.3))
spans = [("fit", "2021-10-01", "2022-08-01", "0.94", "Fit"), ("val", "2022-08-01", "2022-10-01", "0.82", "Val."),
         ("test", "2022-11-01", "2023-01-01", "0.70", "Test"), ("replication", "2023-01-01", "2026-01-01", "0.97", "Replication (frozen model)")]
for p_, a_, b_, c_, t_ in spans:
    A_, B_ = pd.Timestamp(a_), pd.Timestamp(b_)
    ax.axvspan(A_, B_, color=c_, lw=0, zorder=0)
    ax.text(A_ + (B_ - A_) / 2, 0.97, t_, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=7)
    d_ = g[g.period == p_]
    ax.plot(d_.month.dt.to_timestamp() + pd.Timedelta(days=14), d_.rate * 100, color="black", marker="o", ms=2.5, lw=0.9, zorder=3)
ax.set_ylabel("Unreliable intervals (%)")
ax.set_xlim(pd.Timestamp("2021-10-01"), pd.Timestamp("2026-01-01"))
ax.set_ylim(0, g.rate.max() * 100 * 1.3)
save(fig, 1, f"Fig. 1. Monthly share of unreliable decision forecasts (|f(w_t) − p̄_t| > AUD 300/MWh) across the five NEM regions. "
     f"Shading marks the fit ({h['n_fit']:,} intervals), validation ({h['n_val']:,}), test ({h['n_test']:,}) and 2023–25 "
     f"replication ({h['rep_lead30']:,}) periods. October 2022 is not in the dataset.")

# ---------- Fig. 3: decision timeline ----------
fig, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.2), sharey=True, gridspec_kw={"width_ratios": [3, 2]})
runs = np.arange(-27.5, -0.49, 0.5)
for ax_ in (a, b):
    ax_.grid(False)
    ax_.axvspan(-28.5, -0.5, color="0.92", lw=0, zorder=0)
    ax_.scatter(runs, np.full(len(runs), 2), marker="|", s=60, color="0.35", zorder=2)
a.set_xlim(-28.5, -1.25); b.set_xlim(-1.25, 0.75)
a.spines["right"].set_visible(False); b.spines["left"].set_visible(False); b.tick_params(left=False)
b.scatter([-0.5], [2], marker="D", s=30, color="black", zorder=3)
b.axvline(-0.5, color="black", ls="--", lw=0.8)
b.axvspan(0, 0.5, color="0.75", lw=0, zorder=0)
b.scatter(np.arange(1, 7) / 12, np.full(6, 1), marker="o", s=14, facecolor="white", edgecolor="black", zorder=3)
a.annotate("Earliest run (median lead ≈ 27.5 h)", xy=(-27.5, 2), xytext=(-27.8, 2.6), fontsize=7,
           arrowprops=dict(arrowstyle="-", lw=0.5))
a.text(-14, 2.3, "Revision path: runs up to the decision run (features)", ha="center", fontsize=7)
b.text(-0.58, 2.6, "Decision run $f(w_t)$\nlead 30 min", ha="right", va="center", fontsize=7)
b.text(0.25, 1.45, "Interval $t$", ha="center", fontsize=7)
b.text(0.25, 0.55, "Six 5-min settled prices\n" + r"$\rightarrow \bar{p}_t$ (label only)", ha="center", va="center", fontsize=7)
a.set_ylim(0.2, 3.0); a.set_yticks([1, 2]); a.set_yticklabels(["Settlement\n(label only)", "Pre-dispatch runs\n(features)"])
fig.supxlabel("Hours relative to the start of trading interval t", fontsize=8)
save(fig, 3, "Fig. 3. Information timeline for one trading interval. Features use only pre-dispatch runs published up to the decision run "
     "(shaded). The label compares the decision forecast f(w_t) with the mean of the six settled 5-min DISPATCHPRICE values "
     "(INTERVENTION = 0): Y_t = 1[|f(w_t) − p̄_t| > δ_Y], δ_Y = AUD 300/MWh. Run spacing is schematic.")

# ---------- Fig. 4: error amplification (R1) ----------
r1 = pd.DataFrame(S["R1_regions"])
x = np.arange(len(r1)); w = 0.38
fig, ax = plt.subplots(figsize=(W1, 2.5))
ax.bar(x - w / 2, r1.mean_err_extreme, w, color="black", label=r"Extreme ($\bar{p}_t \geq$ AUD 300/MWh)")
ax.bar(x + w / 2, r1.mean_err_normal, w, color="white", edgecolor="black", hatch="////", lw=0.6, label="Normal")
for i, r in r1.iterrows():
    ax.text(i - w / 2, r.mean_err_extreme * 1.15, f"×{r.ratio:.0f}", ha="center", fontsize=7)
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(r1.region.str.replace("1", "", regex=False))
ax.set_ylabel(r"Mean $|f(w_t) - \bar{p}_t|$ (AUD/MWh)")
ax.set_ylim(10, r1.mean_err_extreme.max() * 3)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)
save(fig, 4, f"Fig. 4. Mean absolute error of the decision forecast against the settled price in extreme and normal intervals, "
     f"2023–25 (R1; log scale). Labels give the ratio of means ({h['R1_ratio_min']:.0f}–{h['R1_ratio_max']:.0f}); Welch p < 0.001 in every region.")

# ---------- Fig. 5: ROC and PR ----------
fig, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.8))
for y_, p_, ls, lbl in [(y22, p22, "-", "2022 test"), (y25, p25, "--", "2023–25")]:
    f_, t_, _ = roc_curve(y_, p_); a.plot(f_, t_, color="black", ls=ls, label=f"{lbl} (AUC {roc_auc_score(y_, p_):.3f})")
    pr, rc, _ = precision_recall_curve(y_, p_); b.plot(rc, pr, color="black", ls=ls, label=f"{lbl} (AP {average_precision_score(y_, p_):.3f})")
vol_note = ""
if "recent_std_3h" in rep.columns:
    v = rep.recent_std_3h.values.astype(float)
    v = np.where(np.isnan(v), np.nanmin(v) - 1, v)
    ap_v = average_precision_score(y25, v)
    check("dAP 2023-25 (R4)", average_precision_score(y25, p25) - ap_v, float(S["R"][3]["result"].split()[1]))
    pr, rc, _ = precision_recall_curve(y25, v)
    b.plot(rc, pr, color="0.5", ls="-.", label=f"recent_std_3h, 2023–25 (AP {ap_v:.3f})")
    vol_note = " The dash-dot curve is raw recent_std_3h on 2023–25 (R4 comparison)."
a.plot([0, 1], [0, 1], color="0.6", ls=":", lw=0.8)
for ax_, t_, xl, yl, loc in [(a, "(a) ROC", "False positive rate", "True positive rate", "lower right"),
                             (b, "(b) Precision–recall", "Recall", "Precision", "upper right")]:
    ax_.set_title(t_, loc="left"); ax_.set_xlabel(xl); ax_.set_ylabel(yl)
    ax_.set_xlim(0, 1); ax_.set_ylim(0, 1.02); ax_.legend(loc=loc)
save(fig, 5, f"Fig. 5. ROC (a) and precision–recall (b) curves of the FRI model, fitted on 2021–22 and frozen, on the 2022 test set "
     f"({h['n_test']:,} intervals, {h['n_test_pos']} unreliable) and the 2023–25 replication ({h['rep_lead30']:,} intervals).{vol_note}")

# ---------- Fig. 6: feature attribution ----------
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]
imp = pd.Series(S["importance"]).sort_values()
fig, ax = plt.subplots(figsize=(W1, 3.4))
for i, (k, v) in enumerate(imp.items()):
    st = dict(color="black") if k == "f_decision" else (dict(facecolor="0.6", edgecolor="black", lw=0.5) if k in PATH
                                                        else dict(facecolor="white", edgecolor="black", hatch="....", lw=0.5))
    ax.barh(i, v, height=0.7, **st); ax.text(v + 0.6, i, f"{v:.1f}", va="center", fontsize=6.5)
ax.set_yticks(range(len(imp))); ax.set_yticklabels(imp.index, fontsize=6.5)
ax.set_xlabel("Importance (% of total)"); ax.set_xlim(0, imp.max() * 1.18); ax.grid(axis="y", visible=False)
ax.legend(handles=[Patch(color="black", label="Decision forecast"), Patch(facecolor="0.6", edgecolor="black", label="Revision path"),
                   Patch(facecolor="white", edgecolor="black", hatch="....", label="Price dynamics")], loc="lower right")
save(fig, 6, f"Fig. 6. Feature importance of the FRI model ({len(imp)} features). The decision forecast accounts for {h['attr_f_decision']:.1f}% "
     f"and the revision-path group for {h['attr_path_group']:.1f}%.")

# ---------- Fig. 7: exposure by agent ----------
ORDER = [("baseline", "Baseline"), ("vol_matched", "Volatility-matched"), ("const_0.75", "Constant ×0.75"),
         ("const_0.25", "Constant ×0.25"), ("fri_3band", "FRI three-band")]
g22 = {r["agent"]: r for r in S["gateA"] if abs(r["beta"] - 2.03) < 1e-9}
g25 = {r["agent"]: r for r in S["agents_2325"]}
fig, axs = plt.subplots(1, 2, figsize=(W2, 2.2), sharey=True)
for ax_, g_, t_ in [(axs[0], g22, "(a) 2022 test"), (axs[1], g25, "(b) 2023–25 replication")]:
    vals = [g_[k]["mwh_into_overforecast"] for k, _ in ORDER]
    for i, (k, _) in enumerate(ORDER):
        ax_.barh(i, vals[i], height=0.65, color="black" if k == "fri_3band" else "0.82", edgecolor="black", lw=0.5)
        ax_.text(vals[i] + max(vals) * 0.02, i, f"{vals[i]:,.1f}", va="center", fontsize=7)
    ax_.set_title(t_, loc="left"); ax_.set_xlim(0, max(vals) * 1.2)
    ax_.set_xlabel("MWh into over-forecast intervals"); ax_.grid(axis="y", visible=False)
axs[0].set_yticks(range(len(ORDER))); axs[0].set_yticklabels([l for _, l in ORDER])
a2 = re.findall(r"\[[-\d., ]+\]", h["h5_h7"]["A2 exposure 2022"]["result"])[-1]
r3 = [r for r in S["hypotheses"] if r["id"] == "R3"][0]["result"].split("; ", 1)[1]
save(fig, 7, f"Fig. 7. Energy discharged into over-forecast intervals (f(w_t) − p̄_t > AUD 300/MWh) by agent, β = 2.03. "
     f"FRI reduces exposure against the baseline by {h['exposure_reduction_2022_pct']}% in 2022 (95% CI {a2} MWh) and by "
     f"{h['rep_exposure_reduction_pct']}% in 2023–25 ({r3}; R3).")

# ---------- Fig. 8: R6 degradation curvature ----------
B = [1.0, 1.5, 2.03]
gb = lambda b_, a_: next(r for r in S["gateA"] if abs(r["beta"] - b_) < 1e-9 and r["agent"] == a_)["net_revenue"]
r6 = {round(r["beta"], 2): r for r in S["R6"]}
s22_ = {"baseline": [gb(b_, "baseline") for b_ in B], "fri": [gb(b_, "fri_3band") for b_ in B], "c25": [gb(b_, "const_0.25") for b_ in B]}
s25_ = {"baseline": [r6[b_]["net_baseline"] for b_ in B], "fri": [r6[b_]["net_fri"] for b_ in B], "c25": [r6[b_]["net_const025"] for b_ in B]}
STY = {"baseline": dict(ls=":", marker="s", label="Baseline"), "fri": dict(ls="-", marker="o", label="FRI three-band"),
       "c25": dict(ls="--", marker="^", label="Constant ×0.25")}
fig, axs = plt.subplots(1, 2, figsize=(W2, 2.4))
for ax_, s_, k_, t_, u_ in [(axs[0], s22_, 1e3, "(a) 2022 test", "thousand"), (axs[1], s25_, 1e6, "(b) 2023–25 replication", "million")]:
    for k, v in s_.items():
        ax_.plot(B, np.array(v) / k_, color="black", ms=4, mfc="black" if k == "fri" else "white", lw=1, **STY[k])
    ax_.set_title(t_, loc="left"); ax_.set_xlabel(r"Degradation exponent $\beta$"); ax_.set_ylabel(f"Net revenue (AUD {u_})"); ax_.set_xticks(B)
axs[0].legend(loc="upper left")
save(fig, 8, "Fig. 8. Net revenue of the baseline, FRI and constant ×0.25 agents as degradation becomes less convex (R6). "
     "α is rescaled at each β so that baseline degradation cost is unchanged. The constant ×0.25 advantage at β = 2.03 "
     "disappears at β = 1.0 in both periods.")

# ---------- Fig. 9: per-region AUC ----------
reg = []
for r in S["R_exploratory"]:
    mm = re.match(r"AUC d300 (\w+) \(positives (\d+)\)", r["item"])
    if mm:
        reg.append((mm.group(1), float(r["value"]), int(mm.group(2))))
reg = pd.DataFrame(reg, columns=["region", "auc", "pos"]).sort_values("region").reset_index(drop=True)
yy = np.arange(len(reg))
fig, ax = plt.subplots(figsize=(W1, 2.4))
ax.scatter(reg.auc, yy, marker="o", s=28, color="black", zorder=3, label="2023–25 (frozen)")
rc22 = next((c for c in ["REGIONID", "region"] if c in s22.columns), None)
labels = [f"{r_} (n+ {p_:,})" for r_, p_ in zip(reg.region, reg.pos)]
if rc22:
    a22, n22 = [], []
    for r_ in reg.region:
        d_ = s22[s22[rc22] == r_]; yv = d_[Y22].values
        n22.append(int(yv.sum()))
        a22.append(roc_auc_score(yv, d_[P22].values) if 0 < yv.sum() < len(yv) else np.nan)
    ax.scatter(a22, yy, marker="o", s=28, facecolor="white", edgecolor="black", zorder=3, label="2022 test")
    labels = [f"{r_} (n+ {p_:,}; {q_})" for r_, p_, q_ in zip(reg.region, reg.pos, n22)]
ax.axvline(R2_AUC, color="0.5", ls="--", lw=0.8, label=f"Pooled 2023–25 ({R2_AUC:.3f})")
ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=6.5); ax.set_xlabel("AUC"); ax.set_xlim(0.5, 1.0)
ax.legend(loc="lower left", fontsize=6.5)
save(fig, 9, "Fig. 9. AUC by region for the frozen FRI model (exploratory). n+ gives the number of unreliable intervals "
     "(2023–25" + ("; 2022 test" if rc22 else "") + "). The dashed line is the pooled 2023–25 AUC (R2).")

(FIG / "captions.md").write_text("# Figure captions (generated by make_figures.py)\n\n" + "\n\n".join(CAP[k] for k in sorted(CAP)) + "\n")
print(f"Saved {len(CAP)} figures and captions.md to {FIG}")
