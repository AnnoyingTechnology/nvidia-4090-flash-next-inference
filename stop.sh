#!/usr/bin/env bash
set -euo pipefail
if test -n "${ULMUS_EXPECTED_HOST:-}"; then
    test "$(hostname)" = "$ULMUS_EXPECTED_HOST"
fi
if docker container inspect ulmus-inference-test >/dev/null 2>&1; then
    docker stop --timeout 30 ulmus-inference-test
    # Docker's automatic removal can finish after stop returns.
    for task_try in {1..30}; do
        if ! docker container inspect ulmus-inference-test >/dev/null 2>&1; then
            exit 0
        fi
        sleep 1
    done
    echo 'The owned test container has not finished removal.' >&2
    exit 1
fi
