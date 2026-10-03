#!/usr/bin/env bash
set -euo pipefail
if test -n "${ULMUS_EXPECTED_HOST:-}"; then
    test "$(hostname)" = "$ULMUS_EXPECTED_HOST"
fi
task_root=${ULMUS_ROOT:-$(cd -- "$(dirname -- "$0")" && pwd)}
export ULMUS_ROOT="$task_root"
task_library=${ULMUS_LIBRARY:-$task_root/models}
task_profile=${1:?usage: run.sh flash-q4|flash-iq3s}
case "$task_profile" in
    *-tune-ownertext|*-tune-ownervision|*-tune-ownerq4) task_default_image=ulmus/strata:99f3dbd-ownerapi ;;
    *-tune-eddoursultext|*-tune-eddoursulvision|*-tune-eddoursulq4) task_default_image=ulmus/strata:eddoursul-3a199-native ;;
    *) task_default_image=ulmus/strata:99f3dbd-cu124-sm89 ;;
esac
task_image=${2:-$task_default_image}
if ! [[ "$task_image" =~ ^ulmus/strata:[a-zA-Z0-9._-]+$ ]]; then
    echo 'Expected a locally built Ulmus Strata image.' >&2
    exit 2
fi
if ! [[ "$task_profile" =~ ^flash-(q4|iq3s)(-(32k|128k|256k)(-vision)?)?(-tune-[a-z0-9]+)?$ ]]; then
    exit 2
fi
test -f "$task_root/profiles/$task_profile.json"
# Refuse resource collisions. Only this experiment's container may be replaced.
if test -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"; then
    echo 'A GPU workload is active; stop the owned experiment before switching.' >&2
    exit 1
fi
python3 "$task_root/launch_record.py" "$task_profile" "$task_image"
task_env=()
# Explicit experimental controls only; never inherit arbitrary shell environment.
if test "${ULMUS_VERIFY_PROFILE:-0}" = 1; then
    task_env+=(--env STRATA_VERIFY_PROFILE=1 --env STRATA_DECODE_TIMING=1)
elif test "${ULMUS_DECODE_TIMING:-0}" = 1; then
    task_env+=(--env STRATA_DECODE_TIMING=1)
fi
if test -n "${ULMUS_POOL_QUANT_THRESH:-}"; then
    [[ "$ULMUS_POOL_QUANT_THRESH" =~ ^[0-9]+$ ]] || exit 2
    task_env+=(--env "STRATA_POOL_QUANT_THRESH=$ULMUS_POOL_QUANT_THRESH")
fi
docker run --name ulmus-inference-test --rm --detach --gpus all \
    "${task_env[@]}" \
    --user "$(id -u):$(id -g)" --ulimit memlock=-1 --memory 175g --shm-size 4g \
    --publish 127.0.0.1:19623:19623 \
    --mount "type=bind,src=$task_root,dst=/work" \
    --mount "type=bind,src=$task_library,dst=/models,readonly" \
    "$task_image" python -m serve.server --engine strata \
    --config "/work/profiles/$task_profile.json" --port 19623
