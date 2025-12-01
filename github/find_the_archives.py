#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass
class ArchivedClone:
    path: Path
    owner: str
    name: str
    updated_at: datetime


def configure_logging(quiet: bool, verbose: bool) -> None:
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def run_command(args: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    """Run a command and return stdout, or None on failure."""
    logging.debug("Running command: %s (cwd=%s)", " ".join(args), cwd)
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd is not None else None,
            check=True,
            capture_output=True,
            text=True,
        )
        logging.debug("Command stdout: %s", result.stdout.strip())
        logging.debug("Command stderr: %s", result.stderr.strip())
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.warning("Command failed (%s): %s", e.returncode, " ".join(args))
        logging.debug("Failed stdout: %s", e.stdout)
        logging.debug("Failed stderr: %s", e.stderr)
        return None


def find_git_repos(root: Path) -> List[Path]:
    """Find immediate child directories that are git repositories."""
    repos: List[Path] = []
    for entry in root.iterdir():
        if entry.is_dir():
            git_dir = entry / ".git"
            if git_dir.is_dir():
                logging.debug("Found git repo: %s", entry)
                repos.append(entry)
            else:
                logging.debug("Skipping non-git directory: %s", entry)
    return repos


def parse_github_remote(remote_url: str) -> Optional[Tuple[str, str]]:
    """
    Parse a GitHub remote URL into (owner, repo_name).

    Supports common patterns like:
      - git@github.com:owner/repo.git
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo
      - ssh://git@github.com/owner/repo.git
    """
    remote_url = remote_url.strip()
    logging.debug("Parsing remote URL: %s", remote_url)

    if "github.com" not in remote_url:
        logging.debug("Remote URL is not GitHub: %s", remote_url)
        return None

    # Normalize separator after github.com to always be '/'
    # e.g. git@github.com:owner/repo.git -> github.com/owner/repo.git
    if ":" in remote_url and remote_url.startswith("git@github.com"):
        _, after = remote_url.split("git@github.com", 1)
        after = after.lstrip(":")
        normalized = f"github.com/{after}"
    else:
        # Strip protocol if present
        for prefix in ("https://", "http://", "ssh://", "git://"):
            if remote_url.startswith(prefix):
                remote_url = remote_url[len(prefix) :]
                break
        normalized = remote_url

    # At this point expect "github.com/owner/repo[.git]"
    parts = normalized.split("/")
    try:
        idx = parts.index("github.com")
    except ValueError:
        logging.debug("Could not find github.com in normalized URL: %s", normalized)
        return None

    if len(parts) < idx + 3:
        logging.debug("Normalized URL too short to parse owner/repo: %s", normalized)
        return None

    owner = parts[idx + 1]
    repo = parts[idx + 2]

    # Strip .git suffix if present
    if repo.endswith(".git"):
        repo = repo[:-4]

    logging.debug("Parsed owner=%s, repo=%s from remote", owner, repo)
    return owner, repo


def get_repo_remote_owner_name(repo_path: Path) -> Optional[Tuple[str, str]]:
    """Get (owner, repo_name) for the 'origin' remote of a given repo."""
    stdout = run_command(["git", "-C", str(repo_path), "remote", "get-url", "origin"])
    if stdout is None:
        logging.warning("No origin remote for repo: %s", repo_path)
        return None

    owner_repo = parse_github_remote(stdout.strip())
    if owner_repo is None:
        logging.warning("Could not parse GitHub remote for repo: %s", repo_path)
    return owner_repo


def parse_iso8601(dt_str: str) -> datetime:
    """Parse GitHub ISO 8601 timestamps into timezone-aware datetimes."""
    dt_str = dt_str.strip()
    # GitHub returns something like "2023-01-02T03:04:05Z"
    if dt_str.endswith("Z"):
        dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str).astimezone(timezone.utc)


def query_github_repo(owner: str, name: str) -> Optional[Tuple[bool, datetime]]:
    """
    Use `gh` CLI to query if a repo is archived and when it was last updated.

    Returns:
        (is_archived, updated_at) or None if the query fails.
    """
    json_fields = "isArchived,updatedAt"
    stdout = run_command(
        ["gh", "repo", "view", f"{owner}/{name}", "--json", json_fields]
    )
    if stdout is None:
        logging.warning("Failed to query GitHub for %s/%s", owner, name)
        return None

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        logging.warning("Failed to decode JSON from gh for %s/%s: %s", owner, name, e)
        return None

    is_archived = bool(data.get("isArchived", False))
    updated_at_str = data.get("updatedAt")
    if not updated_at_str:
        logging.warning("No updatedAt field for %s/%s", owner, name)
        return None

    updated_at = parse_iso8601(updated_at_str)
    logging.debug(
        "GitHub repo %s/%s: is_archived=%s, updated_at=%s",
        owner,
        name,
        is_archived,
        updated_at,
    )
    return is_archived, updated_at


def inspect_repo_for_archived_clone(
    repo_path: Path,
    focus_owner: Optional[str],
) -> Optional[ArchivedClone]:
    owner_repo = get_repo_remote_owner_name(repo_path)
    if owner_repo is None:
        return None

    owner, name = owner_repo
    if focus_owner is not None and owner.lower() != focus_owner.lower():
        logging.info(
            "Skipping repo %s (owner %s != focus owner %s)",
            repo_path,
            owner,
            focus_owner,
        )
        return None

    gh_info = query_github_repo(owner, name)
    if gh_info is None:
        return None

    is_archived, updated_at = gh_info
    if not is_archived:
        logging.debug("Repo is not archived: %s/%s (%s)", owner, name, repo_path)
        return None

    logging.info("💀 Archived repo clone detected: %s/%s (%s)", owner, name, repo_path)
    return ArchivedClone(path=repo_path, owner=owner, name=name, updated_at=updated_at)


def find_archived_clones(root: Path, owner: Optional[str]) -> List[ArchivedClone]:
    repos = find_git_repos(root)
    logging.info("Scanning %d git repos under %s", len(repos), root)

    archived: List[ArchivedClone] = []
    for repo_path in repos:
        result = inspect_repo_for_archived_clone(repo_path, owner)
        if result is not None:
            archived.append(result)

    return archived


def print_report(root: Path, archived: Iterable[ArchivedClone]) -> None:
    archived_list = sorted(
        archived, key=lambda a: a.updated_at, reverse=True
    )  # newest first

    if not archived_list:
        print("✅ No local clones of archived GitHub repositories were found.")
        return

    print("🧊 Archived GitHub clones found (sorted by last update):")
    for item in archived_list:
        rel_path = item.path.relative_to(root)
        updated_str = item.updated_at.isoformat()
        print(
            f"  🧊 {item.owner}/{item.name} "
            f"📁 {rel_path} "
            f"🕒 updated {updated_str}"
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scan the current directory for git repos that are clones of "
            "archived GitHub projects for a given account."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory to scan (default: current working directory).",
    )
    parser.add_argument(
        "--owner",
        default="matthewdeanmartin",
        help="GitHub username/owner to filter on (default: %(default)s).",
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode: warnings and errors only.",
    )
    verbosity.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose mode: detailed debug logging.",
    )

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    root: Path = args.root
    owner: str = args.owner
    quiet: bool = args.quiet
    verbose: bool = args.verbose

    configure_logging(quiet=quiet, verbose=verbose)

    logging.info("Root directory: %s", root)
    logging.info("GitHub owner: %s", owner)

    archived = find_archived_clones(root, owner=owner)
    print_report(root, archived)


if __name__ == "__main__":
    main()
