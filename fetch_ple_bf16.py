"""Extract only the original ngram table using validated HTTP byte ranges.

Never downloads or loads a full-precision target model. The main inference weights remain quantized.
Each completed tensor range has a retained SHA-256; retries write the same bounded output interval.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import os
import struct
import time
import urllib.request


def fetch(url, first, last):
    query = '&' if '?' in url else '?'
    request = urllib.request.Request(url + query + f'ulmus_ple_range={first}-{last}',
        headers={'Range': f'bytes={first}-{last}', 'Accept-Encoding': 'identity'})
    response = urllib.request.urlopen(request, timeout=120)
    expected = f'bytes {first}-{last}/'
    if response.status != 206 or not response.headers.get('Content-Range', '').startswith(expected):
        response.close()
        raise RuntimeError('Server did not honor the requested byte range')
    return response


def read_range(url, first, last):
    with fetch(url, first, last) as response:
        data = response.read(last - first + 2)
    if len(data) != last - first + 1:
        raise RuntimeError('Incomplete metadata byte range')
    return data


def gguf_string(value):
    data = value.encode()
    return struct.pack('<Q', len(data)) + data


def kv_string(key, value):
    return gguf_string(key) + struct.pack('<I', 8) + gguf_string(value)


def write_manifest(path, report):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    source = json.loads(Path(args.index).read_text())
    repo, revision = source['repository'], source['revision']
    weights = source['index']['weight_map']
    tensors = {}
    for name, filename in weights.items():
        if '.ngram_embedding.shard_' in name and name.endswith('.weight'):
            shard = int(name.rsplit('.shard_', 1)[1].split('.')[0])
            tensors[shard] = (name, filename)
    if sorted(tensors) != list(range(128)):
        raise RuntimeError('Expected all 128 original ngram shards')
    headers = {}
    parts = []
    rows = 0
    for shard, (name, filename) in sorted(tensors.items()):
        url = f'https://huggingface.co/{repo}/resolve/{revision}/{filename}'
        if filename not in headers:
            size = struct.unpack('<Q', read_range(url, 0, 7))[0]
            if not 2 <= size <= (16 << 20):
                raise RuntimeError('Unexpected safetensors header size')
            headers[filename] = (json.loads(read_range(url, 8, 7 + size)), 8 + size)
        header, base = headers[filename]
        tensor = header[name]
        shape = tensor['shape']
        start, end = tensor['data_offsets']
        if tensor['dtype'] != 'BF16' or shape != [2500012, 160] or end - start != shape[0] * 320:
            raise RuntimeError('Original ngram tensor geometry/dtype mismatch')
        parts.append({'shard': shard, 'name': name, 'file': filename, 'url': url,
                      'source_start': base + start, 'bytes': end - start})
        rows += shape[0]
    kvs = [kv_string('general.architecture', 'strata-ple'),
           kv_string('general.name', 'Original Qwen ngram table, BF16'),
           kv_string('strata.ple.source', repo + '@' + revision)]
    head = b'GGUF' + struct.pack('<IQQ', 3, 1, len(kvs)) + b''.join(kvs)
    head += gguf_string('per_layer_token_embd.weight') + struct.pack('<IQQIQ', 2, 160, rows, 30, 0)
    head += b'\0' * (-len(head) % 32)
    out, manifest = Path(args.out), Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {'repository': repo, 'revision': revision, 'dtype': 'BF16', 'rows': rows,
              'dim': 160, 'header_bytes': len(head), 'parts': []}
    if out.exists():
        old = json.loads(manifest.read_text())
        if old['revision'] != revision or out.stat().st_size != len(head) + rows * 320:
            raise RuntimeError('Existing output provenance/size mismatch')
        if len(old['parts']) != 128:
            raise RuntimeError('Existing table has an incomplete extraction journal')
        digest = hashlib.sha256()
        with out.open('rb') as file:
            while data := file.read(16 << 20):
                digest.update(data)
        if old.get('sha256') and old['sha256'] != digest.hexdigest():
            raise RuntimeError('Existing table checksum mismatch')
        old.update(sha256=digest.hexdigest(), bytes=out.stat().st_size)
        write_manifest(manifest, old)
        print('Already completed:', out, flush=True)
        return
    partial = out.with_suffix(out.suffix + '.part')
    fd = os.open(partial, os.O_RDWR | os.O_CREAT, 0o600)
    os.ftruncate(fd, len(head) + rows * 320)
    os.pwrite(fd, head, 0)
    completed = {}
    if manifest.exists():
        old = json.loads(manifest.read_text())
        if old['revision'] != revision or old['header_bytes'] != len(head):
            raise RuntimeError('Resume provenance mismatch')
        completed = {p['shard']: p for p in old['parts']}
    # Validate retained intervals before trusting a resume journal.
    for shard, part in list(completed.items()):
        digest = hashlib.sha256()
        offset = len(head) + shard * 2500012 * 320
        left = part['bytes']
        while left:
            data = os.pread(fd, min(left, 8 << 20), offset)
            if not data:
                break
            digest.update(data); offset += len(data); left -= len(data)
        if left or digest.hexdigest() != part['sha256']:
            del completed[shard]

    def download(part):
        dest = len(head) + part['shard'] * 2500012 * 320
        for attempt in range(4):
            try:
                digest = hashlib.sha256()
                first, length = part['source_start'], part['bytes']
                # Separate ranges bound retries to 64 MiB, rather than an entire tensor.
                for at in range(0, length, 64 << 20):
                    chunk = min(64 << 20, length - at)
                    with fetch(part['url'], first + at, first + at + chunk - 1) as response:
                        read = 0
                        while read < chunk:
                            data = response.read(min(1 << 20, chunk - read))
                            if not data:
                                raise RuntimeError('Incomplete ngram range')
                            written = os.pwrite(fd, data, dest + at + read)
                            if written != len(data):
                                raise RuntimeError('Short local write')
                            digest.update(data); read += len(data)
                return {k: v for k, v in part.items() if k != 'url'} | {'sha256': digest.hexdigest()}
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        raise AssertionError('Unreachable')

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(download, p) for p in parts if p['shard'] not in completed]
            for future in as_completed(futures):
                part = future.result()
                completed[part['shard']] = part
                report['parts'] = [completed[k] for k in sorted(completed)]
                write_manifest(manifest, report)
                print('Completed', len(completed), '/128 ngram tensors', flush=True)
        os.fsync(fd)
    finally:
        os.close(fd)
    if len(completed) != 128:
        raise RuntimeError('Incomplete table')
    partial.replace(out)
    digest = hashlib.sha256()
    with out.open('rb') as file:
        while data := file.read(16 << 20):
            digest.update(data)
    report['sha256'] = digest.hexdigest()
    report['bytes'] = out.stat().st_size
    write_manifest(manifest, report)
    print('Completed original BF16 ngram table', report['bytes'], report['sha256'], flush=True)


if __name__ == '__main__':
    main()
