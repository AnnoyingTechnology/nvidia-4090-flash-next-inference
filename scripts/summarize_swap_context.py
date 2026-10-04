"""Validate and summarize matched swap-v4 context qualification cells."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.summarize_swap_ab import check_runtimes

RESIDENT = 'sha256:a1649d9812c7944dbbf880a33e272886a5b059bae22e65e713404a50aed46644'
SWAP = 'sha256:24386fa3fb0e4d7ff2680174d5a126090293920c4556f1cf289a6af9d24bdefe'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cells', type=Path, nargs='+', required=True, help='Fresh launches S V V S, or V S')
    ap.add_argument('--context-k', type=int, choices=[64, 128], default=64)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    reports, runs = [], []
    reference = None
    if len(args.cells) not in [2, 4]:
        raise ValueError('Expected two or four matched launches')
    order = ['resident', 'swap'] if len(args.cells) == 2 else ['swap', 'resident', 'resident', 'swap']
    for path, side in zip(args.cells, order):
        r = json.loads(path.read_text())
        api = json.loads(path.with_name(path.stem + '-api.json').read_text())
        log = path.with_name(path.stem + '-engine.log').read_text()
        expected_profile = 'flash-iq3s-256k-vision-tune-owner' + ('swap' if side == 'swap' else 'vision')
        if api['profile'] != expected_profile or api['summary'] != {'passed': 9, 'total': 9}:
            raise ValueError('Profile/API checks differ or fail: ' + path.name)
        if not all(x['passed'] for x in api['checks']) or 'FAILED' in log or 'CUDA error' in log:
            raise ValueError('API or engine error: ' + path.name)
        if r['runtime']['identity']['image_id'] != (SWAP if side == 'swap' else RESIDENT):
            raise ValueError('Unexpected image pin: ' + path.name)
        if r['order'] != [args.context_k] * 3 or r['decode_tokens'] != 512 or len(r['cells']) != 3:
            raise ValueError('Incomplete or changed context protocol: ' + path.name)
        if r['sampling']['reasoning_effort'] != 'low':
            raise ValueError('Expected low reasoning: ' + path.name)
        if any(c['completion_tokens'] != 512 or c['finish_reason'] != 'length' or
               c['decode_tok_s'] <= 0 for c in r['cells']):
            raise ValueError('Incomplete fixed-length performance sample: ' + path.name)
        identity = {'sampling': r['sampling'], 'documents_sha256': r['documents_sha256'],
                    'questions': [(c['question'], c['input_sha256'], c['prompt_tokens']) for c in r['cells']]}
        if reference is not None and identity != reference:
            raise ValueError('Requests, documents, token counts or sampling differ: ' + path.name)
        reference = identity
        rows = r['cells']
        runs.append({'source': path.name, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'profile': expected_profile, 'side': side, 'api': api['summary'], 'cells': rows,
                     'median_decode_tok_s': statistics.median(c['decode_tok_s'] for c in rows),
                     'draft_acceptance': sum(c['draft_n_accepted'] for c in rows) / sum(c['draft_n'] for c in rows)})
        reports.append(r)
    runtime_check = check_runtimes(reports, runs)
    sides = {}
    for side in ['resident', 'swap']:
        selected = [r for r in runs if r['side'] == side]
        medians = [r['median_decode_tok_s'] for r in selected]
        sides[side] = {'launch_decode_medians': medians, 'median_decode_tok_s': statistics.median(medians),
                       'launch_range': [min(medians), max(medians)],
                       'draft_acceptance': statistics.median(r['draft_acceptance'] for r in selected)}
    ratio = sides['swap']['median_decode_tok_s'] / sides['resident']['median_decode_tok_s']
    out = {'scope': f'Matched {args.context_k}K context, three fixed 512-token decode samples per fresh launch.',
           'launch_order': order,
           'replication_limit': 'A single launch per side cannot establish a repeatable gain.' if len(args.cells) == 2 else None,
           'completion_policy': 'Length stops are intentional performance probes; no quality score is inferred.',
           'request_checks': reference, 'runtime_checks': runtime_check, 'runs': runs, 'sides': sides,
           'decode_delta_percent': 100 * (ratio - 1),
           'qualification_rule': {'registered_before_launch': True, 'maximum_decode_regression_percent': 5,
                                  'all_api_checks_pass': True, 'matched_requests': True, 'passed': ratio >= .95}}
    args.out.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'sides': sides, 'decode_delta_percent': out['decode_delta_percent'],
                      'qualification_rule': out['qualification_rule']}, indent=2))


if __name__ == '__main__':
    main()
