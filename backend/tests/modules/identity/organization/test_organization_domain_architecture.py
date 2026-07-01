import ast
from pathlib import Path

FORBIDDEN_IMPORT_MARKERS = (
    "application",
    "infrastructure",
    "api",
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "authentication",
    "authorization",
    "membership",
)

DOMAIN_FILES = (
    "entities/organization.py",
    "ports/organization_repository.py",
)


def _file_path(relative: str) -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "domain"
        / "organization"
        / relative
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


def _assert_no_save_method(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    violations: list[str] = []

    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == "save":
            violations.append("save() method is forbidden on repository ports")

    return violations


def test_organization_domain_modules_do_not_import_outer_layers() -> None:
    violations: dict[str, list[str]] = {}

    for relative in DOMAIN_FILES:
        forbidden = _collect_forbidden_imports(_file_path(relative))
        if forbidden:
            violations[relative] = forbidden

    assert violations == {}


def test_organization_repository_port_does_not_define_save() -> None:
    save_violations = _assert_no_save_method(_file_path("ports/organization_repository.py"))
    assert save_violations == []
