"""Check the adapted fork's numeric components with no full-size target oracle."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'ulmus/strata:eddoursul-3a199-native'
BUILD = '/opt/strata-eddoursul-build/'
LIBRARY = Path(os.environ.get('ULMUS_LIBRARY', ROOT/'models'))
tests = [
    ('ordered-copies', 'native_copy_parity', []),
    ('grouped-gemm-fallback', 'native_grouped_gemm_parity', []),
    ('sampler', 'sampler_parity', ['--selftest']),
    ('ple-reader', 'ple_reader_test', ['--selftest', '--dir', '/tmp']),
    ('qsa', 'qsa_parity', ['--selftest']),
    ('gdn', 'gdn_parity', ['--selftest']),
    ('router-top10', 'router_top10_parity', ['--selftest']),
    ('iq3-native-experts', 'native_expert_parity', [
        '/work/models/gsq-iq3_s/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf']),
    ('q4-native-experts', 'native_expert_parity', [
        '/models/unsloth/Qwen3.8-Flash-Next-GGUF/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf']),
]
report = {'scope': 'Component numeric tests on the same quantized target formats; not full-size quality parity.',
          'image_id': subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'],text=True).strip(),
          'source_pin':'3a19944130d93d204a845234bbb61c1f1fb3b57d',
          'compat_patch_sha256':hashlib.sha256((ROOT/'patches/eddoursul-cuda124-compat.patch').read_bytes()).hexdigest(),
          'tests':[]}
report['native_sha256'] = subprocess.check_output(['docker','run','--rm','--entrypoint','sha256sum',IMAGE,
                                                   BUILD+'strata'],text=True).split()[0]
out = ROOT/'results/eddoursul-native-parity.json'
for label, executable, args in tests:
    name = 'ulmus-native-check-'+uuid.uuid4().hex[:10]
    command = ['docker','run','--rm','--gpus','all','--name',name,
               '--user',f'{os.getuid()}:{os.getgid()}',
               '--mount',f'type=bind,src={ROOT},dst=/work,readonly',
               '--mount',f'type=bind,src={LIBRARY},dst=/models,readonly',
               '--entrypoint',BUILD+executable,IMAGE,*args]
    start=time.monotonic()
    try:
        run=subprocess.run(command,text=True,capture_output=True,timeout=180)
        row={'name':label,'passed':run.returncode==0,'exit_code':run.returncode,
             'elapsed_s':time.monotonic()-start,'stdout':run.stdout,'stderr':run.stderr}
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','rm','--force',name],capture_output=True,timeout=15)
        row={'name':label,'passed':False,'error':'Component check exceeded 180 seconds'}
    report['tests'].append(row)
    report['summary']={'passed':sum(t['passed'] for t in report['tests']),'total':len(tests)}
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(label,row['passed'],flush=True)
    if not row['passed']:raise RuntimeError('Native component check failed: '+label)
