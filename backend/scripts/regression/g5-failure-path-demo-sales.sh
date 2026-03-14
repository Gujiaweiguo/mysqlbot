#!/usr/bin/env bash

set -euo pipefail
set -x

uv run python scripts/regression/g5_failure_path_demo_sales.py "$@"
