#!/bin/bash

set -eu

readonly IMAGE_NAME="ghcr.io/datadog/dd-dependency-sniffer"

# Use buildkit to match CI as closely as possible.
export DOCKER_BUILDKIT=1

# Cache the same RFC 3339 timestamp for re-use in all images built in the same batch.
BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
GIT_HEAD_REF="$(git show-ref --head --hash ^HEAD)"

function do_build() {
  docker buildx build \
    --platform linux/amd64,linux/arm64/v8 \
    --label org.opencontainers.image.created="$BUILD_DATE" \
    --label org.opencontainers.image.source=https://github.com/DataDog/dd-dependency-sniffer \
    --label org.opencontainers.image.revision="$GIT_HEAD_REF" \
    --push \
    --tag "$IMAGE_NAME:latest" \
    ./docker
}

do_build