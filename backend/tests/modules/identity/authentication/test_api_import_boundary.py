import ast
from pathlib import Path

COMPOSITION_ROOT = "dependencies.py"
LEGACY_APPLICATION_AUTH_PREFIX = "app.modules.identity.application.auth"


def _authentication_api_root() -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "api"
        / "authentication"
    )


def _is_forbidden_import(module_name: str) -> bool:
    normalized = module_name.lower()
    if normalized == LEGACY_APPLICATION_AUTH_PREFIX or normalized.startswith(
        f"{LEGACY_APPLICATION_AUTH_PREFIX}."
    ):
        return True
    if "sqlalchemy" in normalized:
        return True
    if ".infrastructure." in normalized or normalized.endswith(".infrastructure"):
        return True
    return False


def _collect_forbidden_imports(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    forbidden: list[str] = []

    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module:
            if _is_forbidden_import(node.module):
                forbidden.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_import(alias.name):
                    forbidden.append(alias.name)

    return forbidden


def test_authentication_api_thin_modules_have_no_forbidden_imports() -> None:
    root = _authentication_api_root()
    violations: dict[str, list[str]] = {}

    for path in root.rglob("*.py"):
        if path.name == COMPOSITION_ROOT:
            continue
        forbidden = _collect_forbidden_imports(path)
        if forbidden:
            violations[str(path.relative_to(root))] = forbidden

    assert violations == {}
