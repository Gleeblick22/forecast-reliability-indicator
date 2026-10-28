"""build_numbers.py (Roadmap v3, B1): collect every reported number into results/numbers.json.
Section 'sources' = full contents of each result file; 'headline' = numbers used in the text.
Re-run after any analysis change; the manuscript must only quote numbers from this file."""
import sys, json
import numpy as np
import pandas as pd
from config.settings import TABLES_DIR, PROCESSED_DIR

T, R = TABLES_DIR, TABLES_DIR.parent
F = {"eval_c2_30": T / "c2_30_label_v2_eval.csv", "eval_c2_31": T / "c2_31_final_eval.csv",
     "grid_c2_31": T / "c2_31_grid.csv", "importance": T / "c2_31_feature_importance.csv",
     "best_params": T / "c2_31_best_params.json", "admin": T / "c2_32_admin_pricing_sensitivity.csv",
     "agents_2022": T / "c3_50_agents_summary.csv", "boot_2022": T / "c3_50_paired_bootstrap.csv",
     "random_2022": T / "c3_50_random_matched.csv", "gateA": T / "c3_51_gateA_checks.csv",
     "gateA_boot": T / "c3_51_gateA_bootstrap.csv", "h5_h7": T / "c3_52_h5_h7.csv",
     "alpha": T / "c3_53_alpha_sensitivity.csv", "R": T / "c4_03_R_outcomes.csv",
     "R1_regions": T / "c4_03_R1_regions.csv", "R6": T / "c4_03_R6.csv",
     "R_exploratory": T / "c4_03_exploratory.csv", "agents_2325": T / "c4_04_agents_summary_2023_2025.csv",
     "hypotheses": R / "hypothesis_outcomes.csv", "coverage": PROCESSED_DIR / "coverage_2023_2025.csv",
     "H1": T / "c1_04_h1_amplification_results.csv", "H2": T / "c1_05_h2_masking_results.csv",
     "H1H2_genuine": T / "h1_h2_genuine_error_results.csv", "H3_wilcoxon": T / "c1_06_h3_horizon_results.csv"}
missing = [k for k, p in F.items() if not p.exists()]
if missing:
    print("MISSING:", missing); sys.exit(1)

src = {}
for k, p in F.items():
    if p.suffix == ".json":
        src[k] = json.load(open(p))
    elif k == "importance":
        src[k] = pd.read_csv(p, index_col=0).iloc[:, 0].round(2).to_dict()
    else:
        src[k] = pd.read_csv(p).replace({np.nan: None}).to_dict(orient="records")


def row(k, **kw):
    df = pd.DataFrame(src[k])
    for c, v in kw.items():
        df = df[df[c] == v]
    assert len(df) == 1, (k, kw, len(df))
    return df.iloc[0]


lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", usecols=["DATETIME", "partition", "y_v2"], parse_dates=["DATETIME"])
tr = lab[lab.partition == "train"]
h = {}
h["n_fit"] = int((tr.DATETIME < "2022-08-01").sum())
h["n_val"] = int((tr.DATETIME >= "2022-08-01").sum())
h["n_test"] = int(len(pd.read_csv(T / "c2_31_test_scores.csv")))
h["prev_train_pct"] = round(tr.y_v2.mean() * 100, 2)
h["prev_test_pct"] = round(lab[lab.partition == "test"].y_v2.mean() * 100, 2)
h["n_test_pos"] = int(row("eval_c2_31", check="full_tuned", label="y_v2_d300")["n_test_pos"])

m = row("eval_c2_31", check="full_tuned", label="y_v2_d300")
h["det2022"] = {c: float(m[c]) for c in ["val_ap", "auc", "auc_lo", "auc_hi", "ap", "f1", "precision", "recall", "theta", "scale_pos_weight"]}
h["auc2022_d150"] = float(row("eval_c2_31", check="full_tuned", label="y_v2_d150")["auc"])
h["auc2022_d500"] = float(row("eval_c2_31", check="full_tuned", label="y_v2_d500")["auc"])
for c in ["no_revision_path", "path_only", "no_recent_std"]:
    r_ = row("eval_c2_31", check=c, label="y_v2_d300")
    h[f"abl_{c}"] = {k: float(r_[k]) for k in ["auc", "ap", "f1"]}
for c in ["raw_recent_std_3h", "raw_rev_abs", "raw_abs_f_decision", "logreg_full"]:
    r_ = row("eval_c2_30", check=c, label="y_v2_d300")
    h[f"base_{c}"] = {k: float(r_[k]) for k in ["auc", "ap", "f1"]}
perm = [r_["auc"] for r_ in src["eval_c2_30"] if str(r_["check"]).startswith("permuted")]
h["perm_auc_min"], h["perm_auc_max"] = round(min(perm), 2), round(max(perm), 2)
imp = src["importance"]
h["attr_f_decision"] = imp["f_decision"]
h["attr_path_group"] = round(sum(imp[k] for k in ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]), 2)
h["registered_settings_val_ap"] = 0.291

w, wo = row("admin", spec="with_window (primary)"), row("admin", spec="without_window")
h["admin_share_fit_pos_pct"] = round((1 - wo["fit_pos"] / w["fit_pos"]) * 100, 1)
h["admin_dAUC"] = round(float(wo["test_auc"] - w["test_auc"]), 4)

for per, k in [("2022", "agents_2022"), ("2325", "agents_2325")]:
    for r_ in src[k]:
        h[f"agent_{per}_{r_['agent']}"] = {c: r_[c] for c in ["net_revenue", "gross_revenue", "degradation", "mwh_into_overforecast", "dispatch_intervals"]}
rn = np.array([r_["net_revenue"] for r_ in src["random_2022"]])
fri_net = h["agent_2022_fri_3band"]["net_revenue"]
h["random_2022"] = {"mean": round(rn.mean()), "p2_5": round(np.percentile(rn, 2.5)), "p97_5": round(np.percentile(rn, 97.5)),
                    "fri_beats_pct": round(float((fri_net > rn).mean() * 100))}
h["boot_2022"] = {r_["comparison"]: [r_["net_diff"], r_["ci_lo"], r_["ci_hi"]] for r_ in src["boot_2022"]}
h["gateA_boot"] = {f"{r_['beta']}|{r_['comparison']}": [r_["net_diff"], r_["ci_lo"], r_["ci_hi"]] for r_ in src["gateA_boot"]}
h["h5_h7"] = {r_["H"]: {"result": r_["result"], "outcome": r_["outcome"]} for r_ in src["h5_h7"]}
h["R"] = {r_["R"]: {"result": r_["result"], "passed": r_["passed"]} for r_ in src["R"]}
h["R1_ratio_min"] = min(r_["ratio"] for r_ in src["R1_regions"])
h["R1_ratio_max"] = max(r_["ratio"] for r_ in src["R1_regions"])
cov = pd.DataFrame(src["coverage"])
h["rep_expected"], h["rep_lead30"], h["rep_lead60"] = int(cov.expected.sum()), int(cov.lead30_rows.sum()), int(cov.lead60_rows.sum())
h["rep_coverage_pct"] = round(h["rep_lead30"] / h["rep_expected"] * 100, 2)
b, f_ = h["agent_2325_baseline"], h["agent_2325_fri_3band"]
h["rep_exposure_reduction_pct"] = round((1 - f_["mwh_into_overforecast"] / b["mwh_into_overforecast"]) * 100, 1)
h["rep_net_change_pct"] = round((f_["net_revenue"] / b["net_revenue"] - 1) * 100, 2)
b2, f2 = h["agent_2022_baseline"], h["agent_2022_fri_3band"]
h["exposure_reduction_2022_pct"] = round((1 - f2["mwh_into_overforecast"] / b2["mwh_into_overforecast"]) * 100, 1)

h1 = pd.DataFrame(src["H1"]); h2 = pd.DataFrame(src["H2"]); hg = pd.DataFrame(src["H1H2_genuine"])
h["H1_ratio_min"], h["H1_ratio_max"] = round(h1.ratio.min(), 2), round(h1.ratio.max(), 2)
h["H1_regions_passed"] = int(h1.passes_h1.sum())
n2 = h2[h2.label == "OVERALL_NEM"].iloc[0]
h["H2_nem"] = {"masking_pct": float(n2.masking_pct), "aggregate_mae": round(float(n2.aggregate_mae), 2),
               "extreme_mae": round(float(n2.extreme_mae), 2), "n": int(n2.total_intervals)}
r2 = h2[h2.label != "OVERALL_NEM"]
h["H2_masking_min"], h["H2_masking_max"] = float(r2.masking_pct.min()), float(r2.masking_pct.max())
h["H1_genuine_ratio_min"], h["H1_genuine_ratio_max"] = round(hg.ratio.min(), 2), round(hg.ratio.max(), 2)
h["H1_genuine_p_max"] = float(hg.p_value.max())
json.dump({"headline": h, "sources": src}, open(R / "numbers.json", "w"), indent=1, default=str)
print(json.dumps(h, indent=1, default=str)[:4000])
print(f"\nSaved {R / 'numbers.json'}")
