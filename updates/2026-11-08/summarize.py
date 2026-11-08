"""Summarize the frozen November update protocol; reject incomplete or mismatched evidence."""
import argparse
import datetime
import json
from pathlib import Path
import re
import statistics


def read(root, name):
    return json.loads((root / name).read_text())


def performance(root, names):
    reports = [read(root, name) for name in names]
    decode, prefill = [], []
    for report in reports:
        assert len(report['decode']) == 6 and len(report['prefill']) == 2
        assert all(r['usage']['completion_tokens'] == 512 and 'error' not in r for r in report['decode'])
        assert all(r['timings']['cache_n'] == 0 and r['timings']['prompt_n'] == 31823 for r in report['prefill'])
        decode.extend(report['decode'])
        prefill.extend(report['prefill'])
    return reports, {
        'reports': names,
        'fresh_starts': len(reports),
        'decode_requests': len(decode),
        'decode_median_tok_s': statistics.median(r['timings']['predicted_per_second'] for r in decode),
        'prefill_median_tok_s': statistics.median(r['timings']['prompt_per_second'] for r in prefill),
        'short_prompt_ttft_median_s': statistics.median(r['ttft_s'] for r in decode),
        'per_start_decode_medians': [r['decode_median_tok_s'] for r in reports],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    baseline, old = performance(args.evidence, ['update-20261108-baseline-ready-perf.json', 'update-20261108-baseline2-perf.json'])
    selected, new = performance(args.evidence, ['perf-fetch.json', 'perf-fetch2.json'])
    for report in baseline + selected:
        for group in ['decode', 'prefill']:
            assert [r['input_sha256'] for r in report[group]] == [r['input_sha256'] for r in baseline[0][group]]
    diagnostic = {}
    for name in ['auto', 'fetch']:
        report = read(args.evidence, f'perf-{name}.json')
        hits = re.findall(r'decode expert cache hit rate: ([0-9.]+)%',
                          (args.evidence / f'engine-{name}.log').read_text())
        diagnostic[name] = {'decode_median_tok_s': report['decode_median_tok_s'],
                            'decode_cache_hit_median_pct': statistics.median(map(float, hits[3:9]))}
    quality = {}
    for effort in ['off', 'low']:
        a = read(args.evidence, f'update-20261108-baseline-{effort}.json')
        b = read(args.evidence, f'selected-{effort}.json')
        assert a['source_sha256'] == b['source_sha256'] and a['grader_image_id'] == b['grader_image_id']
        assert a['protocol'] == b['protocol']
        assert [r['input_sha256'] for r in a['results']] == [r['input_sha256'] for r in b['results']]
        assert a['runtime']['identity']['artifacts']['target_shards'] == b['runtime']['identity']['artifacts']['target_shards']
        for report in [a, b]:
            assert len(report['results']) == 30 and len(report['controls']) == 30
            assert all(r['response']['finish_reason'] == 'stop' for r in report['results'])
            assert all(c['positive']['pass'] and not c['negative']['pass'] for c in report['controls'].values())
        quality[effort] = {'baseline': a['summary'], 'selected': b['summary'], 'max_tokens': b['protocol']['max_tokens'],
                           'all_natural_completions': True, 'same_target_artifact_identity': True}
    api = read(args.evidence, 'api-fetch2.json')['summary']
    vision = read(args.evidence, 'vision-selected.json')['summary']
    checks = read(args.evidence, 'quality-selected.json')
    maximum_images = read(args.evidence, 'maximum-images.json')['checks']
    deployment = read(args.evidence, 'deployment.json')
    assert deployment['qualification_identity_match_except_profile_log_path']
    events = [json.loads(line) for line in (args.evidence / 'opencode-client.jsonl').read_text().splitlines()
              if line.startswith('{')]
    assert ''.join(e['part']['text'] for e in events if e.get('type') == 'text').strip() == 'READY'
    assert any(e.get('type') == 'step_finish' and e.get('part', {}).get('reason') == 'stop' for e in events)
    assert api['passed'] == api['total'] == 9
    assert vision['content_passed'] == vision['total'] == 5 and vision['truncated'] == 0
    assert all(c['pass'] for c in checks) and len(checks) == 10
    assert len(maximum_images) == 3 and all(c['passed'] for c in maximum_images)
    output = {
        'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'deployed and verified through the normal OpenCode launcher',
        'deployment': {'observed_at': deployment['observed_at'], 'service': deployment['service'],
            'image_id': deployment['runtime']['identity']['image_id'], 'gpu': deployment['gpu'],
            'qualification_identity_match_except_profile_log_path': True, 'opencode_response': 'READY'},
        'baseline': old, 'selected': new,
        'decode_change_pct': 100 * (new['decode_median_tok_s'] / old['decode_median_tok_s'] - 1),
        'prefill_change_pct': 100 * (new['prefill_median_tok_s'] / old['prefill_median_tok_s'] - 1),
        'mechanism_diagnostic': {
            'scope': 'One fresh start per setting; same new runtime/profile, with cache admission disabled/enabled.',
            'arms': diagnostic,
            'interpretation': 'ADAPT_FETCH=2 admits eligible fetched misses directly into the GPU cache and disables separate adaptive-tier copies. Automatic CPU/PCIe balancing settled at 0.25; the old profile fixed 0.35.',
            'limits': 'The complete 14.2% gain is not a sum of isolated kernel improvements. CPU-assisted short prefill is enabled, but the 32K prefill gain was not decomposed per kernel.'},
        'code_canaries': quality, 'api': api, 'vision_content': vision,
        'functional_checks': [{'check': c['check'], 'pass': c['pass'], 'usage': c.get('usage')} for c in checks],
        'maximum_image_staging': [{'cached': c['cached'], 'passed': c['passed'],
            'reader_starts': c['observed_reader_starts'], 'ttft_s': c['response']['ttft_s'],
            'usage': c['response']['usage']} for c in maximum_images],
        'limits': ['Two fresh starts per arm; not a universal speed guarantee.',
                   'Thirty synthetic DevOps functions at one seed per effort; not broad quality parity.',
                   'Vision content and JSON formatting are scored separately.',
                   'The first uncached image after encoder idle pays a measured GPU-reader restart cost.',
                   'No local full-size/Q8 target reference, host driver upgrade, or power-policy change.'],
    }
    args.out.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({k: output[k] for k in ['decode_change_pct', 'prefill_change_pct', 'api', 'vision_content']}))


if __name__ == '__main__':
    main()
