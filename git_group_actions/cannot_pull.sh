#!/usr/bin/env bash
set -euo pipefail

main() {
  local base_dir
  base_dir="$(pwd)"
  find_and_test_repos "$base_dir"
}

find_and_test_repos() {
  declare dir="$1"
  shopt -s nullglob
  for repo_path in "$dir"/*; do
    if [[ -d "$repo_path/.git" ]]; then
      test_pull_failure "$repo_path"
    fi
  done
  shopt -u nullglob
}

test_pull_failure() {
  declare repo="$1"
  (
    cd "$repo"
    if git rev-parse --is-inside-work-tree &>/dev/null; then
      git pull --no-rebase --ff-only &>/dev/null || echo "$repo"
    fi
  )
}

main "$@"
