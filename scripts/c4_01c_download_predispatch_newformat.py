"""c4_01c (Phase 4, P4.1): PREDISPATCHPRICE (all runs) Aug 2024 - Dec 2025, direct from MMSDM.
AEMO renamed archives from Aug 2024 (PUBLIC_ARCHIVE#PREDISPATCHPRICE#ALL#FILEnn#...), unsupported
by nemseer 1.0.7. VALIDATION FIRST: Jul 2024 parsed directly must match nemseer's PD_202407.csv
(run-datetime offset chosen empirically; >= 99.99% key and RRP agreement) or the script stops.
Same windows and dedup as c4_01b. Output: PD_YYYYMM.csv + download_log.csv"""
import sys, re, io, zipfile, calendar, urllib.request
from datetime import datetime
import pandas as pd
from config.settings import AEMO_RAW_DIR
from config.logging_config import get_logger

logger = get_logger("c4_01c_download_predispatch_newformat")
OUT = AEMO_RAW_DIR / "predispatch_2023_2025"
ROOT = "https://nemweb.com.au"
DIR = "/Data_Archive/Wholesale_Electricity/MMSDM/{y}/MMSDM_{y}_{m:02d}/MMSDM_Historical_Data_SQLLoader/PREDISP_ALL_DATA/"
KEYS = ["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"]


def get(url):
    with urllib.request.urlopen(url, timeout=600) as r:
        return r.read()


def parse_zip(blob):
    parts = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for n in z.namelist():
            if n.upper().endswith(".CSV"):
                d = pd.read_csv(z.open(n), skiprows=1, low_memory=False)
                d = d[d.iloc[:, 0] == "D"]
                parts.append(d[["PREDISPATCHSEQNO", "REGIONID", "DATETIME", "RRP", "INTERVENTION"]])
    d = pd.concat(parts, ignore_index=True)
    d["DATETIME"] = pd.to_datetime(d.DATETIME)
    d["RRP"] = pd.to_numeric(d.RRP)
    d["INTERVENTION"] = pd.to_numeric(d.INTERVENTION)
    s = d.PREDISPATCHSEQNO.astype(str).str.replace(r"\.0$", "", regex=True)
    d["base"] = pd.to_datetime(s.str[:8], format="%Y%m%d") + pd.to_timedelta(s.str[8:].astype(int) * 30, unit="min")
    return d


def windows(y, m):
    rs = pd.Timestamp(y, m, 1)
    re_ = pd.Timestamp(y, m, calendar.monthrange(y, m)[1], 23, 30)
    return rs, re_, rs + pd.Timedelta(minutes=30), re_.normalize() + pd.Timedelta(days=2, hours=4)


def finish(d, offset, y, m):
    rs, re_, fs, fe = windows(y, m)
    d = d.assign(PREDISPATCH_RUN_DATETIME=d.base + offset)
    d = d[(d.PREDISPATCH_RUN_DATETIME >= rs) & (d.PREDISPATCH_RUN_DATETIME <= re_) &
          (d.DATETIME >= fs) & (d.DATETIME <= fe)]
    d = d.sort_values("INTERVENTION", kind="stable")
    return d[["REGIONID", "RRP", "DATETIME", "PREDISPATCH_RUN_DATETIME", "INTERVENTION"]].drop_duplicates(KEYS, keep="first")


def validate():
    nem = pd.read_csv(OUT / "PD_202407.csv", parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"])
    d = parse_zip(get(ROOT + DIR.format(y=2024, m=7) + "PUBLIC_DVD_PREDISPATCHPRICE_202407010000.zip"))
    best = None
    for k in range(-8, 9):
        off = pd.Timedelta(minutes=30 * k)
        mg = nem.merge(finish(d, off, 2024, 7), on=KEYS, how="outer", suffixes=("_n", "_m"), indicator=True)
        share = (mg["_merge"] == "both").mean()
        if best is None or share > best[1]:
            best = (off, share, mg)
    off, share, mg = best
    b = mg[mg["_merge"] == "both"]
    rrp_ok = ((b.RRP_n - b.RRP_m).abs() < 1e-6).mean()
    logger.info(f"VALIDATION Jul-2024: offset={off}, key agreement={share:.6f}, "
                f"nemseer rows={len(nem):,}, both={len(b):,}, RRP agreement={rrp_ok:.6f}")
    if share < 0.9999 or rrp_ok < 0.9999:
        logger.error("VALIDATION FAILED - not downloading new-format months"); sys.exit(1)
    return off


def main():
    off = validate()
    failed = []
    for y, m in [(2024, mm) for mm in range(8, 13)] + [(2025, mm) for mm in range(1, 13)]:
        out = OUT / f"PD_{y}{m:02d}.csv"
        if out.exists():
            continue
        t0 = datetime.now()
        try:
            html = get(ROOT + DIR.format(y=y, m=m)).decode("latin-1")
            files = sorted(set(re.findall(r'HREF="([^"]*PREDISPATCHPRICE%23ALL%23FILE\d+%23[^"]*\.zip)"', html, flags=re.I)))
            if not files:
                raise RuntimeError("no PREDISPATCHPRICE#ALL files listed")
            d = pd.concat([parse_zip(get(ROOT + f)) for f in files], ignore_index=True)
            df = finish(d, off, y, m)
            df.to_csv(out, index=False)
            status, rows = f"ok ({len(files)} file part(s))", len(df)
            logger.info(f"{y}-{m:02d}: {rows:,} rows from {len(files)} part(s)")
        except Exception as e:
            status, rows = f"FAILED: {e}", 0
            failed.append(f"{y}-{m:02d}: {e}")
            logger.error(f"{y}-{m:02d} FAILED: {e}")
        rs, re_, _, _ = windows(y, m)
        pd.DataFrame([dict(month=f"{y}-{m:02d}", run_start=str(rs), run_end=str(re_), started=t0.isoformat(),
                           finished=datetime.now().isoformat(), rows=rows, status=status)]).to_csv(
            OUT / "download_log.csv", mode="a", index=False, header=not (OUT / "download_log.csv").exists())
    if failed:
        logger.error("Failed months:\n" + "\n".join(failed)); sys.exit(1)
    logger.info("Aug 2024 - Dec 2025 downloaded."); sys.exit(0)


if __name__ == "__main__":
    main()
