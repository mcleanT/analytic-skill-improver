# Empirical Lessons from 3 Skill Improvements

These lessons were learned iteratively across improvements to three analysis skills:
scrna_seq (single-cell RNA-seq), bulk_rnaseq (bulk RNA-seq differential expression),
and survival_analysis (Kaplan-Meier + Cox proportional hazards).

Each lesson includes the specific evidence that taught it.

---

## 1. Prose → Code Blocks Is the Highest-Leverage Change

**Evidence**: In the scrna_seq baseline (N=5 runs), agents produced 5 different
variable encoding approaches when the skill said "encode categorical variables."
After adding a code block showing `df["x_bin"] = (df["x"] == "yes").astype(int)`,
all 3 v2 runs produced identical encodings.

In survival_analysis, baseline runs diverged on whether to log-transform continuous
covariates. Adding "DO NOT log-transform unless there is a specific reason" as a
code comment eliminated this entirely.

**Why it works**: LLMs treat prose as suggestions and code as instructions. A prose
instruction like "normalize the data" has dozens of valid interpretations. A code
block like `sc.pp.normalize_total(adata, target_sum=1e4)` has exactly one.

**Implication**: Every critical protocol step in a skill should have a fenced Python
code block. Prose can accompany it for explanation, but the code block is what agents
will follow. Budget ~60% of skill improvement time on converting prose to code blocks.

---

## 2. Dependency Installation Can Be the Single Largest Improvement

**Evidence**:
- Installing pydeseq2 for bulk_rnaseq: DE gene count went from 257 (OLS fallback)
  to 655 (proper negative binomial) — a 155% improvement.
- Installing leidenalg for scrna_seq: unlocked the Leiden clustering algorithm,
  which produces more biologically meaningful communities than Louvain on weighted graphs.
- Installing lifelines for survival_analysis: C-statistic went from returning None
  in 2/3 runs to 0.688 in 3/3 runs.

**Why it works**: Many skills are written assuming packages are available but guard
with "if available, use X; otherwise fall back to Y." The fallback is always worse.
When the dependency is actually installed, the skill silently upgrades.

**Implication**: Step 1 (Dependency Scan) should always run first. It's the cheapest
step (~$0) with potentially the largest impact.

---

## 3. Reference Comparison Identifies WHY, Not Just WHERE

**Evidence**:
- scrna_seq benchmarks showed low ARI (0.629) but didn't explain why. Comparing
  against the scanpy PBMC3K tutorial revealed: missing regress_out + scale preprocessing,
  wrong neighbor graph (binary vs weighted), wrong MT% threshold (20% vs 5%), wrong
  PCA dimensions.
- bulk_rnaseq benchmarks showed only 4/8 known DE genes recovered. Reference comparison
  against the Himes et al. 2014 analysis revealed: missing paired design formula
  (~ donor + condition), no LFC shrinkage, no PCA quality check.

**Why it works**: Metrics tell you "the score is low." Reference comparison tells you
"the score is low because you're using binary instead of weighted neighbor graphs, and
the reference analysis gets 8 clusters with weighted graphs while you get 6."

**Implication**: Step 6 (Reference Comparison) is the highest-value diagnostic step.
Always dispatch a subagent specifically to compare your best run against the canonical
published analysis for the reference dataset.

---

## 4. Literature Recommendations Must Be Validated Empirically

**Evidence**: The scanpy PBMC3K tutorial applies `sc.pp.regress_out(adata, ['total_counts', 'pct_counts_mt'])`
followed by `sc.pp.scale(adata)`. We added both to the scrna_seq skill based on
literature recommendation. Result: ARI dropped from 0.87 to 0.49.

The problem: regress_out removes variation correlated with total counts and MT%. On
single-sample PBMC data with no batch effects, this removes real biological signal
(T cells have different total counts than B cells). It's appropriate for multi-batch
data where technical variation dominates, not for single-sample data.

**Why it works**: Best practices are calibrated for common scenarios. Your specific
dataset may violate the assumptions that make those practices "best." The only way
to know is to benchmark before and after.

**Implication**: Never keep a literature-recommended change without benchmarking it.
The keep/revert decision in Step 9 must be data-driven, not authority-driven.

---

## 5. Deterministic Pipelines Don't Need Phase 2

**Evidence**:
- bulk_rnaseq: All 3 baseline runs produced identical DE gene lists (same padj values,
  same fold changes, same gene rankings). The only differences were in prose
  interpretation sections, not statistical outputs.
- survival_analysis: All 3 v2 runs produced identical Cox HRs, log-rank p-values,
  and KM curves once code blocks standardized the variable encoding.

**Why it works**: Phase 2 (the benchmark loop) is designed to reduce output variance
across runs. When variance is zero (deterministic statistics with identical code),
there's nothing to reduce. The remaining improvements are toolkit capability gaps
(Bucket B items), not skill wording issues.

**Implication**: After the baseline benchmark (Step 5), check stochasticity immediately.
If outputs are identical across N runs, skip Phase 2 and go to post-convergence.
This saves ~$5-10 per skill in unnecessary benchmark runs.

---

## 6. Cross-Validation Catches Overfit

**Evidence**:
- bulk_rnaseq: Improvements validated on Airway (human) also worked on Pasilla
  (Drosophila) — the blocking_factors feature generalized from donor→library_type.
- survival_analysis: Improvements validated on GBSG2 (breast cancer) also worked on
  lung cancer — C-statistic 0.651, all protocol steps completed, consistent results.

**Why it works**: A skill improvement that only helps on one dataset is dataset-specific
tuning, not a real methodology improvement. The backup dataset (different organism,
tissue, or platform) catches this.

**Implication**: Cross-validation (Step 11) is mandatory, not optional. If the backup
dataset crashes or produces dramatically worse results, the improvement is rejected.

---

## 7. Agents Hallucinate Function Names (~10-15% of runs)

**Evidence**: Across all benchmarks, ~10-15% of analysis scripts contained function
calls that don't exist in the toolkit: `size_factor_normalize` (doesn't exist),
`log2_cpm` (doesn't exist), `perform_clustering` (doesn't exist).

This happened even when the skill had correct code blocks showing the real function names.

**Why it works**: LLMs have strong priors about what function names "should" look like
in a given domain. These priors sometimes override the explicit examples in the prompt.

**Implication**: Accept this as irreducible LLM noise. It's not a skill quality issue.
The skill auditor (Step 2) catches these at audit time, and the function audit is why
code blocks need to show EXACT function names, not approximate ones.

---

## 8. Agents Hallucinate Keyword Arguments (~30% of runs)

**Evidence**:
- `group_summary(df, groupby="status")` — the `groupby` parameter doesn't exist;
  the actual API uses positional args `value_col` and `group_col`.
- `roc_analysis(labels=event_status, scores=biomarker_values)` — the function uses
  positional args `y_true` and `y_score`, not keyword args.
- `finding(name="...", stat=..., biological_interpretation=...)` — none of these
  keyword arguments exist.

This is 2-3x more frequent than function name hallucination.

**Why it works**: LLMs infer keyword argument names from context and convention.
`groupby=` feels natural for a group summary function. `labels=` and `scores=` feel
natural for an ROC function. The LLM generates plausible-sounding kwargs that happen
to be wrong.

**Implication**: Code blocks must show the EXACT call syntax — positional vs keyword
args, in the right order. Just listing the function name is insufficient. This is the
second-most-common error type after prose divergence, and it's entirely preventable
with explicit code blocks.

---

## 9. Literature Findings Must Be Triaged into 3 Buckets

**Evidence**: During survival_analysis improvement, the literature comparison identified
calibration plots, time-dependent AUC, RMST, multiple imputation, AFT models, and
Brier score as gaps. Without triage, these would all be treated as "things to fix in
the skill" — but most require toolkit changes that can't be done by editing the .md file.

After implementing 3-bucket triage:
- Bucket A (skill fix now): wrong API calls, missing code blocks → fixed in Phase 1
- Bucket B (toolkit upgrade): calibration plot, C-statistic fix → implemented as toolkit
  extensions, measurable improvement (C-stat: None→0.688, calibration: new capability)
- Bucket C (follow-up signpost): AFT models, competing risks → added to skill's
  "Common Follow-Up Directions" section

**Why it works**: Not all gaps are the same kind. Treating a toolkit gap as a skill
wording issue leads to workarounds that don't actually fix the problem. Treating a
follow-up direction as a required step bloats the skill with advanced methods that
aren't always applicable.

**Implication**: Step 3 (Literature Comparison) must explicitly categorize each finding
into A/B/C. Bucket B items become the toolkit development backlog (Step 12.5). Bucket C
items become the Follow-Up Signposts (Step 12). Only Bucket A items get fixed in the
current improvement round.
