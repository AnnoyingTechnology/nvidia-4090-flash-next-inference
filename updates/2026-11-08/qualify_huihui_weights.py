"""Fresh-start ABBA plus complete matched gates for the derived Huihui v2 target."""
import json
import os
from pathlib import Path
import subprocess
import time

root=Path.home()/'Documents/MachineLearning/Qwen38-Flash-Next-Ulmus/stack'
os.chdir(root)
container='ulmus-huihui-weight-eval'
image='ulmus/strata:146df3c-owner20261108'
base='flash-iq3s-256k-vision-tune-owner20261108'
candidate='flash-iq3s-256k-vision-tune-huihuiv220261108'
os.environ['ULMUS_EVAL_CONTAINER']=container
os.environ['ULMUS_CONTAINER']=container

while not Path('results/huihui20261108-followup-complete.json').exists():
    p=subprocess.run(['pgrep','-f','^python3 updates/2026-11-08/abliteration_followup.py$'],capture_output=True)
    if p.returncode:raise SystemExit('Vector follow-up stopped; inspect before switching the owned engine.')
    time.sleep(10)
assert Path('results/huihui20261108-weight-candidate-integrity.json').exists()
assert Path(f'profiles/{candidate}.json').exists()

def stop_owned(name):
    p=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
    if p.returncode:return
    d=json.loads(p.stdout)[0]
    assert d['Config']['Image']==image
    cmd=d['Config']['Cmd']
    assert '--config' in cmd and cmd[cmd.index('--config')+1].startswith('/work/profiles/flash-iq3s-256k-vision-tune-')
    subprocess.run(['docker','stop','--timeout','30',name],check=True)

def start(profile,label):
    stop_owned(container)
    with open(f'results/huihui-weight20261108-{label}-launch.log','a') as log:
        subprocess.run(['bash','run.sh',profile,image],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['python3','wait_ready.py'],stdout=log,stderr=subprocess.STDOUT,check=True)
    print('READY',label,profile,flush=True)

def call(label,command):
    with open(f'results/huihui-weight20261108-{label}.log','a') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('COMPLETE',label,flush=True)

stop_owned('ulmus-huihui-eval')
for index,profile in enumerate([base,candidate,candidate,base]):
    label=f'abba-{index}-'+('baseline' if profile==base else 'candidate')
    start(profile,label)
    call(label,['python3','bench.py','--out',f'results/huihui-weight20261108-{label}.json',
        '--repeats','2','--decode-tokens','512','--prefill-k','32','--fixtures','fixtures',
        '--paired-id','huihui-weight-abba20261108','--capture-runtime'])
start(candidate,'quality')
for stage in ['screen','features','practical']:
    call('paired-'+stage,['python3','updates/2026-11-08/abliteration_gate.py','--stage',stage,
        '--tag','huihui-weight20261108','--arms','off','--weight-candidate'])
for effort in ['none','low']:
    name=f'ops-{effort}'
    call(name,['python3','practical_eval.py','--out',f'results/huihui-weight20261108-{name}.json',
        '--label',name,'--effort',effort,'--tokens','32768','--projection','off'])
for script,options,name in [
    ('owner_api_check.py',['--profile',candidate,'--vision'],'api'),
    ('quality.py',['--fixtures','fixtures','--long-k','32','--vision','fixtures/vision.png'],'quality'),
    ('agent_screen.py',['--label','huihui-weight20261108','--projection','off'],'agent'),
    ('conversations.py',['--fixtures','fixtures'],'histories')]:
    call(name,['python3',script,'--out',f'results/huihui-weight20261108-{name}.json',*options])
Path('results/huihui-weight20261108-complete.json').write_text(json.dumps({'complete':True}))
print('COMPLETE all weight-candidate gates',flush=True)
