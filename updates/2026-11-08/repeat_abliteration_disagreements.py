"""Repeat every screen disagreement in both arms; retain independent run noise."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))
from bench import request
from eval import grade
from scripts.evaluation_provenance import capture, assert_container, require_matching

url='http://127.0.0.1:19623'
original=json.loads(Path('results/huihui20261108-paired-screen.json').read_text())
assert original['complete']
runtime=capture(url)
require_matching(original,runtime)
pairs={}
for row in original['results']:
    pairs.setdefault(row['key'],{})[row['projection']]=row
selected={k:v for k,v in pairs.items() if v[False]['verdict']['pass']!=v[True]['verdict']['pass']}
ifeval={f'ifeval-{c["key"]}':c for line in Path('eval/ifeval-80.jsonl').read_text().splitlines() if (c:=json.loads(line))}
mmlu={f'mmlu-{c["id"]}':c['data'] for line in Path('eval/cases.jsonl').read_text().splitlines() if (c:=json.loads(line))['suite']=='mmlupro'}
path=Path('results/huihui20261108-paired-disagreements.json')
report=dict(runtime=runtime,selected_keys=sorted(selected),results=[],
            purpose='Diagnostic repeats of all discordant pairs; not an unbiased replacement for the complete cohort.')
if path.exists():
    old=json.loads(path.read_text());require_matching(old,runtime)
    assert old['selected_keys']==report['selected_keys']
    report=old
for repeat in range(1,4):
    for key in sorted(selected):
        for arm in ([False,True] if repeat%2 else [True,False]):
            identity=f'{key}:{repeat}:{arm}'
            if any(x['identity']==identity for x in report['results']):continue
            if key in ifeval:
                c=ifeval[key]
                messages=[{'role':'user','content':c['prompt']}]
                tokens=4096
            else:
                d=mmlu[key]
                choices='\n'.join(f'{chr(65+i)}. {v}' for i,v in enumerate(d['options']))
                messages=[{'role':'system','content':'Choose the correct answer. Reply with only its single uppercase letter, without explanation.'},
                          {'role':'user','content':d['question']+'\n\n'+choices}]
                tokens=64
            payload=dict(model='ulmus',messages=messages,temperature=0,seed=42,
                reasoning_effort='none',max_tokens=tokens,experimental_speed_projection=arm,
                stream=True,stream_options={'include_usage':True})
            assert hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()==selected[key][arm]['input_sha256']
            assert_container(runtime)
            r=request(url,payload)
            assert_container(runtime)
            verdict=(grade(ifeval[key],r['content'],'ulmus/ifeval:e6890f8') if key in ifeval else {'pass':r['content'].strip()==mmlu[key]['answer']})
            if r['finish_reason']=='length': verdict={'pass':False,'incomplete':True}
            report['results'].append(dict(identity=identity,key=key,repeat=repeat,projection=arm,verdict=verdict,response=r))
            path.write_text(json.dumps(report,indent=2)+'\n')
            print(key,repeat,arm,verdict,flush=True)
report['complete']=True
path.write_text(json.dumps(report,indent=2)+'\n')
