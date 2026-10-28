"""make_tables.py (Roadmap v3, B2): paper Tables I, III-VII.
Numbers come from results/numbers.json; Table I date ranges from the label file.
Outputs: results/tables/paper_table_<n>.csv and results/tables/paper_tables.md"""
import json, re
import pandas as pd
from config.settings import TABLES_DIR, PROCESSED_DIR

R = TABLES_DIR.parent
N = json.load(open(R / "numbers.json"))
h, S = N["headline"], N["sources"]
md = []


def to_md(df):
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v).replace("|", "\\|") for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(lines)


def save(name, title, df, notes=()):
    df.to_csv(TABLES_DIR / f"paper_table_{name}.csv", index=False)
    md.append(f"## Table {name}. {title}\n\n{to_md(df)}\n" + "".join(f"\n{n}\n" for n in notes))
    print(f"Table {name}: {df.shape[0]} rows")


def ci(x, lo, hi, d=3):
    return f"{x:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]"


def last3(s):
    return [float(v) for v in re.findall(r"\d+\.\d+", s.replace(",", ""))][-3:]


aud = lambda x: f"{x:,.0f}"
f3 = lambda x: f"{x:.3f}"
Rres = {r["R"]: r["result"] for r in S["R"]}
Hres = {r["id"]: r for r in S["hypotheses"]}
expl = {r["item"]: r["value"] for r in S["R_exploratory"]}

# ---------- Table I: datasets ----------
lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", usecols=["DATETIME", "partition", "y_v2"], parse_dates=["DATETIME"])
parts = {"fit": lab[(lab.partition == "train") & (lab.DATETIME < "2022-08-01")],
         "val": lab[(lab.partition == "train") & (lab.DATETIME >= "2022-08-01")],
         "test": lab[lab.partition == "test"]}
rng = lambda d: f"{d.DATETIME.min():%d %b %Y} – {d.DATETIME.max():%d %b %Y}"
pct = lambda d: f"{d.y_v2.mean() * 100:.2f}%"
rep_pos = sum(int(re.search(r"positives (\d+)", k).group(1)) for k in expl if "positives" in k)
src_nem = "AEMO pre-dispatch (PREDISPATCHPRICE); settled DISPATCHPRICE (MMSDM)"
t1 = pd.DataFrame([
    ["NEM fit", rng(parts["fit"]), f"{len(parts['fit']):,}", pct(parts["fit"]), "Model fitting", src_nem],
    ["NEM validation", rng(parts["val"]), f"{len(parts['val']):,}", pct(parts["val"]), "Hyperparameters and θ", src_nem],
    ["NEM test", "01 Nov – 31 Dec 2022†", f"{len(parts['test']):,}", pct(parts["test"]), "H1–H7 (held-out)", src_nem],
    ["NEM replication", "01 Jan 2023 – 31 Dec 2025", f"{h['rep_lead30']:,}", f"{rep_pos / h['rep_lead30'] * 100:.2f}%",
     "R1–R6 (frozen model)", src_nem + f"; coverage {h['rep_coverage_pct']}%"],
    ["New Zealand", "as in v1.1", "as in v1.1", "—", "H8 only (original label)", "Electricity Authority EMI"],
    ["Great Britain", "as in v1.1", "as in v1.1", "—", "H8 only (original label)", "Elexon BMRS"]],
    columns=["Dataset", "Period", "Intervals", "Unreliable (δ_Y = 300)", "Use", "Source"])
save("I", "Datasets", t1, ["All NEM sets: five regions, 30-min trading intervals. Replication 60-min-lead set: "
                           f"{h['rep_lead60']:,} intervals. NZ/GB rows: fill from the v1.1 manuscript Table I. "
                           "† Test partition = intervals ending on or after 1 Oct 2022. The October 2022 AEMO archive holds only the latest pre-dispatch run per interval (PREDISPATCHPRICE_D), so no decision run can be built; the partition holds 10 intervals on 1 Oct (00:00–04:30, none unreliable) and 9 intervals early on 1 Nov have no decision run."])

# ---------- Table III: hypotheses ----------
REG = {  # H1-H8: registered wording (v1.1 Table III, from OSF jpfwh); R1-R6: OSF amendment section 5
 "H1": ("Forecast error amplification", "Welch's t-test", "ρ > 1.5, p < 0.05 in ≥ 4/5 regions"),
 "H2": ("Aggregate error masking", "Paired MAE comparison", "m > 0.50 at NEM level"),
 "H3": ("Horizon difference (P5 vs. P30)", "Independent-samples t-test", "p < 0.05 at NEM level"),
 "H4": ("FRI classifier performance", "F1 on held-out test set", "F1 ≥ 0.60"),
 "H5": ("Silent-failure reduction", "McNemar's test", "≥ 20% reduction vs. baseline"),
 "H6": ("Dispatch correlation", "Pearson r, Fisher z CI", "Positive, significant (p < 0.05)"),
 "H7": ("Revenue improvement", "Revenue comparison, Cohen's d", "≥ 15% higher revenue than baseline"),
 "H8": ("Cross-market generalisation", "|F1 difference| vs. NEM", "Within 0.15 of NEM test F1"),
 "R1": ("Error amplification against settled price", "Welch t-test per region; ratio of means", "Ratio > 1.5 and p < 0.05 in ≥ 4 of 5 regions"),
 "R2": ("Temporal transfer of detection", "AUC, stratified bootstrap 95% CI (1,000)", "AUC ≥ 0.80 and CI lower bound > 0.70"),
 "R3": ("Exposure reduction", "MWh into over-forecast intervals; paired daily bootstrap (2,000)", "≥ 30% vs. baseline and 95% CI of (vol-matched − FRI) excludes 0"),
 "R4": ("Beats raw volatility", "ΔAP, bootstrap 95% CI (1,000)", "ΔAP > 0, CI excludes 0"),
 "R5": ("Decision at 60-min lead", "AUC, bootstrap 95% CI", "AUC ≥ 0.75"),
 "R6": ("Degradation boundary", "Descriptive", "Direction and size reported; no pass/fail")}
t3 = pd.DataFrame([[r["id"], *REG[r["id"]], r["result"], r["outcome"]] for r in S["hypotheses"]],
                  columns=["ID", "Hypothesis", "Test", "Registered criterion", "Result", "Outcome"])
save("III", "Registered hypotheses and outcomes", t3,
     ["H1–H8: original registration (OSF, osf.io/jpfwh). R1–R6: amendment registered on 28 October 2026, before the 2023–25 data were downloaded. "
      "H1–H3 use the registered error definition (Eq. (2)); see Section IV.A."])

# ---------- Table IV: deviations ----------
t4 = pd.DataFrame([
    ["Reliability label", "Earliest forecast vs P5MIN proxy", "Decision forecast vs settled 30-min price, δ_Y = AUD 300/MWh",
     "Old label described a forecast the agent did not act on; near-circular with the revision feature"],
    ["Revision feature", "Single first-to-last revision", "Seven revision-path features up to the decision run", "Information available at decision time"],
    ["Price-dynamics features", "Built from the earliest run", "Rebuilt from the earliest run (code had used runs with lead < 30 min in 21.5% of intervals)", "Coding error corrected; negligible effect"],
    ["Hyperparameters", "200 / 9 / 0.3", "300 / 2 / 0.1, chosen on validation AP", f"Validation AP {h['registered_settings_val_ap']:.3f} vs {h['det2022']['val_ap']:.3f}"],
    ["Threshold θ", "Max-F1 on training data", f"Max-F1 on validation (θ = {h['det2022']['theta']})", "Avoids in-sample threshold"],
    ["Dispatch mapping", "High score → full dispatch", "High score → scale down", "Original mapping inverted (coding error)"],
    ["Battery", "One battery for all regions", "One battery per region", "Modelling error"],
    ["Charging", "Used settled price and same-day discharge", "Ex-ante rule: charge when f ≤ AUD 20/MWh in later intervals", "Look-ahead removed"],
    ["Volatility control", "Binary volatility rule", "Volatility-matched control (same band counts as FRI)", "Binary rule flagged no intervals in the 2022 test"],
    ["Degradation α", "5.04 × 10⁻⁴", "5.04 × 10⁻⁴ kept; source value 5.24 × 10⁻⁴ as sensitivity", "Transcription error; rankings unchanged"],
    ["Settlement price", "P5MIN proxy", "DISPATCHPRICE throughout", "Data available"],
    ["Test window", "1 Oct – 31 Dec 2022", "1 Nov – 31 Dec 2022", "October 2022 AEMO archive holds only the latest pre-dispatch run per interval (PREDISPATCHPRICE_D); decision run and revision path cannot be built"],
    ["H8", "Re-run under final method", "Reported under the original label", "ERCOT inaccessible; not re-run"]],
    columns=["Item", "Registered", "Reported", "Reason"])
save("IV", "Deviations from registration", t4, ["CHECK (B5): 'Registered' column against OSF."])

# ---------- Table V: detection ----------
d = h["det2022"]
r2, r4, r5 = last3(Rres["R2"]), last3(Rres["R4"]), last3(Rres["R5"])
f1p = [float(x) for x in expl["F1/precision/recall at frozen theta (d300)"].split("/")]
row = lambda name, per, k: [name, per, f3(h[k]["auc"]), f3(h[k]["ap"]), f3(h[k]["f1"]), "", ""]
t5 = pd.DataFrame([
    ["FRI (XGBoost, 17 features)", "2022 test", ci(d["auc"], d["auc_lo"], d["auc_hi"]), f3(d["ap"]), f3(d["f1"]), f3(d["precision"]), f3(d["recall"])],
    row("  without revision path", "2022 test", "abl_no_revision_path"),
    row("  revision path only", "2022 test", "abl_path_only"),
    row("  without recent_std_3h", "2022 test", "abl_no_recent_std"),
    row("Raw recent_std_3h", "2022 test", "base_raw_recent_std_3h"),
    row("Raw |revision|", "2022 test", "base_raw_rev_abs"),
    row("Raw |f_decision|", "2022 test", "base_raw_abs_f_decision"),
    row("Logistic regression (17 features)", "2022 test", "base_logreg_full"),
    ["Permuted labels (leakage test)", "2022 test", f"{h['perm_auc_min']:.2f}–{h['perm_auc_max']:.2f}", "", "", "", ""],
    ["FRI, δ_Y = 150 / 500", "2022 test", f"{h['auc2022_d150']:.3f} / {h['auc2022_d500']:.3f}", "", "", "", ""],
    ["FRI frozen (R2)", "2023–25", ci(*r2), f3(float(expl["AP (d300)"])), f"{f1p[0]:.3f}*", f"{f1p[1]:.3f}*", f"{f1p[2]:.3f}*"],
    ["FRI frozen, 60-min lead (R5)", "2023–25", ci(*r5), "", "", "", ""],
    ["FRI frozen, δ_Y = 150 / 500", "2023–25", f"{float(expl['AUC y_v2_d150']):.3f} / {float(expl['AUC y_v2_d500']):.3f}", "", "", "", ""],
    ["ΔAP, FRI − raw recent_std_3h (R4)", "2023–25", "", ci(*r4), "", "", ""]],
    columns=["Model / check", "Period", "AUC [95% CI]", "AP", "F1", "Precision", "Recall"])
save("V", "Detection of unreliable decision forecasts", t5,
     [f"Test prevalence 2022: {h['prev_test_pct']}% ({h['n_test_pos']} of {h['n_test']:,}). F1/precision/recall at θ = {d['theta']}. "
      "* Exploratory (not registered); H4 is assessed on the 2022 test only."])

# ---------- Table VI: agents ----------
names = {"baseline": "Baseline (no scaling)", "fri_3band": "FRI three-band", "vol_matched": "Volatility-matched", "fdec_matched": "Forecast-level-matched*",
         "const_0.75": "Constant ×0.75", "const_0.25": "Constant ×0.25"}
g22 = {r["agent"]: r for r in S["gateA"] if abs(r["beta"] - 2.03) < 1e-9}
g25 = {r["agent"]: r for r in S["agents_2325"]}
for r in S["fdec_ctrl"]:
    if r["agent"] == "fdec_matched":
        (g22 if r["period"] == "2022 test" else g25)["fdec_matched"] = r
fb = h["fdec_ctrl_boot"]
FDEC_NOTE = ("* Exploratory control (not registered): same band counts as FRI, assigned by highest f_decision. "
             f"Forecast-level-matched − FRI exposure: 2022 {fb['2022 test|fdec_matched'][0]} MWh [{fb['2022 test|fdec_matched'][1]}, {fb['2022 test|fdec_matched'][2]}]; "
             f"2023–25 {fb['2023-25|fdec_matched'][0]} MWh [{fb['2023-25|fdec_matched'][1]}, {fb['2023-25|fdec_matched'][2]}].")
rows6 = []
for per, g in [("2022 test", g22), ("2023–25", g25)]:
    for a, lbl in names.items():
        r = g[a]
        rows6.append([per, lbl, f"{r['dispatch_intervals']:,}", f"{r['mwh_discharged']:,.0f}", f"{r['mwh_into_overforecast']:,.1f}",
                      r["dispatched_into_overforecast"], r["silent_failures"], aud(r["gross_revenue"]), aud(r["degradation"]),
                      aud(r["charging_cost"]), aud(r["net_revenue"])])
t6 = pd.DataFrame(rows6, columns=["Period", "Agent", "Dispatch intervals", "MWh discharged", "MWh into over-forecast",
                                  "Over-forecast intervals dispatched", "Silent failures", "Gross (AUD)", "Degradation (AUD)",
                                  "Charging (AUD)", "Net (AUD)"])
b22 = h["boot_2022"]["fri_3band - baseline"]
a2 = re.findall(r"\[[-\d., ]+\]", h["h5_h7"]["A2 exposure 2022"]["result"])[-1]
rm = h["random_2022"]
save("VI", "Battery agents: exposure and revenue (β = 2.03)", t6,
     [f"2022: exposure reduction FRI vs baseline {h['exposure_reduction_2022_pct']}% (95% CI: {a2}); "
      f"net FRI − baseline {aud(b22[0])} [{aud(b22[1])}, {aud(b22[2])}]; random band-matched net mean {aud(rm['mean'])} "
      f"[{aud(rm['p2_5'])}, {aud(rm['p97_5'])}], FRI above {rm['fri_beats_pct']}% of draws.",
      f"2023–25: exposure reduction {h['rep_exposure_reduction_pct']}%; {Hres['R3']['result'].split('; ', 1)[1]} (R3); net change {h['rep_net_change_pct']}%.",
      "Over-forecast: f_decision − settled > AUD 300/MWh. The binary volatility control of c3_50 flagged no 2022 test intervals and is not shown.", FDEC_NOTE])

# ---------- Table VII: R6 degradation curvature ----------
rows7 = []
for b in [2.03, 1.5, 1.0]:
    g = {r["agent"]: r for r in S["gateA"] if abs(r["beta"] - b) < 1e-9}
    rows7.append([b, f"{g['baseline']['k_calibration']:.4f}", "2022 test", aud(g["baseline"]["net_revenue"]), aud(g["fri_3band"]["net_revenue"]),
                  aud(g["const_0.25"]["net_revenue"]), aud(g["const_0.25"]["net_revenue"] - g["fri_3band"]["net_revenue"])])
for r in S["R6"]:
    rows7.append([r["beta"], f"{r['k']:.4f}", "2023–25", aud(r["net_baseline"]), aud(r["net_fri"]), aud(r["net_const025"]), aud(r["const025_minus_fri"])])
t7 = pd.DataFrame(rows7, columns=["β", "k", "Period", "Net baseline", "Net FRI", "Net constant ×0.25", "Constant ×0.25 − FRI"])
save("VII", "Net revenue under degradation curvature (R6)", t7,
     ["k scales α so that baseline degradation cost is equal across β. AUD. R6 is descriptive (no pass/fail)."])


# ================= Appendix A tables =================
pfmt = lambda v: "< 0.001" if v < 0.001 else f"{v:.3f}"
tA1 = pd.DataFrame([
    ["Reliability label", "|earliest run − P5MIN proxy| above a threshold", "|f(w_t) − p̄_t| > AUD 300/MWh, settled DISPATCHPRICE"],
    ["Forecast the label describes", "Earliest run", "Decision run (closest to 45 min lead, within 30–60 min)"],
    ["Features", "10, incl. one revision (earliest → latest run)", "17: decision forecast (1), revision path to the decision run (7), earliest-run price and calendar (9)"],
    ["Model selection", "200 trees, depth 9, rate 0.3; CV on training data", "300 trees, depth 2, rate 0.1; validation AP"],
    ["Threshold θ", "Max-F1 on training data", f"Max-F1 on validation (θ = {h['det2022']['theta']})"],
    ["Test set", "Oct–Dec 2022 (15,165 / 14,645 intervals)", f"Nov–Dec 2022 ({h['n_test']:,} intervals)"],
    ["Test prevalence", "3.74%", f"{h['prev_test_pct']}%"],
    ["Test AUC / AP", "0.9666 / 0.8931", f"{h['det2022']['auc']:.3f} / {h['det2022']['ap']:.3f}"],
    ["Largest attribution", "Revision, 52.3%", f"Decision forecast {h['attr_f_decision']:.1f}%; revision path {h['attr_path_group']:.1f}%"],
    ["Dispatch mapping", "High score → full dispatch (inverted)", "High score → ×0.25"],
    ["Battery", "One battery for all regions; discharge only", "One battery per region"],
    ["Charging", "Settled price, same-day discharge (look-ahead)", "Ex ante, decision forecast ≤ AUD 20/MWh"],
    ["Replication", "None", f"2023–25, frozen model; R1–R5 supported"]],
    columns=["Item", "v1.1 (desk-rejected)", "This version"])
save("A.1", "Changes between the desk-rejected version and this version", tA1,
     ["v1.1 values are taken from that manuscript and are not reproduced by the current pipeline."])
H1t, H2t = pd.DataFrame(S["H1"]), pd.DataFrame(S["H2"])
m = H1t.merge(H2t[["label", "aggregate_mae", "masking_pct"]].rename(columns={"label": "region"}), on="region")
tA2 = pd.DataFrame({"Region": m.region, "n normal": m.normal_count.map("{:,}".format), "n extreme": m.extreme_count.map("{:,}".format),
                    "MAE normal": m.mae_normal.map("{:,.2f}".format), "MAE aggregate": m.aggregate_mae.map("{:,.2f}".format),
                    "MAE extreme": m.mae_extreme.map("{:,.2f}".format), "Ratio (H1)": m.ratio.map("{:.2f}".format),
                    "t": m.t_statistic.map("{:.2f}".format), "p": m.p_value.map(pfmt), "Masking % (H2)": m.masking_pct.map("{:.2f}".format)})
n_ = H2t[H2t.label == "OVERALL_NEM"].iloc[0]
tA2.loc[len(tA2)] = ["NEM", f"{int(n_.normal_count):,}", f"{int(n_.extreme_count):,}", f"{n_.normal_mae:,.2f}", f"{n_.aggregate_mae:,.2f}",
                     f"{n_.extreme_mae:,.2f}", "", "", "", f"{n_.masking_pct:.2f}"]
save("A.2", "Registered H1 and H2 by region (error = |earliest − latest run|; extreme if latest run ≥ AUD 300/MWh)", tA2,
     ["MAE in AUD/MWh. Registered analyses on 2021–22 data; see Section IV.A for the interpretation of this error definition."])

G = pd.DataFrame(S["H1H2_genuine"]).sort_values("region")
tA3 = pd.DataFrame({"Region": G.region, "n normal": G.normal_n.map("{:,}".format), "n extreme": G.extreme_n.map("{:,}".format),
                    "Ratio": G.ratio.map("{:.2f}".format), "p": G.p_value.map("{:.1e}".format)})
save("A.3", "Post-hoc check of H1 against the realised price (not registered)", tA3,
     ["Error = |earliest run − realised price|; extreme if realised price ≥ AUD 300/MWh. Realised price = P5MIN-based proxy (c1_14); R1 uses settled DISPATCHPRICE."])

H3t = pd.DataFrame(S["H3_wilcoxon"])
tA4 = pd.DataFrame({"Region": H3t.label.replace({"OVERALL_NEM": "NEM"}), "n extreme": H3t.extreme_count.map("{:,}".format),
                    "Mean error, final run": H3t.p5_mean.map("{:,.2f}".format), "Mean error, 30-min run": H3t.p30_mean.map("{:,.2f}".format),
                    "Wilcoxon W": H3t.w_statistic.map("{:,.1f}".format), "p (Wilcoxon)": H3t.p_value.map(pfmt)})
save("A.4", "H3 by region: Wilcoxon signed-rank test (not registered)", tA4,
     [f"Registered test (Welch t-test, NEM level): {Hres['H3']['result']} → {Hres['H3']['outcome']}. "
      "Wilcoxon results rest on few non-tied pairs (3 of 3,012 in NSW1; 3 of 2,399 in VIC1)."])

AL = pd.DataFrame(S["alpha"])
base_ = AL[AL.alpha < 5.1e-4].set_index(["period", "agent"]).net_revenue
AL["Net change vs 5.04e-4 (%)"] = [round((r.net_revenue / base_[(r.period, r.agent)] - 1) * 100, 2) for r in AL.itertuples()]
chg_ = AL.loc[AL.alpha > 5.1e-4, "Net change vs 5.04e-4 (%)"].abs()
tA6 = pd.DataFrame({"Period": AL.period, "α": AL.alpha.map("{:.2e}".format), "Agent": AL.agent.map(lambda a: names.get(a, a)),
                    "Degradation": AL.degradation.map(aud), "Net revenue": AL.net_revenue.map(aud),
                    "Net change vs 5.04e-4 (%)": AL["Net change vs 5.04e-4 (%)"]})
save("A.6", "Degradation α: simulation value (5.04 × 10⁻⁴) against the source value of [57] (5.24 × 10⁻⁴)", tA6,
     [f"c3_53. With the source value, net revenue changes by {chg_.min():.1f}–{chg_.max():.1f}%; rankings of agents are unchanged. AUD."])

DC = pd.DataFrame(S["daily_cycle"])
tA7 = pd.DataFrame({"Period": DC.period, "Agent": DC.agent.map(lambda a: names.get(a, a)), "Gross": DC.gross.map(aud), "Charging": DC.charging.map(aud),
                    "Degradation per interval": DC.deg_per_interval.map(aud), "Degradation per daily cycle": DC.deg_daily_cycle.map(aud),
                    "Net (per interval)": DC.net_per_interval.map(aud), "Net (per daily cycle)": DC.net_daily_cycle.map(aud)})
dcd = h["daily_cycle"]
save("A.7", "Degradation charged per daily cycle instead of per discharge interval (exploratory; β = 2.03)", tA7,
     [f"Constant ×0.25 − FRI net: 2022 {aud(dcd['2022 test']['c25_minus_fri_interval'])} → {aud(dcd['2022 test']['c25_minus_fri_daily'])}; "
      f"2023–25 {aud(dcd['2023-25']['c25_minus_fri_interval'])} → {aud(dcd['2023-25']['c25_minus_fri_daily'])}. AUD. "
      "Absolute revenues depend on the illustrative replacement cost; only comparisons between agents are findings."])

(TABLES_DIR / "paper_tables.md").write_text("# Paper tables (generated by make_tables.py — do not edit by hand)\n\n" + "\n".join(md))
print(f"Saved {TABLES_DIR / 'paper_tables.md'}")
