#!/usr/bin/env bash
# The 15-image deck at low on fresh launches S V V S (swap prototype vs resident GPU vision), then serve V again.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_label=${1:?usage: run_swap_deck_chain.sh <label>}
[[ "$task_label" =~ ^[a-z0-9-]+$ ]] || exit 2
task_v=flash-iq3s-256k-vision-tune-ownervision
task_s=flash-iq3s-256k-vision-tune-ownerswap
task_serve() {
    bash stop.sh || true
    bash run.sh "$task_v" && python3 wait_ready.py
}
trap task_serve EXIT
task_index=0
for task_profile in "$task_s" "$task_v" "$task_v" "$task_s"; do
    task_index=$((task_index + 1))
    task_tag=gpuvision
    test "$task_profile" = "$task_s" && task_tag=swap
    task_out="results/vision15-$task_label-$task_index-$task_tag"
    test -e "$task_out-engine.log" && continue
    task_log="results/$task_profile-engine.log"
    bash stop.sh
    task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
    bash run.sh "$task_profile"
    python3 wait_ready.py
    python3 vision_compare.py --backend local --model "Qwen3.8-Flash-Next-IQ3_S-$task_tag" --effort low \
        --out "$task_out.json"
    bash stop.sh
    tail -c +$((task_offset + 1)) "$task_log" > "$task_out-engine.log"
done
