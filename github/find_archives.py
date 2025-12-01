#!/usr/bin/env python3
"""
Scan current directory vs GitHub account and report repos that are NOT cloned locally.

Assumptions (because the prompt was slightly contradictory):
- Use GitHub account `matthewdeanmartin` (override with --user).
- Skip forks and archived repos.
- "Do not report the repos that have been cloned already" → only report repos
  that DO NOT have a folder of the same name in the current directory.
- A "clone" is a directory in the current folder whose name == repo name.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Set


@dataclass
class RepoInfo:
    name: str
    is_fork: bool
    is_archived: bool
    updated_at: datetime
    url: str


def run_gh_repo_list(user: str) -> List[RepoInfo]:
    """Call `gh repo list` and return structured repo info."""
    cmd = [
        "gh",
        "repo",
        "list",
        user,
        "--limit",
        "1000",
        "--json",
        "name,isFork,isArchived,updatedAt,url",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to run gh repo list: {exc.stderr.strip() or exc.stdout.strip()}"
        ) from exc

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse JSON from gh output") from exc

    repos: List[RepoInfo] = []
    for item in raw:
        updated_raw = item.get("updatedAt")
        # GitHub returns ISO 8601, usually with trailing Z
        if not isinstance(updated_raw, str):
            continue
        updated = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))

        repos.append(
            RepoInfo(
                name=item["name"],
                is_fork=bool(item.get("isFork")),
                is_archived=bool(item.get("isArchived")),
                updated_at=updated,
                url=item.get("url", ""),
            )
        )

    return repos


def find_local_dirs(root: Path) -> Set[str]:
    """Return a set of directory names directly under root."""
    return {p.name for p in root.iterdir() if p.is_dir()}


def compute_uncloned_repos(
    repos: List[RepoInfo],
    local_dir_names: Set[str],
) -> List[RepoInfo]:
    """
    Filter to repos that:
    - are not forks
    - are not archived
    - do NOT have a local directory of the same name
    Then sort by last updated (descending).
    """
    filtered = [
        r
        for r in repos
        if not r.is_fork and not r.is_archived and r.name not in local_dir_names
    ]
    filtered.sort(key=lambda r: r.updated_at, reverse=True)
    return filtered


def format_repo_line(repo: RepoInfo) -> str:
    updated_str = repo.updated_at.isoformat()
    return f"📦 {repo.name}  ⏱ {updated_str}  🔗 {repo.url}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report GitHub repos that are not cloned in the current directory."
    )
    parser.add_argument(
        "--user",
        "-u",
        default="matthewdeanmartin",
        help="GitHub username (default: %(default)s)",
    )
    parser.add_argument(
        "--path",
        "-p",
        type=Path,
        default=Path("."),
        help="Directory to scan for local clones (default: current directory)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    root: Path = args.path.resolve()
    print(f"🔍 Scanning local path: {root}")
    local_dirs = find_local_dirs(root)

    print(f"🌐 Querying GitHub user: {args.user}")
    repos = run_gh_repo_list(args.user)

    uncloned = compute_uncloned_repos(repos, local_dirs)

    if not uncloned:
        print("✅ All non-fork, non-archived repos appear to be cloned here.")
        return

    print("\n📋 Repos NOT cloned in this directory (sorted by last update):\n")
    for repo in uncloned:
        print(format_repo_line(repo))


if __name__ == "__main__":
    main()
