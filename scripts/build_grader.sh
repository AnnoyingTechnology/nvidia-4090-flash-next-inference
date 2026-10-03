#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
task_rev=28fef95ea8c9f7a547c8329f2cd3d32b92c1fa24
mkdir -p "$task_root/eval-source"
curl --fail --location --retry 3 \
    "https://raw.githubusercontent.com/LiveCodeBench/LiveCodeBench/$task_rev/lcb_runner/evaluation/testing_util.py" \
    --output "$task_root/eval-source/testing_util.py"
curl --fail --location --retry 3 \
    "https://raw.githubusercontent.com/LiveCodeBench/LiveCodeBench/$task_rev/LICENSE" \
    --output "$task_root/eval-source/LICENSE"
docker build -f "$task_root/Dockerfile.eval" -t ulmus/eval:lcb-28fef95 "$task_root"
cd "$task_root"
python3 eval.py --control-only --cases eval/cases.jsonl --out results/grader-controls.json --label controls
