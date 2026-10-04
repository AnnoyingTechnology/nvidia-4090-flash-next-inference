#!/usr/bin/env bash
# Original IQ3 swap-v4 practical30 low canaries, then matched 64K context cells S V V S.
# One model at a time. Restore resident vision on exit; the owner-facing selection is made from the reports.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_v=flash-iq3s-256k-vision-tune-ownervision
task_s=flash-iq3s-256k-vision-tune-ownerswap
task_restore() {
    bash stop.sh || true
    bash run.sh "$task_v" && python3 wait_ready.py
}
trap task_restore EXIT
task_quality=results/practical30-v2-iq3-swap-v4-low.json
if ! test -e results/swap-v4-practical-engine.log; then
    bash stop.sh
    task_log="results/$task_s-engine.log"
    task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
    bash run.sh "$task_s"
    python3 wait_ready.py
    python3 practical_eval.py --cases eval/practical30-v2-cases.jsonl \
        --label iq3-swap-v4-low --effort low --seed 42 --tokens 32768 --out "$task_quality"
    bash stop.sh
    tail -c +$((task_offset + 1)) "$task_log" > results/swap-v4-practical-engine.log
fi
task_index=0
for task_tag in swap resident resident swap; do
    task_index=$((task_index + 1))
    task_profile=$task_v
    test "$task_tag" = swap && task_profile=$task_s
    task_out="results/swap64-control-$task_index-$task_tag"
    test -e "$task_out-engine.log" && continue
    test ! -e "$task_out.json" || { echo "Partial context cell: $task_out" >&2; exit 1; }
    task_log="results/$task_profile-engine.log"
    bash stop.sh
    task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
    bash run.sh "$task_profile"
    python3 wait_ready.py
    python3 scripts/context_decode_probe.py --context-k 64 --out "$task_out.json"
    python3 owner_api_check.py --profile "$task_profile" --vision --out "$task_out-api.json"
    bash stop.sh
    tail -c +$((task_offset + 1)) "$task_log" > "$task_out-engine.log"
done
