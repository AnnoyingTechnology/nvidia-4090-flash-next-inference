"""Freeze 40 official HumanEval tasks and extend the existing MMLU deck to 168."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import random
import pyarrow.parquet as pq

root=Path('/work')
raw=root/'eval/raw/humaneval-b9453e8.jsonl.gz'
info=json.loads((root/'eval/raw/humaneval-b9453e8-source.json').read_text())
data=raw.read_bytes()
assert len(data)==info['size']
assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==info['sha']
tasks=[json.loads(line) for line in gzip.decompress(data).decode().splitlines()]
assert len(tasks)==164
rng=random.Random(20261108)
human=sorted(rng.sample(tasks,40),key=lambda r:int(r['task_id'].split('/')[1]))
parquet=root/'eval/raw/mmlupro.parquet'
manifest=json.loads((root/'eval/manifest.json').read_text())
assert hashlib.sha256(parquet.read_bytes()).hexdigest()==manifest['raw_sha256']['mmlupro.parquet']
old=[c for line in (root/'eval/cases.jsonl').read_text().splitlines() if (c:=json.loads(line))['suite']=='mmlupro']
assert len(old)==140
used={c['id'] for c in old}
groups=collections.defaultdict(list)
for r in pq.read_table(parquet).to_pylist():
    if str(r['question_id']) not in used:groups[r['category']].append(r)
extra=[]
for category,rows in sorted(groups.items()):
    for row in rng.sample(sorted(rows,key=lambda r:r['question_id']),2):
        extra.append({'suite':'mmlupro','id':str(row['question_id']),'data':row})
assert len(extra)==28
out=root/'eval/huihui20261108-dense-bar.json'
payload={'source':{'humaneval_repository':'https://github.com/openai/human-eval',
    'humaneval_commit':'b9453e8f1865df0a0057a1383767caa400acfbcf','humaneval_git_blob':info['sha'],
    'humaneval_sha256':hashlib.sha256(data).hexdigest(),'mmlu_manifest':manifest},
    'seed':20261108,'humaneval':human,'mmlu_extra':extra,
    'purpose':'Match or exceed the 27B dense gate coverage: 40 HumanEval, 168 stratified MMLU-Pro, 80 strict IFEval, plus practical/feature gates.'}
if out.exists():assert json.loads(out.read_text())==payload
else:out.write_text(json.dumps(payload,indent=2)+'\n')
print('FROZEN',len(human),'HumanEval;',len(extra),'additional MMLU-Pro; SHA256',hashlib.sha256(out.read_bytes()).hexdigest())
