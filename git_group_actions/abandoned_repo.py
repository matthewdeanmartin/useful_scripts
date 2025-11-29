#!/usr/bin/env python3
"""
Find git repositories under the current directory that have fewer than N commits.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple

MIN_COMMITS: int = 10


def is_git_repo(path: Path) -> bool:
    """Return True if `path` is a Git repository."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def get_commit_count(path: Path) -> int:
    """
    Return the number of commits in the repo at `path`.
    If no commits or command fails, return 0.
    """
    result = subprocess.run(
        ["git", "-C", str(path), "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        # Likely no commits or invalid HEAD
        return 0

    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def find_small_repos(root: Path, min_commits: int) -> List[Tuple[Path, int]]:
    """
    Return list of (path, commit_count) for repos under `root`
    that have fewer than `min_commits` commits.
    """
    results: List[Tuple[Path, int]] = []

    for entry in root.iterdir():
        if not entry.is_dir():
            continue

        if not is_git_repo(entry):
            continue

        commit_count = get_commit_count(entry)
        if commit_count < min_commits:
            results.append((entry, commit_count))

    return results


def main() -> None:
    root = Path.cwd()
    print(f"🔍 Scanning for repos with < {MIN_COMMITS} commits in: {root}")

    small_repos = find_small_repos(root, MIN_COMMITS)

    if not small_repos:
        print(f"✅ No repositories with fewer than {MIN_COMMITS} commits found.")
        return

    print(f"\n📉 Repositories with fewer than {MIN_COMMITS} commits:\n")
    for path, count in small_repos:
        print(f"📁 {path.name}: {count} commit(s) ⚠️")

    print(f"\n📊 Total repos with < {MIN_COMMITS} commits: {len(small_repos)}")


if __name__ == "__main__":
    main()

