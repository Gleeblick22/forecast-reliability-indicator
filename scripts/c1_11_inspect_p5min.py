"""
c1_04c_inspect_p5min.py
========================
Diagnostic: inspect the structure of compile_data()'s
return value for P5MIN REGIONSOLUTION, since it returned
a dict rather than a DataFrame.
"""
from nemseer import compile_data
from config.settings import AEMO_RAW_DIR, AEMO_START_DATE, AEMO_END_DATE
from config.logging_config import get_logger

logger = get_logger("c1_04c_inspect_p5min")

CACHE_DIR = AEMO_RAW_DIR / "cache_p5min"

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

logger.info(f"Type of result: {type(result)}")
logger.info(f"Keys: {list(result.keys())}")

for key, value in result.items():
    logger.info(f"Key '{key}': type={type(value)}")
    if hasattr(value, "columns"):
        logger.info(f"  Columns: {list(value.columns)}")
        logger.info(f"  Shape: {value.shape}")
    if hasattr(value, "head"):
        logger.info(f"  Head:\n{value.head(3)}")
