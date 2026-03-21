---
name: skill-improver
description: "Improve analysis skills through benchmark-driven iteration. Audits skill against literature/codebase, installs missing dependencies, benchmarks on reference datasets, compares against published analyses, and fixes gaps. Use when the user says 'improve skill', 'self-improve', 'optimize skill', 'benchmark and improve'."
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, WebFetch, WebSearch]
---

# Skill Improver

Benchmark-driven self-improvement for analysis skills in `prompts/skills/*.md`.

## Trigger

"improve skill {name}", "self-improve", "optimize skill", "benchmark and improve"

---

## The Process

```
PHASE 1 — Free Wins (no benchmark runs, always run first)
│
├─ 1.   Install missing dependencies
├─ 1.5  Generate checklist YAML ──────────── ⚡ checklist-generator
├─ 2.   Fix broken function references
├─ 3.   Compare against current literature ─ ⚡ skill-improver-triage
├─ 4.   Replace prose with code blocks ───── ⚡ skill-editor
├─ 5.   Run baseline benchmark (N=3)
│
├─ Stochastic? ──NO──→ Phase 2 adds no value. Fix remaining
│      │                gaps as Tier 2 toolkit extensions.
│     YES                Skip to post-convergence.
│      │
│  PHASE 2 — Benchmark Loop (stochastic pipelines only)
│  │
│  ├─ 6.  Compare best run vs reference ──── ⚡ skill-gap-analyzer
│  ├─ 7.  Diagnose and fix ONE gap ────────── ⚡ skill-editor
│  ├─ 8.  Re-benchmark (N=3)
│  ├─ 9.  Keep if improved, revert if not
│  └─ 10. Check convergence ─────────────── ⚡ convergence-checker
│
POST-CONVERGENCE
├─ 11.   Cross-validate on backup dataset
├─ 12.   Add follow-up signposts (from Bucket C)
├─ 12.5. Log toolkit upgrades (from Bucket B)
├─ 13.   Report results
└─ 13.5. Cross-skill consistency check ──── ⚡ skill-include-propagator
```

---

## Sub-Skills

Six specialized skills automate the manual decision gates. Each is invoked
at its marked step (⚡ in the process diagram). They can also be triggered
independently outside the improvement loop.

| Skill | Step | Trigger phrase | What it does |
|-------|------|---------------|-------------|
| **checklist-generator** | 1.5 | "generate checklist" | Creates YAML adherence checklist from skill protocol |
| **skill-improver-triage** | 3 | "triage findings" | Sorts literature findings into A/B/C buckets |
| **skill-editor** | 4, 7 | "edit skill" | Proposes + applies skill .md edits from audit/gap findings |
| **skill-gap-analyzer** | 6 | "analyze gaps" | Structured reference comparison with gap classification |
| **convergence-checker** | 10 | "check convergence" | Computes continue_value, recommends STOP/CONTINUE |
| **skill-include-propagator** | 13.5 | "propagate includes" | Batch-adds missing `{{include}}` markers |

---

## Phase 1 — Free Wins

Run all of these before spending compute on benchmarks. Order is by value
(highest-impact first), not by cost.

### Automated Tools

The following scripts in `benchmarks/` support the improvement process:

| Tool | Command | Purpose |
|------|---------|---------|
| **Prompt generator** | `python benchmarks/dispatch_benchmark.py {skill} --version {v} --n-runs 3` | Generate standardized benchmark subagent prompts from template |
| **Checklist evaluator** | `python benchmarks/evaluate_checklist.py {skill} --all` | Score protocol adherence of benchmark scripts against YAML checklist |
| **Version comparator** | `python benchmarks/compare_versions.py {skill}` | Extract metrics from summary.json across versions, produce trajectory report |

Use these instead of manual inspection. Dispatch benchmark subagents using the generated prompts for consistency.

### Step 1: Dependency Scan and Install

The single highest-leverage action for deterministic pipelines. Check whether
packages the skill references are actually importable.

> **If no checklist exists** for this skill (`benchmarks/skill_checklists/{skill}.yaml`),
> run the **checklist-generator** sub-skill now (Step 1.5) before proceeding.
> Without a checklist, Steps 5/8 cannot score adherence.

Check whether packages the skill references are actually importable:

```bash
python -c "
packages = ['pydeseq2', 'scanpy', 'anndata', 'leidenalg', 'igraph',
            'scrublet', 'scvelo', 'cellrank', 'lifelines', 'squidpy']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'  OK  {pkg}')
    except ImportError:
        print(f'  MISSING  {pkg}')
"
```

For each missing package the skill references:
1. `pip install {package}`
2. Update the skill: remove "if available" guards, promote from fallback to primary
3. Add to the skill's import block

**Example**: Installing pydeseq2 improved bulk RNA-seq DE gene count by 155% (257→655).

### Step 2: Function Audit

Verify every function called in the skill's code blocks exists with the correct signature:

```python
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'src')
from benchmarks.skill_auditor import audit_skill_file
from pathlib import Path

findings = audit_skill_file(Path('prompts/skills/{skill_name}.md'))
for f in findings:
    print(f'  [{f.severity}] {f.function_name}: {f.message}')
```

Fix every error: wrong param names (`n_bootstrap` → `n_boot`), wrong return types
(`fig, ax = plot_heatmap()` → `ax = plot_heatmap()`), missing imports.

### Step 3: Literature Comparison

Search for current best practices (2024-2025) in the skill's analysis domain.
Use `research-lookup` skill or web search. Compare each protocol step against
field standards.

> **⚡ Sub-skill**: After gathering literature findings, invoke the
> **skill-improver-triage** skill ("triage findings") to automatically sort
> them into A/B/C buckets. Review the triage output and adjust if needed.

**Categorize each finding into one of three buckets:**

| Bucket | Description | Action | Example |
|--------|-------------|--------|---------|
| **A: Skill fix (now)** | Wrong defaults, missing steps, outdated methods | Fix in Phase 1 Step 4 | MT% 20% → 5%; missing PCA step |
| **B: Toolkit upgrade** | Literature requires a capability the toolkit lacks | Log for implementation, add workaround to skill if possible | Calibration plots, RMST regression, time-dependent AUC |
| **C: Follow-up signpost** | Advanced method beyond the core protocol scope | Add to skill's "Common Follow-Up Directions" section in Step 12 | AFT models, competing risks, decision curve analysis |

Flag Bucket A items:
- Outdated methods (e.g., log1p when scTransform is standard)
- Missing steps (e.g., no batch correction, no doublet detection)
- Wrong defaults (e.g., MT% 20% when 5% is standard for PBMCs)
- Missing LFC shrinkage, filterByExpr, or equivalent modern approaches

Flag Bucket B items (toolkit upgrades):
- Functions the skill needs but the toolkit doesn't provide
- Existing toolkit functions that need new parameters
- External package features that should be wrapped as toolkit functions

Flag Bucket C items (follow-up directions):
- Advanced methods beyond the core protocol but valuable for downstream analysis
- Methods the literature recommends that require specialized data or context
- Emerging techniques (2024-2025) not yet standard but worth mentioning

**Bucket B items get logged in Step 12.5 (post-convergence) as toolkit upgrade
tickets. Bucket C items become the Follow-Up Signposts in Step 12.**

### Step 4: Convert Prose to Code Blocks

**This is the core lesson from benchmarking**: prose guidance gets interpreted
differently by every agent. Code blocks are followed identically.

> **⚡ Sub-skill**: Use the **skill-editor** skill ("edit skill") to propose
> prose→code conversions. It verifies every function signature against the
> actual toolkit source before proposing changes.

For every critical step in the skill that is currently prose-only:
- Add a fenced `python` code block with the exact function calls and parameters
- Add `# MANDATORY` comments on steps that must not be skipped
- Include the `finding()` / `stat_result()` / `findings_to_json()` API with
  exact signatures (every benchmark run gets these wrong without documentation)

```python
# finding() API (EXACT — do not deviate):
sr = stat_result("test name", statistic=0.0, p_value=0.001, effect_size=2.5)
f = finding("description of result", [sr], confidence_level=0.9)
json_str = findings_to_json([f1, f2])  # returns STRING, write to file yourself
with open('findings.json', 'w') as fh:
    fh.write(json_str)
```

### Step 5: Baseline Benchmark

Run N=3 parallel subagent analyses on a reference dataset to establish baseline
quality. Each subagent independently writes and executes an analysis script
following the skill protocol.

**Reference dataset selection** (use pre-seeded candidates):

| Skill | Dataset | Source |
|-------|---------|--------|
| scrna_seq | PBMC 3K | scanpy.datasets.pbmc3k() |
| bulk_rnaseq | Airway | GEO GSE52778 / bioconnector mirror |
| survival_analysis | GBSG2 | sklearn / TH.data |
| clustering_analysis | Iris / Wine | sklearn.datasets |
| spatial_analysis | Mouse brain Visium | squidpy.datasets |
| timeseries | Airline passengers | seaborn / statsmodels |

If no pre-seeded dataset exists, search for one: small (<5K samples), public,
with a published reference analysis providing ground truth.

**Stochasticity check**: Are outputs identical across the 3 runs?
- **YES** (bulk DE, survival Cox): The pipeline is deterministic. Phase 2 adds
  no value — replicability is trivially perfect. Remaining gaps are toolkit
  capability issues (Tier 2) or biological. Skip to post-convergence.
- **NO** (clustering, trajectory, dimensionality reduction): Proceed to Phase 2.

**Generate benchmark prompts:**
```bash
python benchmarks/dispatch_benchmark.py {skill_name} --version baseline --n-runs 3
```
Dispatch each generated prompt as a sonnet subagent. After all complete, evaluate:
```bash
python benchmarks/evaluate_checklist.py {skill_name} --all
python benchmarks/compare_versions.py {skill_name}
```

---

## Phase 2 — Benchmark Loop

Only for stochastic pipelines where outputs vary across runs.

### Step 6: Reference Comparison (HIGHEST VALUE STEP)

Compare the best benchmark run against the published canonical analysis for
the reference dataset. This identifies WHY outputs diverge, not just WHERE.

> **⚡ Sub-skill**: Invoke the **skill-gap-analyzer** skill ("analyze gaps")
> to produce a structured gap report with impact ratings (CRITICAL/HIGH/MEDIUM/LOW)
> and root cause tags (SKILL_PROSE/SKILL_MISSING/SKILL_WRONG/TOOLKIT_GAP).

**How**: Dispatch a subagent to:
1. Read the best run's `analysis_code.py` and `summary.json`
2. Research what the reference analysis does (tutorial, vignette, paper)
3. Compare step-by-step: data loading, QC, normalization, feature selection,
   clustering/testing, visualization, interpretation
4. Report: what the reference does that we don't, and what we do that the
   reference doesn't

**This step found**:
- scrna_seq: 2 missing preprocessing steps (regress_out + scale), wrong neighbor
  graph (binary vs weighted), wrong MT% threshold (20% vs 5%), wrong PCA dims
- bulk_rnaseq: missing paired design formula (`~ donor + condition`), missing
  LFC shrinkage, no PCA produced

### Step 7: Diagnose and Fix ONE Gap

> **⚡ Sub-skill**: Use the **skill-editor** skill ("edit skill") to propose
> and apply the fix. It handles all three edit types: prose→code, fix wrong
> reference, and add missing step.

From the reference comparison, pick the highest-impact gap and fix it.

**Gap types and fix actions**:

| Gap | Example | Action |
|-----|---------|--------|
| Prose without code block | "rank markers by fold-change" | Add executable code block to skill |
| Missing dependency | pydeseq2 not installed | pip install + update skill |
| Toolkit capability gap | deseq2_de lacks blocking_factors | Extend toolkit function + tests + update skill |
| Doc-code mismatch | Skill says "applies shrinkage" but doesn't | Fix code or fix docs |
| Wrong default | MT% 20%, resolution 1.0 | Update with evidence from benchmark |
| Missing protocol step | No PCA before DE | Add MANDATORY code block |

**Toolkit extensions** (Tier 2) require:
- Backward-compatible new params (defaults preserve existing behavior)
- Test covering the new capability
- All existing tests still pass
- Separate commit before the skill change

**After ANY toolkit change** (new function, modified signature, new parameter):
```bash
# MANDATORY: Run full analytics test suite to catch regressions
python -m pytest tests/test_analytics/ -v --tb=short
```
Do not proceed until all tests pass.

### Step 8: Re-benchmark (N=3)

Run 3 parallel subagents with the fixed skill. Compare against previous round
using domain-specific metrics:

**Generate prompts and evaluate:**
```bash
python benchmarks/dispatch_benchmark.py {skill_name} --version {round_N} --n-runs 3
# After runs complete:
python benchmarks/evaluate_checklist.py {skill_name} --all
python benchmarks/compare_versions.py {skill_name}
```

| Skill Domain | Primary Metric |
|-------------|---------------|
| scrna_seq | ARI vs reference labels |
| bulk_rnaseq | Known DE gene recovery (N/total) |
| survival_analysis | C-index vs published model |
| clustering_analysis | ARI vs known labels |
| spatial_analysis | Domain ARI |

### Step 9: Keep or Revert

- **Keep** if the primary metric improved
- **Revert** if it regressed (e.g., regress_out dropped ARI from 0.87 to 0.49)
- Revert is manual: undo the edit. No git machinery needed for interactive sessions.

### Step 10: Check Convergence (Diminishing Returns)

> **⚡ Sub-skill**: Invoke the **convergence-checker** skill ("check convergence")
> to auto-compute continue_value from benchmark artifacts and get a
> STOP/CONTINUE recommendation.

Compute the **continue_value** after each round to decide whether further
investment is worthwhile:

```
continue_value = bucket_ratio × gap_ratio × metric_headroom

where:
  bucket_ratio    = bucket_items_remaining / bucket_items_total
  gap_ratio       = 1 - adherence_score
  metric_headroom = (reference_metric - current_metric) / reference_metric
```

**Stop when `continue_value < 0.05`.** This means: most literature-identified
gaps are resolved, the checklist is nearly saturated, AND the primary metric
is close to the published reference.

**How to compute each term:**

1. **bucket_ratio** — Count Bucket A + B items from Step 3. Subtract resolved
   items. Check `benchmarks/toolkit_upgrades/{skill}.md` for remaining B items.
   Example: 8 items identified, 5 resolved → ratio = 3/8 = 0.375

2. **gap_ratio** — Run the checklist evaluator:
   ```bash
   python benchmarks/evaluate_checklist.py {skill_name} --all
   ```
   Use `1 - mean_adherence_score`. Example: 92% adherence → gap = 0.08

3. **metric_headroom** — Compare current primary metric against the published
   reference value for the dataset. Run:
   ```bash
   python benchmarks/compare_versions.py {skill_name}
   ```
   Example: reference C-index = 0.70, current = 0.688 → headroom = 0.017

**Worked example (survival_analysis, end of v3):**
```
bucket_ratio    = 4/8   = 0.50  (4 Low/Medium items remain)
gap_ratio       = 1-1.0 = 0.00  (100% checklist adherence)
metric_headroom = (0.70 - 0.688) / 0.70 = 0.017

continue_value  = 0.50 × 0.00 × 0.017 = 0.000  →  STOP ✓
```
The zero gap_ratio collapses the product — even though bucket items remain,
the checklist is saturated and the metric is near-reference. Further rounds
would only address Low-priority toolkit items with diminishing returns.

**Edge cases:**
- If adherence is already 100% (gap_ratio = 0), continue_value = 0 regardless
  of other terms. This is correct: if agents follow every protocol step
  perfectly, remaining improvements are toolkit-level, not skill-level.
- If metric_headroom is 0 or negative (we match/exceed reference), stop.
- For deterministic pipelines where Phase 2 is skipped, compute continue_value
  after Phase 1 only. If > 0.05, implement Bucket B toolkit upgrades before
  stopping.

---

## Post-Convergence

### Step 11: Cross-Dataset Validation (MANDATORY)

Run N=3 analyses on the **backup dataset** (different organism, tissue, or
platform if possible). The skill must generalize — a fix that only helps on
one dataset is overfit.

| Outcome | Action |
|---------|--------|
| Backup works comparably | **ACCEPT** — improvement generalizes |
| Backup works but worse | **WARNING** — review, may be difficulty difference |
| Backup fails or crashes | **REJECT** — revert to pre-improvement skill |

**Example**: scrna_seq improved on PBMC 3K (human). Cross-validate on PBMC 10K
or a mouse dataset. bulk_rnaseq improved on Airway (human). Cross-validated on
Pasilla (Drosophila) — passed.

### Step 12: Follow-Up Signposts (sourced from literature)

Add a "Common Follow-Up Directions" section sourced from **Bucket C items**
identified during Step 3 (Literature Comparison). Each direction should:
- Name the method and when it applies
- Explain why it matters (not just what it is)
- Be actionable as a sub-hypothesis or downstream analysis direction

Target 6-9 directions. Include both established methods the core protocol
doesn't cover and emerging techniques (2024-2025). These inform sub-hypothesis
generation in the pipeline's iterative deepening loop — NOT full protocols.

**Example** (survival_analysis): Calibration assessment, time-dependent AUC,
multiple imputation, competing risks, AFT models, decision curve analysis,
nomograms, molecular subtyping, treatment × biomarker interaction.

### Step 12.5: Log Toolkit Upgrades

For each **Bucket B item** from Step 3, create an actionable entry in
`benchmarks/toolkit_upgrades/{skill_name}.md` documenting:

```markdown
## {Capability Name}

**Current state**: What the toolkit does now
**Literature standard**: What the field expects
**Proposed change**: Specific function/parameter to add
**Priority**: High (blocks core protocol) / Medium (improves quality) / Low (nice-to-have)
**Workaround**: What the skill does in the meantime (if any)
```

**Examples from completed improvements:**
- bulk_rnaseq: `deseq2_de()` lacked `blocking_factors` → toolkit extended → +380% DE genes
- survival: `cox_proportional_hazards()` C-statistic returns None → lifelines fallback added
- survival: No calibration plot function → logged as Medium priority toolkit upgrade

This step ensures toolkit gaps identified during skill improvement are not lost.
They become the backlog for targeted toolkit development.

### Step 13: Report

Summarize the improvement trajectory:

```
| Version | Primary Metric | Key Change |
|---------|---------------|------------|
| Baseline | X | — |
| + Phase 1 | Y | dependency install / code blocks |
| + Round N | Z | toolkit extension / parameter fix |
| Cross-val | W | backup dataset validation |
```

**Generate the final trajectory report:**
```bash
python benchmarks/compare_versions.py {skill_name}
```
This produces `benchmarks/runs/{skill_name}/improvement_trajectory.md` with the full metric comparison table.

### Step 13.5: Cross-Skill Consistency Check (MANDATORY)

After the trajectory report, run the consistency checker across all skills:

```bash
python scripts/check_cross_skill_consistency.py --skill-dir prompts/skills/ --shared-dir prompts/skills/_shared/
```

If inconsistencies are found:
- Review the proposed fixes
- Apply fixes that are correct (auto-fix with confirmation)
- Skip fixes that need domain-specific judgment (e.g., a skill intentionally uses a non-standard pattern marked with `# raw:`)
- Re-run the checker to verify clean

> **⚡ Sub-skill**: If missing `{{include}}` markers are detected, invoke the
> **skill-include-propagator** skill ("propagate includes") to batch-add them
> across all affected skills. It knows the correct placement rules for each
> shared block and which skills need `correction_guidance.md`.

This step prevents skill improvements from introducing drift that breaks other skills.

---

## Key Lessons (from 3 completed skill improvements)

1. **Prose → code blocks** is the highest-leverage skill wording change.
   Every step where the skill provides exact code is followed identically.
   Every step described in prose diverges across runs.

2. **Dependency installation** can be the single largest improvement.
   pydeseq2 install: +155% DE genes. leidenalg install: unlocked proper
   Leiden clustering.

3. **Reference comparison** identifies WHY, not just WHERE.
   Benchmarks show low scores. Reference comparison shows the specific
   preprocessing/statistical steps causing the gap.

4. **regress_out taught us**: literature recommendations must be validated
   empirically. The scanpy tutorial applies regress_out, but it HURT our
   benchmark (ARI 0.87→0.49 on single-sample data). Always benchmark
   before keeping a literature-recommended change.

5. **Deterministic pipelines don't need Phase 2**.
   Bulk DE produces identical outputs every run. The autoresearch
   keep/discard loop adds nothing when replicability is trivially 1.0.
   Improvements come from toolkit extensions (Tier 2), not iterative
   prompt tuning.

6. **Cross-validation catches overfit**.
   A fix that improves one dataset but fails on another is
   dataset-specific, not a real methodology improvement. Always validate
   on a second dataset before accepting.

7. **Agents hallucinate function names** (~10-15% of runs).
   Even with correct code blocks, agents occasionally invent function
   names (e.g., `size_factor_normalize`). This is irreducible LLM noise,
   not a skill quality issue. Accept it.

8. **Agents hallucinate keyword arguments** (~30% of runs).
   Even when the skill names the correct function, agents guess wrong
   kwargs (e.g., `roc_analysis(labels=..., scores=...)` instead of
   positional `y_true, y_score`). Code blocks must show the EXACT call
   with correct positional vs keyword args.

9. **Literature findings must be triaged into 3 buckets**.
   Bucket A (skill fix now), Bucket B (toolkit upgrade needed), Bucket C
   (follow-up signpost). Without this triage, toolkit gaps get noted but
   lost, and follow-up directions are invented rather than sourced from
   literature. Bucket B items become the toolkit development backlog.

---

## Running Autonomously (--all --autonomous)

For autonomous batch improvement of all skills:

1. Sort skills by expected value (stochastic skills first — they benefit
   most from the benchmark loop)
2. For each skill: run Phase 1 → baseline → stochasticity check →
   Phase 2 if needed → cross-validate → report
3. Commit each skill's improvements on a dedicated branch
4. After all skills: merge to staging branch for human review

**Cost estimate**: ~$10-15 per skill (Phase 1 + 3 rounds × 3 runs).
Full 12-skill run: ~$120-180, 6-12 hours.
