"""Header-only IQ3/Q4 tensor inventory; run in Strata's container, no inference."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, '/opt/strata/tools')
from gguf_reader import GGUFFile


def group(name):
    if name == 'per_layer_token_embd.weight': return 'ngram'
    if name == 'token_embd.weight': return 'embedding'
    if name == 'output.weight': return 'output_head'
    if '_exps.' in name: return 'routed_experts'
    if 'ffn_gate_inp' in name: return 'routers'
    if '_shexp.' in name: return 'shared_experts'
    if 'hc_' in name: return 'hyper_connections'
    if 'ssm_' in name: return 'gdn'
    if 'attn_' in name or 'indexer.' in name: return 'attention_indexer'
    if '.ple_' in name: return 'ngram_projections'
    return 'other'


def inventory(shards):
    tensors, groups = {}, defaultdict(lambda: defaultdict(lambda: {'tensors': 0, 'bytes': 0}))
    for shard in shards:
        for tensor in GGUFFile(shard).tensors:
            if tensor.name in tensors: raise RuntimeError('Duplicate tensor: '+tensor.name)
            row = {'shape': tensor.shape, 'type': tensor.type_name,
                   'bytes': tensor.expected_bytes(), 'group': group(tensor.name)}
            if row['bytes'] is None: raise RuntimeError('Unknown byte geometry')
            tensors[tensor.name] = row
            counts = groups[row['group']][row['type']]
            counts['tensors'] += 1; counts['bytes'] += row['bytes']
    return {'source_shards': [p.name for p in shards], 'tensor_count': len(tensors),
            'groups': dict(groups), 'tensors': tensors}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iq3', type=Path, nargs='+', required=True)
    ap.add_argument('--q4', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    iq3, q4 = inventory(args.iq3), inventory(args.q4)
    if iq3['tensors'].keys() != q4['tensors'].keys(): raise RuntimeError('Tensor sets differ')
    differences = []
    for name, left in iq3['tensors'].items():
        right = q4['tensors'][name]
        if left['shape'] != right['shape']: raise RuntimeError('Shape differs: '+name)
        if left['type'] != right['type']:
            differences.append({'name': name, 'group': left['group'], 'shape': left['shape'],
                                'iq3_type': left['type'], 'q4_type': right['type']})
    args.out.write_text(json.dumps({'scope': 'GGUF source header types/shapes/bytes; no tensor data read. '
        'Same type does not imply identical values; converted runtime pack types are separate.',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'iq3': iq3, 'q4': q4, 'type_differences': differences}, indent=2)+'\n')
    print('Tensor inventory:', iq3['tensor_count'], 'matching names/shapes;',len(differences),'type differences')
    for label, data in [('iq3', iq3), ('q4', q4)]:
        for category in ['embedding','output_head','routers','hyper_connections','gdn','attention_indexer','routed_experts']:
            print(label,category,json.dumps(data['groups'].get(category),sort_keys=True))


if __name__ == '__main__':
    main()
