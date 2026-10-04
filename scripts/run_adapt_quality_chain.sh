#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
python3 -c 'import json; assert json.load(open("results/adapt-batch-20261004-summary.json"))["gate"]["passed"]'
test ! -e results/practical30-v2-iq3-adapt24-low.json
task_restore() {
    bash stop.sh || true
    bash run.sh flash-iq3s-256k-vision-tune-ownerswap && python3 wait_ready.py
}
trap task_restore EXIT
bash stop.sh
bash run.sh flash-iq3s-256k-vision-tune-owneradapt24 ulmus/strata:99f3dbd-lendvram
python3 wait_ready.py
python3 practical_eval.py --cases eval/practical30-v2-cases.jsonl --label iq3-adapt24-low \
    --effort low --seed 42 --tokens 32768 --out results/practical30-v2-iq3-adapt24-low.json
python3 scripts/check_swap_large_images.py --engine-log results/flash-iq3s-256k-vision-tune-owneradapt24-engine.log \
    --out results/adapt24-large-image-20261004.json
