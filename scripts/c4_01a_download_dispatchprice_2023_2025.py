"""c4_01a (Phase 4, P4.1): MMSDM DISPATCHPRICE for Jan 2023 - Dec 2025.
Tries the old file name and the newer PUBLIC_ARCHIVE#...#FILE01# name.
Saves as PUBLIC_DVD_DISPATCHPRICE_YYYYMM010000.CSV so c1_30's loader works unchanged.
Output: data/raw/aemo_nem/dispatchprice_2023_2025/ + download_log.csv"""
import sys, zipfile, urllib.request
from datetime import datetime
import pandas as pd
from config.settings import AEMO_RAW_DIR
from config.logging_config import get_logger

logger = get_logger("c4_01a_download_dispatchprice_2023_2025")
OUT = AEMO_RAW_DIR / "dispatchprice_2023_2025"
BASE = "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/{y}/MMSDM_{y}_{m:02d}/MMSDM_Historical_Data_SQLLoader/DATA/"
NAMES = ["PUBLIC_DVD_DISPATCHPRICE_{y}{m:02d}010000.zip",
         "PUBLIC_ARCHIVE%23DISPATCHPRICE%23FILE01%23{y}{m:02d}010000.zip"]

OUT.mkdir(parents=True, exist_ok=True)
log, failed = [], []
for y in (2023, 2024, 2025):
    for m in range(1, 13):
        csv = OUT / f"PUBLIC_DVD_DISPATCHPRICE_{y}{m:02d}010000.CSV"
        if csv.exists():
            continue
        t0, ok = datetime.now(), False
        for name in NAMES:
            url = BASE.format(y=y, m=m) + name.format(y=y, m=m)
            zp = OUT / "tmp.zip"
            try:
                urllib.request.urlretrieve(url, zp)
                with zipfile.ZipFile(zp) as z:
                    member = [n for n in z.namelist() if n.upper().endswith(".CSV")][0]
                    csv.write_bytes(z.read(member))
                ok = True
                logger.info(f"{y}-{m:02d} ok via {name.split('_')[1]}")
                break
            except Exception as e:
                last = f"{e} | {url}"
            finally:
                if zp.exists():
                    zp.unlink()
        if not ok:
            failed.append(f"{y}-{m:02d}: {last}")
            logger.error(f"{y}-{m:02d} FAILED: {last}")
        log.append(dict(month=f"{y}-{m:02d}", started=t0.isoformat(), finished=datetime.now().isoformat(),
                        status="ok" if ok else "failed"))
pd.DataFrame(log).to_csv(OUT / "download_log.csv", mode="a", index=False,
                         header=not (OUT / "download_log.csv").exists())
if failed:
    logger.error("Failed months:\n" + "\n".join(failed)); sys.exit(1)
logger.info("All 36 months present."); sys.exit(0)
