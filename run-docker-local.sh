#!/usr/bin/env bash
# run-docker-local.sh - build and run the jaxmusic docker image locally
set -euo pipefail

IMAGE_NAME="jaxmusic:local"

echo "Building Docker image..."
docker build -t "$IMAGE_NAME" .

if [ -z "${TELEGRAM_TOKEN-}" ]; then
  echo "Please set TELEGRAM_TOKEN environment variable before running."
  echo "On Linux/macOS: export TELEGRAM_TOKEN=\"your_token\""
  exit 1
fi

echo "Running container..."
docker run --rm -e TELEGRAM_TOKEN="$TELEGRAM_TOKEN" "$IMAGE_NAME"
