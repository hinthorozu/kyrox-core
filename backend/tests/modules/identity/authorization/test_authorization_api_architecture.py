import ast
from pathlib import Path

THIN_API_FILES = (
    "routes.py",
    "schemas.py",
    "mappers.py",
    "error_mapping.py",
)


def _file_path(filename: str) -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "api"
        / "authorization"
        / filename
    )


def _is_forbidden_import(module_name: str) -> bool:
    normalized = module_name.lower()
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


def test_authorization_api_thin_modules_do_not_import_infrastructure() -> None:
    violations: dict[str, list[str]] = {}

    for filename in THIN_API_FILES:
        forbidden = _collect_forbidden_imports(_file_path(filename))
        if forbidden:
            violations[filename] = forbidden

    assert violations == {}
