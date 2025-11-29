#!/usr/bin/env bash

set -eou pipefail

# Namespace: pre_commit_ci

pre_commit_ci::find_repos() {
  gh repo list --limit 1000 --json nameWithOwner -q '.[].nameWithOwner'
}

pre_commit_ci::find_prs() {
  local repo="$1"
  gh pr list \
    --repo "$repo" \
    --search "[pre-commit.ci] in:title is:open" \
    --json number,title,state \
    --jq '.[] | .number'
}

pre_commit_ci::approve_pr() {
  local repo="$1"
  local pr_number="$2"
  gh pr review "$pr_number" --repo "$repo" --approve
}

pre_commit_ci::merge_pr() {
  local repo="$1"
  local pr_number="$2"
  gh pr merge "$pr_number" --repo "$repo" --squash --delete-branch
}

pre_commit_ci::process_repo() {
  local repo="$1"
  local pr_number

  while IFS= read -r pr_number; do
    echo "Approving and merging PR #$pr_number in $repo"
    pre_commit_ci::approve_pr "$repo" "$pr_number"
    pre_commit_ci::merge_pr "$repo" "$pr_number"
  done < <(pre_commit_ci::find_prs "$repo")
}

main() {
  local repo
  for repo in $(pre_commit_ci::find_repos); do
    pre_commit_ci::process_repo "$repo"
  done
}

main "$@"
