"""Executable code and operational decisions, evaluated without acting on infrastructure."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

from bench import request
from eval import grade, GRADER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    ap.add_argument('--cases', default='eval/practical-cases.jsonl')
    ap.add_argument('--out', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--effort', choices=['none', 'low', 'medium'], default='low')
    ap.add_argument('--tokens', type=int, default=8192)
    args = ap.parse_args()
    source, path = Path(args.cases), Path(args.out)
    cases = [json.loads(line) for line in source.read_text().splitlines()]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    grader_id = subprocess.check_output(['docker', 'image', 'inspect', GRADER,
                                        '--format', '{{.Id}}'], text=True).strip()
    protocol = {'effort': args.effort, 'max_tokens': args.tokens, 'seed': 42,
                'temperature': 1, 'top_p': 0.95, 'top_k': 20, 'min_p': 0,
                'presence_penalty': 0, 'repetition_penalty': 1}
    if args.effort == 'none':
        protocol.update(temperature=0.7, top_p=0.8, presence_penalty=1.5)
    report = {'label': args.label, 'source_sha256': digest, 'grader_image_id': grader_id,
              'protocol': protocol, 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'controls': {}, 'results': []}
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != report[k] for k in ['label', 'source_sha256', 'grader_image_id', 'protocol']):
            raise RuntimeError('Resume provenance mismatch')
        report = old
    for case in cases:
        if case['kind'] != 'code' or case['id'] in report['controls']:
            continue
        positive = grade(case['problem'], case['control'])
        negative = grade(case['problem'], 'def solve(*args): return "incorrect"')
        if not positive['pass'] or negative['pass']:
            raise RuntimeError('Practical grader control failed: ' + case['id'] + repr(positive))
        report['controls'][case['id']] = {'positive': positive, 'negative': negative}
    completed = {r['id'] for r in report['results']}
    for case in cases:
        if case['id'] in completed:
            continue
        payload = {'model': 'ulmus', 'messages': [{'role': 'user', 'content': case['prompt']}],
                   **{k: v for k, v in protocol.items() if k != 'effort'},
                   'reasoning_effort': args.effort, 'stream': True,
                   'stream_options': {'include_usage': True}}
        payload['max_tokens'] = args.tokens if case['kind'] == 'code' else 2048
        response = request(args.url, payload)
        if case['kind'] == 'decision':
            verdict = {'pass': response['content'].strip() == case['answer']}
        else:
            blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', response['content'], re.DOTALL)
            verdict = grade(case['problem'], blocks[0]) if blocks else {'pass': False, 'error': 'No complete code'}
        report['results'].append({'id': case['id'], 'kind': case['kind'], 'verdict': verdict,
            'input_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            'response': response})
        report['summary'] = {kind: {'passed': sum(r['verdict'].get('pass', False) for r in report['results'] if r['kind'] == kind),
            'total': sum(r['kind'] == kind for r in report['results']),
            'truncated': sum(r['kind'] == kind and r['response']['finish_reason'] == 'length' for r in report['results'])}
            for kind in ['code', 'decision']}
        path.write_text(json.dumps(report, indent=2))
        print(case['id'], verdict.get('pass'), response['usage'].get('completion_tokens'), report['summary'], flush=True)


if __name__ == '__main__':
    main()
