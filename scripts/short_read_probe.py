"""Per-turn prompt cost of short fresh reads in an agent-like chain at realistic context.

Each request repeats the previous conversation and adds a fixed short assistant turn plus a
tool-style message of a chosen line count, so the server resumes from the previous turn's
checkpoint and reads only the new part. Run the same seeded order once per --short-read
engine setting. The reported prompt time includes lending and refilling expert-cache slots.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import request
from scripts.evaluation_provenance import capture, assert_container

LINES = [1, 2, 4, 6, 8, 12, 16, 24, 32, 48]
SYSTEM = 'You are a terse operations assistant. Reply in at most one short sentence.'
ASSISTANT = 'Checked. Continue with the next batch.'


def tool_message(lines, step):
    rows = [f'host web-{(step * 7 + i) % 97:02d} status ok latency {(step * 13 + i * 29) % 400} ms'
            for i in range(lines)]
    return 'Tool output:\n' + '\n'.join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--document', type=Path, default=Path('fixtures/document-64k.txt'))
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--seed', type=int, default=20261004)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit('Output exists; use a fresh label')
    order = [lines for lines in LINES for _ in range(args.repeats)]
    random.Random(args.seed).shuffle(order)
    document = args.document.read_text()
    report = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'document': args.document.name, 'document_sha256': hashlib.sha256(document.encode()).hexdigest(),
              'seed': args.seed, 'order': order, 'runtime': capture(args.url), 'turns': []}
    messages = [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': document + '\n\nKeep this inventory in mind for the tool outputs.'}]
    for step, lines in enumerate([0] + order):
        if lines:
            messages += [{'role': 'assistant', 'content': ASSISTANT},
                         {'role': 'user', 'content': tool_message(lines, step)}]
        payload = {'model': 'ulmus', 'messages': messages, 'max_tokens': 8, 'temperature': 0, 'seed': 42,
                   'reasoning_effort': 'none', 'stream': True, 'stream_options': {'include_usage': True}}
        assert_container(report['runtime'])
        result = request(args.url, payload)
        assert_container(report['runtime'])
        timings = result['timings']
        report['turns'].append({'step': step, 'lines': lines, 'reused_tokens': timings['cache_n'],
            'read_tokens': timings['prompt_n'], 'prompt_ms': timings['prompt_ms'],
            'ttft_s': result['ttft_s'], 'total_s': result['total_s'], 'finish_reason': result['finish_reason'],
            'input_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()})
        args.out.write_text(json.dumps(report, indent=2))
        print(step, lines, timings['cache_n'], timings['prompt_n'], round(timings['prompt_ms']), flush=True)


if __name__ == '__main__':
    main()
