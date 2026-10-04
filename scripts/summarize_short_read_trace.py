"""Decompose short chained prompt reads with the engine's STRATA_TRACE lines.

Joins one short_read_probe.py report with the engine-log slice of the same traced launch.
Per request: slot lending, batched read, refill, verify-window read, and the remainder of the
server-reported prompt time (checkpoint saves, scheduling and API overhead).
"""
import argparse
import json
from pathlib import Path
import re
import statistics

LENT = re.compile(r'strata trace: lent (\d+) slots for (\d+) tokens in ([\d.]+) ms')
READ = re.compile(r'strata trace: read (\d+) tokens \((batched|windows)\) in ([\d.]+) ms')
REFILLED = re.compile(r'strata trace: refilled (\d+) slots on \d+ stage\(s\) in ([\d.]+) ms')


def requests(log_text):
    out = []
    for line in log_text.splitlines():
        if line.startswith('strata trace: request '):
            out.append({'lent_slots': 0, 'lend_ms': 0.0, 'batched_tokens': 0, 'batched_ms': 0.0,
                        'refilled_slots': 0, 'refill_ms': 0.0, 'window_tokens': 0, 'window_ms': 0.0})
        elif out:
            r = out[-1]
            if m := LENT.search(line):
                r['lent_slots'] += int(m[1])
                r['lend_ms'] += float(m[3])
            elif m := READ.search(line):
                kind = 'batched' if m[2] == 'batched' else 'window'
                r[kind + '_tokens'] += int(m[1])
                r[kind + '_ms'] += float(m[3])
            elif m := REFILLED.search(line):
                r['refilled_slots'] += int(m[1])
                r['refill_ms'] += float(m[2])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', type=Path, required=True)
    ap.add_argument('--engine-log', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    report = json.loads(args.probe.read_text())
    traced = requests(args.engine_log.read_text(errors='replace'))
    turns = report['turns']
    if len(traced) < len(turns):
        raise ValueError(f'{len(traced)} traced requests for {len(turns)} probe turns')
    traced = traced[-len(turns):]
    rows = []
    for turn, tr in zip(turns, traced):
        # the last prompt token goes through the first decode window, outside the traced reads
        tr['untraced_tokens'] = turn['read_tokens'] - tr['batched_tokens'] - tr['window_tokens']
        accounted = tr['lend_ms'] + tr['batched_ms'] + tr['refill_ms'] + tr['window_ms']
        rows.append({**{k: turn[k] for k in ('step', 'lines', 'read_tokens', 'prompt_ms')}, **tr,
                     'other_ms': turn['prompt_ms'] - accounted})
    chained = [r for r in rows if r['step'] > 0 and r['batched_tokens'] > 0]
    by_lines = {}
    for r in chained:
        by_lines.setdefault(r['lines'], []).append(r)
    keys = ['read_tokens', 'batched_tokens', 'window_tokens', 'prompt_ms', 'lend_ms', 'batched_ms', 'refill_ms',
            'window_ms', 'other_ms', 'lent_slots', 'refilled_slots']
    summary = {lines: {k: statistics.median(r[k] for r in group) for k in keys} | {'n': len(group)}
               for lines, group in sorted(by_lines.items())}
    pooled = {k: statistics.median(r[k] for r in chained) for k in keys} | {'n': len(chained)}
    result = {'scope': 'One traced launch of the selected vision profile; chained agent-like turns at about 64K '
                       'context. Engine trace timings are wall-clock spans inside the engine; other_ms is the '
                       'server-reported prompt time not covered by them.',
              'probe': args.probe.name, 'engine_log': args.engine_log.name, 'runtime': report.get('runtime'),
              'batched_turns_by_tool_lines': summary, 'batched_turns_pooled_median': pooled, 'turns': rows}
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps({'by_lines': summary, 'pooled': pooled}, indent=2))


if __name__ == '__main__':
    main()
