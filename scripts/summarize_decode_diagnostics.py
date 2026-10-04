"""Summarize existing instrumentation; overlapping counters are not additive CPU/GPU costs."""
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
PATTERN = re.compile(
    r'strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = '
    r'verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+) '
    r'\[plan ([\d.]+) actq ([\d.]+) jobs ([\d.]+) CPU ([\d.]+)\] \+ stage ([\d.]+)\) '
    r'\+ commit/emit ([\d.]+) \+ draft ([\d.]+); per layer-window: CPU experts ([\d.]+) '
    r'\(([\d.]+) entries\), VRAM hits ([\d.]+), PCIe ([\d.]+)')
KEYS = ['windows', 'average_T', 'tokens_per_window', 'window_ms', 'verify_ms', 'host_wait_gpu_ms',
        'host_layer_ms', 'plan_ms', 'activation_quant_ms', 'jobs_ms', 'cpu_expert_ms',
        'host_staging_ms', 'commit_emit_ms', 'draft_ms', 'cpu_experts_per_layer_window',
        'cpu_entries_per_layer_window', 'gpu_hit_entries_per_layer_window', 'pcie_experts_per_layer_window']


def main():
    report = {'interpretation': 'Diagnostic only. Host wait and CPU counters overlap GPU work; do not sum them with GPU stages. GPU stamps perturb timing. Fixed 512-token limits measure speed, not quality.',
              'runs': {}}
    for mode in ['aggregate', 'stamps']:
        base = RESULTS / f'decode-explore-20261004-{mode}'
        raw = json.loads(base.with_suffix('.json').read_text())
        log = Path(str(base) + '-engine.log').read_text()
        timings = list(PATTERN.finditer(log))
        stages = [line for line in log.splitlines() if line.startswith('strata decode GPU stages')]
        assert len(timings) == len(raw['cells']) == 6
        assert len(stages) == (6 if mode == 'stamps' else 0)
        assert not re.search(r'FAILED|CUDA error| - OVERFLOW', log)
        cells = []
        for index, (cell, match) in enumerate(zip(raw['cells'], timings)):
            assert cell['completion_tokens'] == 512 and cell['finish_reason'] == 'length'
            values = dict(zip(KEYS, map(float, match.groups())))
            values['other_ms'] = values['window_ms'] - values['verify_ms'] - values['commit_emit_ms'] - values['draft_ms']
            entry = {**cell, 'timing': values}
            if stages:
                line = stages[index].split('(ms/window):', 1)[1]
                groups = {}
                for block in line.split(' | ')[:2]:
                    name, contents = block.split(' layers:', 1)
                    groups[name.strip()] = {k.strip(): float(v) for k, v in re.findall(r'(.+?) ([0-9]+\.[0-9]+)(?= |$)', contents)}
                entry['gpu_stage_ms_per_window'] = groups
            cells.append(entry)
        report['runs'][mode] = {'cells': cells, 'input_sha256': hashlib.sha256(base.with_suffix('.json').read_bytes()).hexdigest(),
                                'engine_log_sha256': hashlib.sha256(log.encode()).hexdigest(),
                                'median_timing': {key: statistics.median(c['timing'][key] for c in cells) for key in cells[0]['timing']}}
    assert [c['input_sha256'] for c in report['runs']['aggregate']['cells']] == [c['input_sha256'] for c in report['runs']['stamps']['cells']]
    out = RESULTS / 'decode-diagnostics-20261004-summary.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    for mode, run in report['runs'].items():
        print(mode, json.dumps(run['median_timing']))


if __name__ == '__main__':
    main()
