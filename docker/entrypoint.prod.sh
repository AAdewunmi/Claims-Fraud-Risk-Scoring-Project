#!/bin/sh
set -eu

# Backward-compatible shim. The canonical entrypoint is docker/entrypoint.sh.
exec /app/docker/entrypoint.sh "$@"
