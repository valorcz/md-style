#!/usr/bin/env bash
set -euo pipefail

# Use the actual path of the script, regardless of the symlinks
SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

exec uv run --project "$PROJECT_DIR" md-to-report "$@"
