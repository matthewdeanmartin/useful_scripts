#!/usr/bin/env bash
set -euo pipefail

JWT="$1"
PAYLOAD=$(echo "$JWT" | cut -d. -f2 | base64 -d 2>/dev/null)
EXP=$(echo "$PAYLOAD" | jq '.exp')

if [[ -z "$EXP" || "$EXP" == "null" ]]; then
  echo "No exp field found."
  exit 1
fi

NOW=$(date +%s)
if (( NOW < EXP )); then
  echo "✅ Token is still valid (expires at $(date -d @"$EXP"))"
else
  echo "❌ Token is expired (expired at $(date -d @"$EXP"))"
fi