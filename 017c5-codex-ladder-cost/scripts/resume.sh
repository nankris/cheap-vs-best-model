#!/bin/bash
set -euo pipefail
source /workspace/tools/setup.sh
cd "$(dirname "$0")/.."
python scripts/run.py >> results/runner.log 2>&1
/workspace/tools/mlenv/bin/python scripts/analyze.py
