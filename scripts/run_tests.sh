#!/usr/bin/env bash
# Install the modules in a fresh database and run their tests inside the Odoo 17 image.
# Usage: ./scripts/run_tests.sh [module1,module2]   (default: every module in the repo)
set -euo pipefail
cd "$(dirname "$0")/.."

ALL_MODULES=$(ls -d */__manifest__.py | cut -d/ -f1 | paste -sd, -)
MODULES=${1:-$ALL_MODULES}
TAGS=$(echo "$MODULES" | sed 's/[^,]*/\/&/g')
DB="test_$(date +%s)"
LOG=$(mktemp)

docker compose up -d db
until docker compose exec -T db pg_isready -U odoo >/dev/null 2>&1; do sleep 1; done

echo "Modules: $MODULES"
docker compose run --rm -T odoo odoo \
    -d "$DB" -i "$MODULES" --test-tags "$TAGS" \
    --without-demo=all --stop-after-init --log-level=test --http-port=8070 \
    2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}

docker compose exec -T db dropdb -U odoo --if-exists "$DB" || true

# Odoo exits with 0 on some failures (e.g. a broken view in a module): check the log too.
if [ "$RC" -ne 0 ] || grep -qE "(ERROR|CRITICAL) .*odoo\.(modules|tests|addons)" "$LOG"; then
    echo "Tests FAILED"; exit 1
fi
echo "Tests passed"
