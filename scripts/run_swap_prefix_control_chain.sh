#!/usr/bin/env bash
# Replay the original swap-ab-v1 requests on resident, v3 and v4, counterbalanced R 3 4 4 3 R.
# One model at a time; restore the selected resident vision profile on every exit.
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
task_index=0
for task_tag in resident v3 v4 v4 v3 resident; do
    task_index=$((task_index + 1))
    task_profile=$task_s
    case "$task_tag" in
        resident) task_profile=$task_v; task_image=ulmus/strata:99f3dbd-ownerapi ;;
        v3) task_image=ulmus/strata:99f3dbd-lendvram-v3 ;;
        v4) task_image=ulmus/strata:99f3dbd-lendvram ;;
    esac
    ULMUS_AB_IMAGE="$task_image" bash scripts/run_ab_cells.sh swap-ab-v1 \
        "swap-prefix-control-$task_index-$task_tag" "$task_profile"
done
