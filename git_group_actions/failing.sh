#!/usr/bin/env bash

set -eou pipefail

# Namespace: gh_failing

gh_failing::get_repos() {
  gh repo list --limit 1000 --json nameWithOwner -q '.[].nameWithOwner'
}

gh_failing::get_latest_failed_run_url() {
  local repo="$1"
  local api_url

  api_url=$(gh run list --repo "$repo" --limit 1 \
    --json status,conclusion,url \
    -q '.[] | select(.status == "completed" and .conclusion == "failure") | .url') || return 1

  # Convert API URL to web URL
  # From: https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID
  # To:   https://github.com/OWNER/REPO/actions/runs/RUN_ID
  echo "${api_url/https:\/\/api.github.com\/repos/https:\/\/github.com}"
}

main() {
  local repo url
  for repo in $(gh_failing::get_repos); do
    if url=$(gh_failing::get_latest_failed_run_url "$repo"); then
      echo "$url"
    fi
  done
}

main "$@"
