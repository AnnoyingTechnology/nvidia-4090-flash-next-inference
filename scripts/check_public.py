"""Check the tracked public surface before committing or publishing."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
errors=[]
for name in filter(None,files):
    path=ROOT/name
    if name.startswith('results/') and not name.startswith('results/public/'):
        errors.append('Private result tracked: '+name)
    if name.startswith(('models/','packs/','mtp/','api-wheels/','eval/')) or path.name=='.env':
        errors.append('Local-only payload tracked: '+name)
    if path.stat().st_size>10<<20:
        errors.append('Unexpected large artifact: '+name)
    if path.suffix in ['.png','.jpg','.jpeg']:
        continue
    content=path.read_text()
    if re.search(r'/(?:home|Users)/[a-zA-Z0-9_.-]+/|192\.168\.1\.50|gh[oaprs]_[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9]{20,}',content):
        errors.append('Private host path/address or credential-like value: '+name)
    if path.suffix=='.md':
        for target in re.findall(r'\]\(([^\s)]+)\)',content):
            if target.startswith(('http:','https:','#','mailto:')):
                continue
            resolved=(path.parent/target.split('#')[0]).resolve()
            if not resolved.exists():
                errors.append(f'Broken link: {name}: {target}')
            elif str(resolved.relative_to(ROOT)) not in files:
                errors.append(f'Link targets an unpublished file: {name}: {target}')
manifest=ROOT/'results/public/export-manifest.json'
if manifest.exists():
    for name, entry in json.loads(manifest.read_text())['sources'].items():
        actual=hashlib.sha256((manifest.parent/name).read_bytes()).hexdigest()
        if actual!=entry['public_export_sha256']:
            errors.append('Public export checksum mismatch: '+name)
if errors:
    raise SystemExit('\n'.join(errors))
print('Public surface, links and export checksums verified:',len(files)-1,'files')
