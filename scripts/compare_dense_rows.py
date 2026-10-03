"""Screen dense tensor coordinate compatibility using sampled rows, without inference.

Run in the pinned Strata image. Header reading supports all target types; only
the selected dense rows pass through llama.cpp's gguf-py dequantizers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, '/opt/strata/tools')
sys.path.insert(0, '/opt/strata/ref/llama.cpp/gguf-py')
import numpy as np
from gguf import GGMLQuantizationType
from gguf.quants import dequantize
from gguf_reader import GGUFFile, BLOCK_GEOMETRY


def locate(shards, name):
    matches = [(reader, tensor) for p in shards for reader in [GGUFFile(p)]
               for tensor in reader.tensors if tensor.name == name]
    if len(matches) != 1:
        raise ValueError('Expected exactly one tensor: ' + name)
    return matches[0]


def rows(reader, tensor, indices):
    width = tensor.shape[0]
    block, size = BLOCK_GEOMETRY[tensor.type_name]
    if width % block:
        raise ValueError('Row does not contain whole quantization blocks')
    row_bytes = width // block * size
    values, digest = [], hashlib.sha256()
    with reader.path.open('rb') as stream:
        for index in indices:
            stream.seek(reader.data_start + tensor.offset + int(index) * row_bytes)
            raw = stream.read(row_bytes)
            if len(raw) != row_bytes:
                raise ValueError('Short tensor row')
            digest.update(raw)
            value = dequantize(np.frombuffer(raw, dtype=np.uint8).reshape(1, -1),
                               GGMLQuantizationType(tensor.type_id)).reshape(-1)
            if len(value) != width or not np.isfinite(value).all():
                raise ValueError('Invalid dequantized row')
            values.append(value)
    return np.asarray(values, dtype=np.float64), {
        'shard': reader.path.name, 'type': tensor.type_name, 'shape': tensor.shape,
        'sampled_raw_bytes_sha256': digest.hexdigest(), 'bytes_read': row_bytes * len(indices)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iq3', type=Path, nargs='+', required=True)
    ap.add_argument('--q4', type=Path, nargs='+', required=True)
    ap.add_argument('--rows', type=int, default=512)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.rows < 1:
        ap.error('--rows must be positive')
    report = {'scope': 'Sampled coordinate comparison, not inference or proof of full basis compatibility. '
        'High cosine similarity screens for a gross rotation/layout mismatch; it does not certify a mixed model.',
        'seed': 42, 'requested_random_rows': args.rows,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'tensors': {}}
    for name in ['token_embd.weight', 'output.weight', 'output_hc_down.weight',
                 'output_hc_norm.weight', 'output_hc_up.weight']:
        left, right = locate(args.iq3, name), locate(args.q4, name)
        if left[1].shape != right[1].shape or len(left[1].shape) not in [1, 2]:
            raise ValueError('Expected matching vector/matrix shapes: ' + name)
        height = left[1].shape[1] if len(left[1].shape) == 2 else 1
        indices = sorted(set(np.random.default_rng(42).choice(height,
            min(args.rows, height), replace=False).tolist() +
            [i for i in [0, 1, height-1, 248045, 248046, 248056] if i < height]))
        a, left_id = rows(*left, indices)
        b, right_id = rows(*right, indices)
        norms = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
        good = norms > 0
        cosine = np.sum(a[good] * b[good], axis=1) / norms[good]
        relative_l2 = np.linalg.norm(a-b) / np.linalg.norm(b) if np.linalg.norm(b) else None
        entry = {'iq3': left_id, 'q4': right_id, 'sampled_row_ids': indices,
            'row_count': len(indices), 'nonzero_row_pairs': int(good.sum()),
            'global_relative_l2_to_q4': relative_l2,
            'cosine': {'min': float(cosine.min()), 'median': float(np.median(cosine)),
                'mean': float(cosine.mean()), 'p01': float(np.quantile(cosine, .01))} if len(cosine) else None}
        report['tensors'][name] = entry
        print(name, entry['cosine'], 'relative L2', relative_l2, flush=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
