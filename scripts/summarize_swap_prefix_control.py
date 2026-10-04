"""Compare resident vision, swap v3 and swap v4 on the exact original benchmark requests."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.summarize_native_ab import check_cells
from scripts.summarize_swap_ab import check_runtimes
from scripts.summarize_vision_residency import cell, side_summary

IMAGES = {
    'resident': 'sha256:a1649d9812c7944dbbf880a33e272886a5b059bae22e65e713404a50aed46644',
    'v3': 'sha256:3e3faafd24d367aa999b6b942b6eb7199b653b0df628739f8dc1fbe178c9b2e3',
    'v4': 'sha256:24386fa3fb0e4d7ff2680174d5a126090293920c4556f1cf289a6af9d24bdefe',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--cells', type=Path, nargs=6, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    original = json.loads(args.reference.read_text())
    rows = []
    for path in args.cells:
        match = re.match(r'swap-prefix-control-\d+-(resident|v3|v4)-1-', path.name)
        if not match:
            raise ValueError('Unexpected control-cell name: ' + path.name)
        build = match[1]
        perf, run = cell(path)
        for key in ['sampling', 'tune', 'decode_tokens', 'paired_id']:
            if perf[key] != original[key]:
                raise ValueError('Original benchmark protocol differs: ' + key)
        check_cells(original, perf)
        identity = perf['runtime']['identity']
        if identity['image_id'] != IMAGES[build]:
            raise ValueError('Unexpected measured image for ' + build)
        run.update(build=build, image_id=identity['image_id'],
                   native_sha256=identity['artifacts']['native_sha256'],
                   completion_sha256=[hashlib.sha256(json.dumps(
                       {k: r[k] for k in ['content', 'reasoning', 'tool_deltas']},
                       sort_keys=True).encode()).hexdigest() for r in perf['decode']])
        rows.append((perf, run))
    order = [run['build'] for _, run in rows]
    if order != ['resident', 'v3', 'v4', 'v4', 'v3', 'resident']:
        raise ValueError('Expected the counterbalanced resident/v3/v4/v4/v3/resident order')
    groups = {build: [r for _, r in rows if r['build'] == build] for build in IMAGES}
    sides = {build: side_summary(runs) for build, runs in groups.items()}
    controls = sides['resident']['per_launch_decode_median_tok_s']
    comparisons = {}
    for build in ['v3', 'v4']:
        selected = [(p, r) for p, r in rows if r['build'] in ['resident', build]]
        runtime = check_runtimes([p for p, _ in selected], [r for _, r in selected])
        rates = sides[build]['per_launch_decode_median_tok_s']
        gain = 100 * (sides[build]['median_of_launch_medians_tok_s'] /
                      sides['resident']['median_of_launch_medians_tok_s'] - 1)
        overlap = max(min(controls), min(rates)) <= min(max(controls), max(rates))
        comparisons[build] = {'decode_gain_percent': gain, 'per_launch_ranges_overlap': overlap,
                              'meets_original_decode_gate': gain >= 5 and not overlap, 'runtime': runtime}
    result = {
        'scope': 'Build control on the original swap-ab-v1 requests. Two fresh launches per build; '
                 'resident, v3, v4, v4, v3, resident. Image latency uses the separately completed decks. '
                 'This does not make a uniform speed claim across prompts.',
        'reference': {'source': args.reference.name,
                      'sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest()},
        'protocol': {k: original[k] for k in ['sampling', 'tune', 'decode_tokens', 'paired_id']},
        'all_original_request_hashes_match': True,
        'order': order, 'runs': [r for _, r in rows], 'sides': sides, 'comparisons': comparisons,
    }
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    for build, summary in sides.items():
        print(build, json.dumps(summary))
    for build, comparison in comparisons.items():
        print(build, json.dumps({k: v for k, v in comparison.items() if k != 'runtime'}))


if __name__ == '__main__':
    main()
