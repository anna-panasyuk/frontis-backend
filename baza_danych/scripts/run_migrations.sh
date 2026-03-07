#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL, e.g. postgres://frontin:frontin_pass@localhost:5432/frontin}"

for file in "$(dirname "$0")"/../migrations/*.up.sql; do
  echo "Applying $file"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file"
done

echo "Migrations applied."
