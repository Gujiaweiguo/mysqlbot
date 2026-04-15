#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

"$SCRIPT_DIR/dev-stop.sh"
"$SCRIPT_DIR/dev-start.sh"
