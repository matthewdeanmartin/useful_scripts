#!/usr/bin/env python3
"""
Scan immediate subdirectories for Git repos, inspect their GitHub Actions
workflows, and report any workflows that use python-version < 3.14.

Heuristics:
- Look in .github/workflows/**/*.yml / **/*.yaml
- Parse lines containing "python-version" (including matrix configs)
- Compare numeric versions (e.g. 3.8, 3.10, 3.13.1) against 3.14.0
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Threshold: anything strictly less than this is considered "too old"
PYTHON_VERSION_THRESHOLD: Tuple[int, int, int] = (3, 14, 0)


def is_git_repo(path: Path) -> bool:
    """Return True if `path` is a Git repository."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def parse_version(version: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse a version string like '3.10', '3.13.1' into (3, 10, 0) / (3, 13, 1).
    Return None if it doesn't look like a numeric version.
    """
    version = version.strip()
    # Basic sanity filter
    if not re.fullmatch(r"\d+(?:\.\d+){1,2}", version):
        return None

    parts = version.split(".")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None

    # Pad to 3 components
    while len(nums) < 3:
        nums.append(0)

    return nums[0], nums[1], nums[2]


def is_legacy_python_version(version: str) -> bool:
    """True if the parsed version is < PYTHON_VERSION_THRESHOLD."""
    parsed = parse_version(version)
    if parsed is None:
        return False
    return parsed < PYTHON_VERSION_THRESHOLD


def extract_versions_from_text(text: str) -> List[str]:
    """
    Extract all version-like strings (e.g. 3.8, 3.10, 3.13.1) from a text fragment.
    """
    pattern = re.compile(r'["\']?(\d+(?:\.\d+){1,2})["\']?')
    return pattern.findall(text)


def find_legacy_python_versions_in_text(text: str) -> Set[str]:
    """
    Given full YAML text of a workflow file, find all python-version entries
    whose versions are < 3.14.

    Handles:
    - Inline: python-version: "3.10"
    - Inline list: python-version: ["3.10", "3.11"]
    - Matrix-style block:

        python-version:
          - "3.10"
          - "3.11"
    """
    lines = text.splitlines()
    legacy_versions: Set[str] = set()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if "python-version" not in line or ":" not in line:
            i += 1
            continue

        # Compute indentation and trailing text after colon
        indent = len(line) - len(line.lstrip())
        _, after_colon = line.split(":", 1)
        after_colon = after_colon.strip()

        if after_colon:
            # Inline scalar or list
            for ver in extract_versions_from_text(after_colon):
                if is_legacy_python_version(ver):
                    legacy_versions.add(ver)
            i += 1
            continue

        # Block-style: collect subsequent more-indented lines
        i += 1
        while i < n:
            sub = lines[i]
            stripped = sub.strip()

            # Skip empty/comment lines inside the block
            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            sub_indent = len(sub) - len(sub.lstrip())
            if sub_indent <= indent:
                # Dedent → end of this python-version block
                break

            # E.g. `- "3.10"` or `- 3.11`
            for ver in extract_versions_from_text(sub):
                if is_legacy_python_version(ver):
                    legacy_versions.add(ver)

            i += 1

        continue

    return legacy_versions


def find_legacy_python_versions_in_file(path: Path) -> Set[str]:
    """Return all legacy python versions referenced in a YAML workflow file."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    return find_legacy_python_versions_in_text(text)


def find_repos_with_legacy_actions(root: Path) -> Dict[Path, List[Tuple[Path, Set[str]]]]:
    """
    Scan immediate subdirectories of `root` for git repos, search their
    .github/workflows/*.yml|*.yaml files, and record ones with python-version < 3.14.

    Returns:
        { repo_path: [(workflow_file_path, {versions...}), ...], ... }
    """
    results: Dict[Path, List[Tuple[Path, Set[str]]]] = {}

    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not is_git_repo(entry):
            continue

        workflows_dir = entry / ".github" / "workflows"
        if not workflows_dir.is_dir():
            continue

        matching_files: List[Tuple[Path, Set[str]]] = []

        for pattern in ("*.yml", "*.yaml"):
            for wf in workflows_dir.rglob(pattern):
                legacy_versions = find_legacy_python_versions_in_file(wf)
                if legacy_versions:
                    matching_files.append((wf, legacy_versions))

        if matching_files:
            results[entry] = matching_files

    return results


def main() -> None:
    root = Path.cwd()
    print(f"🔍 Scanning GitHub Actions workflows under repos in: {root}")
    print(f"   Threshold: python-version < {'.'.join(map(str, PYTHON_VERSION_THRESHOLD))}\n")

    repos = find_repos_with_legacy_actions(root)

    if not repos:
        print("✅ No workflows found using python-version below 3.14. 🐍")
        return

    total_files = 0

    for repo_path, files in sorted(repos.items(), key=lambda item: item[0].name.lower()):
        print(f"📁 {repo_path.name}")
        for wf_path, versions in files:
            total_files += 1
            if not "tox" in str(wf_path):
                rel = wf_path.relative_to(repo_path)
                version_list = ", ".join(sorted(versions))
                print(f"   ├─ {rel} ⚠️ python-version(s): {version_list}")
        print()

    print(f"📊 Summary: {len(repos)} repos, {total_files} workflow file(s) using python-version < 3.14 🧮")


if __name__ == "__main__":
    main()
