import ast
from pathlib import Path

FORBIDDEN_IMPORT_MARKERS = ("application", "api", "fastapi")

INFRASTRUCTURE_FILES = (
    "repositories/sqlalchemy_role_repository.py",
    "repositories/sqlalchemy_permission_group_repository.py",
    "repositories/sqlalchemy_permission_repository.py",
    "repositories/sqlalchemy_role_permission_repository.py",
    "repositories/sqlalchemy_organization_role_repository.py",
    "repositories/sqlalchemy_user_role_repository.py",
    "services/sqlalchemy_permission_checker.py",
    "services/sqlalchemy_platform_user_reader.py",
    "persistence/mappers/role_mapper.py",
    "persistence/mappers/permission_group_mapper.py",
    "persistence/mappers/permission_mapper.py",
    "persistence/mappers/organization_role_mapper.py",
    "persistence/mappers/user_role_mapper.py",
)


def _file_path(relative: str) -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "infrastructure"
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


def test_infrastructure_authorization_modules_do_not_import_application_or_api() -> None:
    violations: dict[str, list[str]] = {}

    for relative in INFRASTRUCTURE_FILES:
        forbidden = _collect_forbidden_imports(_file_path(relative))
        if forbidden:
            violations[relative] = forbidden

    assert violations == {}


def test_infrastructure_authorization_repositories_do_not_define_save() -> None:
    repository_dir = _file_path("repositories")
    violations: list[str] = []

    for path in repository_dir.glob("sqlalchemy_*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if isinstance(node, ast.FunctionDef) and node.name == "save":
                violations.append(f"{path.name}:save")

    assert violations == []
