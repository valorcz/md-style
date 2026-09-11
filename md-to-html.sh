#!/usr/bin/env bash
# ==============================================================================
# md-to-html.sh - Compatibility wrapper for md-to-report.sh
# ==============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
exec "${SCRIPT_DIR}/md-to-report.sh" "$@"
