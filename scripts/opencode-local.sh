#!/usr/bin/env bash
# Ulmus: start the selected dedicated service and use its loopback provider.
set -euo pipefail
task_model=ai-ulmus-flash-next/qwen3.8-flash-next
task_unit=qwen3.8-flash-next.service
if [[ "${0##*/}" == opencode-27b ]]; then
    task_model=ai-ulmus/qwen3.8-27b
    task_unit=qwen3.8-27b.service
fi
systemctl --user start "$task_unit"
task_cli=$(command -v opencode || true)
if [[ -z "$task_cli" ]]; then task_cli=$HOME/.opencode/bin/opencode; fi
test -x "$task_cli"
if [[ "${1:-}" == --run ]]; then
    shift
    exec "$task_cli" run --model "$task_model" "$@"
fi
exec "$task_cli" --model "$task_model" "$@"
