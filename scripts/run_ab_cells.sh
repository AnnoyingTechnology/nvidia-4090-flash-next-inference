#!/usr/bin/env bash
# Fresh-launch benchmark cells in the given profile order, for matched A/B comparisons.
# Each cell: launch, paired bench, API checks, stop, then slice its own engine-log section.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_paired=${1:?usage: run_ab_cells.sh <paired-id> <cell-prefix> <profile>...}
task_prefix=${2:?usage: run_ab_cells.sh <paired-id> <cell-prefix> <profile>...}
shift 2
[[ "$task_prefix" =~ ^[a-z0-9-]+$ ]] || exit 2
task_sampling='{"temperature":1,"top_p":0.95,"top_k":20,"min_p":0,"presence_penalty":0,"repetition_penalty":1,"reasoning_effort":"low","seed":42}'
task_index=0
for task_profile in "$@"; do
    task_index=$((task_index + 1))
    task_cell="results/$task_prefix-$task_index-$task_profile"
    # The engine-log slice is written last, so it marks a complete cell.
    if test -e "$task_cell-engine.log"; then
        echo "Cell complete, skipping: $task_cell" >&2
        continue
    fi
    if test -e "$task_cell-perf.json" || test -e "$task_cell-api.json"; then
        echo "Partial cell; move it aside before rerunning: $task_cell" >&2
        exit 1
    fi
    task_log="results/$task_profile-engine.log"
    bash stop.sh
    task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
    bash run.sh "$task_profile"
    python3 wait_ready.py
    python3 bench.py --out "$task_cell-perf.json" --repeats 2 --decode-tokens 512 \
        --fixtures fixtures --prefill-k 32 --paired-id "$task_paired" \
        --sampling "$task_sampling" --capture-runtime
    task_vision=()
    if [[ "$task_profile" == *-vision-* ]]; then
        task_vision=(--vision)
    fi
    python3 owner_api_check.py --profile "$task_profile" "${task_vision[@]}" --out "$task_cell-api.json"
    bash stop.sh
    tail -c +$((task_offset + 1)) "$task_log" > "$task_cell-engine.log"
    echo "Cell complete: $task_cell" >&2
done
