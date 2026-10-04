#!/usr/bin/env bash
# Smoke test of the lend-VRAM prototype: launch, API checks with images, then serve the selected profile again.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_profile=flash-iq3s-256k-vision-tune-ownerswap
task_serving=flash-iq3s-256k-vision-tune-ownervision
task_log="results/$task_profile-engine.log"
task_serve() {
    bash stop.sh || true
    bash run.sh "$task_serving" && python3 wait_ready.py
}
trap task_serve EXIT
bash stop.sh
task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
bash run.sh "$task_profile"
python3 wait_ready.py
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
python3 owner_api_check.py --profile "$task_profile" --vision --out results/swap-smoke-api.json
python3 scripts/swap_image_smoke.py
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
docker logs ulmus-inference-test 2>&1 | tail -20
tail -c +$((task_offset + 1)) "$task_log" > results/swap-smoke-engine.log
