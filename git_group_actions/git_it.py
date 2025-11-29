from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

HAD_ERRORS: bool = False


def report_error(repo: Optional[Path], cmd: List[str], returncode: int, stderr_text: str) -> None:
    """
    Log an error for a given repo/command and mark global error flag.
    """
    global HAD_ERRORS
    HAD_ERRORS = True
    target = repo.name if repo is not None else "."
    command_str = " ".join(cmd)
    sys.stderr.write(f"❌ [{target}] Command failed (exit {returncode}): {command_str}\n")
    if stderr_text.strip():
        sys.stderr.write(f"   ↳ {stderr_text.strip()}\n")


def run_cmd(args: List[str], cwd: Path) -> Tuple[int, str, str]:
    """
    Run a subprocess command and return (returncode, stdout, stderr).
    Always catches FileNotFoundError and reports it as an error.
    """
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as exc:
        report_error(cwd, args, 127, f"Executable not found: {exc}")
        return 127, "", str(exc)


def is_git_repo(path: Path) -> bool:
    """
    Detect if a directory is a git repository by checking for a .git directory.
    """
    return (path / ".git").exists()


def has_uncommitted_changes(path: Path) -> Optional[bool]:
    """
    Return True if there are uncommitted changes, False if clean.
    If an error occurs, report it and return None.
    """
    code, out, err = run_cmd(["git", "status", "--porcelain"], path)
    if code != 0:
        report_error(path, ["git", "status", "--porcelain"], code, err)
        return None
    return bool(out.strip())


def get_unpushed_commit_count(path: Path) -> Optional[int]:
    """
    Return count of commits ahead of upstream, or 0 if none.
    If no upstream or an error occurs, report it and return None.
    """
    code, out, err = run_cmd(["git", "rev-list", "--count", "@{u}..HEAD"], path)
    if code != 0:
        # No upstream or some error – treat as error but don't guess.
        report_error(path, ["git", "rev-list", "--count", "@{u}..HEAD"], code, err)
        return None
    text = out.strip()
    try:
        return int(text)
    except ValueError:
        report_error(path, ["git", "rev-list", "--count", "@{u}..HEAD"], code, f"Unexpected output: {text}")
        return None


def iter_child_dirs(root: Path) -> List[Path]:
    """
    Return a sorted list of immediate child directories of root.
    """
    return sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name.lower())


def cmd_stranded(root: Path, verbose: bool) -> None:
    """
    Inspect repos for uncommitted or unpushed work.
    """
    uncommitted: List[Path] = []
    unpushed: List[Tuple[Path, int]] = []
    clean: List[Path] = []
    non_git: List[Path] = []

    print("🔍 Checking for stranded work…")

    for d in iter_child_dirs(root):
        if not is_git_repo(d):
            non_git.append(d)
            continue

        uncomm = has_uncommitted_changes(d)
        unpushed_count = get_unpushed_commit_count(d)

        if uncomm:
            uncommitted.append(d)

        if unpushed_count is not None and unpushed_count > 0:
            unpushed.append((d, unpushed_count))

        if uncomm is False and (unpushed_count == 0):
            clean.append(d)

    if uncommitted:
        print("✏️ Repos with uncommitted changes:")
        for d in uncommitted:
            print(f"  - {d.name}")
    else:
        print("✏️ No repos with uncommitted changes found.")

    if unpushed:
        print("📤 Repos with unpushed commits:")
        for d, count in unpushed:
            print(f"  - {d.name} (ahead by {count} commit{'s' if count != 1 else ''})")
    else:
        print("📤 No repos with unpushed commits found (for branches with an upstream).")

    if verbose:
        if clean:
            print("✅ Clean repos (no uncommitted or unpushed work):")
            for d in clean:
                print(f"  - {d.name}")
        if non_git:
            print("📁 Non-git directories:")
            for d in non_git:
                print(f"  - {d.name}")


def cmd_pull(root: Path) -> None:
    """
    Fetch and pull all git repos using the currently active branch.
    """
    print("⬇️  Fetching and pulling all repositories…")
    for d in iter_child_dirs(root):
        if not is_git_repo(d):
            continue
        print(f"📥 [{d.name}] git fetch && git pull")
        code_f, out_f, err_f = run_cmd(["git", "fetch", "--all"], d)
        if code_f != 0:
            report_error(d, ["git", "fetch", "--all"], code_f, err_f)
        elif out_f.strip():
            print(out_f.strip())

        code_p, out_p, err_p = run_cmd(["git", "pull"], d)
        if code_p != 0:
            report_error(d, ["git", "pull"], code_p, err_p)
        elif out_p.strip():
            print(out_p.strip())


def cmd_push(root: Path) -> None:
    """
    Push all repos that have unpushed commits. Do not stage anything.
    """
    print("⬆️  Pushing repositories with unpushed commits…")
    for d in iter_child_dirs(root):
        if not is_git_repo(d):
            continue

        count = get_unpushed_commit_count(d)
        if count is None:
            # Error already reported; skip.
            continue
        if count == 0:
            continue

        print(f"🚀 [{d.name}] git push (ahead by {count} commit{'s' if count != 1 else ''})")
        code, out, err = run_cmd(["git", "push"], d)
        if code != 0:
            report_error(d, ["git", "push"], code, err)
        elif out.strip():
            print(out.strip())


def cmd_failing(root: Path) -> None:
    """
    For each local git repo, use `gh` to check the most recent GitHub Action run.
    Report repos where the most recent run concluded with failure.
    """
    print("🧪 Checking GitHub Actions for failing workflows…")
    any_reported = False

    for d in iter_child_dirs(root):
        if not is_git_repo(d):
            continue

        code, out, err = run_cmd(
            [
                "gh",
                "run",
                "list",
                "--limit",
                "1",
                "--json",
                "status,conclusion,name,headBranch,headSha",
            ],
            d,
        )
        if code != 0:
            report_error(
                d,
                ["gh", "run", "list", "--limit", "1", "--json", "status,conclusion,name,headBranch,headSha"],
                code,
                err,
            )
            continue

        text = out.strip()
        if not text:
            # No runs.
            continue

        try:
            data: List[Dict[str, Any]] = json.loads(text)
        except json.JSONDecodeError as exc:
            report_error(
                d,
                ["gh", "run", "list", "--limit", "1", "--json", "status,conclusion,name,headBranch,headSha"],
                code,
                f"JSON decode error: {exc}",
            )
            continue

        if not data:
            continue

        run = data[0]
        status = str(run.get("status", ""))
        conclusion = str(run.get("conclusion", ""))
        name = str(run.get("name", ""))
        branch = str(run.get("headBranch", ""))
        sha = str(run.get("headSha", ""))

        # Treat explicit failure conclusion as "failing".
        if conclusion.lower() == "failure":
            any_reported = True
            print(
                f"💥 [{d.name}] Most recent workflow is failing\n"
                f"    • Name: {name}\n"
                f"    • Branch: {branch}\n"
                f"    • SHA: {sha}\n"
                f"    • Status: {status}\n"
                f"    • Conclusion: {conclusion}"
            )

    if not any_reported:
        print("✅ No failing workflows detected (based on most recent runs).")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Operate on all git repositories in the current directory. 🧰",
    )
    parser.add_argument(
        "command",
        choices=["stranded", "stranded-commits", "pull", "push", "failing"],
        help="Operation to perform on each git repository.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="For 'stranded' commands, also list clean repos and non-git directories.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    global HAD_ERRORS
    args = parse_args(argv)
    root = Path.cwd()

    if args.command in ("stranded", "stranded-commits"):
        cmd_stranded(root, verbose=args.verbose)
    elif args.command == "pull":
        cmd_pull(root)
    elif args.command == "push":
        cmd_push(root)
    elif args.command == "failing":
        cmd_failing(root)
    else:
        # Argparse should prevent this, but keep a guard anyway.
        report_error(None, [str(args.command)], 1, "Unknown command")
        sys.exit(1)

    if HAD_ERRORS:
        print("⚠️  Completed with errors. See stderr for details.", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ Completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
