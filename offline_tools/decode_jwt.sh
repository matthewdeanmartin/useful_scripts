#!/usr/bin/env bash
set -euo pipefail

JWT="$1"
IFS='.' read -r HEADER PAYLOAD SIGNATURE <<<"$JWT"

echo "=== Header ==="
echo "$HEADER" | base64 -d 2>/dev/null | jq .

echo "=== Payload ==="
echo "$PAYLOAD" | base64 -d 2>/dev/null | jq .

echo "=== Signature (raw) ==="
echo "$SIGNATURE"