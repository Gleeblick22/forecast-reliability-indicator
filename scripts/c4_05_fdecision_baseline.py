"""c4_05 (exploratory, NOT registered): |f_decision| as a ranking baseline on the 2022 test set and 2023-25.
Also checks whether unreliable intervals among the highest forecasts are mostly over-forecasts."""
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
from config.settings import PROCESSED_DIR, TABLES_DIR

lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
rep = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"])
need = ["f_decision", "p_disp30", "y_v2"]
for name, d in [("label file", lab), ("replication", rep)]:
    miss = [c for c in need if c not in d.columns]
    if miss:
        sys.exit(f"{name}: missing {miss}; columns are {list(d.columns)}")
out = []
for per, d in [("2022 test", lab[lab.partition == "test"]), ("2023-25", rep)]:
    y, f, p = d.y_v2.values, d.f_decision.values, d.p_disp30.values
    a = np.abs(f)
    k = max(1, int(round(len(d) * 0.01)))
    top = np.argsort(-a)[:k]
    unrel = y == 1
    over = (f - p) > 300
    out.append({"period": per, "n": len(d), "positives": int(y.sum()),
                "auc_abs_f": round(roc_auc_score(y, a), 4), "ap_abs_f": round(average_precision_score(y, a), 4),
                "top1pct_n": k, "top1pct_precision": round(y[top].mean(), 4),
                "top1pct_unreliable_overforecast_share": round(over[top][unrel[top]].mean(), 4) if unrel[top].any() else None,
                "all_unreliable_overforecast_share": round(over[unrel].mean(), 4)})
res = pd.DataFrame(out)
res.to_csv(TABLES_DIR / "c4_05_fdecision_baseline.csv", index=False)
print(res.to_string(index=False))
