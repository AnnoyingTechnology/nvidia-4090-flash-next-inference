"""Fetch only the selected GSQ files; preserve existing files and verify pinned hashes."""
import concurrent.futures
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REV = 'ed59f92082b1e93c0e96d60a8b11aab089b52f09'
FILES = [
    ('IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf', 54817524224,
     '4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3'),
    ('IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf', 28800138432,
     '316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113'),
    ('mmproj-Qwen3.8-Flash-Next-BF16.gguf', 907543008,
     'b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0'),
]


def verify(path, size, expected):
    if path.stat().st_size != size:
        raise RuntimeError(f'Unexpected size: {path}; preserved for diagnosis')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise RuntimeError(f'Hash mismatch: {path}; preserved for diagnosis')


def fetch(item):
    name, size, digest = item
    target = ROOT / 'models/gsq-iq3_s' / Path(name).name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        verify(target, size, digest)
    else:
        partial = target.with_suffix(target.suffix + '.part')
        url = f'https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/resolve/{REV}/{name}'
        subprocess.run(['curl', '--fail', '--location', '--retry', '6', '--connect-timeout', '20',
                        '--continue-at', '-', '--output', str(partial), url], check=True)
        verify(partial, size, digest)
        partial.rename(target)
    print('Verified', target.name, flush=True)


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(fetch, FILES))
