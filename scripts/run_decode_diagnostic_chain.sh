#!/usr/bin/env bash
# Bounded attribution on selected v4; rates under stamps are diagnostic only.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_profile=flash-iq3s-256k-vision-tune-ownerswap
task_prefix=results/decode-explore-20261004
task_log="results/$task_profile-engine.log"
for task_mode in aggregate stamps; do
    test ! -e "$task_prefix-$task_mode.json" || exit 2
done
task_restore() {
    bash stop.sh || true
    bash run.sh "$task_profile" && python3 wait_ready.py
}
trap task_restore EXIT
for task_mode in aggregate stamps; do
    bash stop.sh
    task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
    if test "$task_mode" = aggregate; then
        ULMUS_DECODE_TIMING=1 bash run.sh "$task_profile"
    else
        ULMUS_VERIFY_PROFILE=1 bash run.sh "$task_profile"
    fi
    python3 wait_ready.py
    python3 scripts/context_decode_probe.py --context-k 32 128 --out "$task_prefix-$task_mode.json"
    bash stop.sh
    tail -c +$((task_offset + 1)) "$task_log" > "$task_prefix-$task_mode-engine.log"
done
