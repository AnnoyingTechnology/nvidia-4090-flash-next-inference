"""Separate thinking/protocol effects from quantization on the frozen knowledge deck.

This remains a local zero-shot screen; published MMLU-Pro uses another protocol.
The entire preselected deck is evaluated, not only cases one candidate previously lost.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re

from bench import request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    ap.add_argument('--cases', default='eval/cases.jsonl')
    ap.add_argument('--out', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--effort', choices=['none', 'low', 'medium', 'high'], default='low')
    ap.add_argument('--tokens', type=int, default=4096)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    source, output = Path(args.cases), Path(args.out)
    cases = [c for line in source.read_text().splitlines()
             if (c := json.loads(line))['suite'] == 'mmlupro']
    if args.limit:
        cases = cases[:args.limit]
    sampling = {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0,
                'presence_penalty': 1.5, 'repetition_penalty': 1, 'seed': args.seed}
    if args.effort != 'none':
        sampling.update(temperature=1, top_p=0.95, presence_penalty=0)
    protocol = {'suite': 'MMLU-Pro frozen 140 zero-shot screen', 'effort': args.effort,
                'sampling': sampling, 'max_tokens': args.tokens, 'version': 1}
    report = {'label': args.label, 'protocol': protocol,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'results': []}
    if output.exists():
        old = json.loads(output.read_text())
        if any(old[k] != report[k] for k in ['label', 'protocol', 'source_sha256']):
            raise RuntimeError('Resume provenance mismatch')
        report = old
    completed = {r['id'] for r in report['results']}
    for case in cases:
        if case['id'] in completed:
            continue
        row = case['data']
        choices = '\n'.join(f'{chr(65+i)}. {text}' for i, text in enumerate(row['options']))
        payload = {'model': 'ulmus', 'messages': [
            {'role': 'system', 'content': 'Choose the correct answer. Reply with only '
             'its single uppercase letter, without explanation.'},
            {'role': 'user', 'content': row['question'] + '\n\n' + choices}],
            **sampling, 'reasoning_effort': args.effort, 'max_tokens': args.tokens,
            'stream': True, 'stream_options': {'include_usage': True}}
        response = request(args.url, payload)
        content = response['content'].strip()
        answer = content if re.fullmatch(r'[A-J]', content) else None
        report['results'].append({'id': case['id'], 'category': row['category'],
            'expected': row['answer'], 'answer': answer, 'pass': answer == row['answer'],
            'input_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            'response': response})
        results = report['results']
        report['summary'] = {'passed': sum(r['pass'] for r in results), 'total': len(results),
            'truncated': sum(r['response']['finish_reason'] == 'length' for r in results),
            'format_failures': sum(r['answer'] is None for r in results),
            'wall_seconds': sum(r['response']['total_s'] for r in results)}
        output.write_text(json.dumps(report, indent=2))
        print(case['id'], row['category'], answer, 'pass', answer == row['answer'],
              'tokens', response['usage'].get('completion_tokens'), report['summary'], flush=True)


if __name__ == '__main__':
    main()
