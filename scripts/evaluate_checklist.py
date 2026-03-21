"""Evaluate analysis script adherence to a skill checklist.

Usage:
    python scripts/evaluate_checklist.py survival_analysis benchmarks/runs/survival_analysis/v3/run1/analysis_code.py
    python scripts/evaluate_checklist.py survival_analysis --all
    python scripts/evaluate_checklist.py survival_analysis --all --config config.yaml
"""

import re
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: Path) -> dict[str, Any]:
    """Load config.yaml, return empty dict if not found."""
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def resolve_checklist_dir(config: dict[str, Any], default: str = "checklists") -> Path:
    """Resolve checklist_dir from config, falling back to default."""
    return Path(config.get("checklist_dir", default))


def resolve_benchmark_dir(config: dict[str, Any], default: str = "benchmarks/runs") -> Path:
    """Resolve benchmark_dir from config, falling back to default."""
    return Path(config.get("benchmark_dir", default))


def load_checklist(skill_name: str, checklist_dir: Path) -> dict[str, Any]:
    """Load the YAML checklist for a skill."""
    path = checklist_dir / f"{skill_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No checklist found at {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def load_script(path: Path) -> str:
    """Load an analysis script."""
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {path}")
    return path.read_text()


def check_step(script_text: str, step: dict) -> tuple[bool, list[str]]:
    """Check if a step is present in the script.

    Returns (detected, matched_patterns).
    """
    patterns = step.get("detect_any", [])
    matched = []
    for pattern in patterns:
        # Case-insensitive search
        if re.search(re.escape(pattern), script_text, re.IGNORECASE):
            matched.append(pattern)
    return len(matched) > 0, matched


def check_ordering(
    script_text: str,
    constraints: list[dict],
    step_positions: dict[str, int],
) -> list[str]:
    """Check ordering constraints between steps.

    Returns list of violation descriptions.
    """
    violations = []
    for constraint in constraints:
        before = constraint.get("before")
        after = constraint.get("after")
        if before in step_positions and after in step_positions:
            if step_positions[before] > step_positions[after]:
                violations.append(f"{before} should come before {after}")
    return violations


def find_first_position(script_text: str, patterns: list[str]) -> int | None:
    """Find the earliest character position where any pattern matches."""
    earliest = None
    for pattern in patterns:
        match = re.search(re.escape(pattern), script_text, re.IGNORECASE)
        if match:
            pos = match.start()
            if earliest is None or pos < earliest:
                earliest = pos
    return earliest


def evaluate(skill_name: str, script_path: Path, checklist_dir: Path) -> dict[str, Any]:
    """Evaluate a script against the checklist."""
    checklist = load_checklist(skill_name, checklist_dir)
    script_text = load_script(script_path)

    results = {
        "skill": skill_name,
        "script": str(script_path),
        "steps": [],
        "ordering_violations": [],
    }

    step_positions = {}
    required_found = 0
    required_total = 0
    optional_found = 0
    optional_total = 0

    for step in checklist.get("required_steps", []):
        is_required = step.get("required", True)
        detected, matched = check_step(script_text, step)

        step_result = {
            "name": step["name"],
            "description": step.get("description", ""),
            "required": is_required,
            "detected": detected,
            "matched_patterns": matched,
        }
        results["steps"].append(step_result)

        if is_required:
            required_total += 1
            if detected:
                required_found += 1
        else:
            optional_total += 1
            if detected:
                optional_found += 1

        # Track position for ordering check
        if detected:
            pos = find_first_position(script_text, step.get("detect_any", []))
            if pos is not None:
                step_positions[step["name"]] = pos

    # Check ordering
    for constraint in checklist.get("ordering_constraints", []):
        before = constraint.get("before")
        after = constraint.get("after")
        if before in step_positions and after in step_positions:
            if step_positions[before] > step_positions[after]:
                results["ordering_violations"].append(
                    f"{before} (pos {step_positions[before]}) should come before "
                    f"{after} (pos {step_positions[after]})"
                )

    # Compute scores
    results["adherence_score"] = required_found / max(required_total, 1)
    results["required_found"] = required_found
    results["required_total"] = required_total
    results["optional_found"] = optional_found
    results["optional_total"] = optional_total
    results["ordering_violations_count"] = len(results["ordering_violations"])

    return results


def format_report(result: dict) -> str:
    """Format evaluation result as readable text."""
    lines = [
        f"## Checklist Evaluation: {result['skill']}",
        f"Script: `{result['script']}`",
        "",
        f"**Adherence Score: {result['adherence_score']:.0%}** "
        f"({result['required_found']}/{result['required_total']} required steps)",
        f"Optional: {result['optional_found']}/{result['optional_total']}",
        f"Ordering violations: {result['ordering_violations_count']}",
        "",
    ]

    # Step details
    for step in result["steps"]:
        status = "+" if step["detected"] else "x"
        req = "REQUIRED" if step["required"] else "optional"
        matched = ", ".join(step["matched_patterns"][:3]) if step["matched_patterns"] else "none"
        lines.append(f"  [{status}] [{req}] {step['name']}: {step['description']}")
        if step["detected"]:
            lines.append(f"    matched: {matched}")

    if result["ordering_violations"]:
        lines.append("\nOrdering violations:")
        for v in result["ordering_violations"]:
            lines.append(f"  WARNING: {v}")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate analysis script adherence to a skill checklist"
    )
    parser.add_argument("skill_name", help="Skill name to evaluate")
    parser.add_argument(
        "script_path",
        nargs="?",
        help="Path to analysis script (omit to use --all)",
    )
    parser.add_argument("--all", action="store_true", help="Evaluate all runs for this skill")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    checklist_dir = resolve_checklist_dir(config)
    runs_dir = resolve_benchmark_dir(config)

    if args.script_path and not args.all:
        # Single script evaluation
        script_path = Path(args.script_path)
        result = evaluate(args.skill_name, script_path, checklist_dir)
        print(format_report(result))
    else:
        # Evaluate all runs for this skill
        skill_dir = runs_dir / args.skill_name
        if not skill_dir.exists():
            print(f"No runs found at {skill_dir}")
            sys.exit(1)

        all_results = []
        for version_dir in sorted(skill_dir.iterdir()):
            if not version_dir.is_dir():
                continue
            for run_dir in sorted(version_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                # Look for analysis_code.py
                for candidate in [
                    run_dir / "analysis_code.py",
                    run_dir / "output" / "analysis_code.py",
                ]:
                    if candidate.exists():
                        try:
                            result = evaluate(args.skill_name, candidate, checklist_dir)
                            all_results.append(result)
                            print(format_report(result))
                            print()
                        except Exception as e:
                            print(f"Error evaluating {candidate}: {e}")
                        break

        # Summary
        if all_results:
            scores = [r["adherence_score"] for r in all_results]
            print(f"\n## Summary ({len(all_results)} scripts evaluated)")
            print(f"Mean adherence: {statistics.mean(scores):.0%}")
            if len(scores) > 1:
                print(f"Std: {statistics.stdev(scores):.0%}")
            print(f"Min: {min(scores):.0%}, Max: {max(scores):.0%}")

            # Per-version breakdown
            print("\n## Per-version breakdown")
            version_scores: dict[str, list[float]] = {}
            for r in all_results:
                # Extract version from path: .../runs/<skill>/<version>/run*/...
                parts = Path(r["script"]).parts
                skill_idx = next((i for i, p in enumerate(parts) if p == args.skill_name), None)
                version = (
                    parts[skill_idx + 1]
                    if skill_idx is not None and skill_idx + 1 < len(parts)
                    else "unknown"
                )
                version_scores.setdefault(version, []).append(r["adherence_score"])

            for version, vscores in sorted(version_scores.items()):
                mean = statistics.mean(vscores)
                print(
                    f"  {version}: {mean:.0%} (n={len(vscores)}, runs: {[f'{s:.0%}' for s in vscores]})"
                )


if __name__ == "__main__":
    main()
