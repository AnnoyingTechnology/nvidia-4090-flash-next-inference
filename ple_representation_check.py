"""Check shard/row/basis alignment against the released IQ4_NL table, without target inference."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import sys
sys.path.insert(0, '/opt/strata/tools')
from gguf_reader import GGUFFile

CODEBOOK = [-127, -104, -83, -65, -49, -35, -22, -10, 1, 13, 25, 38, 53, 69, 89, 113]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bf16', required=True)
    ap.add_argument('--iq4nl', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    files = [GGUFFile(Path(path)) for path in [args.bf16, args.iq4nl]]
    tensors = [next(t for t in f.tensors if t.name == 'per_layer_token_embd.weight') for f in files]
    if tensors[0].shape != tensors[1].shape or tensors[0].type_id != 30 or tensors[1].type_id != 20:
        raise RuntimeError('Ngram geometry or dtype mismatch')
    rng = random.Random(42)
    rows = sorted({shard * 2500012 + at for shard in range(128)
                   for at in [0, 2500011, rng.randrange(2500012), rng.randrange(2500012)]})
    handles = [os.open(f.path, os.O_RDONLY) for f in files]
    errors, dot, a2, b2 = 0., 0., 0., 0.
    samples = []
    try:
        for row in rows:
            raw = [os.pread(fd, width, f.data_start + t.offset + row * width)
                   for fd, f, t, width in zip(handles, files, tensors, [320, 90])]
            if [len(x) for x in raw] != [320, 90]:
                raise RuntimeError('Short table row read')
            full = [struct.unpack('<f', struct.pack('<I', x << 16))[0] for x in struct.unpack('<160H', raw[0])]
            quant = []
            for block in range(5):
                start = 18 * block
                scale = struct.unpack('<e', raw[1][start:start+2])[0]
                codes = raw[1][start+2:start+18]
                quant.extend(scale * CODEBOOK[x & 15] for x in codes)
                quant.extend(scale * CODEBOOK[x >> 4] for x in codes)
            error = sum((a-b)**2 for a,b in zip(full, quant))
            norm = sum(x*x for x in full)
            errors += error; a2 += norm; b2 += sum(x*x for x in quant)
            dot += sum(a*b for a,b in zip(full,quant))
            samples.append({'row': row, 'bf16_raw_sha256': hashlib.sha256(raw[0]).hexdigest(),
                            'iq4nl_raw_sha256': hashlib.sha256(raw[1]).hexdigest(),
                            'relative_rms_error': math.sqrt(error/norm) if norm else None})
    finally:
        for fd in handles:
            os.close(fd)
    report = {'purpose': 'Detect gross row/shard/basis mismatch; not a task quality measurement',
              'rows_sampled': len(rows), 'all_128_shards_covered': True, 'seed': 42,
              'cosine_similarity': dot / math.sqrt(a2*b2), 'relative_rms_error': math.sqrt(errors/a2),
              'bf16_source': files[0].metadata.get('strata.ple.source'),
              'files': [str(f.path) for f in files], 'samples': samples}
    Path(args.out).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'samples'}))


if __name__ == '__main__':
    main()
