"""Fetch pinned official Huihui v2 patch assets for compatibility inspection."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

assert socket.gethostname() == 'Ulmus'
root = Path.home() / 'Documents/MachineLearning/Qwen38-Flash-Next-Ulmus/stack'
dest = root / 'models/huihui-v2-patch'
dest.mkdir(exist_ok=True)
repo = 'huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF'
rev = '6e298f56319a5735f88ae952dd27222369f2f44a'
info = json.load(urllib.request.urlopen(
    f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true',timeout=60))
assert info['sha'] == rev
rows=[]
for s in info['siblings']:
    name=s['rfilename']
    if not name.startswith('patch-unsloth/'): continue
    path=dest / Path(name).name
    url=f'https://huggingface.co/{repo}/resolve/{rev}/{name}'
    if not path.exists() or path.stat().st_size != s['size']:
        subprocess.run(['curl','-fsSL','--retry','3','--connect-timeout','20','--max-time','900',
                        '--continue-at','-','--output',str(path),url],check=True)
    assert path.stat().st_size == s['size']
    sha=hashlib.sha256()
    git_sha=hashlib.sha1(f'blob {s["size"]}\0'.encode())
    with path.open('rb') as f:
        while chunk:=f.read(8<<20):
            sha.update(chunk); git_sha.update(chunk)
    if 'lfs' in s: assert sha.hexdigest()==s['lfs']['sha256']
    else: assert git_sha.hexdigest()==s['blobId']
    rows.append(dict(file=path.name,size=s['size'],sha256=sha.hexdigest(),repository_file=name))
    print('VERIFIED',path.name,s['size'],flush=True)
(dest/'manifest.json').write_text(json.dumps(dict(repository=repo,revision=rev,files=rows),indent=2)+'\n')
