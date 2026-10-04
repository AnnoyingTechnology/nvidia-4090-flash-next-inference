#!/usr/bin/env bash
# One attribution-driven candidate, ABBA at fixed 32K/128K inputs; no build overlap.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_restore() {
    bash stop.sh || true
    bash run.sh flash-iq3s-256k-vision-tune-ownerswap && python3 wait_ready.py
}
for task_index in 1 2 3 4; do
    test ! -e "results/adapt-batch-20261004-$task_index.json" || exit 2
done
trap task_restore EXIT
task_index=0
for task_tag in ownerswap owneradapt24 owneradapt24 ownerswap; do
    task_index=$((task_index+1))
    task_profile="flash-iq3s-256k-vision-tune-$task_tag"
    task_prefix="results/adapt-batch-20261004-$task_index"
    task_log="results/$task_profile-engine.log"
    bash stop.sh
    task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
    bash run.sh "$task_profile" ulmus/strata:99f3dbd-lendvram
    python3 wait_ready.py
    python3 scripts/context_decode_probe.py --context-k 32 128 --out "$task_prefix.json"
    python3 owner_api_check.py --profile "$task_profile" --vision --out "$task_prefix-api.json"
    bash stop.sh
    tail -c +$((task_offset+1)) "$task_log" > "$task_prefix-engine.log"
done
