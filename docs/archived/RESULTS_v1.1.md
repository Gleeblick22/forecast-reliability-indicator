# Results

**Forecast Reliability Indicator (FRI)**

This document reports every final, confirmed result behind the manuscript, organised by topic rather than chronologically. For the complete research log — every experiment, intermediate finding, and reviewer-response entry in the order it happened — see the project's internal documentation (not included in this public repository).

**Two classifiers were built.** An *original, price-level classifier* was used through early validation. A *relabelled, genuine-reliability classifier* superseded it after peer review identified that the original target conflated "extreme price" with "unreliable forecast" (Section 4). **Unless explicitly marked "(original classifier)", every result below is the relabelled classifier's final, confirmed figure** — this is what the manuscript reports and what `results/models/fri_model_relabeled.pkl` contains. A small number of robustness checks were run only once, on the original classifier, and were not subsequently re-run on the relabelled classifier; these are explicitly labelled as such throughout, since presenting them without that label would overstate what has actually been verified for the final model.

---

## Table of contents

- [Results](#results)
  - [Table of contents](#table-of-contents)
  - [1. H1 — Forecast error amplification](#1-h1--forecast-error-amplification)
  - [2. H2 — Aggregate error masking](#2-h2--aggregate-error-masking)
  - [3. H3 — Horizon effects](#3-h3--horizon-effects)
  - [4. Classifier relabelling: why and what changed](#4-classifier-relabelling-why-and-what-changed)
  - [5. H4 — Classifier performance](#5-h4--classifier-performance)
  - [6. Feature importance (SHAP) and ablation](#6-feature-importance-shap-and-ablation)
  - [7. H5 — Dispatch agent comparison and economic value](#7-h5--dispatch-agent-comparison-and-economic-value)
  - [8. Signal attribution: is the value genuinely from the reliability signal?](#8-signal-attribution-is-the-value-genuinely-from-the-reliability-signal)
  - [9. H6 — Dispatch–confidence correlation](#9-h6--dispatchconfidence-correlation)
  - [10. H7 — Revenue comparison](#10-h7--revenue-comparison)
  - [11. H8 — Cross-market transfer](#11-h8--cross-market-transfer)
  - [12. Robustness and diagnostic checks](#12-robustness-and-diagnostic-checks)
  - [13. Reproducing these results](#13-reproducing-these-results)
  - [14. Data and code availability](#14-data-and-code-availability)

---

## 1. H1 — Forecast error amplification

**Hypothesis:** during extreme price events (≥ AUD 300/MWh), predispatch forecast error is at least 1.5× greater than during normal conditions.

| Region | Normal MAE | Extreme MAE | Amplification | p-value |
|---|---|---|---|---|
| NSW1 | $80.07 | $1,583.96 | 19.78× | <0.0001 |
| VIC1 | $105.54 | $2,479.90 | 23.50× | <0.0001 |
| QLD1 | $139.51 | $1,812.89 | 12.99× | <0.0001 |
| SA1 | $744.26 | $3,265.88 | 4.39× | <0.0001 |
| TAS1 | $190.42 | $1,517.42 | 7.97× | <0.0001 |
| **Overall (mean)** | — | — | **13.73×, 95% CI [7.54, 19.91]** | — |

**Result: confirmed in all 5 regions.** Independently re-verified against a genuine, outcome-based error definition (settled price vs. earliest forecast, rather than forecast revision): amplification held at 4.41×–19.71× across all regions (p < 10⁻⁴¹ throughout), confirming H1 is not an artefact of the error definition used.

---

## 2. H2 — Aggregate error masking

**Hypothesis:** standard aggregate accuracy metrics mask at least 50% of the true error magnitude occurring during extreme events.

| Region | Aggregate MAE | Normal MAE | Extreme MAE | Masking |
|---|---|---|---|---|
| NSW1 | $300.65 | $80.07 | $1,583.96 | 81.0% |
| VIC1 | $383.38 | $105.54 | $2,479.90 | 84.5% |
| QLD1 | $404.02 | $139.51 | $1,812.89 | 77.7% |
| SA1 | $1,085.51 | $744.26 | $3,265.88 | 66.8% |
| TAS1 | $284.57 | $190.42 | $1,517.42 | 81.2% |
| **Overall** | $491.63 | $251.96 | $2,163.41 | **77.28%** |

**Result: confirmed, all regions exceed the 50% threshold.** Independently re-verified under genuine outcome-based error: 77.32% overall (essentially unchanged from 77.28%).

---

## 3. H3 — Horizon effects

**Hypothesis:** forecast error differs significantly between the P5 and P30 pre-dispatch horizons.

Primary pre-registered test (t-test, overall NEM): **p = 0.9155 — not significant.** *(This is the figure from an independent, direct re-verification of the primary test, run specifically to confirm this result and reproduced identically on repeat; an earlier value of p = 0.9374 appears in an intermediate sensitivity-analysis log and is superseded by this re-verified figure.)* Secondary Wilcoxon test: p = 0.0123 (significant), but only 1 of 5 regions individually significant, and a secondary check's significance does not override a null primary result under standard pre-registration practice. **H3 is accepted as a pre-registered null result.**

**Post-hoc exploratory finding:** a full horizon sweep (P30 through P1440 minutes) reveals a universal amplification jump between the P30 and P60 horizons in all 5 regions:

| Region | P30 ratio | P60 ratio | Jump |
|---|---|---|---|
| NSW1 | 0.63× | 6.75× | +10.8× |
| VIC1 | 2.22× | 13.86× | +6.2× |
| QLD1 | 5.03× | 10.50× | +2.1× |
| SA1 | 3.08× | 10.28× | +3.3× |
| TAS1 | 1.62× | 7.40× | +4.6× |

**Interpretation:** the null result on P5 vs. P30 reflects both horizons sitting inside a shared "convergence zone" close to dispatch; the real onset of forecast unreliability occurs 30–60 minutes before dispatch, confirmed consistently across every region. This is an exploratory finding, not part of the pre-registered hypothesis set.

---

## 4. Classifier relabelling: why and what changed

The original classifier's target was $y = 1$ if settled price ≥ AUD 300/MWh — a price-level indicator, not a reliability measure, since a correctly-forecast extreme price is not a forecast failure. Following anonymous pre-submission review, the classifier was rebuilt against a genuine reliability label:

$$Y^{new} = 1 \text{ if } |f^{(1)} - p_{actual}| > \text{AUD } 300$$

i.e. whether the earliest available forecast diverged from the true settled price by more than the threshold, regardless of whether the price itself was extreme.

**Direct empirical evidence the relabelling was necessary:** 69.5% of intervals originally classified "extreme" under the price-level label were reclassified as *reliable* under the genuine label — the original target was substantially measuring price level, not forecast failure.

| Metric | Original classifier | Relabelled classifier |
|---|---|---|
| AUC | 0.9893 | **0.9666**, 95% CI [0.9557, 0.9765] |
| F1 (at operating threshold) | 0.6207 | **0.8898** |
| Precision / Recall | 0.6081 / 0.6338 | 0.9638 / 0.8263 |
| Operating threshold θ | 0.8006 | 0.856818 |
| Top SHAP feature | Current price level (34.94%) | **Forecast revision (52.32%)** |
| Test-partition size | 15,165 | 14,645 *(reduced by P5MIN-merge coverage; see Section 12)* |

The relabelled classifier's own SHAP ranking now reflects the paper's actual claim (revision-based reliability detection), where the original classifier's ranking did not.

---

## 5. H4 — Classifier performance

**Hypothesis:** the classifier achieves F1 ≥ 0.60 on the held-out test set.

| Metric | Value | 95% CI |
|---|---|---|
| AUC | 0.9666 | [0.9557, 0.9765] |
| Average Precision | 0.8931 | — |
| F1 | 0.8898 | — |
| Precision | 0.9638 | — |
| Recall | 0.8263 | — |
| Operating threshold θ | 0.856818 | — |
| Confusion matrix | TP=452, FP=17, FN=95, TN=14,081 | — |

**Result: confirmed, F1 substantially exceeds the 0.60 criterion.** Full precision-recall and ROC data available in `results/tables/c2_23_*.csv`.

**Independently validated against true settlement price:** the classifier's outcome label was originally built using a P5MIN forecast as a proxy for the true settled price (settlement data required a separate retrieval pipeline). True DISPATCHPRICE was subsequently retrieved for the full test partition and compared directly:

| | P5MIN-based label | True-price-based label |
|---|---|---|
| Label agreement | — | **99.58%** |
| AUC | 0.9667 | 0.9653 |
| F1 | 0.8908 | 0.8939 |

The proxy is confirmed adequate; no results depend materially on this choice.

---

## 6. Feature importance (SHAP) and ablation

**Full SHAP ranking, relabelled classifier (PermutationExplainer, n=500):**

| Rank | Feature | Contribution | Direction |
|---|---|---|---|
| 1 | Forecast revision | 52.32% | positive |
| 2 | Current price level | 18.04% | positive |
| 3 | Rolling 30-min max price | 7.41% | positive |
| 4 | 30-min price change | 5.32% | positive |
| 5 | Rolling 30-min mean price | 4.59% | positive |
| 6 | Hour of day | 4.22% | negative |
| 7 | 60-min price change | 3.94% | positive |
| 8 | Day of week | 2.02% | positive |
| 9 | Consecutive high-price count | 1.71% | negative |
| 10 | Is peak hour | 0.43% | positive |

Top 2 features combined: **70.36%** (original classifier: 65.64%).

**Ablation (drop-one) study, relabelled classifier:**

| Feature removed | F1 after removal | % loss |
|---|---|---|
| (none — full model) | 0.8898 | — |
| Forecast revision | 0.7381 | 17.0% |
| Current price level | 0.8781 | 1.3% |

The relabelled classifier is considerably more robust to single-feature removal than the original (which lost 90.9% of F1 when its top feature was removed) — a genuinely more resilient model, drawing meaningful secondary support from multiple features rather than depending almost entirely on one.

---

## 7. H5 — Dispatch agent comparison and economic value

**Hypothesis:** a reliability-conditioned dispatch agent experiences at least 20% fewer silent failures than a naive baseline.

The final agent comparison uses matched information timing (both agents decide on a ~5-minute-lead forecast, removing the information-freshness confound identified in peer review) and complete battery economics (discharge and charging degradation costs, using a validated convex degradation model).

| Agent | Gross revenue | Degradation cost | Net revenue |
|---|---|---|---|
| P5-timed baseline (no signal) | $277,516.06 | $106,580.26 | $170,935.79 |
| + charging economics | — | — | **$187,603.24** |
| P5-timed + FRI (relabelled) | $286,457.81 | $25,275.53 | $261,182.28 |
| + charging economics | — | — | **$299,614.46** |

**Complete net-revenue advantage: AUD 112,011.22 (+59.7%).**

**Silent-failure counts (sign-aware, i.e. only over-forecasts count as genuine failures):** both agents reduce from 5 to 3 once profitable under-forecasts are correctly excluded; the reduction is identical for both agents, so relative comparisons are unaffected by this correction.

**Sensitivity to battery replacement cost (R) — original classifier, not yet re-run for the relabelled classifier:** run once, on the original classifier's discharge-only agent comparison, before the relabelling. The advantage was positive and grew monotonically across a 4× range of R, indicating the mechanism (shallower cycling under graded scaling is disproportionately cheaper under a convex degradation cost) is not an artefact of the specific R value chosen. This check has not been repeated on the relabelled classifier's complete-economics figures above, and the exact percentages below should not be read as describing the 59.7% headline result:

| R scenario | Baseline net (original classifier, discharge-only) | FRI net (original classifier, discharge-only) | Advantage |
|---|---|---|---|
| Half (AUD 21M) | $228,313 | $279,183 | 22.3% |
| Baseline (AUD 42M) | $174,163 | $267,178 | 53.4% |
| Double (AUD 84M) | $65,864 | $243,167 | 269.2% |

---

## 8. Signal attribution: is the value genuinely from the reliability signal?

A signal-free control agent was built — identical timing and trigger logic, but scaling every dispatch at a constant 0.75 factor regardless of the reliability score — to test whether FRI's advantage is genuinely attributable to the signal, or merely to conservative scaling in general.

| Agent | Complete net revenue | Advantage over baseline |
|---|---|---|
| P5-timed baseline (no scaling) | AUD 187,603.24 | — |
| Signal-free control (constant 0.75×) | AUD 226,740.88 | AUD 39,137.64 (20.9%) |
| P5-timed + FRI (informed scaling) | AUD 299,614.46 | AUD 112,011.22 (59.7%) |

**Signal-attributable fraction: 65.1%** of FRI's total advantage is not captured by the signal-free control — the majority of the economic benefit is genuinely attributable to the reliability signal, not conservative scaling alone.

**Related methodological check (feature/label circularity):** a specific reviewer concern raised whether the revision feature might implicitly contain the classifier's own label (since true settlement was confirmed close to the final pre-dispatch run). Direct inspection of the feature-construction code confirmed the revision feature is built exclusively from runs issued 30–60 minutes before dispatch, deliberately and verifiably excluding the final, near-dispatch run — the concern does not apply to the classifier actually used in this study.

---

## 9. H6 — Dispatch–confidence correlation

**Hypothesis:** dispatch magnitude is positively, significantly correlated with the reliability confidence score.

| Metric | Value |
|---|---|
| Pearson r | **0.3223** |
| 95% CI | [0.2639, 0.3783] |
| r² | 0.104 |
| Dispatched intervals | 944 |

**Result: confirmed.** Mean dispatch by band: HIGH = 23.25 MW (n=8), LOW = 5.15 MW (n=936); no intervals were dispatched from the MEDIUM band under the relabelled classifier, which cleanly resolves an earlier non-monotonicity concern (an intermediate finding under the original classifier where MEDIUM-band dispatch briefly exceeded HIGH-band dispatch).

---

## 10. H7 — Revenue comparison

**Hypothesis:** the reliability-conditioned agent achieves at least 15% higher raw revenue than the baseline.

| Metric | Value |
|---|---|
| Revenue change | **−1.55%**, not significant |
| Baseline extreme-regime revenue | $6,612.47 |
| FRI extreme-regime revenue | $7,545.87 |
| Baseline normal-regime revenue | $252,330.09 |
| FRI normal-regime revenue | $247,385.25 |

**Result: null, honestly reported.** Notably, under the relabelled classifier FRI's extreme-regime revenue exceeds baseline's, a directionally favourable shift versus the original classifier.

**Statistical power context — original classifier, not yet re-run for the relabelled classifier's 14,645-row test partition:** a power analysis run on the original classifier's test partition (n=142 extreme events, out of 15,165 total rows) found the test structurally underpowered: achieved power 5.3%, with a sample size of 47,090 required for conventional 80% power. This analysis has not been recomputed on the relabelled classifier's smaller, 14,645-row test partition, whose exact extreme-event count differs; the underlying conclusion (the test is underpowered given the available extreme-event sample) is expected to still hold, but the specific figures above should be read as the original classifier's numbers, not a precise recomputation for the −1.55% result shown.

---

## 11. H8 — Cross-market transfer

**Hypothesis:** classifier F1 on a validation market is within 0.15 of NEM F1, with no retraining.

| Market | F1 | AUC | Result |
|---|---|---|---|
| SA1 (same-market, cross-region) | 0.8577 | 0.9673 | **Pass** |
| New Zealand | 0.0787 | 0.8399 | Fail |
| Great Britain (original threshold) | 0.0778 | 0.9800 | Fail |
| Great Britain (harmonised threshold) | 0.0206 | 0.8252 | Fail |

**Two mechanistically distinct transfer boundaries were identified:**

**Great Britain — structural.** GB's market does not publish the pre-dispatch revision sequences the classifier's dominant feature (52.32% of SHAP contribution) depends on; the feature is zero-filled. Confirmed by comparing a full-feature model against a revision-excluded ("FRI-Lite") variant under an identical, harmonised label — this specific comparison was run on the **original classifier**:

| Model variant | GB F1 (original classifier, harmonised label) | Result |
|---|---|---|
| Full model (with revision) | 0.6658 | Pass |
| Revision-excluded variant | 0.3162 | Fail |

The gap (0.35) isolates the genuine, structural contribution of the missing feature under the original classifier. The relabelled classifier fails GB at both the original and harmonised thresholds (table above); harmonisation, which rescued the original classifier's GB result, does not rescue the relabelled classifier's — consistent with the same structural cause, but confirming the mechanism differs somewhat between the two classifiers and should not be assumed identical without further comparison.

**New Zealand — scale.** NZ publishes equivalent revision data, and the underlying signal is genuinely present: revision magnitude runs ~91× higher for unreliable intervals than reliable ones (2,928.57 vs. 32.04), and revision correlates with the true label at r = 0.327. However, the classifier's NEM-calibrated decision threshold does not activate at NZ's smaller absolute price scale. Label harmonisation was tested and made the result worse (F1 fell to 0.01–0.05), ruling out labelling selectivity as the explanation and confirming this is a genuine feature-scale mismatch, distinct from GB's structural boundary.

---

## 12. Robustness and diagnostic checks

| Check | Classifier basis | Result |
|---|---|---|
| Calibration (Brier score) | Relabelled | 0.0398 overall; MEDIUM/HIGH bands show real overconfidence (predicted probabilities exceed observed frequencies) — bands should be read as ordinal confidence tiers, not literal probabilities |
| Isotonic recalibration impact on dispatch bands | Original classifier | 99.4% of band assignments unaffected; the original classifier's H5-style conclusions were robust to the calibration finding. Not re-run on the relabelled classifier |
| Regularization sweep | Original classifier | All 4 tested regularised configurations underperform the original, unregularised model on the test set — the near-perfect training fit is not harmful overfitting. Not re-run on the relabelled classifier |
| Excluding June 2022 (market-suspension month) from training | Original classifier | AUC 0.9879 vs. an original-classifier baseline of 0.9893; F1 0.6642 vs. 0.6207 — performance does not depend on this anomalous period. Not re-run on the relabelled classifier |
| Wilcoxon test statistic verification | N/A (statistical methodology check) | Small W-statistics in Table 6 confirmed mathematically correct given >97% tied pairs at those sample sizes — not a computational error |
| Test-partition size note | Relabelled | 15,165 raw chronological test intervals; 14,645 after merging with the P5MIN-based outcome label used to build the genuine reliability target (missing rows fall at the 1 Jan 2023 boundary, <0.3% of data) |

---

## 13. Reproducing these results

```bash
pip install -r requirements.txt

# Quick test using included samples:
python scripts/c2_18_retrain_relabeled_full_scores.py   # loads data/samples/

# Full pipeline (requires full data download):
python scripts/c1_01_download_aemo_nem.py
# see run.sh for the complete, ordered sequence
```

The trained, relabelled classifier is included at `results/models/fri_model_relabeled.pkl`. Every figure and table in this document is generated by a script in `scripts/`, numbered by pipeline stage: `c1_` (preprocessing), `c2_` (classifier), `c3_` (dispatch agents and economics), `figure_` (all figure outputs).

---

## 14. Data and code availability

- **Dataset provenance, licensing, attribution:** [`docs/DATA_CARD.md`](DATA_CARD.md) — covers all four datasets (AEMO NEM, AEMO DISPATCHPRICE validation, GB Elexon, NZ EMI).
- **Complete deviations log:** [`docs/COMPLIANCE.md`](COMPLIANCE.md) — every departure from the pre-registered analysis plan, with rationale.
- **Full reference list:** [`docs/FRI_master_references.md`](FRI_master_references.md).
- **OSF pre-registration:** 10.17605/OSF.IO/Z89HD.
