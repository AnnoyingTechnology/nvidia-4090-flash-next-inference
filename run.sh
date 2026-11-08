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
    *-tune-owner20261108) task_default_image=ulmus/strata:146df3c-owner20261108 ;;
    *-tune-ownertext|*-tune-ownervision|*-tune-ownerq4|*-tune-ownerq4static|*-tune-ownerhead|*-tune-ownerembedhead|*-tune-ownersr[0-9]*|*-tune-ownercpuvision) task_default_image=ulmus/strata:99f3dbd-ownerapi ;;
    *-tune-ownerswap|*-tune-owneradapt24|*-tune-owner9950x3d2) task_default_image=ulmus/strata:99f3dbd-lendvram ;;
    *-tune-eddoursultext|*-tune-eddoursulvision|*-tune-eddoursulq4|*-tune-eddoursulq4static) task_default_image=ulmus/strata:eddoursul-3a199-native ;;
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
task_container=${ULMUS_CONTAINER:-ulmus-inference-test}
[[ "$task_container" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]+$ ]] || exit 2
task_mode=(--detach)
if [[ "${ULMUS_FOREGROUND:-0}" == 1 ]]; then
    task_mode=()
fi
python3 "$task_root/launch_record.py" "$task_profile" "$task_image"
task_env=()
# Explicit experimental controls only; never inherit arbitrary shell environment.
if test "${ULMUS_VERIFY_PROFILE:-0}" = 1; then
    task_env+=(--env STRATA_VERIFY_PROFILE=1 --env STRATA_DECODE_TIMING=1)
elif test "${ULMUS_DECODE_TIMING:-0}" = 1; then
    task_env+=(--env STRATA_DECODE_TIMING=1)
fi
if test "${ULMUS_TRACE:-0}" = 1; then
    task_env+=(--env STRATA_TRACE=1)
fi
if test -n "${ULMUS_POOL_QUANT_THRESH:-}"; then
    [[ "$ULMUS_POOL_QUANT_THRESH" =~ ^[0-9]+$ ]] || exit 2
    task_env+=(--env "STRATA_POOL_QUANT_THRESH=$ULMUS_POOL_QUANT_THRESH")
fi
exec docker run --name "$task_container" --rm "${task_mode[@]}" --gpus all \
    "${task_env[@]}" \
    --user "$(id -u):$(id -g)" --ulimit memlock=-1 --memory 175g --shm-size 4g \
    --publish 127.0.0.1:19623:19623 \
    --mount "type=bind,src=$task_root,dst=/work" \
    --mount "type=bind,src=$task_library,dst=/models,readonly" \
    "$task_image" python -m serve.server --engine strata \
    --config "/work/profiles/$task_profile.json" --port 19623
