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

## CLI Options

```
--skill <name>       Single skill to improve
--all                Improve all skills in {skill_dir}/ sequentially
--autonomous         No human review between rounds
--max-rounds N       Cap experiment loop iterations per skill (default: 3)
--n-runs N           Parallel benchmark runs per round (default: 3, minimum: 2)
--phase1-only        Static audit only — commit fixes, write report, stop
--skip-phase1        Skip audit, go straight to Phase 1.5 comprehension
--skip-comprehension Skip Phase 1.5/1.75 (only if taxonomy already exists and was validated)
--converge           Run until score plateaus, ignoring max-rounds
--wall-time-limit M  Maximum minutes per skill before stopping (default: 60)
```

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
├─ PHASE 1.5 — Comprehension (close the Gulf of Comprehension)
│  ├─ 5a. Generate 5 diverse outputs
│  ├─ 5b. Open coding (read everything, freeform notes)
│  ├─ 5c. Axial coding (build failure taxonomy)
│  └─ 5d. Gate (human review or auto-proceed)
│
├─ PHASE 1.75 — Judge Calibration (close the Gulf of Specification)
│  ├─ 5e. Map taxonomy → judges
│  ├─ 5f. Build golden dataset
│  └─ 5g. Validate judge agreement ≥ 0.70 kappa
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
├─ 13. Report results
└─ 13.5. Cross-skill consistency check
```

---

## Phase 1 — Free Wins

Run all of these before spending compute on benchmarks. Order is by value
(highest-impact first), not by cost.

### Automated Tools

The following scripts in `scripts/` support the improvement process:

| Tool | Command | Purpose |
|------|---------|---------|
| **Prompt generator** | `python scripts/dispatch_benchmark.py {skill} --version {v} --n-runs 3` | Generate standardized benchmark subagent prompts from template |
| **Checklist evaluator** | `python scripts/evaluate_checklist.py {skill} --all` | Score protocol adherence of benchmark scripts against YAML checklist |
| **Version comparator** | `python scripts/compare_versions.py {skill}` | Extract metrics from summary.json across versions, produce trajectory report |
| **Skill auditor** | `python scripts/skill_auditor.py {skill_dir}/{skill}.md` | Audit function calls against toolkit signatures |
| **Consistency checker** | `python scripts/check_cross_skill_consistency.py --skill-dir {skill_dir} --shared-dir {skill_dir}/_shared/` | Check cross-skill consistency |
| **Skill expander** | `python scripts/expand_skill.py {skill_dir}/{skill}.md` | Inline `{{include}}` markers before dispatching |

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

The auditor:
- Extracts function calls from fenced `python` code blocks only (prose references are noted but
  not parsed — only executable code blocks are authoritative for signature checking)
- Verifies each extracted call exists in the toolkit with correct signature via `inspect.signature()`
- Checks: parameter names match, return types match, imports are present in the skill's import block
- Flags: missing functions, wrong parameter names (e.g., `n_bootstrap` vs `n_boot`), wrong
  return types (e.g., `fig, ax = plot_heatmap()` when it returns `Axes` only)

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
  reduction): Proceed to Phase 1.5.

**Generate benchmark prompts:**
```bash
python scripts/dispatch_benchmark.py {skill_name} --version baseline --n-runs 3
```
Dispatch each generated prompt as a sonnet subagent. After all complete, evaluate:
```bash
python scripts/evaluate_checklist.py {skill_name} --all
python scripts/compare_versions.py {skill_name}
```

---

## Phase 1.5 — Comprehension

**Purpose**: Close the Gulf of Comprehension — the gap between what you think the skill
produces and what it actually produces. This phase is mandatory. Skipping it means Phase 2
optimizes against imagined failure modes.

**Rationale** (Three Gulfs framework, Husain & Shankar): Automated optimization of
non-deterministic systems fails when judges are not grounded in manually observed failure
patterns. The Gulf of Comprehension must be closed before the Gulf of Specification (judges),
and both before the Gulf of Generalization (autoresearch loop). "If you are not willing to
look at some data manually on a regular cadence you are wasting your time with evals."

### Step 5a — Generate Diverse Outputs

Run the skill on **5 diverse analysis prompts** that vary along key dimensions of the
input space. Use the reference dataset from Step 5.

Input diversity dimensions (vary at least 3):
- **Persona**: novice analyst vs experienced bioinformatician
- **Scope**: quick exploratory pass vs comprehensive publication-quality analysis
- **Emphasis**: statistical rigor vs biological interpretation vs visualization
- **Constraints**: time-limited ("key findings only") vs unconstrained
- **Data framing**: "here is RNA-seq data" (generic) vs domain-specific context

Dispatch 5 parallel **sonnet** subagents, each with a different prompt variant + the skill
injected. Collect all outputs (code + figures + interpretation) to:
`{benchmark_dir}/runs/{skill_name}_{dataset_name}/comprehension/run_{1..5}/`

### Step 5b — Open Coding (Read Everything)

Dispatch a single **opus** subagent with ALL 5 outputs. Its task:

> Read every output end-to-end. For each output, write freeform notes on what is wrong,
> what is surprisingly good, what is generic, what misses constraints the prompt specified,
> what is off in a way that couldn't have been predicted. Do NOT categorize yet — just
> observe and describe. Write notes to `comprehension/open_coding_notes.md`.

This is the step that builds intuition about failure. It cannot be replaced by scoring.

### Step 5c — Axial Coding (Failure Taxonomy)

Dispatch a second **opus** subagent with the open coding notes. Its task:

> Group these freeform observations into a coherent failure taxonomy: a small set (5-10)
> of distinct, binary failure categories. Each category should be:
> - **Named**: short label (e.g., "generic_interpretation", "missed_batch_correction",
>   "wrong_normalization_order", "no_effect_sizes", "uncritical_thresholds")
> - **Defined**: one sentence defining what counts as this failure
> - **Grounded**: cite specific examples from the open coding notes
> - **Binary**: an output either exhibits this failure or it doesn't
>
> Write taxonomy to `comprehension/failure_taxonomy.yaml`.

**Output format** (`failure_taxonomy.yaml`):

```yaml
taxonomy_version: 1
skill: "{skill_name}"
generated_from: "5 diverse runs on {dataset_name}"
categories:
  - name: generic_interpretation
    definition: "Biological interpretation restates statistics without domain-specific mechanistic reasoning"
    examples: ["run_2: 'Gene X is upregulated (p=0.001)' with no pathway context"]
    severity: high  # high/medium/low

  - name: missed_batch_correction
    definition: "Analysis proceeds without checking or correcting for batch effects"
    examples: ["run_1, run_4: no mention of batch variables despite multi-sample data"]
    severity: high
```

### Step 5d — Gate

If `--skip-comprehension` was passed, skip Phase 1.5 entirely (for re-runs where the
taxonomy already exists and was manually validated). Otherwise, this phase always runs.

In **guided mode**: present the failure taxonomy to the user for review before proceeding.
The user may add, remove, or redefine categories.

In **autonomous mode**: proceed directly to Phase 1.75.

---

## Phase 1.75 — Judge Calibration

**Purpose**: Close the Gulf of Specification — the gap between what you want the skill to do
and what your judges actually measure. Uses the failure taxonomy from Phase 1.5 to ensure
judges are grounded in observed behavior.

### Step 5e — Taxonomy → Judge Mapping

For each category in `failure_taxonomy.yaml`, determine how (or whether) the current
judge system detects it:

| Taxonomy Category | Current Detection | Gap |
|-------------------|------------------|-----|
| {category_name} | adherence checklist step X / effectiveness metric Y / not detected | {describe gap} |

Any "not detected" category requires either:
1. A new `detect_any` pattern in the checklist YAML (for code-level failures)
2. A new effectiveness sub-metric (for output-quality failures like generic interpretation)
3. An annotation in the taxonomy marking it as "beyond current judge scope" (acceptable
   for <20% of categories)

### Step 5f — Golden Dataset Construction

Take the 5 comprehension outputs from Phase 1.5 plus 10-15 additional outputs (from the
baseline benchmark run in Step 5, or generate them now). For each output, manually score
every taxonomy category as PASS/FAIL:

```yaml
# {benchmark_dir}/runs/{skill_name}_{dataset_name}/comprehension/golden_labels.yaml
outputs:
  - run_id: comprehension/run_1
    labels:
      generic_interpretation: FAIL
      missed_batch_correction: PASS
      wrong_normalization_order: PASS
      # ... all categories
  - run_id: comprehension/run_2
    labels:
      generic_interpretation: FAIL
      missed_batch_correction: FAIL
      # ...
```

In **guided mode**: the user scores outputs (or reviews LLM-proposed scores).
In **autonomous mode**: dispatch an **opus** subagent to score, with instructions to be
conservative (when uncertain, label FAIL).

### Step 5g — Judge Agreement Check

Run the current judge system (adherence checker + effectiveness scorer) on the golden
dataset outputs. Compare judge verdicts against golden labels:

```
For each taxonomy category:
  - True positive rate (judge detects failure when golden says FAIL)
  - False positive rate (judge flags failure when golden says PASS)
  - Cohen's kappa or simple agreement %
```

**Gate**: Proceed to Phase 2 only when mean agreement across categories ≥ 0.70 (kappa)
or ≥ 80% (simple agreement). If below threshold:
- Update `detect_any` patterns for low-recall categories
- Adjust effectiveness weights for categories that dominate failures
- Re-check agreement. If still below after 2 iterations, flag to user and proceed
  with documented judge limitations.

Write calibration results to `comprehension/judge_calibration.md`.

---

## Phase 2 — Benchmark Loop

Phase 2 follows autoresearch's exact modify-run-evaluate-keep/discard loop structure.
Phase 2 costs ~$3–5 per round (3 sonnet subagents × ~70K tokens) and typically converges
in 2–3 rounds. Only for stochastic pipelines where outputs vary across runs.

### Step 6 — Setup: Branch and Reference Dataset

**Create the experiment branch:**

```bash
git checkout -b skill-improve/{skill_name}
```

**Initialize results.tsv:**

```bash
printf '# schema_version=1\n' > {benchmark_dir}/runs/{skill_name}_{dataset_name}/results.tsv
printf 'commit\tcomposite\tadherence\teffectiveness\treplicability\tstatus\tdescription\n' \
  >> {benchmark_dir}/runs/{skill_name}_{dataset_name}/results.tsv
```

### Step 6a — Run Baseline

Before any modifications, benchmark the unmodified skill to establish a baseline.

**Generate prompts and evaluate:**
```bash
python scripts/dispatch_benchmark.py {skill_name} --version baseline --n-runs 3
# After runs complete:
python scripts/evaluate_checklist.py {skill_name} --all
python scripts/compare_versions.py {skill_name}
```

Compute composite score from the baseline results. Record in results.tsv with
`status=baseline` and `commit` = current HEAD short hash.

### Step 6b — Reference Comparison (HIGHEST VALUE STEP)

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

### Step 7 — Experiment Loop (autoresearch pattern)

**Scope rule**: The only file modified during this loop is `{skill_dir}/{skill_name}.md`.
All other files are immutable. `git reset --hard HEAD~1` on discard always reverts exactly
one skill file change.

```
LOOP (repeat until convergence):

  1. READ current state
     - Read {skill_dir}/{skill_name}.md
     - Read results.tsv (all previous rounds)

  2. IDENTIFY next improvement
     Priority order:
       a. Failure taxonomy categories (from Phase 1.5) not yet addressed —
          highest priority, ordered by severity (high → medium → low)
       b. Phase 1 audit findings not yet applied
       c. Low-scoring dimensions from previous round diagnosis
       d. Reference analysis comparison — what does the gold-standard
          reference analysis do differently from what agents produce?
       e. Code-level divergence — where do agent outputs deviate from
          the skill's prescribed steps?

     Specific improvement types (in order of benchmark impact):
       - Fix high-severity taxonomy failures (e.g., generic interpretation,
         missed batch correction) — these are grounded in observed behavior
       - Replace ambiguous prose with executable code blocks
       - Add MANDATORY annotations to critical steps
       - Add parameter defaults backed by benchmark evidence
       - Remove unnecessary steps that don't improve effectiveness
       - Sharpen detect_any patterns in checklist YAML for low-hit steps

  3. MODIFY {skill_dir}/{skill_name}.md ONLY
     (no changes to checklist, reference dataset, or benchmark infrastructure)

  4. COMMIT the change
     git add {skill_dir}/{skill_name}.md
     git commit -m "experiment: {concise description of change}"

  5. RUN BENCHMARK
     Dispatch N parallel sonnet subagents, each independently analyzing
     the reference dataset with the updated skill injected.

     python scripts/dispatch_benchmark.py {skill_name} --version {round_N} --n-runs 3
     # After runs complete:
     python scripts/evaluate_checklist.py {skill_name} --all

  5b. OUTPUT REVIEW (taxonomy regression check)
     After scoring, dispatch a sonnet subagent to spot-check one run's output
     against the failure taxonomy. For each high-severity category, confirm
     whether the fix actually resolved it or whether the category regressed.
     Write a one-paragraph summary to round_{R}/taxonomy_check.md.
     This prevents "score went up but failure moved sideways."

  6. EVALUATE composite score

  7. DECIDE keep or discard
     KEEP if:
       composite improved ≥ 0.01 compared to previous round
       AND no individual dimension regressed > 0.05
       AND change did NOT add > 10% of current skill line count
            with improvement < 0.01 (simplicity criterion)
     DISCARD if:
       composite improved < 0.01 (no meaningful improvement)
       OR any dimension regressed > 0.05
       OR simplicity criterion violated

     On discard:
       git reset --hard HEAD~1
       (branch returns to previous state)

  8. LOG to results.tsv
     Append a tab-separated row:
     {commit_hash}\t{composite}\t{adherence}\t{effectiveness}\t{replicability}\t{keep|discard}\t{description}

  9. CHECK convergence — STOP if ANY condition is met:
       - Score improvement < 0.01 for 2 consecutive rounds (plateau)
       - max_rounds reached (unless --converge was passed)
       - All Phase 1 findings addressed AND effectiveness > 0.85
       - wall_time_limit reached (keep best result achieved so far)
     CONTINUE if:
       - Score is still improving AND rounds remain
       - A diagnosed gap has a clear fix not yet attempted
```

In **guided mode** (default): pause after each round, show the updated results.tsv, and wait
for user input before proceeding to the next round.

In **autonomous mode** (`--autonomous`): loop without pausing.

---

## Composite Score Formula

```python
composite = 0.40 * effectiveness + 0.30 * adherence + 0.30 * replicability
```

Where:
- `adherence` (0–1) — step detection rate × ordering compliance fraction
- `effectiveness` (0–1) — domain-specific; from the skill's agreement scoring method
- `replicability` (0–1) — cross-run consistency scalar collapsed from pairwise metrics:

```python
def replicability_score(rep) -> float:
    """Collapse replicability result into a 0-1 scalar.

    Uses only populated fields. Returns 0.0 if result is empty.
    """
    components = []
    if rep.pairwise_ari_mean > 0:               # clustering-based skills only
        components.append(rep.pairwise_ari_mean)
    if rep.cluster_count_range > 0:             # clustering-based skills only
        components.append(max(0, 1.0 - rep.cluster_count_range / 10))
    if rep.protocol_step_hit_rates:             # always available
        components.append(min(rep.protocol_step_hit_rates.values()))
    if rep.score_stds:                          # always available
        mean_std = sum(rep.score_stds.values()) / len(rep.score_stds)
        components.append(max(0, 1.0 - mean_std))
    if rep.cells_retained_cv < float('inf') and rep.cells_retained_cv > 0:
        components.append(max(0, 1.0 - rep.cells_retained_cv / 0.5))
    return sum(components) / len(components) if components else 0.0
```

---

## results.tsv Format

Tab-separated with a schema version header comment. Written to
`{benchmark_dir}/runs/{skill_name}_{dataset_name}/results.tsv`.

```
# schema_version=1
commit	composite	adherence	effectiveness	replicability	status	description
a1b2c3d	0.450	0.650	0.350	0.880	baseline	unmodified skill baseline
b2c3d4e	0.723	0.850	0.650	0.950	keep	fix marker ranking with composite score
c3d4e5f	0.710	0.830	0.640	0.890	discard	add regress_out (hurt single-sample datasets)
d4e5f6g	0.851	0.920	0.877	0.990	keep	conditional regress_out + resolution sweep
```

Fields:

| Field | Type | Description |
|-------|------|-------------|
| `commit` | git short hash | HEAD at time of benchmark run |
| `composite` | 0–1 float | Weighted composite score |
| `adherence` | 0–1 float | Protocol adherence score |
| `effectiveness` | 0–1 float | Domain-specific effectiveness |
| `replicability` | 0–1 float | Cross-run consistency scalar |
| `status` | string | `baseline`, `keep`, or `discard` |
| `description` | string | Concise description of the change tested |

---

## Simplicity Criterion

Discard an experiment if the composite improvement is < 0.01 **and** the change adds > 10%
of the current skill's line count. Fewer lines of skill prose = better, all else equal.

A simplification that maintains or improves score is always kept, even if improvement < 0.01.

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
generation in downstream analysis — NOT full protocols.

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
python scripts/compare_versions.py {skill_name}
```

### Step 13.5: Cross-Skill Consistency Check (MANDATORY)

After the trajectory report, run the consistency checker across all skills:

```bash
python scripts/check_cross_skill_consistency.py --skill-dir {skill_dir} --shared-dir {skill_dir}/_shared/
```

If inconsistencies are found:
- Review the proposed fixes
- Apply fixes that are correct (auto-fix with confirmation)
- Skip fixes that need domain-specific judgment (e.g., a skill intentionally uses a non-standard pattern marked with `# raw:`)
- Re-run the checker to verify clean

This step prevents skill improvements from introducing drift that breaks other skills.

**Shared sub-protocol files**: Skills can use `{{include _shared/X.md}}` markers for
common documentation blocks (visualization standards, reporting API, imports, correction
guidance). Use `scripts/expand_skill.py` to inline these markers before dispatching
benchmark subagents.

### Merge Decision

**Guided mode**: Present the final results.tsv table and benchmark report to the user. Wait
for explicit approval before merging.

**Autonomous mode** (`--autonomous`): Merge the skill branch to the staging branch
`skill-improve/batch-{YYYY-MM-DD}` (NOT directly to main). After all skills in `--all`
complete, the staging branch is presented for human review. This prevents cross-skill
interference and allows rollback of the entire batch.

```bash
# Autonomous merge to staging
git checkout skill-improve/batch-{date} 2>/dev/null || git checkout -b skill-improve/batch-{date}
git merge --no-ff skill-improve/{skill_name} -m "merge: {skill_name} improvements from benchmark loop"
git checkout skill-improve/{skill_name}
```

### Preserved Artifacts

After convergence, the following files are kept for future benchmarks and CI:

| Artifact | Location | Reuse |
|----------|----------|-------|
| Reference dataset | `{benchmark_dir}/reference_datasets/{dataset_name}/` | Reusable for future rounds |
| Failure taxonomy | `{benchmark_dir}/runs/{skill}_{dataset}/comprehension/failure_taxonomy.yaml` | Priority queue for experiments; skip Phase 1.5 on re-runs |
| Golden labels | `{benchmark_dir}/runs/{skill}_{dataset}/comprehension/golden_labels.yaml` | Judge calibration on re-runs |
| Judge calibration report | `{benchmark_dir}/runs/{skill}_{dataset}/comprehension/judge_calibration.md` | Track judge improvement over time |
| Skill checklist YAML | `{benchmark_dir}/skill_checklists/{skill_name}.yaml` | Protocol adherence monitoring in CI |
| Experiment history | `{benchmark_dir}/runs/{skill_name}_{dataset_name}/results.tsv` | Audit trail |
| Final benchmark report | `{benchmark_dir}/runs/{skill_name}_{dataset_name}/benchmark_report.md` | Summary |

---

## Convergence Formula

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
   python scripts/evaluate_checklist.py {skill_name} --all
   ```
   Use `1 - mean_adherence_score`. Example: 92% adherence → gap = 0.08

3. **metric_headroom** — Compare current primary metric against the published
   reference value for the dataset. Run:
   ```bash
   python scripts/compare_versions.py {skill_name}
   ```
   Example: reference C-index = 0.70, current = 0.688 → headroom = 0.017

**Worked example (survival_analysis, end of v3):**
```
bucket_ratio    = 4/8   = 0.50  (4 Low/Medium items remain)
gap_ratio       = 1-1.0 = 0.00  (100% checklist adherence)
metric_headroom = (0.70 - 0.688) / 0.70 = 0.017

continue_value  = 0.50 × 0.00 × 0.017 = 0.000  →  STOP
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

## `--all` Mode

Process all skills in `{skill_dir}/` sequentially (no cross-skill parallelism — each skill
may extend shared infrastructure like agreement types).

```bash
# Autonomous batch improvement of all skills
/skill-improver --all --autonomous --max-rounds 3
```

Execution order:
1. Sort skills alphabetically
2. For each skill: run Phase 1 → Phase 1.5 → Phase 1.75 → Phase 2 (unless skipped)
3. On convergence: merge to `skill-improve/batch-{YYYY-MM-DD}` staging branch
4. After all skills complete: report the staging branch name for human review

---

## Failure Mode Diagnosis

Use these patterns to identify the right next experiment when a round scores poorly:

| Pattern | Diagnosis | Next Fix |
|---------|-----------|----------|
| High adherence, low effectiveness | Skill prescribes wrong methodology | Compare vs reference gold standard; update the core algorithm |
| Low adherence, high effectiveness | Skill not constraining agent behavior | Check keyword triggering; add MANDATORY annotations |
| High effectiveness, low replicability | Ambiguous decision points | Add explicit parameter recommendations at branch points |
| Low adherence, specific steps failing | Checklist `detect_any` patterns too narrow | Add library aliases to checklist; also tighten skill wording |
| Score plateau after 2 rounds | True convergence, or wrong dataset | Try backup candidate dataset before concluding |

---

## Cost Estimate

| Phase | Per Skill | Notes |
|-------|-----------|-------|
| Phase 1 (static audit) | ~$0.50 | Research lookup + grep, minimal LLM |
| Phase 1.5 (comprehension) | ~$2–3 | 5 sonnet runs + 2 opus reads (open/axial coding) |
| Phase 1.75 (judge calibration) | ~$1–2 | Opus scoring + agreement calculation |
| Phase 2, one round (3 runs) | ~$3–5 | 3 sonnet subagents × ~70K tokens each |
| Phase 2, 3 rounds (default) | ~$10–15 | Typical convergence in 2–3 rounds |
| Full 12-skill autonomous run | ~$180–270 | All phases for all skills |
| Wall-time (12 skills) | ~8–16 hours | ~40–80 min per skill (comprehension adds ~15 min) |

Sonnet is the default model for benchmark runs. Use opus when biological interpretation rate
is consistently failing with sonnet.

---

## Running Autonomously (--all --autonomous)

For autonomous batch improvement of all skills:

1. Read `config.yaml` to get the full list of skills under `skills:` and sort
   them by expected value (stochastic skills first — they benefit most from
   the benchmark loop).
2. For each skill: run Phase 1 → Phase 1.5 → Phase 1.75 → baseline →
   stochasticity check → Phase 2 if needed → cross-validate → report
3. Commit each skill's improvements on a dedicated branch
4. After all skills: merge to staging branch for human review

**Cost estimate**: ~$15-23 per skill (all phases + 3 rounds × 3 runs).
Actual total depends on the number of skills in `config.yaml`.
