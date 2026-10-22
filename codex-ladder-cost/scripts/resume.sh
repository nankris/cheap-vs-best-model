#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/run.py >> results/runner.log 2>&1
python scripts/analyze.py
