#!/usr/bin/env bash
set -euo pipefile

MSYS_NO_PATHCONV=1 docker run -it  --rm -v "$PWD:/app" -w /app python python "$@"