"""
c3_20_download_nz_emi.py
=========================
Download New Zealand EMI data for H8 cross-market validation.
Secondary Dataset 2 -- NZ NZEM predispatch prices.

Data sources:
  PRSS: Price-responsive short schedule
        49 runs per day every 30 minutes
        Used for f_forecast_revision construction
        2021-2022

  NodalPricesAndVolumes_F: Final settlement prices
        Daily CSV with all nodes
        Used as actual_rrp
        2021-2022

Storage: Azure Blob Storage (public access)
Base URL: https://emidatasets.blob.core.windows.net/publicdata

Deviation D-020 recorded in COMPLIANCE.md.
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import time
import zipfile
import io
import urllib.request
import urllib.error
from pathlib import Path
from config.settings import RAW_DIR
from config.logging_config import get_logger

logger = get_logger("c3_20_download_nz_emi")

BASE = "https://emidatasets.blob.core.windows.net/publicdata"
SAS  = ("sv=2021-10-04&si=publicdata&sr=c"
        "&sig=f034UWz1xmMbk89jd76zY0M"
        "%2BwycFDhhumejUrjqlfIw%3D")

NZ_DIR = RAW_DIR / "nz_emi"


def list_blobs(prefix):
    """List all blobs with given prefix."""
    url = (f"{BASE}?restype=container&comp=list"
           f"&prefix={prefix}&{SAS}")
    with urllib.request.urlopen(url, timeout=30) as r:
        content = r.read().decode("utf-8")

    import xml.etree.ElementTree as ET
    root = ET.fromstring(content)
    return [b.text for b in root.findall(".//Name")]


def download_file(blob_path, dest_path, retries=3):
    """Download a single blob to dest_path."""
    url = f"{BASE}/{blob_path}?{SAS}"
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        return True

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(
                    url, timeout=30) as r:
                data = r.read()
            dest_path.write_bytes(data)
            return True
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                logger.warning(
                    f"Failed {blob_path}: {e}")
                return False


def download_prss_year(year):
    """Download all PRSS zip files for a year."""
    prefix = f"Datasets/Wholesale/ForecastPrices/PRSS/{year}/"
    blobs  = list_blobs(prefix)
    dest   = NZ_DIR / f"prss_{year}"
    dest.mkdir(parents=True, exist_ok=True)

    logger.info(f"PRSS {year}: {len(blobs)} files")
    ok = 0
    for blob in blobs:
        fname = Path(blob).name
        dest_file = dest / fname
        if download_file(blob, dest_file):
            ok += 1
        if ok % 30 == 0:
            logger.info(f"  PRSS {year}: {ok}/{len(blobs)}")
        time.sleep(0.1)

    logger.info(f"PRSS {year}: {ok}/{len(blobs)} downloaded")
    return ok


def download_nodal_year(year):
    """Download all nodal price CSV files for a year."""
    prefix = (f"Datasets/Wholesale/DispatchAndPricing/"
              f"Pre1November2022Archive/"
              f"NodalPricesAndVolumes/{year}/")
    blobs  = list_blobs(prefix)
    dest   = NZ_DIR / f"nodal_{year}"
    dest.mkdir(parents=True, exist_ok=True)

    # Only download Final (_F) files
    blobs = [b for b in blobs if "_F.csv" in b]
    logger.info(f"Nodal {year}: {len(blobs)} final files")
    ok = 0
    for blob in blobs:
        fname = Path(blob).name
        dest_file = dest / fname
        if download_file(blob, dest_file):
            ok += 1
        if ok % 30 == 0:
            logger.info(f"  Nodal {year}: {ok}/{len(blobs)}")
        time.sleep(0.1)

    logger.info(f"Nodal {year}: {ok}/{len(blobs)} downloaded")
    return ok


def main():
    logger.info("=" * 60)
    logger.info("c3_20_download_nz_emi.py started")
    logger.info("Downloading NZ EMI data for H8 validation")
    logger.info("=" * 60)

    NZ_DIR.mkdir(parents=True, exist_ok=True)

    for year in [2021, 2022]:
        logger.info(f"\n=== YEAR {year} ===")
        prss_ok  = download_prss_year(year)
        nodal_ok = download_nodal_year(year)
        logger.info(
            f"Year {year}: PRSS={prss_ok} Nodal={nodal_ok}")

    logger.info("\n" + "=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info(f"Data saved to: {NZ_DIR}")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
