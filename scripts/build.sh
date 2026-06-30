#!/usr/bin/env bash
# Build production Docker images with traceable metadata.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
BUILD_NUMBER="${BUILD_NUMBER:-local}"
BUILD_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
APP_VERSION="${APP_VERSION:-0.1.0}"
IMAGE_NAME="${IMAGE_NAME:-cast-it}"
IMAGE_TAG="${IMAGE_TAG:-${GIT_COMMIT}}"

echo "Building ${IMAGE_NAME}:${IMAGE_TAG}"
docker build \
  --file docker/Dockerfile \
  --target production \
  --build-arg BUILD_GIT_COMMIT="${GIT_COMMIT}" \
  --build-arg BUILD_NUMBER="${BUILD_NUMBER}" \
  --build-arg BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
  --build-arg APP_VERSION="${APP_VERSION}" \
  --build-arg IMAGE_TAG="${IMAGE_TAG}" \
  --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
  .

echo "Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
