"""c3_53 (Roadmap v3, A4): degradation coefficient check.
Code used alpha = 5.04e-4; the source (Xu et al., cycle depth stress function, NMC cells)
gives 5.24e-4 with beta = 2.03. Registered runs are unchanged; this reports the sensitivity
of net revenue (baseline, FRI, const x0.25) on the 2022 test set and the 2023-25 replication."""
import sys, json, importlib.util
import numpy as np
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_53_alpha_sensitivity")
spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
KEYS = ["REGIONID", "DATETIME"]
theta = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["theta_d300"]


def setup(t):
    t = t.sort_values(KEYS).reset_index(drop=True)
    t["day"] = t.DATETIME.dt.floor("D").factorize()[0]
    g = [(x.index.values, x.day.tolist(), x.f_decision.tolist(), x.p_disp30.tolist())
         for _, x in t.groupby("REGIONID", sort=False)]
    s = t.fri_score.values
    sc = {"baseline": np.ones(len(t)), "fri_3band": np.where(s >= theta, 0.25, np.where(s >= 0.5, 0.75, 1.0)),
          "const_0.25": np.full(len(t), 0.25)}
    return t, g, sc


rows = []
for label, f in [("2022 test", TABLES_DIR / "c2_31_test_scores.csv"), ("2023-25", TABLES_DIR / "c4_03_scores.csv")]:
    t, g, sc = setup(pd.read_csv(f, parse_dates=["DATETIME"]))
    for alpha in [5.04e-4, 5.24e-4]:
        A.ALPHA = alpha
        A.deg_cost = lambda d, a=alpha: A.R_REPL * a * d ** A.BETA
        for name, scale in sc.items():
            r = A.run_agent(t, scale, g)
            rows.append(dict(period=label, alpha=alpha, agent=name, degradation=round(r.deg.sum()),
                             net_revenue=round(r.net.sum())))
res = pd.DataFrame(rows)
res.to_csv(TABLES_DIR / "c3_53_alpha_sensitivity.csv", index=False)
with pd.option_context("display.width", 200):
    logger.info(f"\n{res.pivot_table(index=['period', 'agent'], columns='alpha', values='net_revenue')}")
sys.exit(0)
