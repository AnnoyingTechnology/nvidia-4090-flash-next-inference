"""Validate the single adaptation-batch candidate against the preregistered ABBA gate."""
import hashlib
import json
from pathlib import Path
import re
import statistics as st
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_provenance import fingerprint
from scripts.summarize_swap_ab import SAME

R = Path(__file__).resolve().parents[1] / 'results'
IMAGE = 'sha256:24386fa3fb0e4d7ff2680174d5a126090293920c4556f1cf289a6af9d24bdefe'


def command_without_adapt(command):
    c = list(command)
    if '--adapt-swaps' in c:
        i = c.index('--adapt-swaps')
        assert c[i+1] == '24'
        del c[i:i+2]
    return c


def main():
    runs, identities = [], {96:[], 24:[]}
    reference = None
    for index, cap in enumerate([96,24,24,96],1):
        base = R / f'adapt-batch-20261004-{index}'
        path = base.with_suffix('.json')
        r = json.loads(path.read_text())
        api = json.loads(Path(str(base)+'-api.json').read_text())
        log = Path(str(base)+'-engine.log').read_text()
        suffix = 'ownerswap' if cap == 96 else 'owneradapt24'
        assert api['profile'] == 'flash-iq3s-256k-vision-tune-'+suffix
        assert api['summary'] == {'passed':9,'total':9} and all(c['passed'] for c in api['checks'])
        assert not re.search('FAILED|CUDA error| - OVERFLOW',log)
        assert r['order'] == [32,128,128,32,32,128]
        assert r['runtime']['identity']['image_id'] == IMAGE
        assert r['sampling']['reasoning_effort'] == 'low'
        assert r['decode_tokens'] == 512 and len(r['cells']) == 6
        assert all(c['completion_tokens']==512 and c['finish_reason']=='length' for c in r['cells'])
        identity = (r['sampling'],r['documents_sha256'],[(c['context_k'],c['input_sha256'],c['prompt_tokens']) for c in r['cells']])
        if reference is not None: assert identity == reference
        reference = identity
        identities[cap].append(r['runtime']['identity'])
        cmd = r['runtime']['identity']['artifacts']['native_command']
        assert ('--adapt-swaps' in cmd) == (cap == 24)
        runs.append({'cap':cap,'source':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'api':api['summary'],'cells':r['cells'],
                     'context_medians':{str(k):st.median(c['decode_tok_s'] for c in r['cells'] if c['context_k']==k) for k in [32,128]},
                     'median_decode_tok_s':st.median(c['decode_tok_s'] for c in r['cells']),
                     'acceptance':sum(c['draft_n_accepted'] for c in r['cells'])/sum(c['draft_n'] for c in r['cells'])})
    for items in identities.values(): assert len({fingerprint(i) for i in items})==1
    a,b=identities[96][0],identities[24][0]
    assert a['chat_template_sha256']==b['chat_template_sha256']
    for key in SAME+['native_sha256','vision_artifacts']:
        assert a['artifacts'][key]==b['artifacts'][key], key
    assert command_without_adapt(a['artifacts']['native_command'])==command_without_adapt(b['artifacts']['native_command'])
    contexts={}
    for k in [32,128]:
        sides={cap:[r['context_medians'][str(k)] for r in runs if r['cap']==cap] for cap in [96,24]}
        contexts[str(k)]={'launch_medians':sides,'delta_percent':100*(st.median(sides[24])/st.median(sides[96])-1),
                          'candidate_above_baseline_range':min(sides[24])>max(sides[96])}
    medians={cap:st.median(r['median_decode_tok_s'] for r in runs if r['cap']==cap) for cap in [96,24]}
    delta=100*(medians[24]/medians[96]-1)
    passed=delta>=3 and all(c['candidate_above_baseline_range'] and c['delta_percent']>=-3 for c in contexts.values())
    equal_work={cap:len([c for r in runs if r['cap']==cap for c in r['cells']])/sum(1/c['decode_tok_s'] for r in runs if r['cap']==cap for c in r['cells']) for cap in [96,24]}
    out={'equal_output_aggregate_tok_s':equal_work,'equal_output_gain_percent':100*(equal_work[24]/equal_work[96]-1),
         'scope':'Single candidate ABBA, same v4 image, unchanged target/sampling; fixed 512-token performance cells, not quality scores.',
         'runs':runs,'contexts':contexts,'aggregate_launch_medians':medians,'aggregate_delta_percent':delta,
         'gate':{'registered_before_launch':True,'minimum_aggregate_gain_percent':3,'positive_range_separation_each_context':True,
                 'maximum_context_regression_percent':3,'all_api_pass':True,'passed':passed},
         'decision':'Proceed to natural quality and image staging qualification; not yet adopted.' if passed else 'Reject candidate; keep selected v4 with 96 swaps.'}
    (R/'adapt-batch-20261004-summary.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='runs'},indent=2))


if __name__ == '__main__': main()
