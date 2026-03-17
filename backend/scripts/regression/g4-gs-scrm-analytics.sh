#!/usr/bin/env bash

set -euo pipefail
set -x

uv run python scripts/regression/gs_scrm_analytics_regression.py "$@"
