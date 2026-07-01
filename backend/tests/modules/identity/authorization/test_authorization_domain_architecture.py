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
)

DOMAIN_FILES = (
    "entities/permission_group.py",
    "entities/permission.py",
    "entities/role.py",
    "entities/role_permission.py",
    "entities/organization_role.py",
    "entities/user_role.py",
    "ports/role_repository.py",
    "ports/permission_repository.py",
    "ports/role_permission_repository.py",
    "ports/organization_role_repository.py",
    "ports/user_role_repository.py",
    "ports/permission_checker.py",
    "ports/platform_user_reader.py",
)


def _file_path(relative: str) -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "domain"
        / "authorization"
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


def test_authorization_domain_modules_do_not_import_outer_layers() -> None:
    violations: dict[str, list[str]] = {}

    for relative in DOMAIN_FILES:
        forbidden = _collect_forbidden_imports(_file_path(relative))
        if forbidden:
            violations[relative] = forbidden

    assert violations == {}


def test_authorization_repository_ports_do_not_define_save() -> None:
    violations: dict[str, list[str]] = {}

    for relative in DOMAIN_FILES:
        if not relative.startswith("ports/"):
            continue
        save_violations = _assert_no_save_method(_file_path(relative))
        if save_violations:
            violations[relative] = save_violations

    assert violations == {}
