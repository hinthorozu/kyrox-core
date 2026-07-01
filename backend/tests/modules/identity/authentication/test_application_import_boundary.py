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


def _authentication_application_root() -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "application"
        / "authentication"
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


def test_authentication_application_has_no_forbidden_imports() -> None:
    root = _authentication_application_root()
    violations: dict[str, list[str]] = {}

    for path in root.rglob("*.py"):
        forbidden = _collect_forbidden_imports(path)
        if forbidden:
            violations[str(path.relative_to(root))] = forbidden

    assert violations == {}
