import ast
import importlib
import importlib.util
from pathlib import Path

LEGACY_RBAC_REPOSITORY_CLASSES = (
    "SqlAlchemyRoleRepository",
    "SqlAlchemyPermissionRepository",
    "SqlAlchemyRolePermissionRepository",
    "SqlAlchemyPermissionChecker",
)

LEGACY_RBAC_ENTITY_NAMES = ("Role", "Permission", "RolePermission")

LEGACY_RBAC_MAPPER_FUNCTIONS = (
    "role_to_domain",
    "role_to_model",
    "permission_to_domain",
    "permission_to_model",
    "role_permission_to_domain",
    "role_permission_to_model",
    "organization_role_to_model",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "app.modules.identity.api.dependencies",
    "app.modules.identity.api.guards",
    "app.modules.identity.api.context",
    "app.modules.identity.domain.exceptions",
)


def _identity_root() -> Path:
    return Path(__file__).resolve().parents[4] / "app" / "modules" / "identity"


def _collect_imports(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []

    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

    return imports


def test_repositories_module_has_no_legacy_rbac_classes() -> None:
    repositories = importlib.import_module("app.modules.identity.infrastructure.repositories")

    for class_name in LEGACY_RBAC_REPOSITORY_CLASSES:
        assert not hasattr(repositories, class_name)


def test_domain_entities_has_no_legacy_rbac_types() -> None:
    entities = importlib.import_module("app.modules.identity.domain.entities")

    for entity_name in LEGACY_RBAC_ENTITY_NAMES:
        assert not hasattr(entities, entity_name)


def test_domain_ports_has_no_legacy_rbac_protocols() -> None:
    ports = importlib.import_module("app.modules.identity.domain.ports")

    assert not hasattr(ports, "RoleRepository")
    assert not hasattr(ports, "PermissionRepository")
    assert not hasattr(ports, "RolePermissionRepository")
    assert not hasattr(ports, "PermissionChecker")


def test_persistence_mappers_has_no_legacy_rbac_functions() -> None:
    mappers = importlib.import_module("app.modules.identity.infrastructure.persistence.mappers")

    for function_name in LEGACY_RBAC_MAPPER_FUNCTIONS:
        assert not hasattr(mappers, function_name)


def test_legacy_authorization_exception_module_removed() -> None:
    spec = importlib.util.find_spec("app.modules.identity.domain.exceptions")
    assert spec is None


def test_production_modules_do_not_import_legacy_authorization_paths() -> None:
    violations: dict[str, list[str]] = {}

    for path in _identity_root().rglob("*.py"):
        relative = str(path.relative_to(_identity_root()))
        if relative.startswith("infrastructure/authorization/"):
            continue
        if relative.startswith("application/authorization/"):
            continue
        if relative.startswith("domain/authorization/"):
            continue
        if relative.startswith("api/authorization/"):
            continue

        forbidden = [
            module_name
            for module_name in _collect_imports(path)
            if any(
                module_name == prefix or module_name.startswith(f"{prefix}.")
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            )
        ]
        if forbidden:
            violations[relative] = forbidden

    assert violations == {}
