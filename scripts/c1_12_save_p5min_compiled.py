"""
c1_04d_save_p5min_compiled.py
==============================
Saves the compiled P5MIN REGIONSOLUTION data to CSV,
keeping only the columns needed (RRP as actual-price proxy).
"""
from nemseer import compile_data
from config.settings import AEMO_RAW_DIR, AEMO_START_DATE, AEMO_END_DATE
from config.logging_config import get_logger

logger = get_logger("c1_04d_save_p5min_compiled")

CACHE_DIR   = AEMO_RAW_DIR / "cache_p5min"
OUTPUT_FILE = AEMO_RAW_DIR / "aemo_nem_p5min_actual_2021_2022_raw.csv"

start_str = str(AEMO_START_DATE).replace("-", "/") + " 00:00:00"
end_str   = str(AEMO_END_DATE).replace("-", "/") + " 23:55:00"

result = compile_data(
    forecast_type="P5MIN",
    tables="REGIONSOLUTION",
    raw_cache=str(CACHE_DIR),
    run_start=start_str,
    run_end=end_str,
    forecasted_start=start_str,
    forecasted_end=end_str,
)

df = result["REGIONSOLUTION"][["RUN_DATETIME", "INTERVAL_DATETIME", "REGIONID", "RRP"]].copy()
logger.info(f"Trimmed shape: {df.shape}")
df.to_csv(OUTPUT_FILE, index=False)
logger.info(f"Saved: {OUTPUT_FILE}")
