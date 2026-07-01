import ast
from pathlib import Path

FORBIDDEN_IMPORT_MARKERS = ("application", "api", "fastapi")

INFRASTRUCTURE_FILES = (
    "repositories/sqlalchemy_user_repository.py",
    "repositories/sqlalchemy_session_repository.py",
    "repositories/sqlalchemy_refresh_token_repository.py",
    "security/argon2_password_hasher.py",
    "security/jwt_token_service.py",
    "security/refresh_token_service.py",
    "clock.py",
    "persistence/mappers/user_mapper.py",
    "persistence/mappers/session_mapper.py",
    "persistence/mappers/refresh_token_mapper.py",
)


def _file_path(relative: str) -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "infrastructure"
        / "authentication"
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


def test_infrastructure_authentication_modules_do_not_import_application_or_api() -> None:
    violations: dict[str, list[str]] = {}

    for relative in INFRASTRUCTURE_FILES:
        forbidden = _collect_forbidden_imports(_file_path(relative))
        if forbidden:
            violations[relative] = forbidden

    assert violations == {}
