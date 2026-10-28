"""c4_04 (Roadmap v3, B0): descriptive agent summary for 2023-25 (Table VI).
Same frozen scores (c4_03_scores.csv), same agents and controls as c4_03 (+ const_0.75).
Not a hypothesis test. Output: results/tables/c4_04_agents_summary_2023_2025.csv"""
import sys, importlib.util
import numpy as np
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c4_04_agents_summary_2023_2025")
spec = importlib.util.spec_from_file_location("M", "scripts/c4_03_test_R.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
KEYS = M.KEYS
d = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"]).sort_values(KEYS).reset_index(drop=True)
sc = pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])
d = d.merge(sc[KEYS + ["fri_score"]], on=KEYS, how="left")
assert d.fri_score.notna().all()
t, groups, scales = M.agent_setup(d, d.fri_score.values)
scales["const_0.75"] = np.full(len(t), 0.75)
rows = [M.A.summarise(name, t, M.A.run_agent(t, s, groups)) for name, s in scales.items()]
res = pd.DataFrame(rows)
res.to_csv(TABLES_DIR / "c4_04_agents_summary_2023_2025.csv", index=False)
with pd.option_context("display.width", 250, "display.max_columns", 20):
    logger.info(f"\n{res}")
sys.exit(0)
