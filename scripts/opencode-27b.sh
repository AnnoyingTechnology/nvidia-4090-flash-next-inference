#!/usr/bin/env bash
# Juniperus: start the dedicated 27B service over SSH; its API uses the configured LAN endpoint.
set -euo pipefail
task_target=${ULMUS_SSH_TARGET:?Set ULMUS_SSH_TARGET to the SSH user@host}
ssh -F /dev/null -o BatchMode=yes "$task_target" systemctl --user start qwen3.8-27b.service
if [[ "${1:-}" == --run ]]; then
    shift
    exec opencode run --model ai-ulmus/qwen3.8-27b "$@"
fi
exec opencode --model ai-ulmus/qwen3.8-27b "$@"
