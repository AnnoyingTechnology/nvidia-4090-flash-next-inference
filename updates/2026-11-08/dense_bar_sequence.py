"""Run the remaining dense-bar coverage serially after full target qualification."""
import json
import os
from pathlib import Path
import subprocess
import time

root=Path.home()/'Documents/MachineLearning/Qwen38-Flash-Next-Ulmus/stack'
os.chdir(root)
while not Path('results/huihui-weight20261108-complete.json').exists():
    p=subprocess.run(['pgrep','-f','^python3 updates/2026-11-08/qualify_huihui_weights.py$'],capture_output=True)
    if p.returncode:raise SystemExit('Weight qualification stopped; inspect before continuing.')
    time.sleep(10)
container='ulmus-huihui-weight-eval'
os.environ['ULMUS_CONTAINER']=container
os.environ['ULMUS_EVAL_CONTAINER']=container
for label,profile in [('baseline','flash-iq3s-256k-vision-tune-owner20261108'),
                      ('candidate','flash-iq3s-256k-vision-tune-huihuiv220261108')]:
    d=json.loads(subprocess.check_output(['docker','inspect',container],text=True))[0]
    assert d['Config']['Image']=='ulmus/strata:146df3c-owner20261108'
    assert '--config' in d['Config']['Cmd'] and '/work/profiles/flash-iq3s-' in d['Config']['Cmd'][d['Config']['Cmd'].index('--config')+1]
    subprocess.run(['docker','stop','--timeout','30',container],check=True)
    with open(f'results/huihui-weight20261108-dense-bar-{label}.log','a') as log:
        subprocess.run(['bash','run.sh',profile,'ulmus/strata:146df3c-owner20261108'],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['python3','wait_ready.py'],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['python3','updates/2026-11-08/dense_bar.py','--label',label],stdout=log,stderr=subprocess.STDOUT,check=True)
    print('COMPLETE',label,flush=True)
Path('results/huihui-weight20261108-dense-bar-complete.json').write_text(json.dumps({'complete':True}))
