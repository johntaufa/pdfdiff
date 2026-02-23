#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/.venv/bin/activate"

pdfdiff compare \
    -t "$SCRIPT_DIR/test-pdfs" \
    -r "$SCRIPT_DIR/reference" \
    -o "$SCRIPT_DIR/results" \
    "$@"
