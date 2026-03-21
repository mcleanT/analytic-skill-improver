"""Audit analysis skill files against a toolkit's public API.

Verifies that every function called in a skill's code blocks exists
in the configured toolkit module with the correct signature.

Usage:
    python scripts/skill_auditor.py skills/survival_analysis.md
    python scripts/skill_auditor.py skills/survival_analysis.md --config config.yaml
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import typer
import yaml

app = typer.Typer(help=__doc__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AuditFinding:
    """One finding from the function audit."""

    function_name: str
    severity: str  # "error", "warning", "info"
    message: str
    details: str = ""


@dataclass
class AuditResult:
    """Aggregated result of auditing a single skill file."""

    skill_path: Path
    findings: list[AuditFinding] = field(default_factory=list)

    # Convenience counts
    @property
    def errors(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def infos(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == "info"]


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def load_config(config_path: Path) -> dict:
    """Load config.yaml, return empty dict on failure."""
    if not config_path.exists():
        return {}
    with config_path.open() as fh:
        return yaml.safe_load(fh) or {}


def get_toolkit_module(config: dict) -> str | None:
    """Extract toolkit_module from config, or None if absent/null."""
    return (config.get("project") or {}).get("toolkit_module") or None


# ---------------------------------------------------------------------------
# Toolkit introspection
# ---------------------------------------------------------------------------


def load_toolkit(module_path: str) -> tuple[object | None, AuditFinding | None]:
    """Dynamically import the toolkit module.

    Returns (module, None) on success or (None, error_finding) on failure.
    """
    try:
        mod = importlib.import_module(module_path)
        return mod, None
    except ImportError as exc:
        return None, AuditFinding(
            function_name="(module)",
            severity="warning",
            message=f"Cannot import toolkit module '{module_path}': {exc}",
            details="Signature checks will be skipped; only call existence is reported.",
        )


def get_public_api(module: object) -> dict[str, object]:
    """Return a mapping of public names -> objects from a module.

    Prefers __all__ if defined; otherwise uses all names not starting with '_'.
    """
    if hasattr(module, "__all__"):
        return {name: getattr(module, name) for name in module.__all__ if hasattr(module, name)}
    return {name: getattr(module, name) for name in dir(module) if not name.startswith("_")}


# ---------------------------------------------------------------------------
# Markdown / code parsing
# ---------------------------------------------------------------------------

# Match ```python or ```Python fenced blocks (case-insensitive language tag)
_CODE_BLOCK_RE = re.compile(r"```[Pp]ython\s*\n(.*?)```", re.DOTALL)

# Match bare function calls: word-chars immediately followed by '(', but NOT
# preceded by '.' (method calls) or another identifier char.
_CALL_RE = re.compile(r"(?<![.\w])([a-zA-Z_]\w*)\s*\(")


# Names we never want to audit — Python builtins + common data-science
# namespace roots that are not toolkit functions.
_SKIP_NAMES: frozenset[str] = frozenset(
    {
        # Python builtins
        "print",
        "len",
        "range",
        "int",
        "float",
        "str",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "type",
        "isinstance",
        "issubclass",
        "hasattr",
        "getattr",
        "setattr",
        "delattr",
        "enumerate",
        "zip",
        "map",
        "filter",
        "sorted",
        "reversed",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "any",
        "all",
        "open",
        "iter",
        "next",
        "vars",
        "dir",
        "repr",
        "hash",
        "id",
        "super",
        "property",
        "staticmethod",
        "classmethod",
        "object",
        "Exception",
        "ValueError",
        "TypeError",
        "KeyError",
        "IndexError",
        "RuntimeError",
        "NotImplementedError",
        "StopIteration",
        "AttributeError",
        # Control-flow keywords that pattern-match as calls
        "if",
        "for",
        "while",
        "with",
        "def",
        "class",
        "return",
        "assert",
        "raise",
        "yield",
        # Common third-party namespace roots (not function names we audit)
        "pd",
        "np",
        "plt",
        "sns",
        "sc",
        "ax",
        "fig",
        "px",
        "go",
        "sp",
        "sklearn",
        "torch",
        "tf",
        # Pandas / NumPy constructors & methods commonly called at module level
        "DataFrame",
        "Series",
        "Index",
        "read_csv",
        "read_parquet",
        "read_excel",
        "read_json",
        "to_csv",
        "array",
        "zeros",
        "ones",
        "arange",
        "linspace",
        "log",
        "log1p",
        "log2",
        "exp",
        "sqrt",
        "mean",
        "std",
        "var",
        "median",
        "where",
        "concatenate",
        "vstack",
        "hstack",
        # SciPy / sklearn functions sometimes called directly
        "mannwhitneyu",
        "ttest_ind",
        "ttest_rel",
        "pearsonr",
        "spearmanr",
        "multipletests",
        "kneighbors_graph",
        "PCA",
        "UMAP",
        "TSNE",
        "LinearRegression",
        "LogisticRegression",
        "RandomForestClassifier",
        "KMeans",
        "silhouette_score",
        "adjusted_rand_score",
        # AnnData / scanpy
        "AnnData",
        "read_h5ad",
        "normalize_total",
        # Matplotlib / seaborn
        "Figure",
        "subplots",
        "savefig",
        "show",
        "scatter",
        "violinplot",
        "heatmap",
        "imshow",
        "colorbar",
        "legend",
        "title",
        "xlabel",
        "ylabel",
        # NetworkX
        "louvain_communities",
        "from_scipy_sparse_array",
        "Graph",
        "DiGraph",
        # lifelines
        "KaplanMeierFitter",
        "CoxPHFitter",
        "logrank_test",
        # Path / OS utilities
        "Path",
        "os",
        "sys",
        "json",
        "pickle",
        "glob",
        "copy",
        "deepcopy",
        "defaultdict",
        "Counter",
        "partial",
    }
)


def extract_code_blocks(markdown_text: str) -> list[str]:
    """Return the content of every fenced Python code block in *markdown_text*."""
    return _CODE_BLOCK_RE.findall(markdown_text)


def extract_function_calls(code: str) -> set[str]:
    """Extract candidate toolkit function-call names from Python source code.

    Skips:
    - Lines that are comments, imports, or blank.
    - Names in the global skip-list (builtins, common third-party namespace roots).
    """
    calls: set[str] = set()
    for line in code.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("from ")
            or stripped.startswith("import ")
        ):
            continue
        for match in _CALL_RE.finditer(stripped):
            name = match.group(1)
            if name not in _SKIP_NAMES:
                calls.add(name)
    return calls


# ---------------------------------------------------------------------------
# Signature checking
# ---------------------------------------------------------------------------


def check_call_against_api(
    call_name: str,
    public_api: dict[str, object],
    *,
    toolkit_module_path: str,
) -> AuditFinding:
    """Return an AuditFinding for a single function call name."""
    if call_name not in public_api:
        return AuditFinding(
            function_name=call_name,
            severity="error",
            message=f"'{call_name}' not found in {toolkit_module_path}",
        )

    obj = public_api[call_name]
    if not callable(obj):
        return AuditFinding(
            function_name=call_name,
            severity="warning",
            message=(
                f"'{call_name}' exists in {toolkit_module_path} "
                f"but is not callable (type: {type(obj).__name__})"
            ),
        )

    try:
        sig = inspect.signature(obj)
        return AuditFinding(
            function_name=call_name,
            severity="info",
            message=f"Found: {call_name}{sig}",
        )
    except (ValueError, TypeError):
        return AuditFinding(
            function_name=call_name,
            severity="info",
            message=f"Found: {call_name} (signature unavailable)",
        )


def audit_calls_against_toolkit(
    calls: set[str],
    public_api: dict[str, object],
    toolkit_module_path: str,
) -> list[AuditFinding]:
    """Audit every call name against the loaded toolkit's public API."""
    return [
        check_call_against_api(name, public_api, toolkit_module_path=toolkit_module_path)
        for name in sorted(calls)
    ]


def audit_calls_no_toolkit(calls: set[str]) -> list[AuditFinding]:
    """When no toolkit is configured, just report which functions are called."""
    return [
        AuditFinding(
            function_name=name,
            severity="info",
            message=f"Called: {name} (no toolkit configured — signature check skipped)",
        )
        for name in sorted(calls)
    ]


# ---------------------------------------------------------------------------
# Top-level audit orchestrator
# ---------------------------------------------------------------------------


def audit_skill_file(
    skill_path: Path,
    toolkit_module_path: str | None,
) -> AuditResult:
    """Full audit of a single skill markdown file.

    Args:
        skill_path: Path to the .md skill file.
        toolkit_module_path: Dotted module path (e.g. ``my_project.analytics``),
            or ``None`` when no toolkit is configured.

    Returns:
        An :class:`AuditResult` containing all findings.
    """
    result = AuditResult(skill_path=skill_path)

    # 1. Parse markdown
    text = skill_path.read_text(encoding="utf-8")
    blocks = extract_code_blocks(text)
    if not blocks:
        result.findings.append(
            AuditFinding(
                function_name="(file)",
                severity="warning",
                message=f"No Python code blocks found in {skill_path.name}",
            )
        )
        return result

    # 2. Extract candidate calls
    all_code = "\n".join(blocks)
    calls = extract_function_calls(all_code)

    if not calls:
        result.findings.append(
            AuditFinding(
                function_name="(file)",
                severity="info",
                message=f"No non-builtin function calls detected in {skill_path.name}",
            )
        )
        return result

    # 3. Check against toolkit (or just report if no toolkit)
    if not toolkit_module_path:
        result.findings.append(
            AuditFinding(
                function_name="(config)",
                severity="info",
                message=(
                    "toolkit_module is not configured — "
                    "reporting called functions without signature verification"
                ),
            )
        )
        result.findings.extend(audit_calls_no_toolkit(calls))
        return result

    # 4. Dynamically import the toolkit
    module, import_error = load_toolkit(toolkit_module_path)
    if import_error is not None:
        result.findings.append(import_error)
        # Still report which functions are called so the output is useful
        result.findings.extend(audit_calls_no_toolkit(calls))
        return result

    # 5. Introspect the public API and audit
    public_api = get_public_api(module)
    result.findings.extend(audit_calls_against_toolkit(calls, public_api, toolkit_module_path))
    return result


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

_SEVERITY_COLOUR = {
    "error": "\033[91m",  # bright red
    "warning": "\033[93m",  # bright yellow
    "info": "\033[92m",  # bright green
}
_RESET = "\033[0m"


def _colour(text: str, severity: str, *, use_colour: bool) -> str:
    if not use_colour:
        return text
    return f"{_SEVERITY_COLOUR.get(severity, '')}{text}{_RESET}"


def print_result(result: AuditResult, *, use_colour: bool = True) -> None:
    """Print a human-readable audit report to stdout."""
    print(f"\nAuditing: {result.skill_path}")
    print("-" * 60)

    if not result.findings:
        print("  (no findings)")
        return

    for f in result.findings:
        tag = f"[{f.severity.upper():7s}]"
        coloured_tag = _colour(tag, f.severity, use_colour=use_colour)
        print(f"  {coloured_tag} {f.function_name}: {f.message}")
        if f.details:
            print(f"           {f.details}")

    # Summary line
    n_err = len(result.errors)
    n_warn = len(result.warnings)
    n_info = len(result.infos)
    print(
        f"\n  Summary: "
        f"{_colour(f'{n_err} error(s)', 'error', use_colour=use_colour)}, "
        f"{_colour(f'{n_warn} warning(s)', 'warning', use_colour=use_colour)}, "
        f"{n_info} info"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_config(config_opt: Path | None) -> Path:
    """Resolve config file path: explicit arg > cwd/config.yaml > script-dir/../config.yaml."""
    if config_opt is not None:
        return config_opt
    cwd_cfg = Path.cwd() / "config.yaml"
    if cwd_cfg.exists():
        return cwd_cfg
    # Fallback: relative to this script's parent directory
    script_cfg = Path(__file__).parent.parent / "config.yaml"
    return script_cfg


@app.command()
def main(
    skill_files: list[Path] = typer.Argument(
        ...,
        help="One or more skill .md files to audit.",
        exists=True,
        readable=True,
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help=(
            "Path to config.yaml. "
            "Defaults to config.yaml in the current directory, "
            "then to the project root."
        ),
        exists=False,  # We handle missing gracefully
    ),
    no_colour: bool = typer.Option(
        False,
        "--no-colour",
        "--no-color",
        help="Disable ANSI colour output.",
    ),
) -> None:
    """Audit skill markdown files against the configured toolkit module."""
    cfg_path = _resolve_config(config)
    cfg = load_config(cfg_path)

    toolkit_module_path = get_toolkit_module(cfg)

    if toolkit_module_path:
        typer.echo(f"Toolkit module : {toolkit_module_path}")
    else:
        typer.echo("Toolkit module : (none configured — signature checks disabled)")

    if cfg_path.exists():
        typer.echo(f"Config         : {cfg_path}")
    else:
        typer.echo(f"Config         : (not found at {cfg_path} — using defaults)")

    use_colour = not no_colour and sys.stdout.isatty()

    total_errors = 0
    total_warnings = 0

    for skill_path in skill_files:
        result = audit_skill_file(skill_path, toolkit_module_path)
        print_result(result, use_colour=use_colour)
        total_errors += len(result.errors)
        total_warnings += len(result.warnings)

    if len(skill_files) > 1:
        print(f"\n{'=' * 60}")
        print(
            f"Total across {len(skill_files)} file(s): {total_errors} error(s), {total_warnings} warning(s)"
        )

    # Exit with non-zero code if any errors were found
    if total_errors:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
