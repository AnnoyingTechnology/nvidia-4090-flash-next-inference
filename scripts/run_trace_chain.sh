#!/usr/bin/env bash
# Traced short-read decomposition on the selected vision profile, then the standalone vision
# memory probe on the idle GPU. The selected serving profile is relaunched at the end, also on failure.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
task_label=${1:?usage: run_trace_chain.sh <label>}
[[ "$task_label" =~ ^[a-z0-9-]+$ ]] || exit 2
task_profile=flash-iq3s-256k-vision-tune-ownervision
task_log="results/$task_profile-engine.log"
task_out="results/short-read-trace-$task_label"
test ! -e "$task_out.json" || { echo "Output exists: $task_out.json" >&2; exit 1; }
task_serve() {
    if ! docker container inspect ulmus-inference-test >/dev/null 2>&1; then
        bash run.sh "$task_profile" && python3 wait_ready.py
    fi
}
trap task_serve EXIT
bash stop.sh
task_offset=$(stat -c %s "$task_log" 2>/dev/null || echo 0)
ULMUS_TRACE=1 bash run.sh "$task_profile"
python3 wait_ready.py
python3 scripts/short_read_probe.py --out "$task_out.json" --repeats 3
bash stop.sh
tail -c +$((task_offset + 1)) "$task_log" > "$task_out-engine.log"
python3 scripts/summarize_short_read_trace.py --probe "$task_out.json" --engine-log "$task_out-engine.log" \
    --out "$task_out-summary.json"
python3 scripts/vision_memory_probe.py --out "results/vision-memory-$task_label.json"
