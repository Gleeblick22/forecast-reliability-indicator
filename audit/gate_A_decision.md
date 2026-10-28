# Gate A decision — 28 Oct 2026

## Decision
Paper reframed as a DETECTION + RISK-EXPOSURE paper. Economics become a boundary analysis, not a headline.

## Evidence
- Label redesign (c1_30): decision forecast f(w_t) vs settled 30-min DISPATCHPRICE; delta_Y = 300.
- Leakage: permuted-label test AUC <= 0.44 (5 repeats) -> PASS (c2_30).
- Model selected on validation: depth 2 / lr 0.1 / 300 trees (val AP 0.349 vs registered 0.301) (c2_31).
- Test (d300, 94 positives): AUC 0.891 [0.844, 0.930], AP 0.373, F1 0.482 -> H4 (F1 >= 0.60) NOT MET.
- Attribution: decision-forecast level 45%, revision-path group 35%; rev_abs alone 1.4%.
- Admin-pricing window (12-24 Jun 2022, dates to verify): 74% of fit positives; dAUC +0.004 -> primary kept (c2_32).
- Old FRI agent mapping INVERTED (c2_18/c3_39: s >= 0.75 -> x1.00). Old agents also shared one battery across 5 regions.
  Old 59.7% degradation advantage = conservative scaling, not the signal.
- Agents v2 (c3_50, c3_51): FRI vs baseline +AUD 1.6-2.2k (significant only for beta >= 1.5);
  FRI vs vol_matched n.s. for all beta; const_0.25 dominates for beta >= 1.5, no difference at beta = 1.0.
- Exposure: MWh into over-forecast (> AUD 300) intervals: baseline 65.0, vol_matched 45.2, FRI 18.8 (-71%).
- Silent failures (registered definition) = 0 for all agents -> H5 not testable.

## Open items
- Bootstrap CI for the exposure reduction.
- Verify June 2022 administered-pricing dates (AEMO report).
- Degradation parameters (M09): cite a published model.
- 60-min decision-lead sensitivity.
