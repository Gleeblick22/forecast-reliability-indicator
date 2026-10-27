"""
c1_29_download_dispatchprice.py  (Roadmap P2.1 / P4.2)
Downloads AEMO MMSDM DISPATCHPRICE monthly files (Oct 2021 - Dec 2022)
into data/raw/aemo_nem/dispatchprice/. Existing CSVs are skipped.
Failed months print their URL for manual download.
"""
import sys
import zipfile
import urllib.request
from config.settings import AEMO_RAW_DIR
from config.logging_config import get_logger

logger = get_logger("c1_29_download_dispatchprice")

OUT_DIR = AEMO_RAW_DIR / "dispatchprice"
START = (2021, 10)
END = (2022, 12)
BASE = ("https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/"
        "{y}/MMSDM_{y}_{m:02d}/MMSDM_Historical_Data_SQLLoader/DATA/"
        "PUBLIC_DVD_DISPATCHPRICE_{y}{m:02d}010000.zip")


def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for y, m in months(START, END):
        csv_name = f"PUBLIC_DVD_DISPATCHPRICE_{y}{m:02d}010000.CSV"
        if (OUT_DIR / csv_name).exists():
            logger.info(f"Present, skipping: {csv_name}")
            continue
        url = BASE.format(y=y, m=m)
        zip_path = OUT_DIR / f"{csv_name}.zip"
        try:
            logger.info(f"Downloading {url}")
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path) as z:
                members = [n for n in z.namelist() if n.upper().endswith(".CSV")]
                if not members:
                    raise RuntimeError("zip contains no CSV")
                with z.open(members[0]) as src, open(OUT_DIR / csv_name, "wb") as dst:
                    dst.write(src.read())
            zip_path.unlink()
            logger.info(f"Extracted: {csv_name}")
        except Exception as e:
            logger.error(f"FAILED {y}-{m:02d}: {e}  URL: {url}")
            failed.append(url)
            if zip_path.exists():
                zip_path.unlink()
    if failed:
        logger.error(f"{len(failed)} month(s) failed. Download manually:\n" + "\n".join(failed))
        sys.exit(1)
    logger.info("All months present.")
    sys.exit(0)


if __name__ == "__main__":
    main()
