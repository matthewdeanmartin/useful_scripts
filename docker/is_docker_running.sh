#!/usr/bin/env bash
set -euo pipefail

echo "Checking if Docker daemon is running..."

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Attempting to start Docker Desktop..."
  # powershell.exe -Command "Start-Process 'Docker Desktop' -Verb RunAs" >/dev/null 2>&1 &
  "/c/Program Files/Docker/Docker/frontend/Docker Desktop.exe"
  echo "Docker Desktop launched. Waiting for Docker to become available..."

  # Wait up to 60 seconds for Docker to start
  for i in {1..60}; do
    if docker info >/dev/null 2>&1; then
      echo "Docker is now running."
      exit 0
    fi
    sleep 1
  done

  echo "Docker did not start in time."
  exit 1
else
  echo "Docker is already running."
fi