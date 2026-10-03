"""Freeze a full AIME25 set and stratified MMLU-Pro/LCB screens before comparing quants."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random

import pyarrow.parquet as pq

root = Path('/work/eval')
raw = root / 'raw'
out = root / 'cases.jsonl'
rng = random.Random(20261003)
cases = []
for row in map(json.loads, (raw / 'aime25.jsonl').read_text().splitlines()):
    cases.append({'suite': 'aime25', 'id': row['id'], 'data': row})
groups = defaultdict(list)
for row in pq.read_table(raw / 'mmlupro.parquet').to_pylist():
    groups[row['category']].append(row)
for category, rows in sorted(groups.items()):
    for row in rng.sample(rows, 10):
        cases.append({'suite': 'mmlupro', 'id': str(row['question_id']), 'data': row})
groups.clear()
for row in map(json.loads, (raw / 'lcb-v6.jsonl').read_text().splitlines()):
    groups[row['difficulty']].append(row)
for difficulty, rows in sorted(groups.items()):
    for row in rng.sample(rows, 8):
        cases.append({'suite': 'lcb-v6-screen', 'id': row['platform'] + '/' + row['question_id'], 'data': row})
out.write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in cases))
manifest = {'seed': 20261003, 'aime25': 30, 'mmlupro': 140, 'lcb_v6_screen': 24,
            'case_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
            'raw_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.iterdir())},
            'revisions': {'math-ai/aime25': '563bb8404243c5f09de6ec262f2db674fe5bce9b',
                'TIGER-Lab/MMLU-Pro': 'b189ec765aa7ed75c8acfea42df31fdae71f97be',
                'livecodebench/code_generation_lite': '0fe84c3912ea0c4d4a78037083943e8f0c4dd505',
                'LiveCodeBench/LiveCodeBench': '28fef95ea8c9f7a547c8329f2cd3d32b92c1fa24'}}
(root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
