"""Fail closed unless the official patch covers every intended GSQ dense tensor."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,'/opt/strata-next/tools')
import _paths
_paths.add_gguf_py()
import gguf

root=Path('/work')
dest=root/'models/huihui-v2-patch'
manifest=json.loads((dest/'manifest.json').read_text())
patch=dest/'Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf'
assert patch.stat().st_size==3561572544
p=gguf.GGUFReader(str(patch))
patched={t.name:t for t in p.tensors}
original=root/'models/gsq-iq3_s/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf'
src=gguf.GGUFReader(str(original))
rows=[]
missing=[]
for t in src.tensors:
    if not re.fullmatch(r'blk\.\d+\.(ssm_out|attn_output|ffn_down_shexp)\.weight',t.name):continue
    key=f'{t.name}_{t.tensor_type}'
    if key not in patched:
        missing.append(dict(name=t.name,type=int(t.tensor_type),patch_tensor=key))
        continue
    pt=patched[key]
    assert pt.tensor_type==t.tensor_type and list(pt.shape)==list(t.shape), f'Patch geometry mismatch: {key}'
    rows.append(dict(name=t.name,type=int(t.tensor_type),shape=[int(x) for x in t.shape],patch_tensor=key))
assert len(rows)+len(missing)==96
mode1=[r for r in rows if '.ffn_down_shexp.' not in r['name']]
mode1_missing=[r for r in missing if '.ffn_down_shexp.' not in r['name']]
report=dict(compatible=not missing,matched_tensors=len(rows),tensors=rows,missing=missing,
            mode1_compatible=not mode1_missing and len(mode1)==48,mode1_matched=len(mode1),
            manifest=manifest,note='Static coverage and geometry only; candidate remains unqualified.')
(root/'results/huihui20261108-patch-compatibility.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['tensors','manifest']}))
