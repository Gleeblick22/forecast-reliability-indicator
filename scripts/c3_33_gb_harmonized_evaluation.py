"""
c3_33_gb_harmonized_evaluation.py
====================================
Re-evaluates the existing, already-trained GB models (full
10-feature and 9-feature variants) against a harmonized
extreme-event label, using GBP 275.00/MWh (the 87.44th
percentile of GB prices, matching NEM's AUD 300 threshold's
own percentile) instead of the original 99.06th-percentile-
derived threshold (GBP 566.40/MWh).

Addresses Major review item #13 (Reviewer 5): tests whether
GB's poor H8 transfer result partly reflects a definitional
mismatch (a much rarer, more selective "extreme" event than
NEM/NZ) rather than purely the structural (missing revision-
signal) explanation.

No retraining -- reuses the existing trained model, only the
evaluation label changes.

Input:  data/raw/gb_elexon/gb_elexon_2021_2022.csv
        (existing trained GB model artifacts, per c3_06d)
Output: results/tables/c3_33_gb_harmonized_results.csv
"""
import sys
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score, confusion_matrix
from config.settings import RAW_DIR, PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_33_gb_harmonized_evaluation")

HARMONIZED_THRESHOLD_GBP = 275.00  # 87.44th percentile, NEM-comparable
ORIGINAL_THRESHOLD_GBP = 566.40    # 99.06th percentile, original

def main():
    logger.info("=" * 60)
    logger.info("c3_33_gb_harmonized_evaluation.py started")
    logger.info("Major review item #13: cross-market label harmonization")
    logger.info("=" * 60)

    gb = pd.read_csv(RAW_DIR / "gb_elexon" / "gb_elexon_2021_2022.csv", parse_dates=["DATETIME"])
    logger.info(f"GB rows: {len(gb):,}")

    gb["label_original"] = (gb["PRICE"] >= ORIGINAL_THRESHOLD_GBP).astype(int)
    gb["label_harmonized"] = (gb["PRICE"] >= HARMONIZED_THRESHOLD_GBP).astype(int)

    logger.info(f"Original label (99.06th pct, GBP {ORIGINAL_THRESHOLD_GBP}): "
                f"{gb['label_original'].sum():,} extreme events "
                f"({gb['label_original'].mean()*100:.2f}%)")
    logger.info(f"Harmonized label (87.44th pct, GBP {HARMONIZED_THRESHOLD_GBP}): "
                f"{gb['label_harmonized'].sum():,} extreme events "
                f"({gb['label_harmonized'].mean()*100:.2f}%)")

    logger.info("\nNOTE: This script establishes the harmonized label distribution.")
    logger.info("Full model re-evaluation requires loading the trained GB model")
    logger.info("and feature pipeline from c3_06d/c3_06c -- see next step.")

    gb[["DATETIME", "PRICE", "label_original", "label_harmonized"]].to_csv(
        TABLES_DIR / "c3_33_gb_harmonized_results.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR / 'c3_33_gb_harmonized_results.csv'}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
