"""c3_54_h5_registered.py: H5 evaluated with the REGISTERED definition (OSF 10.17605/OSF.IO/Z89HD, 28 Apr 2026):
a silent failure is an interval whose forecast error exceeds AUD 300/MWh while no FRI warning is active.
Error = |f_decision - p_disp30| (the corrected label); warning = fri_score >= theta; the baseline issues no warnings.
Criterion: >= 20% reduction, FRI vs baseline. Paired test: exact McNemar. 2022 test set (test 1).
The dispatch-based silent failure of c3_52 is a secondary, unregistered measure (Table IV).
Output: results/tables/c3_54_h5_registered.csv"""
import json
import pandas as pd
from scipy.stats import binomtest
from pathlib import Path

T = Path("results/tables")
t = pd.read_csv(T / "c2_31_test_scores.csv")
theta = json.load(open(T / "c2_31_best_params.json"))["theta_d300"]
err = (t.f_decision - t.p_disp30).abs() > 300
assert (t.y_v2_d300.astype(bool) == err).all(), "label and error definition differ"
warn = t.fri_score >= theta
n_b = int(err.sum())                    # baseline: every unreliable interval is unwarned
n_f = int((err & ~warn).sum())          # FRI: unreliable and not warned
b, c = n_b - n_f, 0                     # discordant pairs: baseline-only, FRI-only
p = binomtest(b, b + c, 0.5).pvalue if b + c > 0 else 1.0
red = (1 - n_f / n_b) * 100
out = pd.DataFrame([dict(H="H5", definition="registered: error > 300 and no FRI warning", theta=theta,
                         baseline=n_b, fri=n_f, reduction_pct=round(red, 1), criterion="reduction >= 20%",
                         mcnemar_exact_p=f"{p:.2e}", supported=red >= 20)])
out.to_csv(T / "c3_54_h5_registered.csv", index=False)
print(out.T.to_string())
