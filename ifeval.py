"""Resumable IFEval screen, separate from the fixed reasoning/knowledge/code deck."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from bench import request
from eval import grade

IMAGE = 'ulmus/ifeval:e6890f8'
PROTOCOL = {'max_tokens': 2048, 'reasoning_effort': 'none', 'temperature': 0, 'seed': 42}
ap = argparse.ArgumentParser()
ap.add_argument('--cases', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--label', required=True)
args = ap.parse_args()
source, path = Path(args.cases), Path(args.out)
digest = hashlib.sha256(source.read_bytes()).hexdigest()
image_id = subprocess.check_output(['docker', 'image', 'inspect', IMAGE,
                                    '--format', '{{.Id}}'], text=True).strip()
report = {'label': args.label, 'cases_sha256': digest, 'grader_image_id': image_id,
          'protocol': PROTOCOL, 'results': []}
if path.exists():
    report = json.loads(path.read_text())
    if (report['label'], report['cases_sha256'], report['grader_image_id'], report['protocol']) != (
            args.label, digest, image_id, PROTOCOL):
        raise RuntimeError('Resume provenance does not match')
completed = {r['id'] for r in report['results']}
for row in map(json.loads, source.read_text().splitlines()):
    if row['key'] in completed:
        continue
    result = request('http://127.0.0.1:19623', {'model': 'ulmus',
        'messages': [{'role': 'user', 'content': row['prompt']}], **PROTOCOL,
        'stream': True, 'stream_options': {'include_usage': True}})
    verdict = grade(row, result['content'], IMAGE)
    report['results'].append({'id': row['key'], 'verdict': verdict, 'response': result})
    report['passed'] = sum(r['verdict']['pass'] for r in report['results'])
    report['truncated'] = sum(r['response']['finish_reason'] == 'length' for r in report['results'])
    path.write_text(json.dumps(report, indent=2))
    print(row['key'], verdict['pass'], report['passed'], len(report['results']),
          result['finish_reason'], flush=True)
