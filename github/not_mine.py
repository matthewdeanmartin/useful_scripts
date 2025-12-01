#!/usr/bin/env python3
"""
Scan current directory for Git repos that are forks of someone else's repo.

Requirements:
- git and gh must be on PATH
- gh must be authenticated
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GITHUB_USERNAME: str = "matthewdeanmartin"


def is_git_repo(path: Path) -> bool:
    """Return True if `path` is a Git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except OSError:
        return False


def gh_repo_view(path: Path) -> Optional[Dict[str, Any]]:
    """
    Run `gh repo view` in the given repo directory and return parsed JSON,
    or None if the command fails.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                "--json",
                "name,owner,isFork,parent",
            ],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        print(f"⚠️  gh command not found when processing {path}")
        return None

    if result.returncode != 0:
        # Most likely not a GitHub repo, or no access
        stderr = result.stderr.strip()
        print(f"⚠️  Failed to query GitHub for {path.name}: {stderr}")
        return None

    try:
        data: Dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"⚠️  Failed to parse JSON for {path.name}: {exc}")
        return None

    return data


def is_fork_of_other_user(repo_info: Dict[str, Any], username: str) -> bool:
    """
    Return True if the repo is:
    - a fork
    - owned by `username`
    - and the parent repo is owned by someone else
    """
    is_fork: bool = bool(repo_info.get("isFork"))
    owner = repo_info.get("owner") or {}
    owner_login: str = owner.get("login", "")

    if not is_fork:
        return False

    # Parent can be None if GitHub didn't return it for some reason
    parent = repo_info.get("parent") or {}
    parent_owner = parent.get("owner") or {}
    parent_owner_login: str = parent_owner.get("login", "")

    return owner_login == username and parent_owner_login != username


def find_forked_repos(root: Path, username: str) -> List[Tuple[Path, Dict[str, Any]]]:
    """Return list of (path, repo_info) for repos that are forks of someone else."""
    results: List[Tuple[Path, Dict[str, Any]]] = []

    for entry in root.iterdir():
        if not entry.is_dir():
            continue

        if not is_git_repo(entry):
            continue

        repo_info = gh_repo_view(entry)
        if not repo_info:
            continue

        if is_fork_of_other_user(repo_info, username):
            results.append((entry, repo_info))

    return results


def main() -> None:
    root = Path.cwd()
    print(f"🔍 Scanning for forked repos in: {root}")

    forked_repos = find_forked_repos(root, GITHUB_USERNAME)

    if not forked_repos:
        print("✅ No forks of other users' repos found (owned by you).")
        return

    print("\n🍴 Forked repositories of other users (owned by you):\n")
    for path, info in forked_repos:
        name: str = info.get("name", path.name)
        owner = info.get("owner") or {}
        parent = info.get("parent") or {}
        parent_owner = parent.get("owner") or {}

        owner_login: str = owner.get("login", "?")
        parent_full_name: str = parent.get("nameWithOwner") or (
            f"{parent_owner.get('login', '?')}/{parent.get('name', '?')}"
            if parent_owner or parent
            else "unknown"
        )

        print(f"📁 {path.name}")
        print(f"   ├─ Repo: {owner_login}/{name}")
        print(f"   └─ Forked from: {parent_full_name}")
        print()

    print(f"📊 Total forked repos of others: {len(forked_repos)}")


if __name__ == "__main__":
    main()
