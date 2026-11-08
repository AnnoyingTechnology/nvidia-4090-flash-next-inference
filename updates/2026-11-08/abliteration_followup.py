"""Run remaining paired action-boundary checks after the serial qualification."""
import json
import os
from pathlib import Path
import subprocess
import time

root=Path.home()/'Documents/MachineLearning/Qwen38-Flash-Next-Ulmus/stack'
os.chdir(root)
os.environ['ULMUS_EVAL_CONTAINER']='ulmus-huihui-eval'
marker=Path('results/huihui20261108-sequence-complete.json')
while not marker.exists():
    p=subprocess.run(['pgrep','-f','^python3 updates/2026-11-08/abliteration_sequence.py$'],capture_output=True)
    if p.returncode:raise SystemExit('Main sequence stopped; inspect logs.')
    time.sleep(10)
commands=[('repeat', ['python3','updates/2026-11-08/repeat_abliteration_disagreements.py'])]
for arm in ['off','on']:
    for effort in ['none','low']:
        if arm=='off' and effort=='low':continue  # Existing completed identical-runtime baseline.
        name=f'ops-{arm}-{effort}'
        commands.append((name,['python3','practical_eval.py','--out',f'results/huihui20261108-{name}.json',
            '--label',name,'--effort',effort,'--tokens','32768','--projection',arm]))
    name=f'agent-{arm}'
    commands.append((name,['python3','agent_screen.py','--out',f'results/huihui20261108-{name}.json',
                          '--label',name,'--projection',arm]))
commands.append(('histories',['python3','conversations.py','--out','results/huihui20261108-histories.json',
                             '--fixtures','fixtures']))
for name,command in commands:
    with open(f'results/huihui20261108-followup-{name}.log','a') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('COMPLETE',name,flush=True)
Path('results/huihui20261108-followup-complete.json').write_text(json.dumps({'complete':True}))
