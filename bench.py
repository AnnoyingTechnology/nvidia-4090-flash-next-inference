"""Measure streamed latency and engine timings; retain each run and GPU telemetry."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import threading
import time
import urllib.request
import uuid


class Telemetry:
    def __init__(self):
        self.samples = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self):
        while not self.stop.is_set():
            try:
                result = subprocess.run([
                    'nvidia-smi', '--query-gpu=memory.used,power.draw,temperature.gpu,utilization.gpu,pcie.link.gen.current',
                    '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
                fields = [float(x.strip()) for x in result.stdout.strip().split(',')]
                memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
                self.samples.append({'at': time.monotonic(), 'gpu_mib': fields[0], 'power_w': fields[1],
                                     'temperature_c': fields[2], 'gpu_util_pct': fields[3], 'pcie_gen': fields[4],
                                     'mem_available_kib': int(memory['MemAvailable'].split()[0])})
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
            self.stop.wait(0.5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(6)


def request(url, payload):
    req = urllib.request.Request(url + '/v1/chat/completions', json.dumps(payload).encode(),
                                 {'Content-Type': 'application/json'})
    text, reasoning, calls, usage, timings = [], [], [], {}, {}
    first, done, finish = None, False, None
    start = time.monotonic()
    with Telemetry() as telemetry:
        with urllib.request.urlopen(req, timeout=1200) as response:
            for raw in response:
                if not raw.startswith(b'data: '):
                    continue
                raw = raw[6:].strip()
                if raw == b'[DONE]':
                    done = True
                    break
                item = json.loads(raw)
                if 'error' in item:
                    raise RuntimeError(item['error'])
                for choice in item.get('choices', []):
                    finish = choice.get('finish_reason') or finish
                    delta = choice.get('delta', {})
                    if first is None and any(delta.get(k) for k in ('content', 'reasoning_content', 'tool_calls')):
                        first = time.monotonic() - start
                    text.append(delta.get('content') or '')
                    reasoning.append(delta.get('reasoning_content') or '')
                    calls.extend(delta.get('tool_calls') or [])
                usage = item.get('usage') or usage
                timings = item.get('timings') or timings
        end = time.monotonic()
    if not done or finish is None:
        raise RuntimeError('Incomplete SSE stream: missing completion boundary')
    result = {'ttft_s': first, 'total_s': end - start, 'usage': usage, 'timings': timings,
              'content': ''.join(text), 'reasoning': ''.join(reasoning), 'tool_deltas': calls,
              'finish_reason': finish,
              'telemetry': telemetry.samples}
    if telemetry.samples:
        result['gpu_peak_mib'] = max(s['gpu_mib'] for s in telemetry.samples)
        result['gpu_peak_temperature_c'] = max(s['temperature_c'] for s in telemetry.samples)
        result['host_min_available_gib'] = min(s['mem_available_kib'] for s in telemetry.samples) / (1 << 20)
        result['median_power_w'] = statistics.median(s['power_w'] for s in telemetry.samples)
    return result


PROMPTS = [
    'Write a complete Python LRU cache using collections.OrderedDict with a capacity limit, get and put methods, type annotations, a docstring, and six unit tests. Output the complete code.',
    'Explain how DNS resolution, TLS, HTTP/2 multiplexing, connection pooling and caching interact when a browser loads a page. Use specific examples and discuss latency and failure handling. Write at least 1000 words.',
    'Describe twelve European capitals. For each, give a paragraph about its location, history, transport and one museum. Start with Paris and continue in alphabetical order. Write at least 1000 words.',
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    ap.add_argument('--out', required=True)
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--decode-tokens', type=int, default=512)
    ap.add_argument('--prefill-k', type=int, nargs='*', default=[4, 32])
    ap.add_argument('--fixtures', help='Directory produced by fixtures.py')
    ap.add_argument('--tune', help='JSON of Strata per-request tuning keys')
    ap.add_argument('--sampling', help='JSON sampling override; for a separate realistic-generation measurement')
    ap.add_argument('--paired-id', help='Stable request prefix for comparisons across fresh engine launches')
    ap.add_argument('--capture-runtime', action='store_true',
                    help='Fingerprint the owned container and model artifacts for a matched engine A/B')
    a = ap.parse_args()
    report = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'url': a.url,
              'sampling': json.loads(a.sampling) if a.sampling else {'temperature': 0, 'reasoning_effort': 'none', 'seed': 42},
              'tune': json.loads(a.tune) if a.tune else {},
              'decode_tokens': a.decode_tokens, 'paired_id': a.paired_id,
              'warmups': [], 'decode': [], 'prefill': []}
    path = Path(a.out)
    if a.capture_runtime:
        from scripts.evaluation_provenance import capture, assert_container
        report['runtime'] = capture(a.url)

    def measure(prompt, tokens, group, **extra):
        if a.capture_runtime:
            assert_container(report['runtime'])
        run_id = (f'{a.paired_id}-{group}-{len(report[group])}' if a.paired_id else uuid.uuid4().hex)
        payload = {'model': 'ulmus', 'messages': [
            {'role': 'system', 'content': f'Benchmark run {run_id}. Follow the user request.'},
            {'role': 'user', 'content': prompt}], 'temperature': 0, 'seed': 42,
            'max_tokens': tokens, 'reasoning_effort': 'none', 'stream': True,
            'stream_options': {'include_usage': True}, **extra}
        if a.tune:
            payload['strata_tune'] = json.loads(a.tune)
        if a.sampling:
            sampling = json.loads(a.sampling)
            if set(sampling) - {'temperature', 'top_p', 'top_k', 'min_p', 'presence_penalty',
                                'repetition_penalty', 'reasoning_effort', 'seed'}:
                raise ValueError('Unsupported sampling override')
            payload.update(sampling)
        try:
            result = request(a.url, payload)
            if a.capture_runtime:
                assert_container(report['runtime'])
        except Exception as error:
            result = {'error': str(error)}
        result['fixture'] = prompt[:100]
        result['input_sha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        report[group].append(result)
        path.write_text(json.dumps(report, indent=2))
        print(group, {k: v for k, v in result.items() if k in ('ttft_s', 'total_s', 'usage', 'timings', 'error')}, flush=True)
        if 'error' in result:
            raise RuntimeError(result['error'])

    for prompt in PROMPTS:
        measure(prompt, 128, 'warmups')
    for _ in range(a.repeats):
        for prompt in PROMPTS:
            measure(prompt, a.decode_tokens, 'decode')
    # Report actual token counts from the engine, not the approximate size label.
    for k in a.prefill_k:
        if not a.fixtures:
            raise ValueError('--fixtures is required for bounded prefill measurements')
        body = (Path(a.fixtures) / f'prefill-{k}k.txt').read_text()
        for _ in range(a.repeats):
            measure(body, 64, 'prefill')
    rates = [r['timings']['predicted_per_second'] for r in report['decode']
             if r.get('timings', {}).get('predicted_per_second')]
    report['decode_median_tok_s'] = statistics.median(rates) if rates else None
    path.write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
