"""Fixed-length decode speed at 32K, 64K and 128K of context on one loaded profile.

Each request is a document of the given size plus one of three questions, with a 512-token
low-reasoning generation. Engine timings keep prompt reading and decode separate; the order
is balanced against drift, and the first read of each document is uncached.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import request
from scripts.evaluation_provenance import capture, assert_container

ORDER = [32, 64, 128, 128, 64, 32, 32, 64, 128]
QUESTIONS = ['List the main components this document describes and explain each one.',
             'Describe the structure of this document section by section.',
             'Explain what an operator should check first when following this document, and why.']
SAMPLING = {'temperature': 1, 'top_p': 0.95, 'top_k': 20, 'min_p': 0, 'presence_penalty': 0,
            'repetition_penalty': 1, 'reasoning_effort': 'low', 'seed': 42}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--decode-tokens', type=int, default=512)
    ap.add_argument('--routing-trace', type=Path, help='Optional engine trace; record request byte boundaries')
    ap.add_argument('--context-k', type=int, nargs='+', choices=[32, 64, 128],
                    help='Restrict the existing balanced order to these context sizes')
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit('Output exists; use a fresh label')
    order = [k for k in ORDER if args.context_k is None or k in args.context_k]
    documents = {k: Path(f'fixtures/document-{k}k.txt').read_text() for k in sorted(set(order))}
    report = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'order': order,
              'sampling': SAMPLING, 'decode_tokens': args.decode_tokens,
              'documents_sha256': {k: hashlib.sha256(v.encode()).hexdigest() for k, v in documents.items()},
              'runtime': capture(args.url), 'cells': []}
    asked = {k: 0 for k in documents}
    for size in order:
        question = QUESTIONS[asked[size] % len(QUESTIONS)]
        asked[size] += 1
        payload = {'model': 'ulmus', 'messages': [{'role': 'user', 'content': documents[size] +
                   '\n\nQuestion: ' + question + ' Answer in detail.'}], 'max_tokens': args.decode_tokens,
                   'stream': True, 'stream_options': {'include_usage': True}, **SAMPLING}
        assert_container(report['runtime'])
        trace_before = args.routing_trace.stat().st_size if args.routing_trace else None
        result = request(args.url, payload)
        trace_after = args.routing_trace.stat().st_size if args.routing_trace else None
        assert_container(report['runtime'])
        t = result['timings']
        report['cells'].append({'context_k': size, 'question': question,
            'prompt_tokens': result['usage']['prompt_tokens'], 'reused_tokens': t['cache_n'],
            'read_tokens': t['prompt_n'], 'prompt_ms': t['prompt_ms'],
            'completion_tokens': result['usage']['completion_tokens'], 'finish_reason': result['finish_reason'],
            'decode_tok_s': t['predicted_per_second'], 'draft_n': t['draft_n'],
            'draft_n_accepted': t['draft_n_accepted'], 'median_power_w': result.get('median_power_w'),
            'input_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            **({'routing_trace_bytes': [trace_before, trace_after]} if args.routing_trace else {})})
        args.out.write_text(json.dumps(report, indent=2))
        print(size, t['cache_n'], t['prompt_n'], round(t['prompt_ms']), result['usage']['completion_tokens'],
              t['predicted_per_second'], flush=True)


if __name__ == '__main__':
    main()
