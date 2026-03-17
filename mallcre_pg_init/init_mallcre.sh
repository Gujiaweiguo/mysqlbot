#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-localhost}"
PORT="${2:-5432}"
USER_NAME="${3:-root}"
DB_NAME="${4:-mallcre}"

psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$(dirname "$0")/mallcre_postgres.sql"
psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$(dirname "$0")/mallcre_seed.sql"
psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$(dirname "$0")/mallcre_seed_realistic.sql"

printf 'Initialized database %s on %s:%s\n' "$DB_NAME" "$HOST" "$PORT"
