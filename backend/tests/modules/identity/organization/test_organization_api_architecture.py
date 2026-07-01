import ast
from pathlib import Path

THIN_API_FILES = (
    "routes.py",
    "schemas.py",
    "mappers.py",
    "error_mapping.py",
)
LEGACY_APPLICATION_AUTH_PREFIX = "app.modules.identity.application.auth"


def _file_path(filename: str) -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "identity"
        / "api"
        / "organization"
        / filename
    )


def _api_root() -> Path:
    return Path(__file__).resolve().parents[4] / "app" / "modules" / "identity" / "api"


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


def test_organization_api_thin_modules_do_not_import_infrastructure() -> None:
    violations: dict[str, list[str]] = {}

    for filename in THIN_API_FILES:
        forbidden = _collect_forbidden_imports(_file_path(filename))
        if forbidden:
            violations[filename] = forbidden

    assert violations == {}


def test_membership_role_assigner_factory_is_defined_only_in_membership_dependencies() -> None:
    api_root = _api_root()
    definitions: list[Path] = []

    for path in api_root.rglob("dependencies.py"):
        source = path.read_text(encoding="utf-8")
        if "def get_membership_role_assigner" in source:
            definitions.append(path)

    expected = api_root / "membership" / "dependencies.py"
    assert definitions == [expected]


def test_organization_dependencies_import_role_assigner_from_membership() -> None:
    path = _api_root() / "organization" / "dependencies.py"
    source = path.read_text(encoding="utf-8")

    assert "def get_membership_role_assigner" not in source
    assert "app.modules.identity.api.membership.dependencies" in source
    assert "get_membership_role_assigner" in source
