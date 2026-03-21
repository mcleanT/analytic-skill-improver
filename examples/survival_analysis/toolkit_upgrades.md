# Survival Analysis — Toolkit Upgrades

Identified during skill improvement (2026-03-21). Sourced from literature comparison (Bucket B items).

## ~~Calibration Plot Function~~ DONE (2026-03-21)

**Implemented**: `plot_calibration()` added to `analytics/viz.py` and exported from `__init__.py`. Skill updated with MANDATORY code block in Step 7.

## Time-Dependent AUC

**Current state**: Only global C-index (which averages across all times)
**Literature standard**: Time-dependent AUC at clinically relevant time points (1yr, 3yr, 5yr) is more informative and increasingly required by reviewers
**Proposed change**: Add `time_dependent_auc(df, time_col, event_col, risk_scores, eval_times)` to `analytics/survival.py`
**Priority**: Medium — improves model evaluation quality
**Workaround**: Skill mentions this in Follow-Up Directions but no code path

## RMST Function

**Current state**: RMST described in prose in the skill, no toolkit function
**Literature standard**: RMST is increasingly preferred by FDA for non-proportional hazards (immuno-oncology). Computable from KM curve data we already generate.
**Proposed change**: Add `restricted_mean_survival(km_data, tau)` that computes area under KM curve up to tau, with bootstrap CI
**Priority**: Medium — valuable for PH-violated cases (common in our benchmarks: 4/8 covariates violated PH)
**Workaround**: Skill describes manual computation from KM curve arrays

## ~~C-statistic Fix in cox_proportional_hazards()~~ DONE (2026-03-21)

**Implemented**: lifelines.utils.concordance_index fallback added to `analytics/survival.py`. All 41 tests pass. Skill workaround removed (no longer needed).

## Migrate Cox PH to lifelines

**Current state**: Uses statsmodels PHReg — minimal features, no built-in diagnostics
**Literature standard**: lifelines CoxPHFitter provides: check_assumptions(), concordance, AIC, BIC, log-likelihood, partial residuals, baseline hazard, predict_survival_function, plot_partial_effects
**Proposed change**: Rewrite `cox_proportional_hazards()` to use lifelines CoxPHFitter internally, keep same return signature
**Priority**: Medium — would fix C-statistic bug, add diagnostics, improve AFT model support path
**Workaround**: Current statsmodels backend works for core functionality

## Brier Score

**Current state**: No proper scoring rule for survival models
**Literature standard**: Brier score combines discrimination and calibration into a single metric, decomposable into reliability + resolution + uncertainty
**Proposed change**: Add `brier_score(predicted_probs, observed_events, eval_time)` to `analytics/survival.py`
**Priority**: Low — nice-to-have for model comparison
**Workaround**: None
