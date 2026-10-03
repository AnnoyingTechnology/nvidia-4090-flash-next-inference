"""Freeze 80 prompts covering every official IFEval instruction class."""
import hashlib
import json
from pathlib import Path
import random

root = Path(__file__).resolve().parent / 'eval'
source = root / 'raw' / 'ifeval.jsonl'
rows = [json.loads(line) for line in source.read_text().splitlines()]
random.Random(20261003).shuffle(rows)
all_types = {v for row in rows for v in row['instruction_id_list']}
remaining = set(all_types)
selected = []
for row in rows:
    if remaining.intersection(row['instruction_id_list']):
        selected.append(row)
        remaining.difference_update(row['instruction_id_list'])
chosen = {row['key'] for row in selected}
selected += [row for row in rows if row['key'] not in chosen][:80-len(selected)]
path = root / 'ifeval-80.jsonl'
path.write_text(''.join(json.dumps(row) + '\n' for row in selected))
manifest = {'count': len(selected), 'instruction_types': sorted(all_types),
            'revision': 'e6890f85757dd84e27ca6df2dd30651dafad28e0',
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'cases_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'selection': 'seed 20261003: cover all instruction classes, then fill in shuffled order'}
(root / 'ifeval-manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
