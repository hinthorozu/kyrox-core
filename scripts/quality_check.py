#!/usr/bin/env python3
"""Run quality checks for KYROX Core backend."""

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SCRIPTS = ROOT / "scripts"


def check_compile() -> bool:
    print("==> Python compile check")
    backend_ok = compileall.compile_dir(str(BACKEND), quiet=1)
    scripts_ok = compileall.compile_dir(str(SCRIPTS), quiet=1)
    success = backend_ok and scripts_ok
    if success:
        print("    PASS")
    else:
        print("    FAIL")
    return success


def check_import() -> bool:
    print("==> Import check")
    sys.path.insert(0, str(BACKEND))
    try:
        from app.main import create_app

        app = create_app()
        if app is None:
            raise RuntimeError("create_app() returned None")
        print("    PASS")
        return True
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return False


def check_pytest() -> bool:
    print("==> pytest")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        cwd=str(ROOT),
    )
    if result.returncode == 0:
        print("    PASS")
        return True
    print("    FAIL")
    return False


def main() -> int:
    results = [
        check_compile(),
        check_import(),
        check_pytest(),
    ]

    print()
    if all(results):
        print("All quality checks passed.")
        return 0

    print("Quality checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
