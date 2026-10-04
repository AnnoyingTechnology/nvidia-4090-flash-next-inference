"""Matched resident-GPU-vision versus lend-VRAM swap A/B: decode cells plus the 15-image deck latency."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_provenance import fingerprint
from scripts.summarize_native_ab import check_cells
from scripts.summarize_vision_residency import cell, side_summary

SAME = ['tokenizer', 'target_shards', 'pack', 'mtp', 'expert_profile', 'shared_defaults_sha256']
SWAP_LINE = re.compile(
    r'strata serve: (?P<operation>LEND|RECLAIM) (?P<status>done|FAILED), '
    r'(?:(?P<mib>\d+) MiB, )?(?P<slots>\d+) slots, (?P<ms>[\d.]+) ms')
MAP_LINE = re.compile(r'RECLAIM mapped the tail in ([\d.]+) ms(?: \([^)]*\))?, refilled and verified in ([\d.]+) ms')


def side_of(run):
    return 'swap' if run['profile'].endswith('-ownerswap') else 'resident'


def without_lend(command):
    out = list(command)
    if '--lend-vram-mib' in out:
        i = out.index('--lend-vram-mib')
        del out[i:i + 2]
    return out


def check_runtimes(perfs, runs):
    ids = {side: [p['runtime']['identity'] for p, r in zip(perfs, runs) if side_of(r) == side]
           for side in ['resident', 'swap']}
    for side, items in ids.items():
        if not items or len({fingerprint(x) for x in items}) != 1:
            raise ValueError('Each profile needs launches with one runtime: ' + side)
    a, b = ids['resident'][0]['artifacts'], ids['swap'][0]['artifacts']
    if ids['resident'][0]['chat_template_sha256'] != ids['swap'][0]['chat_template_sha256']:
        raise ValueError('Chat templates differ')
    if a['vision_artifacts']['projector'] != b['vision_artifacts']['projector']:
        raise ValueError('Vision projector inputs differ')
    for key in SAME:
        if a[key] != b[key]:
            raise ValueError('Runtime inputs differ: ' + key)
    if without_lend(a['native_command']) != without_lend(b['native_command']):
        raise ValueError('Engine arguments differ beyond --lend-vram-mib')
    return {'engine_binary_differs': a['native_sha256'] != b['native_sha256'],
            'image_ids': {side: items[0]['image_id'] for side, items in ids.items()},
            'native_sha256': {side: items[0]['artifacts']['native_sha256'] for side, items in ids.items()},
            'lend_vram_args': [x for x in b['native_command'] if x not in a['native_command']]}


def deck(path):
    report = json.loads(path.read_text())
    log = path.with_name(path.name.replace('.json', '-engine.log')).read_text()
    swaps = [m.groupdict() for m in SWAP_LINE.finditer(log)]
    if len(swaps) != len(re.findall(r'strata serve: (?:LEND|RECLAIM) (?:done|FAILED)', log)):
        raise ValueError('Unrecognized LEND/RECLAIM log format: ' + path.name)
    expected_swap = report['protocol']['model'].endswith('-swap')
    if expected_swap != bool(swaps):
        raise ValueError('Model label and LEND/RECLAIM evidence disagree: ' + path.name)
    results = report['results']
    if len(results) != 15 or len({x['id'] for x in results}) != 15:
        raise ValueError('Expected the complete fifteen-image deck: ' + path.name)
    if any(x['response'].get('finish_reason') != 'stop' or 'error' in x['response'] for x in results):
        raise ValueError('Every image answer must finish naturally: ' + path.name)
    maps = [(float(m[1]), float(m[2])) for m in MAP_LINE.finditer(log)]
    rows = {x['id']: {'ttft_s': x['response'].get('ttft_s'), 'content_correct': x['verdict']['content_correct'],
                      'strict_correct': x['verdict']['strict_correct'], 'finish': x['response'].get('finish_reason'),
                      'image_sha256': x['image_sha256'], 'prompt_sha256': x['prompt_sha256']}
            for x in report['results']}
    return {'source': path.name, 'model_label': report['protocol']['model'], 'summary': report['summary'],
            'protocol': {k: v for k, v in report['protocol'].items() if k != 'model'},
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'cases': rows,
            'lend_reclaim': {'count': len(swaps), 'failed': sum(s['status'] != 'done' for s in swaps),
                             'lend_ms_median': statistics.median([float(s['ms']) for s in swaps if s['operation'] == 'LEND'] or [0]),
                             'reclaim_ms_median': statistics.median([float(s['ms']) for s in swaps if s['operation'] == 'RECLAIM'] or [0]),
                             'lend_mib': sorted({int(s['mib']) for s in swaps if s['operation'] == 'LEND' and s['mib'] is not None}),
                             'reclaim_map_ms_median': statistics.median([m[0] for m in maps] or [0]),
                             'reclaim_refill_ms_median': statistics.median([m[1] for m in maps] or [0]),
                             'slots': sorted({int(s['slots']) for s in swaps})}}


def first_token(decks):
    reference = decks[0]
    for d in decks[1:]:
        if d['protocol'] != reference['protocol'] or d['cases'].keys() != reference['cases'].keys():
            raise ValueError('Image deck protocol or cases differ: ' + d['source'])
        for case in reference['cases']:
            for key in ['image_sha256', 'prompt_sha256']:
                if d['cases'][case][key] != reference['cases'][case][key]:
                    raise ValueError('Image deck request differs: ' + d['source'] + ': ' + case)
    by_side = {side: [d for d in decks if (d['lend_reclaim']['count'] > 0) == (side == 'swap')]
               for side in ['resident', 'swap']}
    if any(not items for items in by_side.values()):
        raise ValueError('Both resident and swap decks are required')
    if len(by_side['swap']) != len(by_side['resident']):
        raise ValueError('Equal numbers of swap and resident decks are required')
    per_case = {}
    for case in decks[0]['cases']:
        vt = statistics.median(d['cases'][case]['ttft_s'] for d in by_side['resident'])
        st = statistics.median(d['cases'][case]['ttft_s'] for d in by_side['swap'])
        per_case[case] = {'resident_ttft_s': vt, 'swap_ttft_s': st, 'delta_ms': 1000 * (st - vt)}
    deltas = [x['delta_ms'] for x in per_case.values()]
    pair_maxima = [max(1000 * (s['cases'][case]['ttft_s'] - v['cases'][case]['ttft_s'])
                       for case in reference['cases'])
                   for s, v in zip(by_side['swap'], by_side['resident'])]
    return {'per_case': per_case, 'median_delta_ms': statistics.median(deltas), 'max_delta_ms': max(deltas),
            'paired_launch_max_delta_ms': pair_maxima, 'max_single_pair_delta_ms': max(pair_maxima),
            'content_correct': {side: [d['summary']['content_correct'] for d in items]
                                for side, items in by_side.items()},
            'lend_reclaim': [d['lend_reclaim'] for d in by_side['swap']]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cells', type=Path, nargs='*', default=[], help='Per-cell *-perf.json in launch order')
    ap.add_argument('--decks', type=Path, nargs='+', required=True, help='vision15 deck reports in launch order')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    decks = [deck(p) for p in args.decks]
    if not args.cells:                      # a deck-only latency rerun of a later prototype build
        result = {'scope': 'Image first-token latency only: resident GPU vision versus the swap prototype',
                  'decks': decks, 'image_first_token': first_token(decks)}
        args.out.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result['image_first_token'].items() if k != 'per_case'}))
        return
    perfs, runs = zip(*[cell(path) for path in args.cells])
    for perf in perfs[1:]:
        for key in ['sampling', 'tune', 'decode_tokens', 'paired_id']:
            if perf[key] != perfs[0][key]:
                raise ValueError('Benchmark protocol differs: ' + key)
        check_cells(perfs[0], perf)
    runtime = check_runtimes(perfs, runs)
    sides = {side: side_summary([r for r in runs if side_of(r) == side]) for side in ['resident', 'swap']}
    v, s = sides['resident'], sides['swap']
    result = {
        'scope': 'Original IQ3 GPU-vision profile with the encoder resident versus the lend-VRAM swap prototype: '
                 'the encoder frees its weights and work buffers between new images and the engine lends it the '
                 "expert cache's tail per new image. Same weights, settings and requests; fresh launch per cell.",
        'runtime': runtime, 'order': [side_of(r) for r in runs], 'runs': list(runs), 'sides': sides,
        'decode_gain_percent': 100 * (s['median_of_launch_medians_tok_s'] - v['median_of_launch_medians_tok_s'])
                               / v['median_of_launch_medians_tok_s'],
        'per_launch_ranges_overlap': max(min(v['per_launch_decode_median_tok_s']),
                                         min(s['per_launch_decode_median_tok_s'])) <=
                                     min(max(v['per_launch_decode_median_tok_s']),
                                         max(s['per_launch_decode_median_tok_s'])),
        'decks': decks, 'deck_order': ['swap' if d['lend_reclaim']['count'] else 'resident' for d in decks],
        'image_first_token': first_token(decks),
    }
    image = result['image_first_token']
    criteria = {
        'decode_gain_at_least_5_percent_and_nonoverlapping':
            result['decode_gain_percent'] >= 5 and not result['per_launch_ranges_overlap'],
        'api_and_swap_integrity':
            all(d['lend_reclaim']['failed'] == 0 for d in decks),  # cell() requires all API checks
        'image_median_at_most_100_ms_and_every_pair_at_most_250_ms':
            image['median_delta_ms'] <= 100 and image['max_single_pair_delta_ms'] <= 250,
        'equal_image_content_scores':
            image['content_correct']['resident'] == image['content_correct']['swap'],
    }
    result['adoption_rule'] = {'criteria': criteria, 'passes': all(criteria.values())}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['order', 'decode_gain_percent', 'per_launch_ranges_overlap',
                                             'deck_order']}))
    print(json.dumps({k: v for k, v in result['image_first_token'].items() if k != 'per_case'}))
    for side, summary in sides.items():
        print(side, json.dumps(summary))
    for d in decks:
        print(d['source'], d['summary']['content_correct'], json.dumps(d['lend_reclaim']))


if __name__ == '__main__':
    main()
