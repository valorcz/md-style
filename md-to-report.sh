#!/usr/bin/env sh
# md-to-report.sh - POSIX wrapper forwarding to native uv CLI entrypoint
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec uv run --project "$SCRIPT_DIR" md-to-report "$@"
