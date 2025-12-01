#!/usr/bin/env python3
"""
Report GitHub repositories for a user that are NOT cloned
into the specified local directory (by matching folder names).

Requires:
  - GitHub CLI (`gh`) installed and authenticated.

Skips:
  - Forked repositories
  - Archived repositories
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Set


@dataclass
class Repo:
    name: str
    html_url: str
    updated_at: datetime
    fork: bool
    archived: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Repo":
        updated_raw: str = data.get("updated_at", "")
        # GitHub returns ISO 8601 timestamps, e.g. "2025-11-30T12:34:56Z"
        if updated_raw.endswith("Z"):
            updated_raw = updated_raw.replace("Z", "+00:00")
        updated_at = datetime.fromisoformat(updated_raw)

        return cls(
            name=data["name"],
            html_url=data["html_url"],
            updated_at=updated_at,
            fork=bool(data.get("fork", False)),
            archived=bool(data.get("archived", False)),
        )


def run_gh_repos(username: str) -> List[Repo]:
    """
    Use `gh api` to fetch all repos for a user, handling pagination.
    Returns a list of Repo objects.
    """
    cmd: list[str] = [
        "gh",
        "api",
        "-H",
        "Accept: application/vnd.github+json",
        f"/users/{username}/repos",
        "--paginate",
        "--jq",
        ".[]",
    ]

    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        print("❌ `gh` CLI not found on PATH. Install GitHub CLI and try again.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print("❌ Failed to query GitHub via `gh api`.", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(exc.returncode)

    repos: list[Repo] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        data: dict[str, Any] = json.loads(line)
        repos.append(Repo.from_dict(data))

    return repos


def get_local_repo_names(root: Path) -> Set[str]:
    """
    Return the set of directory names directly under `root`.
    These are treated as existing clones.
    """
    return {p.name for p in root.iterdir() if p.is_dir()}


def filter_missing_repos(repos: Iterable[Repo], local_names: Set[str]) -> List[Repo]:
    """
    Filter to repos that:
      - are not forks
      - are not archived
      - do not already exist as a directory (by name) in local_names
    """
    filtered: list[Repo] = []
    for repo in repos:
        if repo.fork:
            continue
        if repo.archived:
            continue
        if repo.name in local_names:
            continue
        filtered.append(repo)
    return filtered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="🔍 Report GitHub repos that are NOT cloned into the current folder."
    )
    parser.add_argument(
        "-u",
        "--username",
        default="matthewdeanmartin",
        help="GitHub username to inspect (default: %(default)s).",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=Path.cwd(),
        help="Directory to check for clones (default: current working directory).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_dir: Path = args.directory.resolve()
    username: str = args.username

    if not target_dir.exists():
        print(f"❌ Target directory does not exist: {target_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"🛰  Scanning GitHub account: {username}")
    print(f"📂 Local folder: {target_dir}")
    print("⏳ Fetching repositories via `gh api`...\n")

    repos: list[Repo] = run_gh_repos(username)
    local_names: set[str] = get_local_repo_names(target_dir)
    missing: list[Repo] = filter_missing_repos(repos, local_names)

    # Sort by last updated, descending (most recently updated first)
    missing.sort(key=lambda r: r.updated_at, reverse=True)

    if not missing:
        print("✅ All non-fork, non-archived repos appear to be cloned here.")
        return

    print("🚨 Repositories NOT cloned into this folder (sorted by last update):\n")
    for repo in missing:
        updated_str: str = repo.updated_at.isoformat()
        # Example output line with emojis
        print(
            f"📁 {repo.name}  |  🕒 {updated_str}  |  🔗 {repo.html_url}"
        )


if __name__ == "__main__":
    main()
