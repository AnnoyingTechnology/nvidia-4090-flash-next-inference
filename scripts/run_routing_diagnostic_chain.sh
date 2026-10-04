#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_prefix=results/decode-routing-20261004
test ! -e "$task_prefix.bin" && test ! -e "$task_prefix.json"
task_restore() {
    bash stop.sh || true
    bash run.sh flash-iq3s-256k-vision-tune-ownerswap && python3 wait_ready.py
}
trap task_restore EXIT
bash stop.sh
bash run.sh flash-iq3s-256k-vision-tune-ownerroute ulmus/strata:99f3dbd-lendvram
python3 wait_ready.py
python3 scripts/context_decode_probe.py --context-k 32 128 --routing-trace "$task_prefix.bin" --out "$task_prefix.json"
python3 owner_api_check.py --profile flash-iq3s-256k-vision-tune-ownerroute --vision --out "$task_prefix-api.json"
