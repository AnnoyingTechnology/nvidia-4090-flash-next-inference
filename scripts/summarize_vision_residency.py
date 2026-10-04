"""Publish the matched text-only versus GPU-vision decode A/B without private runtime captures."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_provenance import fingerprint
from scripts.summarize_native_ab import read, check_cells

REQUEST = re.compile(r'strata serve: prompt (\d+) tokens = (\d+) reused .*?, (\d+) generated in')
HITS = re.compile(r'decode expert cache hit rate: [\d.]+% \((\d+) hits / (\d+) lookups\)')
CACHE = re.compile(r'expert cache (\d+) slots, ([\d.]+) GiB of VRAM')
COMMON = ['api_sources', 'tokenizer', 'target_shards', 'pack', 'mtp', 'expert_profile',
          'native_sha256', 'shared_defaults_sha256']


def served(log):
    """Pair each served request with the decode expert-cache hit line that follows it."""
    rows = []
    for line in log.splitlines():
        if match := REQUEST.search(line):
            rows.append({'prompt_tokens': int(match[1]), 'reused_tokens': int(match[2]),
                         'generated_tokens': int(match[3]), 'hits': None, 'lookups': None})
        elif (match := HITS.search(line)) and rows and rows[-1]['hits'] is None:
            rows[-1].update(hits=int(match[1]), lookups=int(match[2]))
    return rows


def cell(path):
    perf = read(path)
    api_path = path.with_name(path.name.replace('-perf.json', '-api.json'))
    log_path = path.with_name(path.name.replace('-perf.json', '-engine.log'))
    api, log = read(api_path), log_path.read_text()
    if api['summary'] != {'passed': 9, 'total': 9}:
        raise ValueError('All nine API checks must pass: ' + path.name)
    cache = CACHE.findall(log)
    if len(cache) != 1:
        raise ValueError('Expected exactly one engine launch in the cell log: ' + path.name)
    bench = perf['warmups'] + perf['decode'] + perf['prefill']
    engine = served(log)[:len(bench)]
    if [(r['prompt_tokens'], r['generated_tokens']) for r in engine] != [
            (r['usage']['prompt_tokens'], r['usage']['completion_tokens']) for r in bench]:
        raise ValueError('Engine log does not align with the benchmark requests: ' + path.name)
    decode_engine = engine[3:9]
    if any(r['lookups'] is None for r in decode_engine):
        raise ValueError('Decode cell lacks an expert-cache hit line: ' + path.name)
    timings = [r['timings'] for r in perf['decode']]
    drafted = sum(t['draft_n'] for t in timings)
    accepted = sum(t['draft_n_accepted'] for t in timings)
    return perf, {'source': path.name, 'profile': api['profile'],
        'side': 'vision' if '-vision-' in api['profile'] else 'text',
        'started_at': perf['observed_at'],
        'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [path, api_path, log_path]},
        'runtime_fingerprint': fingerprint(perf['runtime']['identity']),
        'expert_cache': {'slots': int(cache[0][0]), 'gib_rounded_in_engine_log': float(cache[0][1])},
        'api_checks': api['summary'],
        'decode_tok_s': [t['predicted_per_second'] for t in timings],
        'decode_median_tok_s': statistics.median(t['predicted_per_second'] for t in timings),
        'decode_hit_rate': [r['hits'] / r['lookups'] for r in decode_engine],
        'decode_hit_rate_aggregate': sum(r['hits'] for r in decode_engine) /
                                     sum(r['lookups'] for r in decode_engine),
        'aggregate_draft_acceptance': accepted / drafted if drafted else None,
        'short_prompt_ttft_median_s': statistics.median(r['ttft_s'] for r in perf['decode']),
        'prefill_tok_s': [r['timings']['prompt_per_second'] for r in perf['prefill']],
        'prefill_prompt_tokens': perf['prefill'][0]['usage']['prompt_tokens'],
        'decode_gpu_peak_mib': max(r['gpu_peak_mib'] for r in perf['decode']),
        'decode_median_board_power_w': statistics.median(r['median_power_w'] for r in perf['decode'])}


def check_runtimes(text, vision):
    for side in [text, vision]:
        if len({fingerprint(r['runtime']['identity']) for r in side}) != 1:
            raise ValueError('Runtime differs between launches of one profile')
    a, b = text[0]['runtime']['identity'], vision[0]['runtime']['identity']
    for key in ['image_id', 'chat_template_sha256']:
        if a[key] != b[key]:
            raise ValueError('Frontend differs: ' + key)
    for key in COMMON:
        if a['artifacts'][key] != b['artifacts'][key]:
            raise ValueError('Runtime inputs differ: ' + key)
    if 'vision_artifacts' in a['artifacts'] or 'vision_artifacts' not in b['artifacts']:
        raise ValueError('Vision residency must differ exactly by the GPU vision worker')
    if [x for x in b['artifacts']['native_command'] if x != '--vision'] != a['artifacts']['native_command']:
        raise ValueError('Engine arguments differ beyond --vision')


def side_summary(runs):
    medians = [r['decode_median_tok_s'] for r in runs]
    return {'launches': len(runs), 'expert_cache_slots': sorted({r['expert_cache']['slots'] for r in runs}),
        'per_launch_decode_median_tok_s': medians,
        'median_of_launch_medians_tok_s': statistics.median(medians),
        'pooled_decode_median_tok_s': statistics.median(x for r in runs for x in r['decode_tok_s']),
        'decode_hit_rate_median_of_launches': statistics.median(r['decode_hit_rate_aggregate'] for r in runs),
        'short_prompt_ttft_median_s': statistics.median(r['short_prompt_ttft_median_s'] for r in runs),
        'prefill_median_tok_s': statistics.median(x for r in runs for x in r['prefill_tok_s'])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cells', type=Path, nargs='+', required=True, help='Per-cell *-perf.json in launch order')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    perfs, runs = zip(*[cell(path) for path in args.cells])
    for perf in perfs[1:]:
        for key in ['sampling', 'tune', 'decode_tokens', 'paired_id']:
            if perf[key] != perfs[0][key]:
                raise ValueError('Benchmark protocol differs: ' + key)
        check_cells(perfs[0], perf)
    text = [p for p, r in zip(perfs, runs) if r['side'] == 'text']
    vision = [p for p, r in zip(perfs, runs) if r['side'] == 'vision']
    if not text or not vision:
        raise ValueError('Both profiles are required')
    check_runtimes(text, vision)
    sides = {side: side_summary([r for r in runs if r['side'] == side]) for side in ['text', 'vision']}
    t, v = sides['text'], sides['vision']
    encoder = 'GPU' if vision[0]['runtime']['identity']['artifacts']['engine_config']['vision']['gpu'] else 'CPU'
    result = {'scope': f'Original IQ3 text-only versus {encoder} BF16 vision profile on the same engine, '
            'weights and settings; a GPU vision worker reduces the expert cache allocated at launch. '
            'Fresh launch per cell; benchmark runs before any other request.',
        'vision_encoder': encoder,
        'protocol': {key: perfs[0][key] for key in ['sampling', 'tune', 'decode_tokens', 'paired_id']},
        'order': [r['side'] for r in runs], 'runs': list(runs), 'sides': sides,
        'decode_gap_percent': 100 * (t['median_of_launch_medians_tok_s'] - v['median_of_launch_medians_tok_s'])
                              / t['median_of_launch_medians_tok_s'],
        'per_launch_ranges_overlap': max(min(t['per_launch_decode_median_tok_s']),
                                         min(v['per_launch_decode_median_tok_s'])) <=
                                     min(max(t['per_launch_decode_median_tok_s']),
                                         max(v['per_launch_decode_median_tok_s'])),
        'interpretation': 'Fixed-length 512-token low-reasoning decode counts reasoning and answer tokens. '
            'No image request is sent in these cells; image latency is outside this comparison.'}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['order', 'decode_gap_percent', 'per_launch_ranges_overlap']}))
    for side, summary in sides.items():
        print(side, json.dumps(summary))


if __name__ == '__main__':
    main()
