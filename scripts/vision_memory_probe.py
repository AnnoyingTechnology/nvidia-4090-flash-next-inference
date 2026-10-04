"""VRAM and latency breakdown of the resident GPU vision encoder, on an otherwise idle GPU.

Measures, one fresh container each: a bare CUDA primary context, then `strata-vision` with the
owner profile's arguments (start to READY, resident VRAM, per-image encode time and peak VRAM,
exit). The host samples total GPU memory with nvidia-smi, so the GPU must be idle at start.
The inner mode runs inside the engine image and reports phase events as JSON lines.
"""
import argparse
import ctypes
import os
import datetime
import json
from pathlib import Path
import struct
import subprocess
import sys
import threading
import time

IMAGE = 'ulmus/strata:99f3dbd-ownerapi'
VISION = ['/opt/vision-build/bin/strata-vision',
          '--mmproj', '/work/models/gsq-iq3_s/mmproj-Qwen3.8-Flash-Next-BF16.gguf',
          '--model', '/work/models/gsq-iq3_s/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf',
          '--gpu', '--max-tokens', '4096', '--threads', '12']
IMAGES = ['fixtures/vision15/nginx-error.png', 'fixtures/vision15/invoice.png',
          'fixtures/vision15/photo-astronaut.png']


def emit(**event):
    print(json.dumps(event), flush=True)


def wait_host():
    if sys.stdin.readline().strip() != 'NEXT':
        raise SystemExit('host stopped the probe')


def write_gray_bmp(path, side):
    row = side * 3
    data = bytes([128]) * (row * side)
    header = struct.pack('<2sIHHI', b'BM', 54 + len(data), 0, 0, 54)
    info = struct.pack('<IiiHHIIiiII', 40, side, side, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    Path(path).write_bytes(header + info + data)


def inner_ctx():
    cuda = ctypes.CDLL('libcuda.so.1')
    dev, ctx = ctypes.c_int(), ctypes.c_void_p()
    t0 = time.monotonic()
    assert cuda.cuInit(0) == 0
    assert cuda.cuDeviceGet(ctypes.byref(dev), 0) == 0
    assert cuda.cuDevicePrimaryCtxRetain(ctypes.byref(ctx), dev) == 0
    assert cuda.cuCtxSetCurrent(ctx) == 0
    emit(phase='ctx_ready', ms=1000 * (time.monotonic() - t0))
    wait_host()


def command(proc, line):
    t = time.monotonic()
    proc.stdin.write(line + '\n')
    proc.stdin.flush()
    return proc.stdout.readline().strip(), 1000 * (time.monotonic() - t)


def inner_reload(repeats):
    """UNLOAD/LOAD cycles of the patched encoder: what an in-process release frees and what a reload costs."""
    big = '/tmp/gray-2048.bmp'
    write_gray_bmp(big, 2048)
    shot = '/work/' + IMAGES[0]
    proc = subprocess.Popen(VISION, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    emit(phase='ready', line=proc.stdout.readline().strip())
    wait_host()
    for rep in range(repeats):
        for step in ['UNLOAD', 'LOAD', f'ENC {shot} /tmp/out.sve', f'ENC {shot} /tmp/out.sve',
                     f'ENC {big} /tmp/out.sve', f'ENC {big} /tmp/out.sve']:
            reply, ms = command(proc, step)
            emit(phase='step', step=step.split()[0] + ('' if step[:3] != 'ENC' else ' ' + Path(step.split()[1]).name),
                 repeat=rep, reply=reply, wall_ms=ms)
            wait_host()
    command(proc, 'QUIT')
    proc.wait(timeout=30)
    emit(phase='exited', code=proc.returncode)


def inner_vision(repeats):
    big = '/tmp/gray-2048.bmp'
    write_gray_bmp(big, 2048)
    images = [big] + ['/work/' + p for p in IMAGES]
    t0 = time.monotonic()
    proc = subprocess.Popen(VISION, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    line = proc.stdout.readline().strip()
    emit(phase='ready', line=line, ms=1000 * (time.monotonic() - t0))
    wait_host()
    for rep in range(repeats):
        for path in images:
            emit(phase='encode_start', image=Path(path).name, repeat=rep)
            t1 = time.monotonic()
            proc.stdin.write(f'ENC {path} /tmp/out.sve\n')
            proc.stdin.flush()
            reply = proc.stdout.readline().strip()
            emit(phase='encode_done', image=Path(path).name, repeat=rep, reply=reply,
                 wall_ms=1000 * (time.monotonic() - t1))
    wait_host()
    t2 = time.monotonic()
    proc.stdin.write('QUIT\n')
    proc.stdin.flush()
    proc.wait(timeout=30)
    emit(phase='exited', ms=1000 * (time.monotonic() - t2), code=proc.returncode)


class Sampler:
    """Total GPU memory used, sampled every 20 ms by one nvidia-smi process."""

    def __init__(self):
        self.samples = []
        self.proc = subprocess.Popen(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits',
                                      '-lms', '20'], stdout=subprocess.PIPE, text=True)
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        for line in self.proc.stdout:
            if line.strip():
                self.samples.append((time.monotonic(), int(line.strip())))

    def now(self):
        time.sleep(0.3)
        return self.samples[-1][1]

    def peak(self, since):
        return max((m for t, m in self.samples if t >= since), default=None)

    def close(self):
        self.proc.terminate()


def run_container(mode, root, sampler, repeats, image):
    cmd = ['docker', 'run', '--rm', '-i', '--gpus', 'all', '--user', f'{os.getuid()}:{os.getgid()}', '--ulimit', 'memlock=-1',
           '--mount', f'type=bind,src={root},dst=/work', '--entrypoint', 'python3', image,
           '/work/scripts/vision_memory_probe.py', '--inner', mode, '--repeats', str(repeats)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    events, mark = [], time.monotonic()
    for line in proc.stdout:
        event = json.loads(line)
        if event['phase'] in ('ctx_ready', 'ready', 'step'):
            event['vram_mib'] = sampler.now()
            proc.stdin.write('NEXT\n')
            proc.stdin.flush()
        elif event['phase'] == 'encode_start':
            mark = time.monotonic()
        elif event['phase'] == 'encode_done':
            event['peak_vram_mib'] = sampler.peak(mark)
            event['vram_after_mib'] = sampler.now()
            if event['image'] == Path(IMAGES[-1]).name and event['repeat'] == repeats - 1:
                proc.stdin.write('NEXT\n')
                proc.stdin.flush()
        events.append(event)
    proc.wait(timeout=60)
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inner', choices=['ctx', 'vision', 'reload'])
    ap.add_argument('--image', default=IMAGE)
    ap.add_argument('--modes', default='ctx,vision')
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    if args.inner == 'ctx':
        return inner_ctx()
    if args.inner == 'vision':
        return inner_vision(args.repeats)
    if args.inner == 'reload':
        return inner_reload(args.repeats)
    if args.out is None or args.out.exists():
        raise SystemExit('Give a fresh --out path')
    apps = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'],
                          capture_output=True, text=True, check=True).stdout.strip()
    if apps:
        raise SystemExit('A GPU workload is active; the probe needs an idle GPU')
    root = Path(__file__).resolve().parents[1]
    sampler = Sampler()
    try:
        report = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'image': args.image,
                  'image_id': subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', args.image],
                                             capture_output=True, text=True, check=True).stdout.strip(),
                  'vision_args': VISION, 'idle_vram_mib': sampler.now()}
        for mode in args.modes.split(','):
            report[mode] = run_container(mode, root, sampler, args.repeats, args.image)
            report[f'idle_after_{mode}_mib'] = sampler.now()
    finally:
        sampler.close()
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
