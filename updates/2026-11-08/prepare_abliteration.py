"""Install the pinned Huihui-derived vector and a separate evaluation profile on Ulmus."""
import hashlib
import json
from pathlib import Path
import shutil
import socket
import urllib.request

assert socket.gethostname() == 'Ulmus'
root = Path.home() / 'Documents/MachineLearning/Qwen38-Flash-Next-Ulmus/stack'
revision = 'd4af3be5701549435e0770d625f79dd2def1358f'
repo = 'alesha-pro/Qwen3.8-Flash-Next-abliterated-GSQ-RCO-Strata-GGUF'
name = 'Huihui-Qwen3.8-Flash-Next-refusal-direction-r.gguf'
expected = '59f9ae8b4372107ae79044278a4406bdfe8f8861fe599aa5848515f0d072be38'
dest = root / 'models/huihui-vector'
dest.mkdir(exist_ok=True)
url = f'https://huggingface.co/{repo}/resolve/{revision}/{name}'
data = urllib.request.urlopen(url, timeout=60).read()
assert len(data) == 483520 and hashlib.sha256(data).hexdigest() == expected
assert data[:4] == b'GGUF'
target = dest / name
if target.exists():
    assert target.read_bytes() == data
else:
    target.write_bytes(data)
(dest / 'manifest.json').write_text(json.dumps(dict(repository=repo, revision=revision,
    file=name, size=len(data), sha256=expected, url=url,
    method='Runtime residual projection, derived from Huihui v1; not Huihui v2 weights.'), indent=2) + '\n')
base = 'flash-iq3s-256k-vision-tune-owner20261108'
candidate = 'flash-iq3s-256k-vision-tune-huihui20261108'
cfg = json.loads((root / f'profiles/{base}.json').read_text())
assert '--control-vector-scaled' not in cfg['args']
cfg['args'] += ['--control-vector-scaled', f'/work/models/huihui-vector/{name}:1.0',
                '--control-vector-layer-range', '4', '44', '--cvec-mode', 'project',
                '--cvec-dir', 'per-layer']
cfg['log'] = f'/work/results/{candidate}-engine.log'
(root / f'profiles/{candidate}.json').write_text(json.dumps(cfg, indent=2) + '\n')
shared = root / f'profiles/{base}.shared-settings.json'
assert shared.exists()
shutil.copy2(shared, root / f'profiles/{candidate}.shared-settings.json')
print(json.dumps(dict(profile=candidate, vector_sha256=expected, bytes=len(data))))
