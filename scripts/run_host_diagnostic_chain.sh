#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_profile=flash-iq3s-256k-vision-tune-ownerswap
task_out=results/decode-host-20261004
test ! -e "$task_out.json"
task_restore() {
    bash stop.sh || true
    bash run.sh "$task_profile" && python3 wait_ready.py
}
trap task_restore EXIT
bash stop.sh
task_log="results/$task_profile-engine.log"
task_offset=$(stat -c %s "$task_log")
ULMUS_DECODE_TIMING=1 bash run.sh "$task_profile" ulmus/strata:99f3dbd-decodehost-diag
python3 wait_ready.py
python3 scripts/context_decode_probe.py --context-k 32 --out "$task_out.json"
python3 owner_api_check.py --profile "$task_profile" --vision --out "$task_out-api.json"
bash stop.sh
tail -c +$((task_offset + 1)) "$task_log" > "$task_out-engine.log"
