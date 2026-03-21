"""Generate benchmark prompts from template, reading skill and dataset config from config.yaml.

Usage:
    python scripts/dispatch_benchmark.py survival_analysis --version v3 --n-runs 3
    python scripts/dispatch_benchmark.py bulk_rnaseq --version v2 --n-runs 3 --config config.yaml
"""

import sys
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: Path) -> dict[str, Any]:
    """Load config.yaml. Errors clearly if the file is missing."""
    if not config_path.exists():
        print(f"ERROR: Config file not found at {config_path}")
        print("Create a config.yaml with a 'skills' section. See templates/config.yaml.example.")
        sys.exit(1)
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return data


def get_skill_config(config: dict[str, Any], skill_name: str) -> dict[str, Any]:
    """Extract skill config from the loaded config. Errors if skill is not found."""
    skills = config.get("skills", {})
    if skill_name not in skills:
        available = list(skills.keys())
        print(f"ERROR: Skill '{skill_name}' not found in config.")
        print(f"Available skills: {available}")
        sys.exit(1)
    return skills[skill_name]


def get_dataset(skill_cfg: dict[str, Any], dataset_type: str, skill_name: str) -> dict[str, Any]:
    """Extract dataset config for the given type (primary or backup)."""
    key = "primary_dataset" if dataset_type == "primary" else "backup_dataset"
    dataset = skill_cfg.get(key)
    if dataset is None:
        print(f"ERROR: No '{key}' defined for skill '{skill_name}' in config.")
        sys.exit(1)
    # Normalise key names: support both flat dict and nested with 'path', 'description', etc.
    return {
        "path": dataset.get("path", ""),
        "description": dataset.get("description", ""),
        "columns": dataset.get("columns", ""),
        "notes": dataset.get("notes", ""),
    }


def resolve_template_path(config: dict[str, Any]) -> Path:
    """Resolve the benchmark prompt template path from config or default."""
    return Path(config.get("benchmark_template", "templates/benchmark_prompt.md"))


def resolve_runs_dir(config: dict[str, Any]) -> Path:
    """Resolve the benchmark runs directory from config or default."""
    return Path(config.get("benchmark_dir", "benchmarks/runs"))


def generate_prompt(
    skill_cfg: dict[str, Any],
    skill_name: str,
    version: str,
    run_number: int,
    dataset_type: str,
    template_path: Path,
    runs_dir: Path,
) -> str:
    """Generate a benchmark prompt for a specific skill/version/run."""
    dataset = get_dataset(skill_cfg, dataset_type, skill_name)
    skill_path = skill_cfg.get("skill_path", f"skills/{skill_name}.md")
    output_dir = str(runs_dir / skill_name / version / f"run{run_number}")

    if not template_path.exists():
        print(f"ERROR: Benchmark prompt template not found at {template_path}")
        sys.exit(1)

    template = template_path.read_text()

    prompt = template.replace("{{dataset_path}}", dataset["path"])
    prompt = prompt.replace("{{dataset_description}}", dataset["description"])
    prompt = prompt.replace("{{column_descriptions}}", dataset["columns"])
    prompt = prompt.replace("{{skill_path}}", skill_path)
    prompt = prompt.replace("{{output_dir}}", output_dir)
    prompt = prompt.replace("{{dataset_specific_notes}}", dataset["notes"])

    return prompt


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate benchmark prompts from config")
    parser.add_argument("skill_name", help="Skill to benchmark (must exist in config.yaml)")
    parser.add_argument("--version", default="v1", help="Version label (default: v1)")
    parser.add_argument(
        "--n-runs", type=int, default=3, help="Number of parallel runs (default: 3)"
    )
    parser.add_argument(
        "--dataset",
        default="primary",
        choices=["primary", "backup"],
        help="Dataset type to use (default: primary)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory for generated prompt files",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    skill_cfg = get_skill_config(config, args.skill_name)
    template_path = resolve_template_path(config)
    runs_dir = resolve_runs_dir(config)

    for i in range(1, args.n_runs + 1):
        prompt = generate_prompt(
            skill_cfg=skill_cfg,
            skill_name=args.skill_name,
            version=args.version,
            run_number=i,
            dataset_type=args.dataset,
            template_path=template_path,
            runs_dir=runs_dir,
        )

        # Save prompt to file
        out_dir = Path(args.output_dir or str(runs_dir / args.skill_name / args.version))
        out_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = out_dir / f"run{i}_prompt.md"
        with open(prompt_file, "w") as f:
            f.write(prompt)
        print(f"Generated: {prompt_file}")

    print(f"\n{args.n_runs} prompts generated for {args.skill_name} {args.version}")
    print("Dispatch each as a sonnet subagent for benchmarking.")


if __name__ == "__main__":
    main()
