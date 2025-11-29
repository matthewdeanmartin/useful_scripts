#!/usr/bin/env python3
"""
Scan all immediate subdirectories of the current folder.
For each project that contains a `.venv`, check if it's Python 3.14.
If not, report it as a problem. Otherwise, count it as good.

Usage:
    python check_venvs.py
"""

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional


def get_python_version(venv_path: Path) -> Optional[str]:
    """Return the Python version string from the given .venv or None if invalid."""
    exe = venv_path / "Scripts" / "python.exe" if (venv_path / "Scripts" / "python.exe").exists() \
        else venv_path / "bin" / "python"
    if not exe.exists():
        return None

    try:
        result = subprocess.run(
            [str(exe), "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return None


def main() -> None:
    base = Path.cwd()
    good = 0
    bad: list[tuple[str, str]] = []

    for project_dir in base.iterdir():
        if not project_dir.is_dir():
            continue
        venv = project_dir / ".venv"
        if not venv.exists():
            continue

        version = get_python_version(venv)
        if version is None:
            bad.append((project_dir.name, "no python found"))
        elif "3.14" in version:
            good += 1
        else:
            bad.append((project_dir.name, version))

    # Output
    if bad:
        print("Non-3.14 virtual environments detected:")
        for name, version in bad:
            print(f"  {name}: {version}")
    print(f"\n{good} good repos")


if __name__ == "__main__":
    main()
