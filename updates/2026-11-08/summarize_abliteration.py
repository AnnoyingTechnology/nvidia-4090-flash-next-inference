"""Derive a compact, response-free qualification summary from retained evidence."""
import collections
import hashlib
import json
from pathlib import Path
import statistics

root=Path.cwd()
res=root/'results'
summary={'status':'qualification in progress','artifacts':{},'vector':{},'weights':{}}
def read(name):
    p=res/name
    if not p.exists():return None
    data=p.read_bytes()
    summary['artifacts'][name]=hashlib.sha256(data).hexdigest()
    return json.loads(data)
def group(key):
    if key.startswith('practical-'):return '-'.join(key.split('-')[:2])
    return key.split('-')[0]
def cohorts(rows):
    groups=collections.defaultdict(list)
    for r in rows:groups[group(r['key'])].append(r)
    out={}
    for k,rs in sorted(groups.items()):
        incomplete=sum(r['response']['finish_reason']=='length' for r in rs)
        out[k]={'passed':sum(r['verdict']['pass'] for r in rs),'total':len(rs),'capped':incomplete,
                'natural_completion_required':k not in ['boundary'],'complete_cohort':incomplete==0,
                'wall_seconds':sum(r['response']['total_s'] for r in rs),
                'median_completion_tokens':statistics.median(r['response']['usage']['completion_tokens'] for r in rs)}
    return out
def compare(baseline,candidate):
    b={r['key']:r for r in baseline};c={r['key']:r for r in candidate}
    shared=set(b)&set(c)
    return {'matched_cases':len(shared),'identical_request_hashes':sum(b[k]['input_sha256']==c[k]['input_sha256'] for k in shared),
            'losses':[k for k in sorted(shared) if b[k]['verdict']['pass'] and not c[k]['verdict']['pass']],
            'gains':[k for k in sorted(shared) if c[k]['verdict']['pass'] and not b[k]['verdict']['pass']]}
for stage in ['screen','features','practical']:
    old=read(f'huihui20261108-paired-{stage}.json')
    if old:
        baseline=[r for r in old['results'] if r['projection'] is False]
        projected=[r for r in old['results'] if r['projection'] is True]
        summary['vector'][stage]={'complete':old.get('complete',False),'baseline':cohorts(baseline),
                                  'candidate':cohorts(projected),'disagreements':compare(baseline,projected)}
        new=read(f'huihui-weight20261108-paired-{stage}.json')
        if new:
            candidate=new['results']
            summary['weights'][stage]={'complete':new.get('complete',False),'baseline':cohorts(baseline),
                'candidate':cohorts(candidate),'disagreements':compare(baseline,candidate)}
perf=read('huihui20261108-paired-performance.json')
if perf:
    arms={}
    for arm in [False,True]:
        rows=[r for r in perf['results'] if r['projection']==arm]
        decode=[r['response']['timings']['predicted_per_second'] for r in rows if r['key'].startswith('decode-')]
        prefill=[r['response']['timings']['prompt_per_second'] for r in rows if r['key']=='prefill']
        arms['candidate' if arm else 'baseline']={'decode_median_tok_s':statistics.median(decode) if decode else None,
            'decode_samples':decode,'prefill_median_tok_s':statistics.median(prefill) if prefill else None,
            'prefill_samples':prefill}
    if all(a['prefill_samples'] and a['decode_samples'] for a in arms.values()):
        arms['decode_delta_pct']=100*(arms['candidate']['decode_median_tok_s']/arms['baseline']['decode_median_tok_s']-1)
        arms['prefill_delta_pct']=100*(arms['candidate']['prefill_median_tok_s']/arms['baseline']['prefill_median_tok_s']-1)
    summary['vector']['performance']=arms
abba=[]
for i,arm in enumerate(['baseline','candidate','candidate','baseline']):
    r=read(f'huihui-weight20261108-abba-{i}-{arm}.json')
    if not r:continue
    decode=[x['timings']['predicted_per_second'] for x in r['decode']]
    prefill=[x['timings']['prompt_per_second'] for x in r['prefill']]
    by_fixture=collections.defaultdict(list)
    for x in r['decode']:by_fixture[x['fixture']].append(x['timings']['predicted_per_second'])
    abba.append({'start':i,'arm':arm,'decode':decode,'prefill':prefill,
        'decode_median':statistics.median(decode) if decode else None,
        'prefill_median':statistics.median(prefill) if prefill else None,
        'decode_by_fixture':dict(by_fixture),
        'image_id':r['runtime']['identity']['image_id'],
        'template_sha256':r['runtime']['identity']['chat_template_sha256'],
        'request_hashes':{g:[x['input_sha256'] for x in r[g]] for g in ['warmups','decode','prefill']}})
summary['weights']['abba_starts']=abba
if len(abba)==4 and all(a['decode'] and len(a['prefill'])==2 for a in abba):
    p={}
    for arm in ['baseline','candidate']:
        rows=[r for r in abba if r['arm']==arm]
        p[arm]={'fresh_starts':len(rows),'decode_median_tok_s':statistics.median(x for r in rows for x in r['decode']),
                'prefill_median_tok_s':statistics.median(x for r in rows for x in r['prefill']),
                'per_start_decode_medians':[r['decode_median'] for r in rows],
                'per_start_prefill_medians':[r['prefill_median'] for r in rows]}
    p['decode_delta_pct']=100*(p['candidate']['decode_median_tok_s']/p['baseline']['decode_median_tok_s']-1)
    p['prefill_delta_pct']=100*(p['candidate']['prefill_median_tok_s']/p['baseline']['prefill_median_tok_s']-1)
    p['identical_requests']=all(r['request_hashes']==abba[0]['request_hashes'] for r in abba)
    p['template_and_image_identical']=len({(r['image_id'],r['template_sha256']) for r in abba})==1
    summary['weights']['performance']=p
integrity=read('huihui20261108-weight-candidate-integrity.json')
if integrity:
    summary['weights']['integrity']={k:integrity[k] for k in ['metadata_equal','ngram_same_inode','projector_same_inode','first_shard_sha256','first_shard_bytes','unchanged_count']}
    summary['weights']['integrity']['changed_count']=len(integrity['changed'])
for tag,key in [('huihui20261108','vector'),('huihui-weight20261108','weights')]:
    for name in ['api','quality','agent','histories','ops-none','ops-low','agent-off','agent-on','ops-off-none','ops-on-none','ops-on-low']:
        r=read(f'{tag}-{name}.json')
        if r is None:continue
        if isinstance(r,list):result={'passed':sum(x.get('pass',False) for x in r),'total':len(r),
            'cache_passed':sum(x.get('cache_pass',False) for x in r)}
        elif 'summary' in r:result=r['summary']
        elif 'results' in r:result={'passed':sum(x.get('pass',False) for x in r['results']),'total':len(r['results'])}
        else:continue
        summary[key][name]=result
repeat=read('huihui20261108-paired-disagreements.json')
if repeat:
    counts=collections.defaultdict(lambda:collections.defaultdict(list))
    for row in repeat['results']:counts[row['key']][str(row['projection'])].append(row['verdict']['pass'])
    summary['vector']['repeated_disagreements']={k:dict(v) for k,v in counts.items()}
for label in ['baseline','candidate']:
    r=read(f'huihui-weight20261108-dense-bar-{label}.json')
    if not r:continue
    groups=collections.defaultdict(list)
    for row in r['results']:groups[row['suite']].append(row)
    summary['weights']['dense_bar_'+label]={'complete':r.get('complete',False),
        'source_sha256':r['source_sha256'],'controls_passed':len(r['controls']),
        'suites':{k:{'passed':sum(x['verdict']['pass'] for x in rows),'total':len(rows),
                     'capped':sum(x['response']['finish_reason']=='length' for x in rows)} for k,rows in groups.items()}}
for label in ['baseline','weights']:
    r=read(f'huihui-repeat-{label}20261108-paired-screen.json')
    if r:summary['weights']['ifeval_repeat_'+label]={'complete':r.get('complete',False),'cohorts':cohorts(r['results'])}
long=[]
long_labels=['baseline','candidate','candidate2','baseline-resume'] if (res/'huihui-weight20261108-long-baseline-resume.json').exists() else ['baseline','candidate','candidate2','baseline2']
for label in long_labels:
    r=read(f'huihui-weight20261108-long-{label}.json')
    if not r:continue
    rows=[]
    for x in r['results']:
        rr=x['response'];tt=rr['timings']
        rows.append({'repeat':x['repeat'],'pass':x['pass'],'input_sha256':x['input_sha256'],
            'content_sha256':hashlib.sha256(rr['content'].encode()).hexdigest(),
            'prompt_tokens':rr['usage']['prompt_tokens'],'completion_tokens':rr['usage']['completion_tokens'],
            'cached_tokens':rr['usage'].get('prompt_tokens_details',{}).get('cached_tokens',0),
            'prefill_tok_s':tt['prompt_per_second'],'decode_tok_s':tt['predicted_per_second'],
            'total_s':rr['total_s'],'ttft_s':rr['ttft_s']})
    long.append({'label':label,'complete':r.get('complete',False),'results':rows})
summary['weights']['long_context_starts']=long
if len(long)==4 and all(r['complete'] and len(r['results'])==2 for r in long):
    summary['weights']['long_context_by_position']={}
    for position in [0,1]:
        pairs={arm:[r['results'][position] for r in long if r['label'].startswith(arm)] for arm in ['baseline','candidate']}
        cell={arm:{'decode_samples':[x['decode_tok_s'] for x in rs],
                   'prefill_samples':[x['prefill_tok_s'] for x in rs],
                   'wall_seconds':[x['total_s'] for x in rs]} for arm,rs in pairs.items()}
        for metric in ['decode','prefill']:
            cell[metric+'_delta_pct']=100*(statistics.median(cell['candidate'][metric+'_samples'])/statistics.median(cell['baseline'][metric+'_samples'])-1)
        cell['identical_inputs']=len({x['input_sha256'] for rs in pairs.values() for x in rs})==1
        cell['identical_outputs']=len({x['content_sha256'] for rs in pairs.values() for x in rs})==1
        summary['weights']['long_context_by_position'][str(position)]=cell
if read('huihui-weight20261108-long-resume-complete.json'):
    summary['status']='not adopted: repeatable long-context decode regression exceeds the measured baseline variation'
    summary['decision']={'selected_profile':'flash-iq3s-256k-vision-tune-owner20261108',
        'candidate_profile':'flash-iq3s-256k-vision-tune-huihuiv220261108',
        'candidate_activated':False,'further_tests_authorized':False,
        'reason':'About 2% lower long-context decode in both matched cache positions; original model retained under the owner no-regression requirement.',
        'manual_boundary_review':{'baseline_refused':['beijing-english','beijing-chinese'],
            'candidate_answered':['beijing-english','beijing-chinese'],
            'both_answered_controls':['offline-security','fictional-profanity']}}
adoption=root/'updates/2026-11-08/huihui-adoption.json'
if adoption.exists():
    record=json.loads(adoption.read_text())
    summary['status']=record['status']
    summary['decision']={'selected_profile':record['selected_profile'],'candidate_activated':True,
        'owner_decision':record['owner_decision'],'adoption_record':'huihui-adoption.json',
        'further_tests_authorized':False}
dest=root/'updates/2026-11-08/abliteration-summary.json'
dest.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='artifacts'},indent=2))
