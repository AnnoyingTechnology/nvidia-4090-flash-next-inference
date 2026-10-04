"""Offline cache-allocation discriminator. No speed or exact live-cache simulation claim."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / 'results'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def windows(data):
    assert len(data) % 88 == 0
    result, current, previous, tokens = [], {}, -1, Counter()
    for offset in range(0, len(data), 88):
        layer, k = struct.unpack_from('<ii', data, offset)
        assert 0 <= layer < 48 and k == 10
        ids = struct.unpack_from('<10i', data, offset + 8)
        assert all(0 <= e < 512 for e in ids)
        if layer < previous:
            assert set(current) == set(range(48)) and len(set(tokens.values())) == 1
            result.append(current)
            current, tokens = {}, Counter()
        current.setdefault(layer, set()).update(ids)
        tokens[layer] += 1
        previous = layer
    if current:
        assert set(current) == set(range(48)) and len(set(tokens.values())) == 1
        result.append(current)
    return result


def count(ws):
    return Counter((layer, e) for w in ws for layer, experts in w.items() for e in experts)


def main():
    trace_path = R / 'decode-routing-20261004.bin'
    request_path = R / 'decode-routing-20261004.json'
    profile_path = ROOT / 'upstream/strata-v0.1.38/data/expert-profile.bin'
    layout_path = R / 'routing-native-experts-20261004.txt'
    raw = json.loads(request_path.read_text())
    assert len(raw['cells']) == 6
    data = trace_path.read_bytes()
    pb = profile_path.read_bytes()
    assert pb[:4] == b'STRP'
    version, nl, ne, _, nr = struct.unpack_from('<5I', pb, 4)
    assert (version, nl, ne, nr) == (1, 48, 512, 24576)
    ranking = [struct.unpack_from('<HH', pb, 24 + 4*i) for i in range(nr)]
    assert len(set(ranking)) == nr
    # Actual logged selected cache count; caller verifies against captured startup log.
    initial = set(ranking[:8379])
    quotas = Counter(l for l, e in initial)
    sizes = {}
    for line in layout_path.read_text().splitlines():
        if line.startswith('#') or not line.strip(): continue
        row = list(map(int, line.split()[:9]))
        sizes[row[0]] = (row[4] + 255) // 256 * 256
    assert len(sizes) == 48
    budget = sum(sizes[l] for l, e in initial)
    cells = []
    last = 0
    for c in raw['cells']:
        assert c['completion_tokens'] == 512 and c['finish_reason'] == 'length'
        start, end = c['routing_trace_bytes']
        assert start == last and end > start
        last = end
        cells.append((c, windows(data[start:end])))
    pairs = [(l,e) for l in range(48) for e in range(512)]
    prior = {p:i for i,p in enumerate(ranking)}

    def allocation(freq, global_budget):
        if not global_budget:
            return {p for l in range(48) for p in sorted([(l,e) for e in range(512)],
                    key=lambda p:(-freq[p],prior[p]))[:quotas[l]]}
        selected, used = set(), 0
        # Greedy benefit/byte, not an exact knapsack optimum.
        for p in sorted(pairs,key=lambda p:(-freq[p]/sizes[p[0]],prior[p])):
            if used+sizes[p[0]] <= budget:
                selected.add(p); used += sizes[p[0]]
        return selected

    def score(freq, selected):
        total=sum(freq.values()); hits=sum(v for p,v in freq.items() if p in selected)
        return {'unique_layer_window_experts':total,'covered':hits,'misses':total-hits,
                'coverage':hits/total,'bytes':sum(sizes[l] for l,e in selected),'slots':len(selected)}

    folds=[]
    for question in sorted({c['question'] for c,w in cells}):
        train=count([w for c,ws in cells if c['question'] != question for w in ws])
        test=count([w for c,ws in cells if c['question'] == question for w in ws])
        fixed=allocation(train,False); global_set=allocation(train,True)
        oracle_fixed=allocation(test,False); oracle_global=allocation(test,True)
        folds.append({'held_out_question':question,'train_windows':sum(len(ws) for c,ws in cells if c['question'] != question),
            'test_windows':sum(len(ws) for c,ws in cells if c['question'] == question),
            'trained_fixed_layer_quotas':score(test,fixed),'trained_global_byte_budget':score(test,global_set),
            'test_fitted_fixed_quotas_diagnostic':score(test,oracle_fixed),
            'test_fitted_global_greedy_diagnostic':score(test,oracle_global),
            'global_layer_slot_counts':dict(sorted(Counter(l for l,e in global_set).items()))})
    report={'method':'Three leave-one-question-out folds, both 32K/128K held out together. Unique experts per layer per verification window. Compare offline frequency-selected static caches at equal byte budgets, fixed current layer quotas versus global greedy frequency/byte. Not the live adaptive policy; includes rejected draft work. Test-fitted figures are optimistic diagnostics, not held-out results. Six questions/context cells share a synthetic document: limited workload diversity.',
        'sources':{p.name:sha(p) for p in [trace_path,request_path,profile_path,layout_path]},
        'budget_bytes':budget,'initial_slots':8379,'initial_layer_slots':dict(sorted(quotas.items())),
        'folds':folds}
    out=R/'routing-allocation-20261004-summary.json';out.write_text(json.dumps(report,indent=2)+'\n')
    for f in folds:
        a=f['trained_fixed_layer_quotas'];b=f['trained_global_byte_budget']
        print(f['held_out_question'], 'coverage',a['coverage'],b['coverage'],'miss reduction',(a['misses']-b['misses'])/a['misses'])


if __name__ == '__main__':
    main()
