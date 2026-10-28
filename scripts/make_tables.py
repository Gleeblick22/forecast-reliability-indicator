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
                           "† Test partition = intervals ending on or after 1 Oct 2022. October 2022 pre-dispatch data are not in the dataset; the partition holds 10 intervals on 1 Oct (00:00–04:30, none unreliable) and 9 intervals early on 1 Nov have no decision run."])

# ---------- Table III: hypotheses ----------
t3 = pd.DataFrame([[r["id"], r["short"], r["registered_criterion"], r["result"], r["outcome"]] for r in S["hypotheses"]],
                  columns=["ID", "Hypothesis", "Registered criterion", "Result", "Outcome"])
save("III", "Registered hypotheses and outcomes", t3,
     ["H1–H8: original registration (OSF). R1–R6: amendment filed before 2023–25 data access. "
      "CHECK (B5): wording must match OSF verbatim."])

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
names = {"baseline": "Baseline (no scaling)", "fri_3band": "FRI three-band", "vol_matched": "Volatility-matched",
         "const_0.75": "Constant ×0.75", "const_0.25": "Constant ×0.25"}
g22 = {r["agent"]: r for r in S["gateA"] if abs(r["beta"] - 2.03) < 1e-9}
g25 = {r["agent"]: r for r in S["agents_2325"]}
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
      "Over-forecast: f_decision − settled > AUD 300/MWh. The binary volatility control of c3_50 flagged no 2022 test intervals and is not shown."])

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

(TABLES_DIR / "paper_tables.md").write_text("# Paper tables (generated by make_tables.py — do not edit by hand)\n\n" + "\n".join(md))
print(f"Saved {TABLES_DIR / 'paper_tables.md'}")
