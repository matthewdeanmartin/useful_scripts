#!/usr/bin/env bash
set -euo pipefail

pretty_print_json() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  elif command -v python >/dev/null 2>&1; then
    python -m json.tool
  else
    echo "Error: Neither jq nor Python is available to pretty-print JSON." >&2
    exit 1
  fi
}

# Usage examples
# cat myfile.json | pretty_print_json