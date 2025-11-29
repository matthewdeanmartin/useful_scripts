#!/usr/bin/env bash
set -eou pipefail

main() {
  declare dir="${1:-$PWD}"
  dir="${dir%/}"  # Remove trailing slash

  for_git_pull::each_subdir "$dir"
}

for_git_pull::each_subdir() {
  declare target_dir="$1"
  local subdir

  for subdir in "$target_dir"/*/; do
    [[ -d "$subdir/.git" ]] || continue
    echo ">>> Pulling in: $subdir"
    git -C "$subdir" pull || echo "!!! Failed to pull in $subdir" >&2
  done
}

[[ "${BASH_SOURCE[0]}" == "$0" ]] && main "$@"
