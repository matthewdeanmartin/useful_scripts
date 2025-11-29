#!/usr/bin/env bash
set -euo pipefail

main() {
  local base_dir
  base_dir="$(pwd)"
  find_and_process_repos "$base_dir"
}

find_and_process_repos() {
  declare root="$1"
  shopt -s nullglob
  for dir in "$root"/*; do
    if [[ -d "$dir/.git" ]]; then
      process_repo "$dir"
    fi
  done
  shopt -u nullglob
}

process_repo() {
  declare repo="$1"
  (
    cd "$repo" || exit 1

    git rev-parse --is-inside-work-tree &>/dev/null || exit 0

    local files=()
    [[ -f ".pre-commit-config.yaml" ]] && files+=(".pre-commit-config.yaml")
    [[ -f "pyproject.toml" ]] && files+=("pyproject.toml")

    if (( ${#files[@]} == 0 )); then
      exit 0
    fi

    git add "${files[@]}" || exit 0

    if ! git diff --cached --quiet; then
      git commit -m "chore: commit config updates" || exit 0
      git push || exit 0
    fi
  ) || echo "⚠️  Failed in: $repo" >&2
}

main "$@"
