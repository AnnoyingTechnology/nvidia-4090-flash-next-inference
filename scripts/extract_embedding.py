"""Copy a source GGUF embedding unchanged into Strata's standalone override format.

Run in the pinned Strata image. Only the selected tensor is read; no dequantization
or inference occurs. Split-model metadata must not accompany a standalone tensor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, '/opt/strata/tools')
from gguf_reader import GGUFFile


def string(value):
    raw = value.encode('utf-8')
    return struct.pack('<Q', len(raw)) + raw


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    args = ap.parse_args()
    reader = GGUFFile(args.source)
    tensors = [t for t in reader.tensors if t.name == 'token_embd.weight']
    if len(tensors) != 1:
        raise ValueError('Expected exactly one token embedding in the source shard')
    tensor = tensors[0]
    size = tensor.expected_bytes()
    if len(tensor.shape) != 2 or tensor.shape[0] % 256 or not size:
        raise ValueError('Invalid embedding shape or block geometry')
    start = reader.data_start + tensor.offset
    if start + size > args.source.stat().st_size:
        raise ValueError('Truncated source tensor')
    if args.out.exists() or args.report.exists():
        raise FileExistsError('Refusing to replace an existing artifact or report')
    metadata = {'general.architecture': 'strata-embd',
                'general.name': 'Unchanged ' + tensor.type_name + ' source embedding',
                'strata.embd.source': args.source.name}
    header = b'GGUF' + struct.pack('<IQQ', 3, 1, len(metadata))
    for key, value in metadata.items():
        header += string(key) + struct.pack('<I', 8) + string(value)
    header += string(tensor.name) + struct.pack('<I', 2)
    header += struct.pack('<QQIQ', *tensor.shape, tensor.type_id, 0)
    header += b'\0' * (-len(header) % 32)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + '.part')
    digest = hashlib.sha256()
    with temporary.open('xb') as target, args.source.open('rb') as source:
        target.write(header)
        source.seek(start)
        remaining = size
        while remaining:
            data = source.read(min(64 << 20, remaining))
            if not data:
                raise ValueError('Short source read')
            target.write(data)
            digest.update(data)
            remaining -= len(data)
    check = GGUFFile(temporary)
    if (temporary.stat().st_size != len(header) + size or check.data_start != len(header)
            or len(check.tensors) != 1 or check.tensors[0].shape != tensor.shape
            or check.tensors[0].type_id != tensor.type_id):
        raise ValueError('Written embedding header or size differs')
    copied, whole = hashlib.sha256(), hashlib.sha256()
    with temporary.open('rb') as target:
        whole.update(target.read(len(header)))
        while data := target.read(64 << 20):
            copied.update(data)
            whole.update(data)
    if copied.digest() != digest.digest():
        raise ValueError('Copied tensor payload differs')
    temporary.rename(args.out)
    args.report.write_text(json.dumps({'operation': 'Exact embedding payload copy; no requantization',
        'source_shard': args.source.name, 'tensor': tensor.name, 'shape': tensor.shape,
        'type': tensor.type_name, 'payload_bytes': size, 'source_payload_sha256': digest.hexdigest(),
        'copied_payload_sha256': copied.hexdigest(), 'artifact_sha256': whole.hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2) + '\n')
    print(args.report.read_text())


if __name__ == '__main__':
    main()
