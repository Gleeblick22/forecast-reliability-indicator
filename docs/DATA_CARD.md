> **Note (November 2026).** This data card (v3.0, August 2026) documents the first version of the study. Since then, the label was redefined as |f(w_t) − p̄_t| > AUD 300/MWh, using the decision forecast and the settled 30-min DISPATCHPRICE (scripts/c1_30_build_label_v2.py), which replaces the f⁽¹⁾/P5MIN label of Sections 3.3 and 4; the 2023–2025 NEM replication data were added (scripts/c4_01a–c4_02, 261,635 test-2 intervals); and the counts, rates and manuscript section, table and reference numbers below refer to the first version. Provenance, access and licence details remain valid. Current results are in the main README and the manuscript.

# DATA CARD
## forecast-reliability-indicator (FRI)

**OSF:** 10.17605/OSF.IO/Z89HD
**Version:** 3.0 (final, complete)
**Date:** August 2026
**Author:** Dhan Prasad Ghale

---

## 1. Document Purpose

This data card documents every dataset used in the FRI research project: provenance, access method, coverage, processing pipeline, leakage-control methodology, corrections, and licensing terms. It covers **four** datasets. For academic literature discussing similar data sources, see `docs/FRI_MASTER_REFERENCES.md`; this document covers dataset provenance and processing only.

---

## 2. Dataset Summary

| # | Dataset | Role | Provider |
|---|---|---|---|
| 1 | AEMO NEM Predispatch Price Data | Primary — training and testing | AEMO |
| 2 | AEMO DISPATCHPRICE (validation) | Validates outcome proxy, test partition only | AEMO |
| 3 | GB Elexon Settlement Price Data | Secondary — structural boundary test | Elexon Limited |
| 4 | NZ EMI Predispatch (PRSS) Data | Secondary — cross-market transfer test | NZ Electricity Authority |

---

## 3. Dataset 1 — AEMO NEM Predispatch Price Data

### 3.1 Description

AEMO publishes predispatch price forecasts for the NEM through NEMWEB, across five regions (NSW1, VIC1, QLD1, SA1, TAS1). Predispatch runs every 30 minutes, publishing revised Regional Reference Price (RRP) forecasts up to 40 hours ahead. Multiple runs per interval form the revision sequences the FRI signal depends on.

### 3.2 Coverage

| Field | Value |
|---|---|
| Period | October 2021 – December 2022 |
| Raw rows | 5,663,125 |
| Processed intervals (chronological split) | 102,675 |
| Test intervals (raw chronological split) | 15,165 |
| Test intervals (after merge with genuine-outcome label; used for all reported classifier performance) | 14,645 |
| Train / test positive rate (genuine reliability label) | 9.19% / 3.74% |

### 3.3 Two distinct target labels, both derived from this dataset

**This is the single most important fact about this dataset's use, documented here explicitly to prevent confusion.**

- **Price-level regime indicator** ($y_{r,t}$, Eq. 4): $y_{r,t}=1$ if settled price $\geq$ AUD 300/MWh. Used only for H1–H3 (amplification, masking, horizon analysis), characterising price behaviour, independent of the classifier.
- **Genuine reliability label** ($Y_{r,t}^{new}$, Eq. 7): $Y_{r,t}^{new}=1$ if $|f_{r,t}^{(1)} - p\_actual_{r,t}| > 300$. This is the classifier's actual training target (H4 onward), built after Round 2 peer review identified that an earlier price-level target conflated "extreme price" with "unreliable forecast." Built by `scripts/c1_16_build_new_label.py`; validated against true settlement price via Dataset 2 below.

### 3.4 Leakage control

Two conventions were applied when constructing model features:

1. **Price-level features** are anchored to the earliest available pre-dispatch run ($f_{r,t}^{(1)}$), not the latest run or settled price, since the reliability label is defined from the settled price; a feature derived from the latest run would expose the model to a near-copy of its own target.
2. **The revision feature** (`new_revision`) is constructed exclusively from pre-dispatch runs issued 30–60 minutes before the interval, explicitly excluding the final, near-dispatch run ($f_{r,t}^{(K_t)}$). Verified directly against `scripts/c1_17_rebuild_revision_feature.py`. This was a direct response to a peer-review concern (label/feature circularity); the classifier has no access to $f_{r,t}^{(K_t)}$ through this feature.

### 3.5 Processing pipeline

```
c1_01_download_aemo_nem.py       raw data retrieval
c1_02_validate_data.py           validation
c1_03_preprocess_data.py         preprocessing, feature construction
c1_15_derive_delta.py            forecast-outcome divergence
c1_16_build_new_label.py         genuine reliability label (Y_new)
c1_17_rebuild_revision_feature.py leakage-controlled revision feature
c1_18_build_final_dataset.py     final assembled dataset
```

Full sequence and dependencies: see `scripts/` and `run.sh`.

### 3.6 Access and Licence

| Field | Value |
|---|---|
| Access | Public, no authentication required |
| Portal | NEMWEB Market Data Portal, nemweb.com.au |
| Licence | AEMO Copyright Permissions Notice: general permission for any purpose, with accurate attribution, no specific permission required |
| Source | [1] |

### 3.7 Official Sources

[1] Australian Energy Market Operator (AEMO). (2022). *Predispatch Price Data* [Dataset]. NEMWEB Market Data Portal. https://www.nemweb.com.au/REPORTS/ARCHIVE/PREDISP_ALL_DATA/

[2] Australian Energy Market Operator (AEMO). (2021). *Market Management System (MMS) Data Model*. https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/market-management-system-mms-data/pre-dispatch

[3] Australian Energy Market Operator (AEMO). (2021). *Pre-dispatch Process Description*. AEMO Technical Report (SO_OP_3704).

---

## 4. Dataset 2 — AEMO DISPATCHPRICE (Validation Dataset)

### 4.1 Description

Retrieved from AEMO's MMSDM historical archive, added after Round 2 peer review, to validate the P5MIN-based outcome proxy used to construct $Y_{r,t}^{new}$ (Section 3.3). P5MIN was used as the practical proxy for the genuine settled outcome during initial development, since a separately-recorded settlement price was not accessible through the data-access tools used at that time.

### 4.2 Coverage and result

| Field | Value |
|---|---|
| Period | November – December 2022 (test partition only) |
| Label agreement (P5MIN vs. true DISPATCHPRICE) | 99.58% |
| AUC (P5MIN-based / true-price-based) | 0.9667 / 0.9653 |
| F1 (P5MIN-based / true-price-based) | 0.8908 / 0.8939 |

**Conclusion:** the P5MIN proxy does not materially affect reported results (manuscript Section 3.C, Table A.4).

### 4.3 Processing pipeline

```
c1_23_extract_true_dispatchprice.py   retrieval from MMSDM archive
c2_20_rescore_true_dispatchprice.py   re-scoring the classifier against true price
```

### 4.4 Access and Licence

| Field | Value |
|---|---|
| Access | Public, no authentication required |
| Portal | AEMO MMSDM Historical Data Archive |
| Licence | Same AEMO Copyright Permissions Notice as Dataset 1 |
| Source | [4] |
| Manuscript citation | [48] |

### 4.5 Official Source

[4] Australian Energy Market Operator (AEMO). *Market Management System Data Model (MMSDM) Historical Data Archive*. https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/

---

## 5. Dataset 3 — GB Elexon Settlement Price Data

### 5.1 Description

Elexon publishes GB settlement prices via BMRS. Settlement prices are the final cash-out price for each 30-minute period after balancing actions are complete. **GB does not publish intraday revision sequences**, only the final settled value is available.

### 5.2 Coverage

| Field | Value |
|---|---|
| Period | January 2021 – December 2022 |
| Intervals | 35,035 |
| Extreme-event threshold | 99.06th percentile (original) / 87.44th percentile (harmonized comparison) |

### 5.3 Feature construction note

**Because GB publishes no pre-dispatch revision sequence, the revision feature (`new_revision`) is zero-filled for every GB interval**, identical construction to the original NEM-trained model, with no GB-specific substitute. This is the structural mechanism behind the paper's GB transfer-failure finding (manuscript Section 4.H): the classifier's dominant feature is systematically unavailable in this market.

### 5.4 Processing pipeline

```
c3_00_download_gb_elexon.py         raw data retrieval
c3_06d_h8_gb_full_model.py          full-model H8 transfer test
c3_33_gb_harmonized_evaluation.py   label-harmonized threshold test
c3_34_gb_harmonized_full_model.py   harmonized, full model
c3_46_h8_gb_relabeled.py            relabelled classifier, final GB result
```

### 5.5 Access and Licence

| Field | Value |
|---|---|
| Access | Public, free of charge |
| Portal | BMRS Insights Solution API, data.elexon.co.uk |
| Licence | Personal, academic, or non-commercial use permitted with attribution: "Contains BMRS data © Elexon Limited 2021–2022." **Commercial use requires separate terms, not sought or assumed by this project.** |
| Source | [5] |
| Manuscript citation | [49] |

### 5.6 Official Sources

[5] Elexon Limited. (2022). *Settlement System Prices (DISEBSP)* [Dataset]. BMRS. https://data.elexon.co.uk/bmrs/api/v1/balancing/settlement/system-prices

[6] Elexon Limited. (2021). *Copyright: Licence to Use BMRS Open Data*. https://www.elexon.co.uk/operations-settlement/bsc-central-services/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/

---

## 6. Dataset 4 — NZ EMI Predispatch (PRSS) Data

### 6.1 Description

The NZ Electricity Authority publishes market data via EMI. The PRSS dataset contains predispatch revision sequences, run every 30 minutes, 49 files/day. Two regions: North Island (NI), South Island (SI).

**Note:** EMI is being decommissioned and migrated to a new "Data & Insights" hub; original EMI URLs may not resolve indefinitely.

### 6.2 Coverage

| Field | Value |
|---|---|
| Period | February 2021 – October 2022 |
| Processed intervals (post-deduplication) | 57,814 |
| Genuine reliability label positive rate | 0.50% |

### 6.3 Transfer result and scale diagnostic

| Test | F1 | AUC |
|---|---|---|
| H8 transfer, relabelled classifier (NEM threshold, no refitting) | 0.0787 | 0.8399 |

**Result: does not meet the pre-registered tolerance.** Diagnostic analysis confirmed the underlying signal remains genuinely present: revision magnitude correlates with the true reliability label at **r = 0.327**, with mean revision approximately 91-fold higher for genuinely unreliable intervals (2,928.57) than reliable ones (32.04). Re-deriving the label threshold to match NEM's own positive rate did not resolve the transfer failure, confirming the limitation is one of feature and threshold scale, not label selectivity, the mechanism that separately explains GB's structural failure above. Full detail: manuscript Table A.6.

### 6.4 Processing pipeline

```
c3_20_download_nz_emi.py               raw data retrieval
c3_21_preprocess_nz_emi.py             preprocessing, deduplication
c3_22_h8_nz_validation.py              original classifier, H8 test
c3_45_h8_nz_relabeled_harmonized.py    relabelled classifier, harmonized threshold test
```

### 6.5 Known corrections applied

- **f_current_rrp leakage fix**: initial construction incorrectly used `last_forecast`; corrected to `first_forecast`, consistent with NEM's leakage-control convention (Section 3.4).
- **Duplicate rows**: 66,140 → 57,814 rows after deduplication on DATETIME + REGIONID.

### 6.6 Access and Licence

| Field | Value |
|---|---|
| Access | Public, no authentication required |
| Portal | Azure Blob Storage mirror, emidatasets.blob.core.windows.net/publicdata |
| Licence | **Creative Commons Attribution (CC-BY) 4.0 International.** Free to copy, store, distribute, and adapt, including commercial use, with attribution to the Electricity Authority. |
| Source | [7] |
| Manuscript citation | [41] |

### 6.7 Official Sources

[7] New Zealand Electricity Authority. (2022). *Predispatch Revised Schedule and Sensitivity (PRSS)* [Dataset]. EMI Platform. https://www.emi.ea.govt.nz/Wholesale/Datasets/DispatchAndPricing/CaseFiles/PRSS/ (Azure mirror: https://emidatasets.blob.core.windows.net/publicdata)

[8] Electricity Authority (New Zealand). *Copyright, Disclaimer and Transparency Statement*. https://www.ea.govt.nz/copyright-disclaimer-transparency/

[9] Electricity Authority (New Zealand). *EMI Retirement and Data & Insights Hub* [Notice]. https://forum.emi.ea.govt.nz/thread/emi-retirement-and-electricity-authority-data-and-insights-hub

---

## 7. Dataset Comparison Summary

| Field | AEMO NEM | AEMO DISPATCHPRICE | GB Elexon | NZ EMI |
|---|---|---|---|---|
| Role | Primary | Validation | Secondary | Secondary |
| Revision sequences | Yes | N/A | **No (zero-filled)** | Yes |
| Transfer result | Training | — | FAIL (structural) | FAIL (scale, signal confirmed present) |
| Licence | AEMO, any purpose | AEMO, any purpose | Elexon, **non-commercial** | CC-BY 4.0, any purpose |

---

## 8. Ethical and Legal Considerations

- All four datasets are publicly available; no personal or sensitive data used; no ethics approval required.
- **GB Elexon data (Dataset 3):** any future commercial use requires separately confirming Elexon's commercial licensing terms; this has not been sought and should not be assumed.
- Small, representative samples (one week each) are included in `data/samples/` for reproducibility; full datasets are retrieved via the scripts referenced above, not redistributed in full here.

---

## 9. Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | May 2026 | Initial data card, three datasets |
| 2.0 | Aug 2026 | Added DISPATCHPRICE dataset; corrected stale NZ/H8 figures; removed duplicated academic-literature sections |
| 3.0 | Aug 2026 | Added: NEM leakage-control methodology (3.4); explicit two-label distinction (3.3); GB revision zero-filling explanation (5.3); NZ scale-mismatch diagnostic with corrected r=0.327 (6.3, was previously misreported as r=0.10); full processing-pipeline script references for all four datasets |
