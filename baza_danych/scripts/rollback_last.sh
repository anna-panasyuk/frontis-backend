#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL, e.g. postgres://frontin:frontin_pass@localhost:5432/frontin}"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$(dirname "$0")/../migrations/001_init.down.sql"
echo "Rolled back 001_init."
