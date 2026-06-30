#!/usr/bin/env python3
"""Run quality checks for KYROX Core backend."""

import compileall
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def check_compile() -> bool:
    print("==> Python compile check")
    success = compileall.compile_dir(str(BACKEND), quiet=1)
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
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(BACKEND / "tests"), "-v"],
        cwd=str(ROOT),
        env=env,
    )
    if result.returncode == 0:
        print("    PASS")
        return True
    print("    FAIL")
    return False


def main() -> int:
    results = [
        check_compile(),
        check_pytest(),
        check_import(),
    ]

    print()
    if all(results):
        print("All quality checks passed.")
        return 0

    print("Quality checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
