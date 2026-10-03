"""Bind local evaluations to the owned live container, target artifacts and template.

Large artifacts use observed inode/size/mtime identities, not invented content hashes.
The pinned download/build recipes provide content-hash evidence separately. Imports
require the exact runtime fingerprint; legacy reports without one cannot be reused.
"""
import hashlib
import json
import subprocess
import urllib.request

CONTAINER = 'ulmus-inference-test'

PROBE = r'''
import hashlib,json,os,re,sys
from pathlib import Path
cfg_path=Path(sys.argv[1]); cfg=json.loads(cfg_path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def identity(path, hash_small=False):
    path=Path(path); s=path.stat()
    row={'path':str(path),'size':s.st_size,'mtime_ns':s.st_mtime_ns,
         'device':s.st_dev,'inode':s.st_ino}
    if hash_small: row['sha256']=digest(path)
    return row
def files(path):
    path=Path(path)
    if path.is_file(): return [identity(path,path.stat().st_size<16*1024*1024)]
    return [identity(p,p.stat().st_size<16*1024*1024) for p in sorted(path.rglob('*')) if p.is_file()]
def split_shards(path):
    path=Path(path)
    match=re.search(r'-\d{5}-of-\d{5}\.gguf$',path.name)
    return sorted(path.parent.glob(path.name[:match.start()]+'-*-of-*.gguf')) if match else [path]
args=cfg['args']; native=Path(args[args.index('--native')+1])
shards=split_shards(native)
processes=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try:
        if os.readlink(p/'exe') == cfg['exe']:
            processes.append((p/'cmdline').read_bytes().decode().split('\0')[:-1])
    except (FileNotFoundError,PermissionError,ProcessLookupError): pass
if len(processes)!=1: raise RuntimeError('Expected one matching native engine process')
result={'config_sha256':digest(cfg_path),'engine_config':cfg,
        'native_sha256':digest(Path(cfg['exe'])),'native_command':processes[0],
        'api_sources':{name:digest(Path('/opt/strata/serve')/name) for name in
                       ['server.py','frontend.py','structured.py']},
        'tokenizer':files(cfg['tokenizer']), 'target_shards':[identity(p) for p in shards]}
for option,key in [('--pack','pack'),('--mtp','mtp'),('--expert-profile','expert_profile')]:
    if option in args: result[key]=files(args[args.index(option)+1])
if '--native-head-gguf' in args:
    result['head_override_shards']=[identity(p) for p in split_shards(args[args.index('--native-head-gguf')+1])]
if '--embd-gguf' in args:
    result['embedding_override']=identity(args[args.index('--embd-gguf')+1])
vision=cfg.get('vision')
if vision:
    result['vision_artifacts']={'native_sha256':digest(Path(vision['exe'])),
                               'projector':identity(vision['mmproj'])}
shared=cfg_path.with_suffix('.shared-settings.json')
if shared.exists(): result['shared_defaults_sha256']=digest(shared)
print(json.dumps(result))
'''


def fingerprint(identity):
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inspect_container():
    return json.loads(subprocess.check_output(['docker', 'inspect', CONTAINER], text=True))[0]


def capture(url):
    container = inspect_container()
    if not container['State']['Running']:
        raise RuntimeError('Owned inference container is not running')
    command = container['Config']['Cmd']
    config = command[command.index('--config') + 1]
    probe = subprocess.run(['docker', 'exec', '--interactive', CONTAINER, 'python', '-', config],
                           input=PROBE, text=True, capture_output=True, check=True, timeout=60)
    with urllib.request.urlopen(url.rstrip('/') + '/props', timeout=10) as response:
        props = json.load(response)
    identity = {'image_id': container['Image'], 'api_command': command,
                'artifacts': json.loads(probe.stdout),
                'api_properties': {key: props.get(key) for key in ['default_generation_settings',
                    'total_slots', 'model_alias', 'model_path', 'build_info', 'modalities']},
                'chat_template_sha256': hashlib.sha256(props['chat_template'].encode()).hexdigest()}
    return {'fingerprint': fingerprint(identity), 'identity': identity,
            'container_id': container['Id'],
            'artifact_identity_policy': 'Small files content-hashed; large files identified by observed '
                'inode/device/size/mtime. This is a run identity, not fresh verification of published weight hashes.'}


def assert_container(runtime):
    current = inspect_container()
    if current['Id'] != runtime['container_id'] or not current['State']['Running']:
        raise RuntimeError('Inference container changed during evaluation')


def require_matching(report, runtime):
    old = report.get('runtime')
    if not old or old.get('fingerprint') != runtime['fingerprint']:
        raise RuntimeError('Runtime provenance differs or is missing; legacy responses cannot be imported/resumed')
