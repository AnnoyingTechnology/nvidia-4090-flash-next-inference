#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
task_source="$task_root/upstream/strata-eddoursul"
task_sha=3a19944130d93d204a845234bbb61c1f1fb3b57d
mkdir -p "$task_root/upstream" "$task_root/results"
if ! test -d "$task_source/.git"; then
    git init "$task_source"
    git -C "$task_source" remote add origin https://github.com/eddoursul/Strata.git
    git -C "$task_source" fetch --depth 1 origin "$task_sha"
    git -C "$task_source" checkout --detach FETCH_HEAD
fi
test "$(git -C "$task_source" rev-parse HEAD)" = "$task_sha"
test -z "$(git -C "$task_source" status --porcelain --untracked-files=no)"
git -C "$task_source" apply --check "$task_root/patches/eddoursul-cuda124-compat.patch"
mkdir -p "$task_source/.ulmus-overlays"
cp "$task_root/patches/eddoursul-cuda124-compat.patch" "$task_source/.ulmus-overlays/"
cp "$task_root/scripts/native_copy_parity.cpp" "$task_source/.ulmus-overlays/"
cp "$task_root/scripts/native_grouped_gemm_parity.cpp" "$task_source/.ulmus-overlays/"
docker build --progress=plain -t ulmus/strata:eddoursul-3a199-native \
    -f "$task_root/Dockerfile.eddoursul-native" "$task_source"
