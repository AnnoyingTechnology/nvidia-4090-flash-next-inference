"""Continue the owned qualification serially after the already-running screen."""
import json
import os
from pathlib import Path
import subprocess
import time

root = Path.home() / 'Documents/MachineLearning/Qwen38-Flash-Next-Ulmus/stack'
os.chdir(root)
os.environ['ULMUS_EVAL_CONTAINER'] = 'ulmus-huihui-eval'
screen = root / 'results/huihui20261108-paired-screen.json'
while True:
    if screen.exists() and json.loads(screen.read_text()).get('complete'): break
    active = subprocess.run(['pgrep', '-f', '^python3 updates/2026-11-08/abliteration_gate.py --stage screen$'],
                            capture_output=True, text=True)
    if active.returncode: raise SystemExit('Screen stopped before completion; inspect its report/log.')
    time.sleep(10)
for stage in ['performance', 'features', 'practical']:
    with open(f'results/huihui20261108-paired-{stage}.log', 'a') as log:
        subprocess.run(['python3', 'updates/2026-11-08/abliteration_gate.py', '--stage', stage],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    print('COMPLETE', stage, flush=True)
for script, options, name in [
    ('owner_api_check.py', ['--profile', 'flash-iq3s-256k-vision-tune-huihui20261108', '--vision'], 'api'),
    ('quality.py', ['--fixtures', 'fixtures', '--long-k', '32', '--vision', 'fixtures/vision.png'], 'quality')]:
    with open(f'results/huihui20261108-{name}.log', 'a') as log:
        subprocess.run(['python3', script, '--out', f'results/huihui20261108-{name}.json', *options],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    print('COMPLETE', name, flush=True)
Path('results/huihui20261108-sequence-complete.json').write_text(json.dumps({'complete':True}))
