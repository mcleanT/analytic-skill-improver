#!/usr/bin/env python3
"""Cross-skill consistency checker.

Scans analysis skills for inconsistencies with shared sub-protocols,
pipeline function adoption, and signature drift.

Usage:
    python scripts/check_cross_skill_consistency.py --skill-dir skills/ --shared-dir skills/_shared/
"""

import argparse
import sys
from pathlib import Path

# Configurable: raw functions that have pipeline wrappers
PIPELINE_REPLACEMENTS = {
    "pca_analysis": "pca_pipeline",
    "kmeans_cluster": "kmeans_pipeline",
    "hierarchical_cluster": "hierarchical_pipeline",
    "correct_pvalues": "correction_pipeline",
}

# Configurable: wrong kwarg patterns
WRONG_KWARGS = {
    "linkage=": ("hierarchical_cluster", "method="),
    "color_col=": ("plot_pca", "group_col="),
    "row_cluster=": ("plot_heatmap", "parameter does not exist"),
}

# Configurable: wrong dict key access patterns
WRONG_KEYS = {
    '["optimal_k"]': '["recommended_k"]',
    '["mean_ari"]': '["overall_stability"]',
    '["std_ari"]': '["overall_stability"]',
    '["embedding"]': "tuple unpacking (returns tuple, not dict)",
}


def extract_code_blocks(text: str) -> list[tuple[int, str]]:
    """Extract fenced python code blocks with their starting line numbers."""
    blocks = []
    in_block = False
    block_start = 0
    block_lines: list[str] = []
    for i, line in enumerate(text.split("\n"), 1):
        if line.strip().startswith("```python"):
            in_block = True
            block_start = i
            block_lines = []
        elif line.strip() == "```" and in_block:
            in_block = False
            blocks.append((block_start, "\n".join(block_lines)))
        elif in_block:
            block_lines.append(line)
    return blocks


def check_shared_freshness(skill_dir: Path, shared_dir: Path) -> list[str]:
    """Category 1: Check {{include}} markers for each shared file."""
    issues = []
    shared_files = sorted(shared_dir.glob("*.md")) if shared_dir.exists() else []
    skill_files = sorted(f for f in skill_dir.glob("*.md") if f.parent == skill_dir)

    for shared in shared_files:
        count = 0
        for skill in skill_files:
            text = skill.read_text()
            if f"{{{{include _shared/{shared.name}}}}}" in text:
                count += 1
        status = "✅" if count == len(skill_files) else "⚠️ "
        issues.append(
            f"  {status} {shared.name}: {count}/{len(skill_files)} skills use {{{{include}}}}"
        )
    return issues


def check_pipeline_adoption(skill_dir: Path) -> list[str]:
    """Category 2: Check for raw function calls that should use pipelines."""
    issues = []
    skill_files = sorted(f for f in skill_dir.glob("*.md") if f.parent == skill_dir)

    for skill in skill_files:
        text = skill.read_text()
        blocks = extract_code_blocks(text)
        for block_start, block_text in blocks:
            for raw_fn, pipeline_fn in PIPELINE_REPLACEMENTS.items():
                for i, line in enumerate(block_text.split("\n")):
                    if f"{raw_fn}(" in line:
                        # Check for # raw: exception
                        prev_line = block_text.split("\n")[i - 1] if i > 0 else ""
                        if "# raw:" in line or "# raw:" in prev_line:
                            continue
                        lineno = block_start + i
                        issues.append(
                            f"  ⚠️  {skill.name}:{lineno} — calls raw {raw_fn}(), "
                            f"suggest {pipeline_fn}()"
                        )
    return issues


def check_signature_consistency(skill_dir: Path) -> list[str]:
    """Category 3: Check for known wrong kwarg patterns."""
    issues = []
    skill_files = sorted(f for f in skill_dir.glob("*.md") if f.parent == skill_dir)

    for skill in skill_files:
        text = skill.read_text()
        blocks = extract_code_blocks(text)
        for block_start, block_text in blocks:
            for wrong, (fn_name, correct) in WRONG_KWARGS.items():
                for i, line in enumerate(block_text.split("\n")):
                    if wrong in line and fn_name in line:
                        lineno = block_start + i
                        issues.append(
                            f"  ⚠️  {skill.name}:{lineno} — uses {wrong} (should be {correct})"
                        )
    return issues


def check_return_types(skill_dir: Path) -> list[str]:
    """Category 4: Check for wrong dict key access patterns."""
    issues = []
    skill_files = sorted(f for f in skill_dir.glob("*.md") if f.parent == skill_dir)

    for skill in skill_files:
        text = skill.read_text()
        blocks = extract_code_blocks(text)
        for block_start, block_text in blocks:
            for wrong_key, fix in WRONG_KEYS.items():
                for i, line in enumerate(block_text.split("\n")):
                    if wrong_key in line:
                        lineno = block_start + i
                        issues.append(
                            f"  ❌ {skill.name}:{lineno} — accesses {wrong_key} — should be {fix}"
                        )
    return issues


def check_inline_drift(skill_dir: Path, shared_dir: Path) -> list[str]:
    """Category 5: Check for inlined copies of shared blocks."""
    issues = []
    # Distinctive first lines for each shared file
    markers = {
        "viz_standards.md": "All figures MUST follow these standards:",
        "reporting_api.md": "stat_result: wraps a single statistical test result",
        "correction_guidance.md": "Default rule: collect ALL p-values before correcting",
    }
    skill_files = sorted(f for f in skill_dir.glob("*.md") if f.parent == skill_dir)

    for shared_name, marker_text in markers.items():
        for skill in skill_files:
            text = skill.read_text()
            has_include = f"{{{{include _shared/{shared_name}}}}}" in text
            has_inline = marker_text in text
            if has_inline and not has_include:
                issues.append(
                    f"  ⚠️  {skill.name} — contains inlined {shared_name} block without {{{{include}}}}"
                )
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-skill consistency checker")
    parser.add_argument(
        "--skill-dir",
        default="skills/",
        help="Directory containing skill .md files",
    )
    parser.add_argument(
        "--shared-dir",
        default=None,
        help="Directory containing shared files (default: skill_dir/_shared/)",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    shared_dir = Path(args.shared_dir) if args.shared_dir else skill_dir / "_shared"

    print("Cross-Skill Consistency Report")
    print("=" * 30)
    print()

    total_warnings = 0
    total_errors = 0

    # Category 1
    print("Category 1 — Shared Block Freshness:")
    cat1 = check_shared_freshness(skill_dir, shared_dir)
    if cat1:
        for line in cat1:
            print(line)
            if "⚠️" in line:
                total_warnings += 1
    else:
        print("  ✅ No shared files found (skip)")
    print()

    # Category 2
    print("Category 2 — Pipeline Adoption:")
    cat2 = check_pipeline_adoption(skill_dir)
    if cat2:
        for line in cat2:
            print(line)
            total_warnings += 1
    else:
        print("  ✅ All skills use pipeline functions.")
    print()

    # Category 3
    print("Category 3 — Signature Consistency:")
    cat3 = check_signature_consistency(skill_dir)
    if cat3:
        for line in cat3:
            print(line)
            total_warnings += 1
    else:
        print("  ✅ No signature issues found.")
    print()

    # Category 4
    print("Category 4 — Return Type Assumptions:")
    cat4 = check_return_types(skill_dir)
    if cat4:
        for line in cat4:
            print(line)
            total_errors += 1
    else:
        print("  ✅ No return type issues found.")
    print()

    # Category 5
    print("Category 5 — Include-vs-Inline Drift:")
    cat5 = check_inline_drift(skill_dir, shared_dir)
    if cat5:
        for line in cat5:
            print(line)
            total_warnings += 1
    else:
        print("  ✅ No inline drift detected.")
    print()

    print(f"Summary: {total_warnings} warning(s), {total_errors} error(s)")

    if total_errors > 0 or total_warnings > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
