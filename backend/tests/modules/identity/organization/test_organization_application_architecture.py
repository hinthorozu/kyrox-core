import ast
from pathlib import Path

FORBIDDEN_IMPORT_MARKERS = (
    "infrastructure",
    "api",
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "app.core.config",
    "app.db",
)

APPLICATION_FILES = (
    "create_organization.py",
    "get_organization.py",
    "update_organization.py",
    "suspend_organization.py",
    "commands.py",
    "results.py",
    "policy.py",
    "mappers.py",
)


def _application_file_path(filename: str) -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "application"
        / "organization"
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


def test_organization_application_modules_do_not_import_outer_layers() -> None:
    violations: dict[str, list[str]] = {}

    for filename in APPLICATION_FILES:
        forbidden = _collect_forbidden_imports(_application_file_path(filename))
        if forbidden:
            violations[filename] = forbidden

    assert violations == {}
