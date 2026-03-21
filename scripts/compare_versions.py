"""Compare benchmark metrics across skill improvement versions.

Usage:
    python scripts/compare_versions.py survival_analysis
    python scripts/compare_versions.py --all
    python scripts/compare_versions.py survival_analysis --config config.yaml
"""

import json
import sys
from pathlib import Path
from typing import Any


def load_config(config_path: Path) -> dict[str, Any]:
    """Load config.yaml, return empty dict if not found."""
    if not config_path.exists():
        return {}
    import yaml

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def resolve_benchmark_dir(config: dict[str, Any], default: str = "benchmarks/runs") -> Path:
    """Resolve benchmark_dir from config, falling back to default."""
    return Path(config.get("benchmark_dir", default))


def load_summary(path: Path) -> dict[str, Any] | None:
    """Load a summary.json file, return None if not found."""
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def find_summaries(skill_dir: Path) -> dict[str, list[dict]]:
    """Find all summary.json files organized by version."""
    versions = {}
    for version_dir in sorted(skill_dir.iterdir()):
        if not version_dir.is_dir():
            continue
        version_name = version_dir.name
        summaries = []
        # Look for summary.json in run subdirs or output subdirs
        for run_dir in sorted(version_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            # Check multiple possible locations
            for candidate in [
                run_dir / "summary.json",
                run_dir / "output" / "summary.json",
            ]:
                summary = load_summary(candidate)
                if summary is not None:
                    summaries.append(summary)
                    break
        if summaries:
            versions[version_name] = summaries
    return versions


def extract_metrics(summaries: list[dict]) -> dict[str, Any]:
    """Extract key metrics from a list of run summaries, computing mean/std."""
    metrics = {}

    # Common metric keys to look for
    metric_keys = [
        "c_statistic",
        "c_index",
        "median_survival",
        "n_patients",
        "n_events",
        "n_significant",
        "n_de_genes",
        "ari",
        "silhouette_score",
    ]

    for key in metric_keys:
        values = []
        for s in summaries:
            v = s.get(key)
            if v is not None and isinstance(v, (int, float)):
                values.append(float(v))
        if values:
            import statistics

            metrics[key] = {
                "mean": statistics.mean(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                "n": len(values),
                "values": values,
            }

    # Also extract significant_covariates count if present
    sig_counts = []
    for s in summaries:
        sc = s.get("significant_covariates")
        if isinstance(sc, list):
            sig_counts.append(len(sc))
        elif isinstance(sc, int):
            sig_counts.append(sc)
    if sig_counts:
        import statistics

        metrics["n_significant_covariates"] = {
            "mean": statistics.mean(sig_counts),
            "std": statistics.stdev(sig_counts) if len(sig_counts) > 1 else 0.0,
            "n": len(sig_counts),
            "values": sig_counts,
        }

    # Check for None values in key fields (indicates toolkit bugs)
    none_counts = {}
    for key in ["c_statistic", "c_index"]:
        none_count = sum(1 for s in summaries if s.get(key) is None)
        if none_count > 0:
            none_counts[key] = f"{none_count}/{len(summaries)} returned None"
    if none_counts:
        metrics["_none_values"] = none_counts

    return metrics


def format_report(skill_name: str, versions: dict[str, dict]) -> str:
    """Format a comparison report."""
    lines = [f"# {skill_name} — Improvement Trajectory\n"]

    # Collect all metric names
    all_metrics = set()
    for v_metrics in versions.values():
        all_metrics.update(k for k in v_metrics if not k.startswith("_"))
    all_metrics = sorted(all_metrics)

    if not all_metrics:
        return f"# {skill_name}\n\nNo metrics found in summary.json files.\n"

    # Table header
    header = "| Metric |"
    sep = "|--------|"
    for v_name in versions:
        header += f" {v_name} |"
        sep += "--------|"
    lines.append(header)
    lines.append(sep)

    # Table rows
    for metric in all_metrics:
        row = f"| {metric} |"
        for v_name, v_metrics in versions.items():
            if metric in v_metrics:
                m = v_metrics[metric]
                if m["std"] > 0.001:
                    row += f" {m['mean']:.3f} ± {m['std']:.3f} (n={m['n']}) |"
                else:
                    row += f" {m['mean']:.3f} (n={m['n']}) |"
            else:
                row += " — |"
        lines.append(row)

    # None values warning
    for v_name, v_metrics in versions.items():
        if "_none_values" in v_metrics:
            lines.append(f"\n**{v_name} warnings**: {v_metrics['_none_values']}")

    # Delta summary
    version_names = list(versions.keys())
    if len(version_names) >= 2:
        lines.append("\n## Deltas")
        first = version_names[0]
        last = version_names[-1]
        for metric in all_metrics:
            if metric in versions[first] and metric in versions[last]:
                delta = versions[last][metric]["mean"] - versions[first][metric]["mean"]
                if abs(delta) > 0.001:
                    direction = "up" if delta > 0 else "down"
                    lines.append(
                        f"- **{metric}**: {direction} {abs(delta):.3f} ({first} -> {last})"
                    )

    return "\n".join(lines) + "\n"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Compare benchmark metrics across versions")
    parser.add_argument("skill_name", nargs="?", help="Skill name to compare (or --all)")
    parser.add_argument("--all", action="store_true", help="Compare all skills")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    runs_dir = resolve_benchmark_dir(config)

    if not args.skill_name and not args.all:
        print("Usage: python scripts/compare_versions.py <skill_name> [--all]")
        if runs_dir.exists():
            print(f"\nAvailable skills: {[d.name for d in runs_dir.iterdir() if d.is_dir()]}")
        sys.exit(1)

    if args.all:
        if not runs_dir.exists():
            print(f"No benchmark runs directory found at {runs_dir}")
            sys.exit(1)
        skills = [d.name for d in sorted(runs_dir.iterdir()) if d.is_dir()]
    else:
        skills = [args.skill_name]

    for skill_name in skills:
        skill_dir = runs_dir / skill_name
        if not skill_dir.exists():
            print(f"No runs found for {skill_name}")
            continue

        version_summaries = find_summaries(skill_dir)
        if not version_summaries:
            print(f"No summary.json files found for {skill_name}")
            continue

        version_metrics = {}
        for v_name, summaries in version_summaries.items():
            version_metrics[v_name] = extract_metrics(summaries)

        report = format_report(skill_name, version_metrics)
        print(report)

        # Also save to file
        report_path = skill_dir / "improvement_trajectory.md"
        with open(report_path, "w") as f:
            f.write(report)
        print(f"Saved to {report_path}\n")


if __name__ == "__main__":
    main()
