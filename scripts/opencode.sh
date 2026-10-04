#!/usr/bin/env bash
# Start only when idle, tunnel the loopback API, and select the owned OpenCode model.
set -euo pipefail
task_target=${ULMUS_SSH_TARGET:?Set ULMUS_SSH_TARGET to the SSH user@host}
task_remote_root=${ULMUS_REMOTE_ROOT:?Set ULMUS_REMOTE_ROOT to the deployed stack directory}
task_model=${ULMUS_OPENCODE_MODEL:-ai-ulmus-flash-next/qwen3.8-flash-next}
[[ "$task_target" =~ ^[a-zA-Z0-9_.@:-]+$ ]] || exit 2
printf -v task_root_quoted '%q' "$task_remote_root"
# A running profile is preserved. run.sh itself refuses any GPU resource collision.
ssh -F /dev/null -o BatchMode=yes "$task_target" "bash -s -- $task_root_quoted" <<'REMOTE'
set -euo pipefail
cd -- "$1"
if ! docker inspect --format '{{.State.Running}}' ulmus-inference-test 2>/dev/null | grep -qx true; then
    bash run.sh flash-iq3s-256k-vision-tune-owneradapt24
    python3 wait_ready.py
fi
python3 - <<'PY'
import json, subprocess, urllib.request
command = json.loads(subprocess.check_output(
    ['docker', 'inspect', '--format', '{{json .Config.Cmd}}', 'ulmus-inference-test'], text=True))
if '/work/profiles/flash-iq3s-256k-vision-tune-owneradapt24.json' not in command:
    raise SystemExit('Stop the owned workload and start the selected owner vision profile first.')
with urllib.request.urlopen('http://127.0.0.1:19623/v1/status', timeout=10) as response:
    status = json.load(response)
if status['model'] != 'Qwen3.8-Flash-Next':
    raise SystemExit('Expected the owned Flash-Next server')
PY
REMOTE
task_tunnel_dir=$(mktemp -d)
task_socket=$task_tunnel_dir/control
cleanup() {
    ssh -F /dev/null -S "$task_socket" -O exit "$task_target" >/dev/null 2>&1 || true
    rmdir "$task_tunnel_dir" 2>/dev/null || true
}
trap cleanup EXIT
# Background only after authentication and successful binding; an occupied port fails.
ssh -F /dev/null -M -S "$task_socket" -fN -o BatchMode=yes -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -L 127.0.0.1:19623:127.0.0.1:19623 "$task_target"
curl -fsS --max-time 5 http://127.0.0.1:19623/health >/dev/null
if [[ "${1:-}" == --run ]]; then
    shift
    opencode run --model "$task_model" "$@"
else
    opencode --model "$task_model" "$@"
fi
