#!/usr/bin/env bash
set -e

# If no arguments provided, display help
if [ $# -eq 0 ]; then
    exec md-style --help
fi

# If first arg is a known shell or command, execute directly
case "$1" in
    sh|bash|python|python3|pytest|node)
        exec "$@"
        ;;
esac

# If first argument starts with a dash or matches md-style subcommands or is a file, run md-style
if [[ "$1" == -* ]] || [[ "$1" == *.md ]] || [[ "$1" == "inspect" ]] || [[ "$1" == "preview" ]] || [[ "$1" == "theme" ]]; then
    exec md-style "$@"
fi

# Fallback: if $1 is an executable in PATH, execute it; otherwise pass to md-style
if command -v "$1" >/dev/null 2>&1; then
    exec "$@"
else
    exec md-style "$@"
fi
