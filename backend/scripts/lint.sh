#!/usr/bin/env bash

set -euo pipefail
set -x

scope="${LINT_SCOPE:-changed}"

targets=()

if [[ "${scope}" == "full" ]]; then
  targets=(apps common main.py)
else
  while IFS= read -r file; do
    if [[ -n "${file}" ]]; then
      if [[ -f "${file}" ]]; then
        targets+=("${file}")
      elif [[ "${file}" == backend/* ]]; then
        targets+=("${file#backend/}")
      fi
    fi
  done < <(git diff --name-only --diff-filter=ACMRTUXB -- '*.py')

  while IFS= read -r file; do
    if [[ -n "${file}" ]]; then
      if [[ -f "${file}" ]]; then
        targets+=("${file}")
      elif [[ "${file}" == backend/* ]]; then
        targets+=("${file#backend/}")
      fi
    fi
  done < <(git diff --name-only --cached --diff-filter=ACMRTUXB -- '*.py')

  while IFS= read -r file; do
    if [[ -n "${file}" ]]; then
      if [[ -f "${file}" ]]; then
        targets+=("${file}")
      elif [[ "${file}" == backend/* ]]; then
        targets+=("${file#backend/}")
      fi
    fi
  done < <(git ls-files --others --exclude-standard -- '*.py')

  if [[ ${#targets[@]} -eq 0 ]]; then
    echo "No Python file changes detected. Set LINT_SCOPE=full to run full scan."
    exit 0
  fi

  declare -A seen=()
  unique_targets=()
  for target in "${targets[@]}"; do
    if [[ -z "${seen["${target}"]+x}" ]]; then
      seen["${target}"]=1
      unique_targets+=("${target}")
    fi
  done
  targets=("${unique_targets[@]}")
fi

if [[ "${scope}" == "full" ]]; then
  uv run mypy "${targets[@]}"
else
  uv run mypy --follow-imports=silent --ignore-missing-imports "${targets[@]}"
fi
uv run ruff check "${targets[@]}"
uv run ruff format "${targets[@]}" --check
