"""Compare batched and verify-window reads of short prompt increments across launches."""
import argparse
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_provenance import fingerprint


def short_read(report):
    command = report['runtime']['identity']['artifacts']['native_command']
    return int(command[command.index('--short-read') + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    reports = [json.loads(path.read_text()) for path in args.runs]
    hashes = [[t['input_sha256'] for t in r['turns']] for r in reports]
    if any(h != hashes[0] for h in hashes) or any(len(r['turns']) != len(r['order']) + 1 for r in reports):
        raise ValueError('Runs are incomplete or their requests differ')
    if any(t['reused_tokens'] == 0 for r in reports for t in r['turns'][1:]):
        raise ValueError('A chained turn did not resume from its checkpoint')
    settings = {}
    for path, report in zip(args.runs, reports):
        command = [x for x in report['runtime']['identity']['artifacts']['native_command']]
        index = command.index('--short-read')
        del command[index:index + 2]
        settings.setdefault(short_read(report), []).append({'source': path.name,
            'runtime_fingerprint': fingerprint(report['runtime']['identity']),
            'common_command': command, 'base_read_ms': report['turns'][0]['prompt_ms'],
            'turns': [{k: t[k] for k in ['lines', 'reused_tokens', 'read_tokens', 'prompt_ms', 'ttft_s']}
                      for t in report['turns'][1:]]})
    if len(settings) != 2 or len({json.dumps(r['common_command']) for runs in settings.values() for r in runs}) != 1:
        raise ValueError('Expected two --short-read settings with otherwise identical engine arguments')
    batched, windows = sorted(settings)
    curves = {}
    for value, runs in settings.items():
        rows = {}
        for run in runs:
            for turn in run['turns']:
                rows.setdefault(turn['lines'], []).append(turn)
        curves[value] = {lines: {'read_tokens_median': statistics.median(t['read_tokens'] for t in turns),
                                 'prompt_ms_median': statistics.median(t['prompt_ms'] for t in turns),
                                 'per_launch_prompt_ms_median': [statistics.median(
                                     t['prompt_ms'] for t in run['turns'] if t['lines'] == lines) for run in runs]}
                         for lines, turns in sorted(rows.items())}
    # Pre-registered: windows must beat batched in every launch, over a contiguous range from the smallest size.
    faster = []
    for lines in curves[batched]:
        if max(curves[windows][lines]['per_launch_prompt_ms_median']) >= \
                min(curves[batched][lines]['per_launch_prompt_ms_median']):
            break
        faster.append(lines)
    result = {'scope': 'Agent-like chained turns on a ~64K-token context; each turn reuses the previous '
            'checkpoint and reads one short assistant reply plus a tool message. Prompt time includes '
            'lending and refilling expert-cache slots on the batched path.',
        'batched_setting': batched, 'windows_setting': windows, 'runs': settings, 'curves': curves,
        'windows_faster_contiguous_line_counts': faster,
        'largest_read_tokens_with_windows_faster': max((curves[batched][l]['read_tokens_median'] for l in faster),
                                                       default=None)}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    for lines in curves[batched]:
        b, w = curves[batched][lines], curves[windows][lines]
        print(f"{lines:3d} lines {b['read_tokens_median']:5.0f} tok: batched {b['prompt_ms_median']:6.0f} ms "
              f"{b['per_launch_prompt_ms_median']}, windows {w['prompt_ms_median']:6.0f} ms {w['per_launch_prompt_ms_median']}")
    print('windows faster in every launch, contiguous from the smallest size:', faster)


if __name__ == '__main__':
    main()
