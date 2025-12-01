#!/usr/bin/env python3
"""
Scan immediate subdirectories of the current directory for git repos
that have local (uncommitted) changes.

"Changes" = anything `git add -A` would pick up:
  - modified files
  - deleted files
  - untracked files
  - etc.

Exit code:
  0 - no repos with local changes
  1 - at least one repo with local changes
"""

from __future__ import annotations

import argparse
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List git repos under the current directory that have local changes."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Also list clean repositories.",
    )
    return parser.parse_args()


def iter_git_repos(root: Path) -> Iterable[Path]:
    """Yield immediate subdirectories of `root` that look like git repositories."""
    for entry in root.iterdir():
        if entry.is_dir() and (entry / ".git").exists():
            yield entry


def git_status_porcelain(repo: Path) -> Tuple[bool, List[str]]:
    """
    Run `git status --porcelain` in `repo`.

    Returns:
        has_changes: True if there is any output.
        lines: Parsed non-empty status lines.
    """
    try:
        proc: CompletedProcess[str] = run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
    except CalledProcessError as exc:  # very unexpected here due to check=False
        # Treat as error, no changes detected.
        print(f"💥 Error inspecting {repo}: {exc}")
        return False, []

    if proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or "unknown git error"
        print(f"💥 Error inspecting {repo}: {msg}")
        return False, []

    lines: List[str] = [line.rstrip("\n") for line in proc.stdout.splitlines() if line.strip()]
    return bool(lines), lines


def main() -> int:
    args = parse_args()
    root = Path.cwd()

    print("🔍 Scanning for git repositories with local changes...\n")

    dirty: list[tuple[Path, list[str]]] = []

    for repo in iter_git_repos(root):
        has_changes, lines = git_status_porcelain(repo)

        if has_changes:
            dirty.append((repo, lines))
        elif args.verbose:
            print(f"✅ {repo.name} is clean.")

    if not dirty:
        if not args.verbose:
            print("✅ All git repositories are clean.")
        return 0

    print("⚠️ Repositories with local changes (would be picked up by `git add -A`):")
    for repo, lines in dirty:
        print(f"\n📁 {repo.name} ({len(lines)} path(s) changed)")
        for line in lines:
            print(f"   • {line}")

    print("\n⚠️ Done. At least one repository has local changes.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
