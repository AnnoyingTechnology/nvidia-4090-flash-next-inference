"""Publish a matched native-engine comparison without private runtime captures."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics


def read(path):
    return json.loads(path.read_text())


def summarize(left_path, right_path):
    left, right = read(left_path), read(right_path)
    for key in ['sampling', 'tune', 'decode_tokens', 'paired_id']:
        if left[key] != right[key]:
            raise ValueError('Benchmark protocol differs: ' + key)
    if not left['paired_id']:
        raise ValueError('A stable paired request ID is required')
    artifacts = [r['runtime']['identity']['artifacts'] for r in [left, right]]
    for key in ['api_sources', 'native_command', 'tokenizer', 'target_shards', 'pack', 'mtp',
                'expert_profile', 'vision_artifacts']:
        if key == 'native_command':
            # Only the executable path differs; actual engine arguments must match.
            values = [a[key][1:] for a in artifacts]
        else:
            values = [a[key] for a in artifacts]
        if values[0] != values[1]:
            raise ValueError('Runtime inputs differ: ' + key)
    for group, count in [('warmups', 3), ('decode', 6), ('prefill', 2)]:
        if any(len(r[group]) != count for r in [left, right]):
            raise ValueError('Incomplete benchmark group: ' + group)
        for a, b in zip(left[group], right[group]):
            if a['input_sha256'] != b['input_sha256']:
                raise ValueError('Paired request hash differs: ' + group)
            if any('error' in r or not r.get('timings') for r in [a, b]):
                raise ValueError('Missing timings or errored request')
            if a['usage']['prompt_tokens'] != b['usage']['prompt_tokens']:
                raise ValueError('Tokenizer counts differ')
            if group == 'decode' and any(r['usage']['completion_tokens'] != left['decode_tokens']
                                         for r in [a, b]):
                raise ValueError('Decode cell is not the requested fixed length')
            if group == 'prefill' and any(r['timings']['cache_n'] != 0 for r in [a, b]):
                raise ValueError('Prefill cell reused prompt cache')
    runs = []
    for path, report, artifact in zip([left_path, right_path], [left, right], artifacts):
        api_path = path.with_name(path.name.replace('-perf.json', '-api.json'))
        api = read(api_path)
        if api['summary'] != {'passed': 9, 'total': 9}:
            raise ValueError('All nine API checks must pass')
        log_path = path.parent / (api['profile'] + '-engine.log')
        log = log_path.read_text()
        cache = re.search(r'expert cache (\d+) slots, ([\d.]+) GiB of VRAM', log)
        if not cache:
            raise ValueError('Expert cache allocation missing from engine log')
        cells = {group: [{key: r.get(key) for key in ['input_sha256', 'finish_reason', 'ttft_s',
                     'total_s', 'usage', 'timings', 'gpu_peak_mib', 'median_power_w']}
                    for r in report[group]] for group in ['warmups', 'decode', 'prefill']}
        timings = [r['timings'] for r in report['decode']]
        drafted = sum(r['draft_n'] for r in timings)
        accepted = sum(r['draft_n_accepted'] for r in timings)
        runs.append({'source': path.name,
            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'runtime_fingerprint': report['runtime']['fingerprint'],
            'image_id': report['runtime']['identity']['image_id'],
            'native_sha256': artifact['native_sha256'],
            'cache_allocation': {'slots': int(cache[1]), 'gib_rounded_in_engine_log': float(cache[2]),
                'engine_log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest()},
            'api_checks': {'profile': api['profile'], 'summary': api['summary'],
                'source_sha256': hashlib.sha256(api_path.read_bytes()).hexdigest(),
                'checks': [{'name': c['name'], 'passed': c['passed']} for c in api['checks']]},
            'engine_args': artifact['native_command'][1:],
            'decode_median_tok_s': statistics.median(r['predicted_per_second'] for r in timings),
            'short_prompt_ttft_median_s': statistics.median(r['ttft_s'] for r in report['decode']),
            'drafted_tokens': drafted, 'accepted_drafts': accepted,
            'aggregate_draft_acceptance': accepted / drafted if drafted else None,
            'cells': cells})
    return {'scope': 'CUDA 12.4 adaptation versus pinned upstream, same quantized target and '
            '32K fully resident int8 KV allocation. Not a 256K fork result.',
        'protocol': {key: left[key] for key in ['sampling', 'tune', 'decode_tokens', 'paired_id']},
        'matching_request_hashes': 11, 'runs': runs,
        'interpretation': 'Fixed-length throughput counts reasoning and answer tokens; intentional '
            'caps are not quality tests. Each engine generates its own continuation. Cache adaptation '
            'and MTP acceptance can differ, so speed differences do not isolate an individual kernel.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--left', type=Path, required=True)
    ap.add_argument('--right', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = summarize(args.left, args.right)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print([(r['source'], r['decode_median_tok_s']) for r in result['runs']])


if __name__ == '__main__':
    main()
