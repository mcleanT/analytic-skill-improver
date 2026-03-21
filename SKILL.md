# Skill Improver

Benchmark-driven self-improvement for analysis skills.

---

## Prerequisites

To use this skill improver, your project needs:

- **An analysis toolkit** — a Python library with a public API (functions that skills reference). This could be a stats/ML package, a domain analysis library, or any collection of reusable analysis functions.
- **Skills as markdown files** — analysis protocol documents that describe how to perform a class of analysis using your toolkit. These live in a directory configured in `config.yaml` as `skill_dir`.
- **A test suite** for the toolkit — so toolkit extensions can be validated before being used by skills.
- **Python 3.10+** with PyYAML installed (`pip install pyyaml`).
- **A `config.yaml`** at the project root (see below for the schema).

### config.yaml Schema

```yaml
# Paths (relative to project root unless absolute)
skill_dir: prompts/skills          # Directory containing *.md skill files
toolkit_module: src/mypackage/analytics  # Root of the analysis toolkit
benchmark_dir: benchmarks          # Directory for benchmark runs, checklists, and reports
test_command: "python -m pytest tests/test_analytics/ -v --tb=short"

# Dependencies to check (Step 1)
dependencies:
  - numpy
  - pandas
  - scipy
  - statsmodels
  # add all packages your skills reference

# Per-skill dataset and metric configuration (Step 5, Step 8, Step 11)
skills:
  my_skill_name:
    primary_dataset:
      path: path/to/dataset.csv        # or a loader expression
      description: "Human PBMC 10x 3K cells"
      notes: "Standard scRNA-seq benchmark"
    backup_dataset:
      path: path/to/backup.csv
      description: "Mouse cortex dataset"
      notes: "Cross-species cross-validation"
    primary_metric: ari                # The key in summary.json to track
    reference_value: 0.87              # Published reference for comparison
    stochastic: true                   # Whether Phase 2 runs (false = deterministic)
```

---

## Trigger

"improve skill {name}", "self-improve", "optimize skill", "benchmark and improve"

---

## The Process

```
PHASE 1 — Free Wins (no benchmark runs, always run first)
│
├─ 1. Install missing dependencies
├─ 2. Fix broken function references
├─ 3. Compare against current literature
├─ 4. Replace prose with code blocks
├─ 5. Run baseline benchmark (N=3)
│
├─ Stochastic? ──NO──→ Phase 2 adds no value. Fix remaining
│      │                gaps as Tier 2 toolkit extensions.
│     YES                Skip to post-convergence.
│      │
│  PHASE 2 — Benchmark Loop (stochastic pipelines only)
│  │
│  ├─ 6. Compare best run against reference analysis
│  ├─ 7. Diagnose and fix ONE gap
│  ├─ 8. Re-benchmark (N=3)
│  ├─ 9. Keep if improved, revert if not
│  └─ 10. Repeat until plateau (2 rounds < 0.01 improvement)
│
POST-CONVERGENCE
├─ 11. Cross-validate on backup dataset
├─ 12. Add follow-up signposts (from Bucket C)
├─ 12.5. Log toolkit upgrades (from Bucket B)
└─ 13. Report results
```

---

## Phase 1 — Free Wins

Run all of these before spending compute on benchmarks. Order is by value
(highest-impact first), not by cost.

### Automated Tools

The following scripts in `{benchmark_dir}/` support the improvement process:

| Tool | Command | Purpose |
|------|---------|---------|
| **Prompt generator** | `python {benchmark_dir}/dispatch_benchmark.py {skill} --version {v} --n-runs 3` | Generate standardized benchmark subagent prompts from template |
| **Checklist evaluator** | `python {benchmark_dir}/evaluate_checklist.py {skill} --all` | Score protocol adherence of benchmark scripts against YAML checklist |
| **Version comparator** | `python {benchmark_dir}/compare_versions.py {skill}` | Extract metrics from summary.json across versions, produce trajectory report |

Use these instead of manual inspection. Dispatch benchmark subagents using the generated prompts for consistency.

### Step 1: Dependency Scan and Install

The single highest-leverage action for deterministic pipelines. Read the
`dependencies` list from `config.yaml` and check each package:

```bash
python -c "
import yaml
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)
packages = cfg.get('dependencies', [])
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

Verify every function called in the skill's code blocks exists with the correct signature.
`scripts/skill_auditor.py` (bundled with this repo) performs this check. It needs to know
which toolkit module to audit against — configure `toolkit_module` in `config.yaml`.

```python
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'src')
from scripts.skill_auditor import audit_skill_file
from pathlib import Path
import yaml

with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

skill_dir = cfg['skill_dir']
findings = audit_skill_file(Path(f'{skill_dir}/{skill_name}.md'))
for f in findings:
    print(f'  [{f.severity}] {f.function_name}: {f.message}')
```

Fix every error: wrong param names, wrong return types, missing imports.

### Step 3: Literature Comparison

Search for current best practices (2024-2025) in the skill's analysis domain.
Use `research-lookup` skill or web search. Compare each protocol step against
field standards.

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

For every critical step in the skill that is currently prose-only:
- Add a fenced `python` code block with the exact function calls and parameters
- Add `# MANDATORY` comments on steps that must not be skipped
- Document your project's reporting API with EXACT function signatures

The #1 cause of agent errors is hallucinated keyword arguments. Show the exact
call syntax — positional vs keyword args, return types. For example:

```python
# EXAMPLE — replace with your project's actual reporting API:
#
# If your toolkit has a findings/reporting API, document it here with EXACT
# call syntax, not just function names. Agents will hallucinate keyword args
# unless every argument is shown explicitly.
#
# stat_result("test name", statistic=0.0, p_value=0.001, effect_size=2.5)
# finding("description", [sr], confidence_level=0.9)
# findings_to_json([f1, f2])   # returns STRING — write to file yourself
```

Adapt this block to match your toolkit's actual reporting API exactly.

### Step 5: Baseline Benchmark

Run N=3 parallel subagent analyses on a reference dataset to establish baseline
quality. Each subagent independently writes and executes an analysis script
following the skill protocol.

**Reference dataset selection**: Configure reference datasets per skill in
`config.yaml`. Each skill entry needs:
- `primary_dataset`: path, description, and notes
- `backup_dataset`: for cross-validation (different organism, tissue, or platform)
- `primary_metric`: the domain-specific quality metric name (key in `summary.json`)
- `reference_value`: published reference value for comparison
- `stochastic`: `true` or `false` (determines whether Phase 2 runs)

If no pre-seeded dataset exists, search for one: small (<5K samples), public,
with a published reference analysis providing ground truth.

**Stochasticity check**: Are outputs identical across the 3 runs?
- **YES** (deterministic pipelines like bulk DE, survival Cox): Phase 2 adds
  no value — replicability is trivially perfect. Remaining gaps are toolkit
  capability issues (Tier 2) or biological. Skip to post-convergence.
- **NO** (stochastic pipelines like clustering, trajectory, dimensionality
  reduction): Proceed to Phase 2.

**Generate benchmark prompts:**
```bash
python {benchmark_dir}/dispatch_benchmark.py {skill_name} --version baseline --n-runs 3
```
Dispatch each generated prompt as a sonnet subagent. After all complete, evaluate:
```bash
python {benchmark_dir}/evaluate_checklist.py {skill_name} --all
python {benchmark_dir}/compare_versions.py {skill_name}
```

---

## Phase 2 — Benchmark Loop

Only for stochastic pipelines where outputs vary across runs.

### Step 6: Reference Comparison (HIGHEST VALUE STEP)

Compare the best benchmark run against the published canonical analysis for
the reference dataset. This identifies WHY outputs diverge, not just WHERE.

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
# MANDATORY: Run full toolkit test suite to catch regressions
# Use the test_command from config.yaml, e.g.:
python -m pytest tests/test_analytics/ -v --tb=short
```
Do not proceed until all tests pass.

### Step 8: Re-benchmark (N=3)

Run 3 parallel subagents with the fixed skill. Compare against previous round
using the primary metric configured for this skill in `config.yaml`.

**Generate prompts and evaluate:**
```bash
python {benchmark_dir}/dispatch_benchmark.py {skill_name} --version {round_N} --n-runs 3
# After runs complete:
python {benchmark_dir}/evaluate_checklist.py {skill_name} --all
python {benchmark_dir}/compare_versions.py {skill_name}
```

The primary metric for each skill is defined in `config.yaml` under
`skills.{skill_name}.primary_metric`. Compare the current run's value in
`summary.json` against `skills.{skill_name}.reference_value` to measure headroom.

### Step 9: Keep or Revert

- **Keep** if the primary metric improved
- **Revert** if it regressed (e.g., regress_out dropped ARI from 0.87 to 0.49)
- Revert is manual: undo the edit. No git machinery needed for interactive sessions.

### Step 10: Check Convergence (Diminishing Returns)

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
   items. Check `{benchmark_dir}/toolkit_upgrades/{skill}.md` for remaining B items.
   Example: 8 items identified, 5 resolved → ratio = 3/8 = 0.375

2. **gap_ratio** — Run the checklist evaluator:
   ```bash
   python {benchmark_dir}/evaluate_checklist.py {skill_name} --all
   ```
   Use `1 - mean_adherence_score`. Example: 92% adherence → gap = 0.08

3. **metric_headroom** — Compare current primary metric against the published
   reference value for the dataset. Run:
   ```bash
   python {benchmark_dir}/compare_versions.py {skill_name}
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
`{benchmark_dir}/toolkit_upgrades/{skill_name}.md` documenting:

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
python {benchmark_dir}/compare_versions.py {skill_name}
```
This produces `{benchmark_dir}/runs/{skill_name}/improvement_trajectory.md` with the full metric comparison table.

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

1. Read `config.yaml` to get the full list of skills under `skills:` and sort
   them by expected value (stochastic skills first — they benefit most from
   the benchmark loop).
2. For each skill: run Phase 1 → baseline → stochasticity check →
   Phase 2 if needed → cross-validate → report
3. Commit each skill's improvements on a dedicated branch
4. After all skills: merge to staging branch for human review

**Cost estimate**: ~$10-15 per skill (Phase 1 + 3 rounds × 3 runs).
Actual total depends on the number of skills in `config.yaml`.
