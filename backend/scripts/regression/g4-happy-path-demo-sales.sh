#!/usr/bin/env bash

set -euo pipefail
set -x

uv run python scripts/regression/g4_happy_path_demo_sales.py "$@"
