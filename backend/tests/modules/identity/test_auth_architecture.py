import ast
from pathlib import Path


def test_auth_module_does_not_import_infrastructure() -> None:
    auth_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "modules"
        / "identity"
        / "application"
        / "auth.py"
    )
    module = ast.parse(auth_path.read_text(encoding="utf-8"))

    infrastructure_imports: list[str] = []
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module and "infrastructure" in node.module:
            infrastructure_imports.append(node.module)

    assert infrastructure_imports == []
