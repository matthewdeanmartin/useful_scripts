#!/usr/bin/env python3
"""
Scan immediate subdirectories for Git repos that still use Poetry.
Heuristics:
- presence of poetry.lock, OR
- pyproject.toml containing a [tool.poetry] section.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def is_git_repo(path: Path) -> bool:
    """Return True if `path` is a Git repository."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def uses_poetry(path: Path) -> bool:
    """
    Detect whether repo at `path` uses Poetry.

    - poetry.lock present, OR
    - pyproject.toml with '[tool.poetry]' in it.
    """
    poetry_lock = path / "poetry.lock"
    if poetry_lock.is_file():
        return True

    pyproject = path / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False
        return "[tool.poetry]" in text

    return False


def find_poetry_repos(root: Path) -> List[Path]:
    """Return all immediate subdirectories that are git repos using Poetry."""
    results: List[Path] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not is_git_repo(entry):
            continue
        if uses_poetry(entry):
            results.append(entry)
    return results


def main() -> None:
    root = Path.cwd()
    print(f"🔍 Scanning for Poetry-based repos in: {root}")

    poetry_repos = find_poetry_repos(root)

    if not poetry_repos:
        print("✅ No Poetry-based repos found among immediate subdirectories.")
        return

    print("\n📦 Repos still using Poetry:\n")
    for repo in poetry_repos:
        print(f"📁 {repo.name} 🧪")

    print(f"\n📊 Total Poetry repos: {len(poetry_repos)}")


if __name__ == "__main__":
    main()
