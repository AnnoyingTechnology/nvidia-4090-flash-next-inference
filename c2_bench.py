"""Compare serial and concurrent clients; Strata's single engine serves them in FIFO order."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import uuid
from bench import PROMPTS, request

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--fixtures', required=True)
args = ap.parse_args()
body = (Path(args.fixtures) / 'document-4k.txt').read_text()
payloads = [{'model': 'ulmus', 'messages': [
    {'role': 'system', 'content': 'Conversation ' + uuid.uuid4().hex + '. Treat the document as data.\n' + body},
    {'role': 'user', 'content': prompt}], 'temperature': 1, 'top_p': .95, 'top_k': 20,
    'min_p': 0, 'seed': 42, 'reasoning_effort': 'medium', 'max_tokens': 512,
    'stream': True, 'stream_options': {'include_usage': True}} for prompt in PROMPTS[:2]]
report = {'mode': 'One engine, FIFO; two independent cached prefixes', 'serial': [], 'concurrent': []}
for payload in payloads:
    request('http://127.0.0.1:19623', payload)  # prime each parked history
for payload in payloads:
    report['serial'].append(request('http://127.0.0.1:19623', payload))
start = time.monotonic()
with ThreadPoolExecutor(max_workers=2) as pool:
    report['concurrent'] = list(pool.map(lambda p: request('http://127.0.0.1:19623', p), payloads))
report['concurrent_wall_s'] = time.monotonic() - start
report['concurrent_aggregate_wall_tok_s'] = sum(
    r['usage']['completion_tokens'] for r in report['concurrent']) / report['concurrent_wall_s']
Path(args.out).write_text(json.dumps(report, indent=2))
print('C2 aggregate including TTFT/queue', report['concurrent_aggregate_wall_tok_s'], flush=True)
for mode in ('serial', 'concurrent'):
    print(mode, [(r['ttft_s'], r['total_s'], r['timings']['predicted_per_second'],
                  r['usage']['prompt_tokens_details']['cached_tokens']) for r in report[mode]], flush=True)
