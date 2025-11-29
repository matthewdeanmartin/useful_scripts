#!/usr/bin/env python3
"""
Scan current directory and report which subfolders are NOT git repositories.
"""

from pathlib import Path

def find_non_git_repos(root: Path) -> list[Path]:
    """Return subdirectories under `root` that do not contain a .git directory."""
    results: list[Path] = []
    for entry in root.iterdir():
        if entry.is_dir():
            if not (entry / ".git").is_dir():
                results.append(entry)
    return results


def main() -> None:
    root = Path.cwd()
    non_git = find_non_git_repos(root)

    if not non_git:
        print("✔️ All subfolders are git repositories.")
        return

    print("❌ Non-git directories detected:")
    for path in non_git:
        print(f"   • {path.name} 🚫")


if __name__ == "__main__":
    main()
