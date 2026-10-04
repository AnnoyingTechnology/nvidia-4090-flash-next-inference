#!/usr/bin/env bash
# A small matched context check: fresh resident then swap, existing questions, no build or sweep.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_context=${1:?usage: run_context_ab_cells.sh 64|128 result-prefix}
task_prefix=${2:?Set a fresh result prefix}
[[ "$task_context" = 64 || "$task_context" = 128 ]] || exit 2
[[ "$task_prefix" =~ ^[a-zA-Z0-9-]+$ ]] || exit 2
task_restore() {
    bash stop.sh || true
    bash run.sh flash-iq3s-256k-vision-tune-ownervision && python3 wait_ready.py
}
trap task_restore EXIT
task_index=0
for task_tag in resident swap; do
    task_index=$((task_index + 1))
    task_profile=flash-iq3s-256k-vision-tune-ownervision
    test "$task_tag" = swap && task_profile=flash-iq3s-256k-vision-tune-ownerswap
    task_out="results/$task_prefix-$task_index-$task_tag"
    test ! -e "$task_out.json" || { echo "Output exists: $task_out" >&2; exit 1; }
    task_log="results/$task_profile-engine.log"
    bash stop.sh
    task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
    bash run.sh "$task_profile"
    python3 wait_ready.py
    python3 scripts/context_decode_probe.py --context-k "$task_context" --out "$task_out.json"
    python3 owner_api_check.py --profile "$task_profile" --vision --out "$task_out-api.json"
    bash stop.sh
    tail -c +$((task_offset + 1)) "$task_log" > "$task_out-engine.log"
done
