#!/usr/bin/env bash
# Build the UNLOAD/LOAD measurement image, measure reload cycles on the idle GPU, then serve again.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_label=${1:?usage: run_vision_reload_chain.sh <label>}
[[ "$task_label" =~ ^[a-z0-9-]+$ ]] || exit 2
task_profile=flash-iq3s-256k-vision-tune-ownervision
task_serve() {
    if ! docker container inspect ulmus-inference-test >/dev/null 2>&1; then
        bash run.sh "$task_profile" && python3 wait_ready.py
    fi
}
trap task_serve EXIT
docker build -f Dockerfile.vision-unload -t ulmus/strata:99f3dbd-visionunload .
bash stop.sh
python3 scripts/vision_memory_probe.py --image ulmus/strata:99f3dbd-visionunload --modes reload --repeats 4 \
    --out "results/vision-reload-$task_label.json"
