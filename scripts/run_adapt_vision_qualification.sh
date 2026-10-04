#!/usr/bin/env bash
# Final content qualification; success leaves the candidate running for selection.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
test ! -e results/vision15-adapt24-low.json
python3 - <<'PY'
import json
r=json.load(open('results/practical30-v2-iq3-adapt24-low.json'))
assert len(r['results'])==30
assert all(c['response']['finish_reason']=='stop' for c in r['results'])
assert sum(bool(c['verdict'].get('pass')) for c in r['results'])>=28
assert len(r['controls'])==30 and all(v['positive']['pass'] and not v['negative']['pass'] for v in r['controls'].values())
s=json.load(open('results/adapt24-large-image-20261004.json'))
assert len(s['checks'])==3 and all(c['passed'] for c in s['checks'])
PY
task_restore_on_failure() {
    task_rc=$?
    if test "$task_rc" -ne 0; then
        bash stop.sh || true
        bash run.sh flash-iq3s-256k-vision-tune-ownerswap && python3 wait_ready.py
    fi
    exit "$task_rc"
}
trap task_restore_on_failure EXIT
bash stop.sh
bash run.sh flash-iq3s-256k-vision-tune-owneradapt24 ulmus/strata:99f3dbd-lendvram
python3 wait_ready.py
python3 vision_compare.py --backend local --model Qwen3.8-Flash-Next-IQ3_S-adapt24 --effort low \
    --out results/vision15-adapt24-low.json
python3 - <<'PY'
import json
r=json.load(open('results/vision15-adapt24-low.json'))
assert len(r['results'])==15
assert all(c['response']['finish_reason']=='stop' for c in r['results'])
assert r['summary']['content_correct']>=14
PY
python3 owner_api_check.py --profile flash-iq3s-256k-vision-tune-owneradapt24 --vision \
    --out results/adapt24-final-api.json
