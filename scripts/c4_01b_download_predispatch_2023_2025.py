"""c4_01b (Phase 4, P4.1): PREDISPATCH/PRICE via nemseer 1.0.7, Jan 2023 - Jul 2024.
(Aug 2024+ uses AEMO's new archive format, unsupported by nemseer -> c4_01c.)
Runs by month; forecasted window extends 2 days past month end so boundary intervals keep
their full run history (overlaps removed later by dedup on DATETIME, REGIONID, RUN).
Output: data/raw/aemo_nem/predispatch_2023_2025/PD_YYYYMM.csv + download_log.csv"""
import sys, shutil, calendar
from datetime import datetime
import pandas as pd
from nemseer import compile_data, download_raw_data
from config.settings import AEMO_RAW_DIR
from config.logging_config import get_logger

logger = get_logger("c4_01b_download_predispatch_2023_2025")
OUT, CACHE = AEMO_RAW_DIR / "predispatch_2023_2025", AEMO_RAW_DIR / "cache_2023_2025"
COLS = ["REGIONID", "RRP", "DATETIME", "PREDISPATCH_RUN_DATETIME", "INTERVENTION"]
FMT = "%Y/%m/%d %H:%M:%S"
MONTHS = [(2023, m) for m in range(1, 13)] + [(2024, m) for m in range(1, 8)]
OUT.mkdir(parents=True, exist_ok=True)
failed = []
for y, m in MONTHS:
    out = OUT / f"PD_{y}{m:02d}.csv"
    if out.exists():
        continue
    rs = pd.Timestamp("2022-12-30 00:00") if (y, m) == (2023, 1) else pd.Timestamp(y, m, 1)
    re_ = pd.Timestamp(y, m, calendar.monthrange(y, m)[1], 23, 30)
    fs, fe = rs + pd.Timedelta(minutes=30), re_.normalize() + pd.Timedelta(days=2, hours=4)
    t0 = datetime.now()
    try:
        download_raw_data(forecast_type="PREDISPATCH", tables="PRICE", raw_cache=str(CACHE),
                          run_start=rs.strftime(FMT), run_end=re_.strftime(FMT))
        res = compile_data(run_start=rs.strftime(FMT), run_end=re_.strftime(FMT),
                           forecasted_start=fs.strftime(FMT), forecasted_end=fe.strftime(FMT),
                           forecast_type="PREDISPATCH", tables="PRICE", raw_cache=str(CACHE))
        df = res["PRICE"] if isinstance(res, dict) else res
        df = df[[c for c in COLS if c in df.columns]]
        df = df.drop_duplicates(["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"], keep="first")
        df.to_csv(out, index=False)
        status, rows = "ok", len(df)
        logger.info(f"{y}-{m:02d}: {rows:,} rows")
    except Exception as e:
        status, rows = f"FAILED: {e}", 0
        failed.append(f"{y}-{m:02d}: {e}")
        logger.error(f"{y}-{m:02d} FAILED: {e}")
    shutil.rmtree(CACHE, ignore_errors=True)
    pd.DataFrame([dict(month=f"{y}-{m:02d}", run_start=rs.strftime(FMT), run_end=re_.strftime(FMT),
                       started=t0.isoformat(), finished=datetime.now().isoformat(), rows=rows,
                       status=status)]).to_csv(OUT / "download_log.csv", mode="a", index=False,
                                               header=not (OUT / "download_log.csv").exists())
if failed:
    logger.error("Failed months:\n" + "\n".join(failed)); sys.exit(1)
logger.info("Jan 2023 - Jul 2024 downloaded."); sys.exit(0)
