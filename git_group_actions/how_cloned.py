#!/usr/bin/env python3
"""
Scan immediate subdirectories of the current directory that are git repositories
and determine whether their `origin` remote is cloned via HTTPS or SSH.

Results are grouped by clone type at the end. 🚀
"""

from __future__ import annotations

import argparse
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Iterable, List, Literal, Optional, Tuple


CloneType = Literal["ssh", "https", "other", "none"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify git repositories in the current directory by clone URL type."
    )
    parser.add_argument(
        "-u",
        "--show-urls",
        action="store_true",
        help="Show full remote URLs in the output.",
    )
    return parser.parse_args()


def iter_git_repos(root: Path) -> Iterable[Path]:
    """Yield immediate subdirectories of `root` that look like git repositories."""
    for entry in root.iterdir():
        if entry.is_dir() and (entry / ".git").exists():
            yield entry


def get_origin_url(repo: Path) -> Optional[str]:
    """Return the `remote.origin.url` for the repo, or None if not set / error."""
    try:
        proc: CompletedProcess[str] = run(
            ["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=False,
        )
    except CalledProcessError as exc:  # shouldn't happen with check=False
        print(f"💥 Error reading origin for {repo}: {exc}")
        return None

    if proc.returncode != 0:
        return None

    url = proc.stdout.strip()
    return url or None


def classify_clone_type(url: Optional[str]) -> CloneType:
    """Classify the clone type based on the origin URL."""
    if url is None:
        return "none"

    lowered = url.lower()

    if lowered.startswith("git@") or lowered.startswith("ssh://"):
        return "ssh"
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return "https"
    return "other"


def main() -> int:
    args = parse_args()
    root = Path.cwd()

    print("🔍 Scanning git repositories for clone type...\n")

    ssh_repos: List[Tuple[Path, Optional[str]]] = []
    https_repos: List[Tuple[Path, Optional[str]]] = []
    other_repos: List[Tuple[Path, Optional[str]]] = []
    none_repos: List[Tuple[Path, Optional[str]]] = []

    for repo in iter_git_repos(root):
        url = get_origin_url(repo)
        ctype = classify_clone_type(url)

        if ctype == "ssh":
            ssh_repos.append((repo, url))
        elif ctype == "https":
            https_repos.append((repo, url))
        elif ctype == "other":
            other_repos.append((repo, url))
        else:
            none_repos.append((repo, url))

    def print_group(
        title: str, icon: str, items: List[Tuple[Path, Optional[str]]]
    ) -> None:
        print(f"{icon} {title}:")
        if not items:
            print("   • (none)")
            return
        for repo, url in items:
            if args.show_urls and url:
                print(f"   • {repo.name} → {url}")
            else:
                print(f"   • {repo.name}")
        print()

    print_group("SSH clones", "🔐", ssh_repos)
    print_group("HTTPS clones", "🌐", https_repos)
    print_group("Other/unknown URL schemes", "⚙️", other_repos)
    print_group("No origin remote configured", "❓", none_repos)

    print("✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
