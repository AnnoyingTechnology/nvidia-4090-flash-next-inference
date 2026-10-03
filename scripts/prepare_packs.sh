#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
task_image=ulmus/strata:99f3dbd-ownerapi
task_docker=(docker run --rm --user "$(id -u):$(id -g)" --mount "type=bind,src=$task_root,dst=/work" "$task_image")
mkdir -p "$task_root/packs/iq3s" "$task_root/mtp"
"${task_docker[@]}" python tools/iq_pack.py \
    --gguf /work/models/gsq-iq3_s/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf \
    --out /work/packs/iq3s
"${task_docker[@]}" python tools/mtp_fetch.py fetch --out /work/mtp
"${task_docker[@]}" python tools/mtp_fetch.py verify --out /work/mtp
"${task_docker[@]}" python tools/mtp_pack.py --src /work/mtp --experts q2_0 --out /work/mtp/mtp-q2_0.gguf
"${task_docker[@]}" python tools/mtp_rt.py --gguf /work/mtp/mtp-q2_0.gguf --out /work/mtp/rt
