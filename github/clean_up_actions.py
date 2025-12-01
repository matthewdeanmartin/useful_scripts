#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path
import logging
import sys

# ===== Settings =====
# Set to True to only log what would be deleted without actually deleting.
DRY_RUN = False

# ===== Logging setup =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
log = logging.getLogger("precommit_ci_cleanup")


def is_git_repo(path: Path) -> bool:
    """Return True if path is a git repository."""
    if (path / ".git").exists():
        return True

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except FileNotFoundError:
        log.error("❌ git not found on PATH.")
        return False


def run_gh(args, cwd: Path):
    """Run `gh` with given args and return stdout text or None on error."""
    cmd = ["gh"] + args
    log.debug("🔧 Running: %s (cwd=%s)", " ".join(cmd), cwd)
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        log.error("❌ gh CLI not found on PATH.")
        return None

    if result.returncode != 0:
        log.error("⚠️ gh command failed in %s: %s", cwd, result.stderr.strip())
        return None

    return result.stdout


def list_precommit_runs(repo_path: Path):
    """
    Return a list of run dicts for the repo at repo_path where
    displayTitle starts with "[pre-commit.ci]".
    """
    # Request key fields via --json
    stdout = run_gh(
        [
            "run",
            "list",
            "--limit",
            "100",
            "--json",
            "databaseId,displayTitle,status,conclusion,workflowName",
        ],
        cwd=repo_path,
    )
    if stdout is None:
        return []

    try:
        runs = json.loads(stdout)
    except json.JSONDecodeError as e:
        log.error("⚠️ Failed to parse JSON from gh in %s: %s", repo_path, e)
        return []

    matches = []
    for run in runs:
        title = run.get("displayTitle") or ""
        if title.startswith("[pre-commit.ci]"):
            matches.append(run)
    return matches


def delete_run(repo_path: Path, run_id: int, title: str):
    """Delete a single run by numeric ID using gh."""
    if DRY_RUN:
        log.info("🧪 DRY RUN: would delete run %s (%s) in %s", run_id, title, repo_path)
        return

    stdout = run_gh(["run", "delete", str(run_id)], cwd=repo_path)
    if stdout is not None:
        log.info("🗑️ Deleted run %s (%s) in %s", run_id, title, repo_path)

def process_repo(repo_path: Path):
    """Scan a single repo for pre-commit.ci runs and delete them."""
    log.info("📦 Scanning repo: %s", repo_path)

    runs = list_precommit_runs(repo_path)
    if not runs:
        log.info("✅ No [pre-commit.ci] runs found in %s", repo_path)
        return

    log.info("🔎 Found %d [pre-commit.ci] runs in %s", len(runs), repo_path)
    for run in runs:
        run_id = run.get("databaseId")
        title = run.get("displayTitle", "<no title>")
        status = run.get("status")
        conclusion = run.get("conclusion")
        workflow_name = run.get("workflowName")

        log.info(
            "➡️  Run %s | title=%r | workflow=%r | status=%s | conclusion=%s",
            run_id,
            title,
            workflow_name,
            status,
            conclusion,
        )

        if run_id is None:
            log.warning("⚠️ Skipping run with missing databaseId in %s", repo_path)
            continue

        delete_run(repo_path, run_id, title)


def main():
    base = Path(".").resolve()
    log.info("🚀 Starting pre-commit.ci cleanup in %s (DRY_RUN=%s)", base, DRY_RUN)

    # Loop over direct subdirectories
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        # Skip .git etc
        if entry.name.startswith("."):
            continue

        if is_git_repo(entry):
            process_repo(entry)
        else:
            log.debug("📁 Skipping non-git directory: %s", entry)

    log.info("🏁 Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("⏹️ Interrupted by user.")
        sys.exit(1)
