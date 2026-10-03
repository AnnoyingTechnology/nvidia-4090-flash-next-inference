#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
task_source="$task_root/upstream/strata"
task_sha=99f3dbd0b21d1401b3769e0c0d963913607f380b
mkdir -p "$task_root/upstream" "$task_root/results" "$task_root/packs" "$task_root/mtp"
if ! test -d "$task_source/.git"; then
    git init "$task_source"
    git -C "$task_source" remote add origin https://github.com/Niko1221/Strata.git
    git -C "$task_source" fetch --depth 1 origin "$task_sha"
    git -C "$task_source" checkout --detach FETCH_HEAD
fi
test "$(git -C "$task_source" rev-parse HEAD)" = "$task_sha"
test -z "$(git -C "$task_source" status --porcelain --untracked-files=no)"
if ! test -d "$task_source/ref/llama.cpp/gguf-py"; then
    curl --fail --location --retry 3 \
        https://github.com/ggml-org/llama.cpp/archive/3cf03257f219afbe7334045ff7c6a06ac68c627d.tar.gz \
        --output "$task_root/upstream/llama-source.tar.gz"
    mkdir -p "$task_source/ref/llama.cpp"
    tar -xzf "$task_root/upstream/llama-source.tar.gz" --strip-components=1 -C "$task_source/ref/llama.cpp"
fi
docker build --progress=plain -t ulmus/strata:99f3dbd-cu124-sm89 \
    -f "$task_root/Dockerfile" "$task_source"
# Download the exact wheels matching the lock from the base image's Python ABI.
docker run --rm --user "$(id -u):$(id -g)" --mount "type=bind,src=$task_root,dst=/work" \
    ulmus/strata:99f3dbd-cu124-sm89 python -m pip download --require-hashes --only-binary=:all: \
    -r /work/api-requirements.lock --dest /work/api-wheels
docker build -f "$task_root/Dockerfile.owner-api" -t ulmus/strata:99f3dbd-ownerapi "$task_root"
docker run --rm ulmus/strata:99f3dbd-ownerapi python -m unittest serve.test_structured
