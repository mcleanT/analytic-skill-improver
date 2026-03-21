# survival_analysis — Improvement Trajectory

| Metric | survival_baseline | survival_crossval | survival_v2 | v3 |
|--------|--------|--------|--------|--------|
| c_statistic | — | 0.651 (n=3) | — | 0.688 (n=3) |
| median_survival | — | — | 1807.000 (n=2) | 1807.000 (n=3) |
| n_events | 299.000 (n=3) | 150.333 ± 25.403 (n=3) | 299.000 (n=2) | 299.000 (n=3) |
| n_patients | 686.000 (n=3) | 208.000 ± 34.641 (n=3) | 686.000 (n=2) | 686.000 (n=3) |
| n_significant_covariates | — | 2.667 ± 0.577 (n=3) | 4.000 (n=2) | 4.000 (n=3) |

**survival_baseline warnings**: {'c_statistic': '3/3 returned None', 'c_index': '3/3 returned None'}

**survival_crossval warnings**: {'c_index': '3/3 returned None'}

**survival_v2 warnings**: {'c_statistic': '2/2 returned None', 'c_index': '2/2 returned None'}

**v3 warnings**: {'c_index': '3/3 returned None'}

## Deltas
