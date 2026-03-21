# Skill Improver

**Benchmark-driven self-improvement for LLM analysis skills**

LLM agents are only as good as the skill protocols they follow. Skill Improver automatically finds what is wrong with your analysis skill files, fixes them, and verifies the fix actually works — on real data with ground-truth results.

---

## The Problem

LLM agents performing data analysis follow *skill protocols* — markdown files that describe analysis steps in prose and code. In practice, skill quality degrades in three ways:

1. **Hallucinated function signatures.** Prose like "call `kaplan_meier()` with the `time_col` argument" gets interpreted differently run to run. If the actual function uses `t` not `time_col`, half of agents silently produce wrong results.

2. **Methodological drift.** Best practices evolve. A survival analysis skill written against 2022 standards may still recommend Kaplan-Meier log-rank tests where Cox PH with Schoenfeld residuals is now the field standard. No one notices until a reviewer flags it.

3. **Underconstrained decision points.** When a skill says "choose an appropriate resolution parameter," agents make different choices every run. Results look plausible individually but are irreproducible in aggregate.

Manual skill maintenance does not scale. With 10+ skills across multiple domains, keeping them aligned with literature, tested against real data, and verified for replicability requires dedicated infrastructure.

---

## The Solution

An automated improvement loop inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — adapted for analysis prompt optimization instead of model training.

**The core idea**: treat each skill `.md` file as a hyperparameter. Run it against a reference dataset with published ground-truth results. Measure three things: does the agent follow the prescribed steps (adherence), does it produce the right answers (effectiveness), and does it produce the same answers across runs (replicability)? Then modify, re-run, and keep or discard — exactly like a gradient step, but on prose.

The loop:

```
literature audit  →  function audit  →  fix Phase 1 findings
       ↓
  run baseline
       ↓
  ┌─── identify next improvement
  │           ↓
  │       modify skill (.md only)
  │           ↓
  │       run N parallel benchmarks
  │           ↓
  │       evaluate composite score
  │           ↓
  │    keep (score ↑ ≥ 0.01) or discard (git reset)
  │           ↓
  └─── converged? (plateau × 2 rounds, or effectiveness > 0.85)
       ↓
  add follow-up signposts  →  final report  →  merge to staging
```

All modifications are isolated on a dedicated git branch. Discard is always safe: `git reset --hard HEAD~1` reverts exactly one change.

---

## Key Results

Three complete improvement runs on production skills:

| Skill | Metric | Before | After | Change | Key fix |
|-------|--------|--------|-------|--------|---------|
| `scrna_seq` | ARI | 0.629 | 0.868 | +38% | Code blocks replace prose; resolution sweep added |
| `bulk_rnaseq` | DE genes detected | 257 | 3,148 | +1,125% | Dependency install step; blocking factors for paired design |
| `survival_analysis` | C-statistic | None | 0.688 | +∞ | Return value contract added; calibration plot step added; 3/3 runs identical |

The bulk RNA-seq result is the most striking: agents following the original skill were silently missing 92% of differentially expressed genes because the skill omitted a `pip install pydeseq2` step and did not mention paired experimental design as a confound.

---

## How It Works

### The 13.5-Step Flow

```
Phase 1 — Static Audit (cheap, ~$0.50/skill)
  Step 1a  Literature audit — compare each step to 2024-2025 field standards
  Step 1b  Function audit   — verify every function call against toolkit signatures
  Step 1c  Apply fixes      — correct broken refs, update outdated methods
  Step 1.5 Create checklist YAML (if not yet exists)

Phase 2 — Dynamic Benchmark (~$3-5/round)
  Step 2a  Branch + reference dataset setup
  Step 2b  Run baseline (unmodified skill → establish floor)

  [Loop until convergence]
  Step 2c-1  Read current state (skill + results.tsv)
  Step 2c-2  Identify next improvement (priority queue)
  Step 2c-3  Modify skill .md only
  Step 2c-4  Commit the change
  Step 2c-5  Run N parallel benchmark subagents
  Step 2c-6  Compute composite score (0.40 × effectiveness + 0.30 × adherence + 0.30 × replicability)
  Step 2c-7  Keep or discard (git reset on discard)
  Step 2c-8  Log to results.tsv
  Step 2c-9  Check convergence
  [End loop]

Post-convergence
  Step 3a  Add follow-up signposts to skill
  Step 3b  Generate final benchmark report
  Step 3c  Merge to staging branch for human review
```

Phase 1 runs first for every skill regardless of mode. It catches broken function references and outdated methods before spending benchmark compute. When `--phase1-only` is set, the loop never starts.

---

## Quick Start

**1. Configure your project**

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` to point at your skill files, analytics toolkit module, and reference datasets. See [Configuration](#configuration) below.

**2. Create a checklist for your skill**

```bash
cp templates/checklist.yaml.example checklists/my_skill.yaml
```

Edit the checklist to describe the required steps for your analysis domain (see [templates/checklist.yaml.example](templates/checklist.yaml.example)).

**3. Run a baseline benchmark**

```bash
python scripts/dispatch_benchmark.py your_skill --version baseline --n-runs 3
```

This runs 3 independent agents on your reference dataset and reports adherence, effectiveness, and replicability scores. No modification is made to your skill file.

**4. Run the full improvement loop**

Follow the SKILL.md protocol in your Claude Code session:

```
/skill-improver --skill your_skill --max-rounds 3
```

Or run autonomously (no pauses between rounds):

```
/skill-improver --skill your_skill --autonomous --max-rounds 3
```

Results are written to `benchmarks/runs/{skill_name}/results.tsv` after each round.

---

## Project Structure

```
skill-improver/
├── config.yaml.example          # Template — copy to config.yaml
├── LICENSE
├── README.md
│
├── scripts/
│   ├── dispatch_benchmark.py    # Run N parallel subagent benchmarks
│   ├── compute_composite.py     # Score aggregation (adherence + effectiveness + replicability)
│   └── audit_skill.py           # Phase 1 static auditor (literature + function checks)
│
├── templates/
│   └── checklist.yaml.example   # Template for per-skill YAML checklists
│
├── examples/
│   ├── survival_analysis/       # Complete worked example (GBSG2 dataset)
│   └── bulk_rnaseq/             # Complete worked example (Airway dataset)
│
└── docs/
    ├── lessons.md               # 9 lessons learned from production runs
    ├── composite_score.md       # Detailed scoring formula and tuning guide
    ├── checklist_authoring.md   # How to write effective detect_any patterns
    └── failure_diagnosis.md     # Pattern → diagnosis → fix table
```

---

## The 9 Lessons

Brief summaries. Full text in [docs/lessons.md](docs/lessons.md).

1. **Phase 1 catches most of the value for free.** In all three production runs, Phase 1 function auditing found at least one broken function reference that would have caused silent wrong results. Run Phase 1 before Phase 2 — always.

2. **Replace prose with code blocks.** The single highest-impact change across all skills was converting ambiguous prose steps ("apply appropriate normalization") into executable code blocks with explicit function calls and parameter values. ARI improved 38% from this change alone on `scrna_seq`.

3. **The replicability dimension is the canary.** A replicability score drop after a change almost always means the change introduced an ambiguous decision point. Low replicability is not bad luck — it is a structural defect in the skill.

4. **Backup datasets are not optional.** Two of three runs hit score plateaus on the primary dataset that resolved when switching to the backup. A plateau on one dataset is often real convergence; a plateau on both datasets usually is.

5. **Checklist `detect_any` patterns need aliases.** A step marked as "missing" is often present but using an alternative library call not in the pattern list. Add both toolkit API calls (`correct_pvalues`) and raw library calls (`fdr_bh`, `multipletests`) to `detect_any`.

6. **The scope rule makes experiments safe.** Only the skill `.md` file changes inside the loop. `git reset --hard HEAD~1` on discard is always safe because no other file was touched. Violating this rule makes rollback unsafe and experiments unreproducible.

7. **Simplicity is a convergence signal.** When a change adds more than 10% to the skill's line count for less than 0.01 composite improvement, it should be discarded even if it doesn't hurt. Longer skill files have higher interpretation variance across runs.

8. **Parallel benchmarks expose variance; serial benchmarks hide it.** Running N=3 agents simultaneously on the same dataset is the minimum to detect replicability issues. N=1 always looks like it works.

9. **Autonomous mode needs a staging branch, not direct-to-main.** When running `--all` autonomously across multiple skills, cross-skill interference is real (shared infrastructure changes, schema conflicts). Always merge to a staging branch and review before touching main.

---

## Configuration

`config.yaml` has three sections:

**`project`** — paths and commands that apply to all skills:
- `skill_dir`: where your `.md` skill files live
- `toolkit_module`: Python module path for function audit (`null` to skip audit)
- `test_command`: run after toolkit changes to detect regressions
- `benchmark_dir` / `checklist_dir`: artifact directories

**`skills`** — one entry per skill with:
- `skill_path`: path to the `.md` file (relative to project root)
- `primary_dataset` / `backup_dataset`: reference data with column descriptions and notes
- `primary_metric`: the domain's key quality metric (e.g., `ari`, `c_statistic`, `de_f1`)
- `reference_value`: published benchmark to compare against (used in diminishing returns)
- `stochastic`: `true` for clustering/dimensionality reduction (Phase 2 always runs); `false` for deterministic pipelines (Phase 2 is skipped if Phase 1 already achieves effectiveness > 0.85)

**`dependencies`** — packages to verify are importable during Phase 1 dependency scan

See [config.yaml.example](config.yaml.example) for the full annotated template.

---

## Automated Tools

Three scripts handle the computational work. The improvement loop itself is orchestrated by an LLM agent following the SKILL.md protocol.

| Script | Purpose | Typical usage |
|--------|---------|---------------|
| `scripts/dispatch_benchmark.py` | Launch N parallel agent runs on a reference dataset; collect outputs | `python scripts/dispatch_benchmark.py skill_name --n-runs 3` |
| `scripts/compute_composite.py` | Aggregate adherence + effectiveness + replicability into one score | Called by the benchmark harness; also usable standalone |
| `scripts/audit_skill.py` | Phase 1 static auditor — literature check + function signature verification | `python scripts/audit_skill.py skill_name` |

---

## Composite Score Formula

```
composite = 0.40 × effectiveness + 0.30 × adherence + 0.30 × replicability
```

Where:
- **effectiveness** — domain-specific quality metric (ARI for clustering, C-statistic for survival, DE F1 for bulk RNA-seq, etc.)
- **adherence** — step detection rate × ordering compliance fraction, computed against the skill's checklist YAML
- **replicability** — collapsed scalar from pairwise run similarity, cluster count stability, and per-step hit rate variance

A change is kept if composite improves by at least 0.01 and no individual dimension regresses by more than 0.05. The 0.01 threshold prevents chasing noise on small benchmarks.

---

## Diminishing Returns

Improvement runs use a `continue_value` formula to detect true convergence vs. plateau:

```
continue_value = (current_composite - reference_value) / (1.0 - reference_value)
```

Where `reference_value` is the published benchmark for the domain (e.g., C-statistic 0.70 for GBSG2 breast cancer survival). A `continue_value` above 0.9 means the skill is outperforming the literature reference — further improvement is unlikely to be meaningful. This prevents the loop from running indefinitely on already-excellent skills.

---

## Requirements

- Python 3.10+
- PyYAML (`pip install pyyaml`)
- An LLM that can dispatch subagents (Claude Code with sonnet recommended)
- Domain-specific packages for your analysis area (e.g., `lifelines`, `scanpy`, `pydeseq2`)

No infrastructure beyond a standard Python environment. The benchmark harness spawns subagent processes; no separate server or database is needed.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Citation

If Skill Improver is useful for your work, please cite it as:

```
Skill Improver: Benchmark-driven self-improvement for LLM analysis skills.
https://github.com/[owner]/skill-improver
```
