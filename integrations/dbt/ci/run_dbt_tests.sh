#!/usr/bin/env bash
set -euo pipefail

echo "=== dbt-hatidata test suite ==="

# Install the adapter in development mode
pip install -e ".[dev]"

# Run unit tests
echo "--- Unit Tests ---"
python -m pytest tests/unit/ -v

# Run functional tests (requires running HatiData proxy)
if [ "${RUN_FUNCTIONAL:-false}" = "true" ]; then
    echo "--- Functional Tests ---"
    echo "Waiting for proxy on port 5439..."
    for i in $(seq 1 30); do
        if pg_isready -h "${HATIDATA_HOST:-localhost}" -p 5439 -q 2>/dev/null; then
            break
        fi
        sleep 2
    done
    python -m pytest tests/functional/ -v --timeout=60
fi

echo "=== All tests passed ==="
