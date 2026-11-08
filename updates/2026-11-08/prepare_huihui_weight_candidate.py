"""Reproduce Huihui v2 edits in GSQ's existing tensor formats using llama-quantize.

The published patch covers 45/96 dense tensors directly. The other 51 are
quantized from its published BF16 tensors, preserving routed expert weights and
the ngram table. This is a derived quantization, not an official Huihui release.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0,'/opt/strata-next/tools')
import _paths
_paths.add_gguf_py()
import gguf
import numpy as np

ap=argparse.ArgumentParser()
ap.add_argument('stage',choices=['prepare','supplement','verify','profile'])
a=ap.parse_args()
root=Path('/work')
assets=root/'models/huihui-v2-patch'
work=root/'models/huihui-v2-derived'
work.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('huihui_patch',assets/'patch-unsloth-Qwen3.8-Flash-Next-dec.py')
author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
key=(assets/'Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf.key').read_text().strip().encode()
patch=gguf.GGUFReader(str(assets/'Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf'))
pt={t.name:t for t in patch.tensors}
srcdir=root/'models/gsq-iq3_s'
first='Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf'
second='Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf'
src=gguf.GGUFReader(str(srcdir/first))
targets={t.name:t for t in src.tensors if re.fullmatch(r'blk\.\d+\.(ssm_out|attn_output|ffn_down_shexp)\.weight',t.name)}
assert len(targets)==96
missing={n:t for n,t in targets.items() if f'{n}_{t.tensor_type}' not in pt}
assert len(missing)==51
assert {int(t.tensor_type) for t in missing.values()}=={12,20}
arch=src.fields['general.architecture'].contents()
if isinstance(arch,bytes):arch=arch.decode()

def digest_array(t):return hashlib.sha256(memoryview(t.data).cast('B')).hexdigest()
def digest_file(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while c:=f.read(8<<20):h.update(c)
    return h.hexdigest()
def close_writer(w):
    w.write_header_to_file();w.write_kv_data_to_file();w.write_tensors_to_file(progress=True);w.close()
def link(source,target):
    if target.exists():assert os.path.samefile(source,target)
    else:os.link(source,target)

if a.stage=='prepare':
    assert not (work/'missing-bf16.gguf').exists(),'Preserve previous output; inspect before rebuilding.'
    writer=gguf.GGUFWriter(str(work/'missing-bf16.gguf'),arch)
    for name,field in src.fields.items():
        if name=='general.architecture' or name.startswith(('GGUF.','split.')):continue
        value=author.to_python(field.contents())
        if field.types[0]==gguf.GGUFValueType.ARRAY and not value:continue
        subtype=field.types[1] if field.types[0]==gguf.GGUFValueType.ARRAY and len(field.types)>1 else None
        writer.add_key_value(name,value,field.types[0],sub_type=subtype)
    types=[]
    for name,t in missing.items():
        original=pt[f'{name}_30']
        assert int(original.tensor_type)==30 and list(original.shape)==list(t.shape)
        decoded=author.xor_tensor(original.data,key)
        floats=(decoded.view(np.uint16).astype(np.uint32)<<16).view(np.float32)
        assert np.isfinite(floats).all(),name
        writer.add_tensor(name,decoded,raw_dtype=original.tensor_type)
        types.append(re.escape(name)+'='+('q4_k' if int(t.tensor_type)==12 else 'iq4_nl'))
    close_writer(writer)
    (work/'tensor-types.txt').write_text('\n'.join(types)+'\n')
    (work/'input').mkdir(exist_ok=True)
    (work/'input'/first).symlink_to(srcdir/first)
    (work/'augmented-patch').mkdir(exist_ok=True)
    link(assets/'Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf',work/'augmented-patch/official.gguf')
    link(assets/'Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf.key',work/'augmented-patch/public-encoding.key')
    print('Prepared',len(missing),'BF16 tensors for the standard CPU quantizer.',flush=True)

elif a.stage=='supplement':
    quantized=gguf.GGUFReader(str(work/'missing-quantized.gguf'))
    qt={t.name:t for t in quantized.tensors}
    assert set(qt)==set(missing)
    writer=gguf.GGUFWriter(str(work/'augmented-patch/derived-gsq-formats.gguf'),arch)
    rows=[]
    for name,base in missing.items():
        t=qt[name]
        assert t.tensor_type==base.tensor_type and list(t.shape)==list(base.shape),name
        writer.add_tensor(f'{name}_{t.tensor_type}',author.xor_tensor(t.data,key),raw_dtype=t.tensor_type)
        rows.append(dict(name=name,type=int(t.tensor_type),shape=[int(x) for x in t.shape],sha256=digest_array(t)))
    close_writer(writer)
    (work/'derived-manifest.json').write_text(json.dumps(dict(
        method='Official Huihui v2 BF16 dense edits, standard llama.cpp quantization into the existing GSQ tensor formats.',
        official=json.loads((assets/'manifest.json').read_text()),
        quantizer_source='llama.cpp 3cf03257f219afbe7334045ff7c6a06ac68c627d, CPU build',
        tensors=rows,source_bf16_sha256=digest_file(work/'missing-bf16.gguf'),
        quantized_sha256=digest_file(work/'missing-quantized.gguf'),
        supplement_sha256=digest_file(work/'augmented-patch/derived-gsq-formats.gguf')),indent=2)+'\n')
    print('Supplement complete',len(rows),flush=True)

elif a.stage=='verify':
    candidate=work/'candidate'
    link(srcdir/second,candidate/second)
    link(srcdir/'mmproj-Qwen3.8-Flash-Next-BF16.gguf',candidate/'mmproj-Qwen3.8-Flash-Next-BF16.gguf')
    dst=gguf.GGUFReader(str(candidate/first));dt={t.name:t for t in dst.tensors}
    assert set(dt)=={t.name for t in src.tensors}
    def metadata(r):return {k:author.to_python(v.contents()) for k,v in r.fields.items() if not k.startswith('GGUF.')}
    assert metadata(src)==metadata(dst),'Metadata changed'
    supplemental=gguf.GGUFReader(str(work/'augmented-patch/derived-gsq-formats.gguf'))
    all_pt={**pt,**{t.name:t for t in supplemental.tensors}}
    changed=[];unchanged=[]
    for t in src.tensors:
        d=dt[t.name]
        assert d.tensor_type==t.tensor_type and list(d.shape)==list(t.shape),t.name
        sh=digest_array(t);dh=digest_array(d)
        if t.name in targets:
            expected=author.xor_tensor(all_pt[f'{t.name}_{t.tensor_type}'].data,key)
            assert np.array_equal(d.data,expected),t.name
            assert sh!=dh,t.name
            changed.append(dict(name=t.name,before_sha256=sh,after_sha256=dh))
        else:
            assert sh==dh,t.name
            unchanged.append(t.name)
    assert len(changed)==96
    report=dict(changed=changed,unchanged_count=len(unchanged),unchanged_names=unchanged,
                metadata_equal=True,ngram_same_inode=True,projector_same_inode=True,
                first_shard_sha256=digest_file(candidate/first),first_shard_bytes=(candidate/first).stat().st_size,
                derivation=json.loads((work/'derived-manifest.json').read_text()))
    (root/'results/huihui20261108-weight-candidate-integrity.json').write_text(json.dumps(report,indent=2)+'\n')
    print('VERIFIED',len(changed),'dense edits;',len(unchanged),'unchanged tensors',flush=True)

elif a.stage=='profile':
    base='flash-iq3s-256k-vision-tune-owner20261108'
    name='flash-iq3s-256k-vision-tune-huihuiv220261108'
    cfg=json.loads((root/f'profiles/{base}.json').read_text())
    assert '--control-vector-scaled' not in cfg['args']
    cfg['args'][cfg['args'].index('--native')+1]=str(work/'candidate'/first)
    cfg['args'][cfg['args'].index('--pack')+1]='/work/packs/iq3s-huihuiv2'
    cfg['vision']['model']=str(work/'candidate'/first)
    cfg['log']=f'/work/results/{name}-engine.log'
    (root/f'profiles/{name}.json').write_text(json.dumps(cfg,indent=2)+'\n')
    shutil.copy2(root/f'profiles/{base}.shared-settings.json',root/f'profiles/{name}.shared-settings.json')
    print('PROFILE',name,flush=True)
