#!/usr/bin/env python3
"""Expand {{include _shared/X.md}} markers in skill files.

Usage:
    python scripts/expand_skill.py skills/clustering_analysis.md
    python scripts/expand_skill.py skills/clustering_analysis.md -o /tmp/expanded.md
"""

import argparse
import re
import sys
from pathlib import Path


def expand(skill_path: str, shared_dir: str | None = None) -> str:
    """Replace {{include _shared/X.md}} markers with file contents."""
    skill = Path(skill_path)
    if shared_dir is None:
        shared_dir = str(skill.parent / "_shared")
    shared = Path(shared_dir)
    text = skill.read_text()

    def replacer(m: re.Match) -> str:
        include_name = m.group(1).strip()
        shared_path = shared / include_name
        if shared_path.exists():
            return shared_path.read_text().strip()
        print(f"WARNING: shared file not found: {shared_path}", file=sys.stderr)
        return m.group(0)

    return re.sub(r"\{\{include\s+_shared/(.+?)\}\}", replacer, text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand skill include markers")
    parser.add_argument("skill_path", help="Path to skill .md file")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--shared-dir",
        default=None,
        help="Directory containing shared files (default: skill_dir/_shared/)",
    )
    args = parser.parse_args()
    expanded = expand(args.skill_path, args.shared_dir)
    if args.output:
        Path(args.output).write_text(expanded)
        print(f"Expanded skill written to {args.output}", file=sys.stderr)
    else:
        print(expanded)


if __name__ == "__main__":
    main()
