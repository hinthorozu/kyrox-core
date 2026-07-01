import ast
from pathlib import Path

FORBIDDEN_IMPORT_MARKERS = ("infrastructure", "api", "fastapi", "sqlalchemy")

QUERY_APPLICATION_FILES = (
    "list_organization_audit_logs.py",
    "query_policy.py",
    "query_commands.py",
    "query_results.py",
)


def _application_file_path(filename: str) -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "app"
        / "modules"
        / "audit"
        / "application"
        / filename
    )


def _collect_forbidden_imports(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    forbidden: list[str] = []

    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module:
            module_name = node.module.lower()
            if any(marker in module_name for marker in FORBIDDEN_IMPORT_MARKERS):
                forbidden.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.lower()
                if any(marker in module_name for marker in FORBIDDEN_IMPORT_MARKERS):
                    forbidden.append(alias.name)

    return forbidden


def test_audit_query_application_modules_do_not_import_outer_layers() -> None:
    violations: dict[str, list[str]] = {}

    for filename in QUERY_APPLICATION_FILES:
        forbidden = _collect_forbidden_imports(_application_file_path(filename))
        if forbidden:
            violations[filename] = forbidden

    assert violations == {}
