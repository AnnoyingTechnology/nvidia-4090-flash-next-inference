"""Observe loaded-model memory and CPU occupancy without creating benchmark traffic."""
import argparse
import datetime
import json
from pathlib import Path
import statistics
import subprocess
import time


def cpu_ticks():
    result = {}
    for line in Path('/proc/stat').read_text().splitlines():
        key, *values = line.split()
        if key.startswith('cpu'):
            # guest ticks are already included in user/nice; do not double count them.
            numbers = list(map(int, values[:8]))
            result[key] = (sum(numbers), numbers[3], numbers[4])
    return result


def memory(path):
    result = {}
    for line in path.read_text().splitlines():
        key, value, *unit = line.replace(':', '').split()
        if value.isdigit():
            result[key] = int(value) * (1024 if unit == ['kB'] else 1)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--container', default='ulmus-inference-test')
    ap.add_argument('--seconds', type=int, default=30)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.seconds < 1:
        ap.error('--seconds must be positive')
    pid = int(subprocess.check_output(['docker', 'inspect', '--format', '{{.State.Pid}}', args.container], text=True))
    if not pid:
        raise RuntimeError('Container is not running')
    cgroup = next(line.split(':', 2)[2] for line in Path(f'/proc/{pid}/cgroup').read_text().splitlines()
                  if line.startswith('0::'))
    group = Path('/sys/fs/cgroup')/cgroup.lstrip('/')
    topology = {}
    for item in Path('/sys/devices/system/cpu').glob('cpu[0-9]*'):
        if (item/'topology/core_id').exists():
            topology[item.name] = {'core': int((item/'topology/core_id').read_text()),
                                  'package': int((item/'topology/physical_package_id').read_text())}
    report = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Active owned container; system-wide per-logical-CPU occupancy includes other processes. '
                 'cgroup CPU usage excludes GPU time. Memory values overlap and must not be added.',
        'container': args.container, 'topology': topology, 'samples': []}
    previous = cpu_ticks()
    previous_usage = memory(group/'cpu.stat')['usage_usec']
    last_time = time.monotonic()
    for _ in range(args.seconds):
        time.sleep(1)
        now = time.monotonic()
        ticks = cpu_ticks()
        per_cpu = {}
        waits = {}
        for key, (total, idle, wait) in ticks.items():
            old_total, old_idle, old_wait = previous[key]
            delta = total-old_total
            per_cpu[key] = 100*(delta-(idle-old_idle)-(wait-old_wait))/delta if delta else 0
            waits[key] = 100*(wait-old_wait)/delta if delta else 0
        usage = memory(group/'cpu.stat')['usage_usec']
        host = memory(Path('/proc/meminfo'))
        gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu,power.draw',
                                       '--format=csv,noheader,nounits'], text=True).strip().split(',')
        report['samples'].append({'container_cpu_core_equivalents': (usage-previous_usage)/1e6/(now-last_time),
            'cpu_busy_percent': per_cpu, 'cpu_iowait_percent': waits,
            'host_total_bytes': host['MemTotal'], 'host_available_bytes': host['MemAvailable'],
            'host_used_excluding_available_bytes': host['MemTotal']-host['MemAvailable'],
            'container_memory_bytes': int((group/'memory.current').read_text()),
            'container_memory_stat': memory(group/'memory.stat'),
            'gpu_used_mib': float(gpu[0]), 'gpu_total_mib': float(gpu[1]),
            'gpu_utilization_percent': float(gpu[2]), 'gpu_board_power_w': float(gpu[3])})
        previous, previous_usage, last_time = ticks, usage, now
    rows = report['samples']
    names = ['container_cpu_core_equivalents', 'host_total_bytes', 'host_available_bytes',
             'host_used_excluding_available_bytes', 'container_memory_bytes',
             'gpu_used_mib', 'gpu_total_mib', 'gpu_utilization_percent', 'gpu_board_power_w']
    report['summary'] = {key: {'median': statistics.median(r[key] for r in rows),
                             'min': min(r[key] for r in rows), 'max': max(r[key] for r in rows)} for key in names}
    report['per_cpu_median_busy_percent'] = {key: statistics.median(r['cpu_busy_percent'][key] for r in rows)
                                           for key in previous}
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'summary': report['summary'], 'per_cpu': report['per_cpu_median_busy_percent']}, indent=2))


if __name__ == '__main__':
    main()
