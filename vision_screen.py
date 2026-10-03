"""Score image content and strict JSON separately, retaining latency and encoder provenance."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import re
from bench import request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--effort', choices=['none', 'low', 'default'], default='none')
    ap.add_argument('--cases', default='fixtures/vision/cases.jsonl')
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    args = ap.parse_args()
    source = Path(args.cases)
    report = {'label': args.label, 'effort': args.effort,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'results': []}
    for case in map(json.loads, source.read_text().splitlines()):
        path = Path(case['image'])
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != case['image_sha256']:
            raise RuntimeError('Vision fixture checksum mismatch')
        payload = {'model': 'ulmus', 'messages': [{'role': 'user', 'content': [
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(data).decode()}},
            {'type': 'text', 'text': case['prompt']}]}], 'max_tokens': 4096,
            'reasoning_effort': args.effort, 'temperature': 0, 'seed': 42, 'stream': True,
            'stream_options': {'include_usage': True}}
        if args.effort == 'default':
            for key in ['reasoning_effort', 'temperature', 'seed']:
                payload.pop(key)
        elif args.effort != 'none':
            payload.update(temperature=1, top_p=.95, top_k=20, min_p=0, presence_penalty=0)
        response = request(args.url, payload)
        text = response['content'].strip()
        strict = True
        try:
            answer = json.loads(text)
        except json.JSONDecodeError:
            strict = False
            fenced = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
            try:
                answer = json.loads(fenced[1]) if fenced else None
            except json.JSONDecodeError:
                answer = None
        semantic = answer == case['expected']
        report['results'].append({'id': case['id'], 'image_sha256': case['image_sha256'],
            'input_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            'strict_pass': strict and semantic, 'content_pass': semantic,
            'answer': answer, 'expected': case['expected'], 'response': response})
        report['summary'] = {'strict_passed': sum(x['strict_pass'] for x in report['results']),
            'content_passed': sum(x['content_pass'] for x in report['results']),
            'total': len(report['results']),
            'truncated': sum(x['response']['finish_reason'] == 'length' for x in report['results'])}
        Path(args.out).write_text(json.dumps(report, indent=2))
        print(case['id'], answer, report['summary'], flush=True)


if __name__ == '__main__':
    main()
