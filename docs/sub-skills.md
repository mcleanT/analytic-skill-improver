# Sub-Skills for the Skill-Improver

Six specialized sub-skills automate the manual decision gates in the 13.5-step
improvement protocol. Each is invoked at its marked step (⚡ in the process diagram).
They can also be triggered independently outside the improvement loop.

## Overview

| Skill | Step | Trigger | What it automates |
|-------|------|---------|-------------------|
| **checklist-generator** | 1.5 | "generate checklist" | Creates YAML adherence checklists from skill protocols |
| **skill-improver-triage** | 3 | "triage findings" | Sorts literature findings into A/B/C buckets |
| **skill-editor** | 4, 7 | "edit skill" | Proposes + applies skill .md edits from audit/gap findings |
| **skill-gap-analyzer** | 6 | "analyze gaps" | Structured reference comparison with gap classification |
| **convergence-checker** | 10 | "check convergence" | Computes continue_value, recommends STOP/CONTINUE |
| **skill-include-propagator** | 13.5 | "propagate includes" | Batch-adds missing `{{include}}` markers |

## checklist-generator (Step 1.5)

**Purpose**: Without a YAML checklist, `evaluate_checklist.py` cannot score
adherence — the benchmark loop is blocked. This skill generates checklists
from skill protocol steps.

**Process**:
1. Read the target skill `.md` file
2. Read the toolkit API reference for function signatures
3. Map each protocol step to a `required_step` with `detect_any` patterns
4. Generate ordering constraints from the step sequence
5. Write to `benchmarks/skill_checklists/{skill_name}.yaml`

**Key design decisions**:
- `detect_any` patterns include toolkit API calls AND raw library equivalents
- Ordering constraints only for scientifically load-bearing dependencies
- Steps marked `# MANDATORY` in the skill get `required: true`

## skill-improver-triage (Step 3)

**Purpose**: Sorts literature comparison findings into three buckets,
eliminating ~30% of Phase 1 manual effort.

**The Three Buckets**:
- **A (Skill fix)**: Can be fixed by editing the skill `.md` alone
- **B (Toolkit upgrade)**: Requires new code in the analytics toolkit
- **C (Follow-up signpost)**: Valuable but out of scope for current improvement

**Routing**:
- Bucket A → Steps 4 + 7 (skill edits)
- Bucket B → Step 12.5 (toolkit upgrade logging)
- Bucket C → Step 12 (follow-up signposts)

## skill-editor (Steps 4, 7)

**Purpose**: Takes audit findings or gap analysis output and proposes precise,
verified edits to skill `.md` files.

**Three edit types**:
1. **Prose → Code Block** (Step 4): Convert ambiguous prose to executable code
2. **Fix Wrong Reference** (Step 7): Correct function signatures, return types, kwargs
3. **Add Missing Step** (Step 7): Insert new protocol steps with code blocks

**Safety rules**:
- Every function signature verified against actual toolkit source before proposing
- Never removes domain-specific content that isn't broken
- Preserves `# MANDATORY` comments and `{{include}}` markers

## skill-gap-analyzer (Step 6)

**Purpose**: Structured comparison between best benchmark run and published
canonical analysis. Identifies WHY outputs diverge, not just WHERE scores are low.

**Gap classification** (two axes):
- **Impact**: CRITICAL / HIGH / MEDIUM / LOW
- **Root cause**: SKILL_PROSE / SKILL_MISSING / SKILL_WRONG / TOOLKIT_GAP / AGENT_HALLUCINATION

**Output**: Prioritized fix queue for Step 7, with TOOLKIT_GAP items routed
to Bucket B.

## convergence-checker (Step 10)

**Purpose**: Auto-computes the diminishing returns formula and recommends
STOP or CONTINUE.

**Formula**:
```
continue_value = bucket_ratio × gap_ratio × metric_headroom
STOP when continue_value < 0.05
```

**Additional stop conditions**:
- 2 consecutive rounds with < 0.01 improvement (plateau)
- effectiveness > 0.85 AND adherence > 0.90 (good enough)
- All Bucket A items resolved AND gap_ratio < 0.05

## skill-include-propagator (Step 13.5)

**Purpose**: After the consistency checker identifies missing `{{include}}`
markers, this skill batch-adds them across all affected skills.

**What it knows**:
- Correct placement rules for each shared block type
- Which skills need `correction_guidance.md` (only those with ≥2 statistical tests)
- How to detect and replace inlined copies with include markers
