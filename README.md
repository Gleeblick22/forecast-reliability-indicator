# Forecast Reliability Indicator (FRI)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-yellow)](https://python.org)
[![Pre-registered](https://img.shields.io/badge/Pre--registered-OSF-lightblue)](https://osf.io/jpfwh)

**An interpretable classifier that predicts, ex ante, whether a pre-dispatch electricity price forecast will prove unreliable, and demonstrates its economic value for autonomous battery dispatch in Australia's National Electricity Market (NEM).**

> Pre-dispatch price forecasts fail hardest exactly when accurate dispatch matters most: error amplifies up to 23.50x (13.73x on average) during extreme price events in Australia's NEM, yet aggregate metrics mask 77.28% of this degradation. We introduce the Forecast Reliability Indicator (FRI), an interpretable classifier predicting ex ante whether a pre-dispatch forecast will prove unreliable (AUC = 0.9666), driven largely by forecast revision across successive pre-dispatch runs. A stale-information baseline overstates FRI's value; once information timing is held constant, it instead delivers value through asset economics, raising net revenue from AUD 187,603 to AUD 299,614 (59.7%) over an equally-informed baseline by scaling dispatch commitment to reliability confidence, a signal-free control agent confirms 65.1% of this advantage is genuinely attributable to the reliability signal rather than conservative scaling alone, under a physically grounded degradation and charging-economics model. A pre-registered revenue test returned null, the result tracing to underpowered testing rather than a true absence of effect. FRI transfers with negligible loss within a scale-identical market but hits two cross-market limits: ranking holds where price scales differ though the threshold needs recalibration, while structural transfer fails under harmonized comparison where the revision signal cannot be built. FRI serves as a reliability instrument for autonomous dispatch, separating reliability prediction from forecast accuracy improvement as orthogonal objectives.

📄 **Paper**: [to be added on submission]
🔗 **Pre-registration (OSF)**: 10.17605/OSF.IO/Z89HD

---
## Hypothesis structure

The eight hypotheses form a dependency chain across four research gates, not eight independent tests:

![Hypothesis dependency chain](results/figures/fig04_hypothesis_chain.png)

- **Gate 1 — Does the problem exist?** (H1, H2, H3): forecast error amplifies and is masked during extreme events
- **Gate 2 — Can it be detected?** (H4): a classifier can predict forecast unreliability ex ante
- **Gate 3 — Does detection add value?** (H5, H6, H7): conditioning dispatch on the signal protects the asset economically
- **Gate 4 — Does it generalise?** (H8): the classifier transfers within-market (SA1), but hits real boundaries, structural (GB) and scale (NZ)

Each gate depends on the one before it holding; H4 only matters because H1–H3 establish there is a real problem to detect, and H5–H7 only matter because H4 confirms detection is genuinely possible.
## Key results at a glance

| Hypothesis | Description | Result | Key metric |
|---|---|---|---|
| H1 | Forecast error amplification during extreme events | **Confirmed** | 4.39×–23.50× across 5 NEM regions, p<0.001 |
| H2 | Aggregate metrics mask extreme forecast failures | **Confirmed** | 77.28% of failures masked |
| H3 | P5 vs. P30 horizon difference | Null (pre-registered) | Exploratory: universal P30→P60 amplification jump |
| H4 | FRI model detects unreliable forecasts (F1 ≥ 0.60) | **Confirmed** | F1 = 0.8898, AUC = 0.9666, θ = 0.856818 |
| H5 | Reliability-conditioned dispatch reduces degradation cost | **Confirmed** | +59.7% net revenue vs. a fairly-timed baseline |
| H6 | Dispatch scaling correlates with reliability confidence | **Confirmed** | r = 0.3223, 95% CI [0.2639, 0.3783] |
| H7 | Reliability signal increases raw trading revenue (≥15%) | Null | −1.55%, underpowered test (achieved power 5.3%) |
| H8 | Classifier transfers across markets (F1 diff ≤ 0.15) | Mixed | SA1 pass (F1=0.8577); NZ, GB fail (mechanistically explained) |


---
### Result tables and figures, direct links

| Hypothesis | Result table (CSV) | Figure |
|---|---|---|
| H1 — Amplification | [`c1_04_h1_amplification_results.csv`](results/tables/c1_04_h1_amplification_results.csv) | [Fig. 5](results/figures/fig05_h1_amplification.png) |
| H2 — Masking | [`c1_05_h2_masking_results.csv`](results/tables/c1_05_h2_masking_results.csv) | [Fig. 6](results/figures/fig06_h2_masking.png) |
| H3 — Horizon | [`c1_06_h3_horizon_results.csv`](results/tables/c1_06_h3_horizon_results.csv) | [Fig. 7](results/figures/fig07_h3_horizon.png) |
| H4 — Classifier performance | [`c2_23_roc_pr_summary_relabeled.csv`](results/tables/c2_23_roc_pr_summary_relabeled.csv) | [Fig. 8 (ROC)](results/figures/fig08_h4_roc.png) · [Fig. 9 (SHAP)](results/figures/fig09_h4_shap.png) |
| H5 — Economic value | [`c3_41_charging_economics_relabeled_results.csv`](results/tables/c3_41_charging_economics_relabeled_results.csv) | [Fig. 10](results/figures/fig10_h5_four_agent.png) |
| Signal attribution (M2) | [`c3_49_charging_economics_control_results.csv`](results/tables/c3_49_charging_economics_control_results.csv) | [Fig. 10](results/figures/fig10_h5_four_agent.png) |
| H6 — Dispatch correlation | [`c3_42_h6_relabeled_results.csv`](results/tables/c3_42_h6_relabeled_results.csv) | [Fig. 11](results/figures/fig11_h6_correlation.png) |
| H7 — Revenue comparison | [`c3_43_h7_relabeled_results.csv`](results/tables/c3_43_h7_relabeled_results.csv) | [Fig. 13](results/figures/fig13_h7_revenue_by_regime.png) · [Fig. 14](results/figures/fig14_h7_mcnemar_power.png) |
| H8 — SA1 / NZ / GB transfer | [`c2_19_h8_sa1_relabeled_results.csv`](results/tables/c2_19_h8_sa1_relabeled_results.csv) · [`c3_45_h8_nz_relabeled_harmonized_results.csv`](results/tables/c3_45_h8_nz_relabeled_harmonized_results.csv) · [`c3_46_h8_gb_relabeled_results.csv`](results/tables/c3_46_h8_gb_relabeled_results.csv) | [Fig. 16](results/figures/fig16_gb_harmonization.png) · [Fig. 17](results/figures/fig17_crossmarket.png) |

Trained classifier: [`results/models/fri_model_relabeled.pkl`](results/models/fri_model_relabeled.pkl)
Full results, confidence intervals, and supporting detail: [`docs/RESULTS.md`](docs/RESULTS.md)


## Research context

Australia's National Electricity Market (NEM) runs predispatch every 30 minutes, producing price forecasts that battery operators rely on for dispatch decisions. During extreme price events (≥ AUD 300/MWh), these forecasts fail dramatically, but standard aggregate accuracy metrics hide this failure because extreme events are rare in the test partition.

This creates **silent failures**: battery operators dispatch confidently based on unreliable forecasts, missing high-value opportunities and incurring preventable degradation costs.

**FRI addresses this gap** by monitoring forecast revision patterns across predispatch runs to detect when the forecast signal is unreliable — before dispatch decisions are made, and conditioning dispatch magnitude on that reliability score.

---

## FRI framework

```
Predispatch runs (every 30 min)
        │
        ▼
┌─────────────────────────┐
│   Feature Engineering   │  10 features; dominant signal is
│   (forecast revision)   │  forecast revision (52.32% SHAP contribution)
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   XGBoost Classifier    │  Relabelled against genuine
│   θ = 0.856818           │  reliability target; AUC = 0.9666
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   FRI Score [0, 1]      │  HIGH   ≥ 0.75 → dispatch 100%
│   Decision Bands         │  MEDIUM ≥ 0.50 → dispatch 75%
│                          │  LOW    < 0.50 → dispatch 25%
└─────────────────────────┘
```

FRI requires **predispatch revision sequences** to construct its dominant feature. This is the structural requirement that explains why FRI works in NEM and SA1 but fails to transfer to GB (a settlement-only market lacking this data) and requires recalibration for NZ (a scale, not structural, mismatch).

---

## Repository structure

```
forecast-reliability-indicator/
├── README.md
├── LICENSE
├── requirements.txt
├── run.sh
│
├── config/                     configuration and settings
│
├── data/samples/                representative one-week samples per market
│
├── scripts/                     full analysis pipeline
│   ├── c1_*.py                  preprocessing, H1/H2/H3
│   ├── c2_*.py                  classifier training, SHAP, calibration
│   ├── c3_*.py                  dispatch agents, degradation/charging economics
│   └── figure_*.py               all figure-generation scripts
│
├── results/
│   ├── tables/                  output CSVs
│   ├── figures/                 final figures (fig01, fig05–fig17)
│   └── models/                  trained, relabelled classifier
│
└── docs/
    ├── RESULTS.md               complete, verified results
    ├── COMPLIANCE.md            deviations D-001 through D-030
    ├── DATA_CARD.md             dataset provenance and licensing
    └── FRI_MASTER_REFERENCES.md complete reference list
```

---

## Datasets

Four datasets were used (primary NEM, an AEMO validation dataset, and two secondary cross-market datasets). See [`docs/DATA_CARD.md`](docs/DATA_CARD.md) for full documentation, citations, processing steps, and reproducibility checklists.

| Dataset | Role | Source | Size | H8 result |
|---|---|---|---|---|
| AEMO NEM 2021–2022 | Primary (training + testing) | [NEMWEB](https://www.nemweb.com.au/REPORTS/ARCHIVE/PREDISP_ALL_DATA/) | 810 MB / 102,675 intervals | Training |
| AEMO DISPATCHPRICE | Validation (test partition only) | [MMSDM Archive](https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/) | Test partition | Proxy confirmed adequate (99.58% label agreement) |
| GB Elexon 2021–2022 | Secondary (structural boundary) | [BMRS API](https://data.elexon.co.uk/bmrs/api/v1/) | 1.6 MB / 35,035 intervals | Fail (structural) |
| NZ EMI 2021–2022 | Secondary (cross-market) | [Azure Blob](https://emidatasets.blob.core.windows.net/publicdata) | 673 MB / 57,814 intervals | Fail (scale mismatch) |

**Attribution:**
- AEMO NEM / DISPATCHPRICE: AEMO Copyright Permissions Notice — general permission for any purpose, with attribution
- GB Elexon: "Contains BMRS data © Elexon Limited 2021–2022" — personal/academic/non-commercial use; commercial use requires separate terms
- NZ EMI: © New Zealand Crown copyright, CC-BY 4.0 — commercial use permitted with attribution

---

## Reproduce the results

### Prerequisites

```bash
Python 3.10+
8 GB RAM minimum
20 GB disk space (for full raw data; data/samples/ works for a quick test without this)
```

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/forecast-reliability-indicator.git
cd forecast-reliability-indicator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Quick test, using included samples

```bash
python scripts/c2_18_retrain_relabeled_full_scores.py   # loads data/samples/
```

### Full pipeline — Component 1: NEM data, H1/H2/H3

```bash
./run.sh scripts/c1_01_download_aemo_nem.py
./run.sh scripts/c1_03_preprocess_data.py
./run.sh scripts/c1_04_test_h1_amplification.py
./run.sh scripts/c1_05_test_h2_masking.py
./run.sh scripts/c1_06_test_h3_horizon.py
```

### Full pipeline — Component 2: classifier, H4

```bash
./run.sh scripts/c2_01_feature_engineering.py
./run.sh scripts/c2_02_train_test_split.py
./run.sh scripts/c2_18_retrain_relabeled_full_scores.py
# Expected: AUC=0.9666, F1=0.8898, threshold=0.856818
```

### Full pipeline — Component 3: dispatch agents, H5/H6/H7/H8

```bash
./run.sh scripts/c3_00_download_gb_elexon.py
./run.sh scripts/c3_20_download_nz_emi.py
./run.sh scripts/c3_39_p5_fri_relabeled.py
./run.sh scripts/c3_40_p5_baseline_relabeled_match.py
./run.sh scripts/c3_42_h6_relabeled.py
./run.sh scripts/c3_43_h7_relabeled.py
./run.sh scripts/c2_19_h8_sa1_relabeled.py
./run.sh scripts/c3_45_h8_nz_relabeled_harmonized.py
./run.sh scripts/c3_46_h8_gb_relabeled.py
./run.sh scripts/c3_48_depth_matched_control.py
./run.sh scripts/c3_49_charging_economics_control.py
```

See `run.sh` for the complete, ordered sequence across all components.

---

## Documentation

| Document | Description |
|---|---|
| [`docs/RESULTS.md`](docs/RESULTS.md) | Complete, verified results for all H1–H8, organised by topic, with every headline and supporting figure |
| [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) | Every deviation from the pre-registered plan (D-001 through D-030) fully disclosed, including the classifier relabelling and two rounds of pre-submission review response |
| [`docs/DATA_CARD.md`](docs/DATA_CARD.md) | Dataset provenance, licensing, leakage-control methodology, and attribution for all four datasets |
| [`docs/FRI_MASTER_REFERENCES.md`](docs/FRI_MASTER_REFERENCES.md) | Complete reference list matching the manuscript exactly |

---

## Pre-registration and research integrity

This research was pre-registered on the Open Science Framework before data collection.

| Item | Detail |
|---|---|
| OSF | 10.17605/OSF.IO/Z89HD *(note: internal project records also reference `osf.io/jpfwh` as the registration URL — confirm the correct, live one before publishing this README)* |
| Pre-registered | H1 through H8 hypotheses, success criteria, train/test split (Oct 1, 2022) |
| Deviations | D-001 through D-030, all documented in `docs/COMPLIANCE.md` |
| Null results | H3 and H7 reported honestly, both bounded by explicit statistical reasoning |
| Major correction | Classifier relabelled against a genuine reliability target during pre-submission review; both classifiers' results retained in the compliance log for audit-trail completeness |

---

## Citation

```
[Citation to be added on publication]
```

## License

Code in this repository is licensed under the [Apache License 2.0](LICENSE).
Data samples in `data/samples/` remain subject to their original sources' terms (see [`docs/DATA_CARD.md`](docs/DATA_CARD.md)) and are **not** covered by the code license. GB Elexon data specifically requires separate confirmation before any commercial use.

## Contact
dh.ghale@gmail.com
