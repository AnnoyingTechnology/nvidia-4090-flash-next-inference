"""Create bounded, deterministic public-code prompts using the target tokenizer."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, '/opt/strata/tools')
import strata_tokenizer as ST

ap = argparse.ArgumentParser()
ap.add_argument('--tokenizer', default='/work/packs/iq3s/tokenizer')
ap.add_argument('--out', default='/work/fixtures')
args = ap.parse_args()
tpath = Path(args.tokenizer)
vocab = json.loads((tpath / 'vocab.json').read_text())
tokens = [None] * len(vocab)
for token, index in vocab.items():
    tokens[index] = token
tok = ST.Tokenizer(tokens, (tpath / 'merges.txt').read_text().split('\n'),
                   json.loads((tpath / 'token_type.json').read_text()))
corpus = '\n'.join(Path('/opt/strata', name).read_text() for name in (
    'docs/HOW_IT_WORKS.md', 'src/program/generate.cpp', 'src/ngram/ple_reader.cpp',
    'serve/server.py', 'tools/iq_pack.py'))
# Chat markers inside source text must be literal data, not synthetic role boundaries.
corpus = corpus.replace('<|', '< |').replace('|>', '| >')
ids = tok.encode(corpus)
out = Path(args.out)
out.mkdir(exist_ok=True)
for k in (4, 32, 64, 128, 256):
    count = k * 1024 - 1024
    chosen = (ids * (count // len(ids) + 1))[:count]
    prompt = tok.decode(chosen) + '\nExplain the main components and their performance trade-offs in three sentences.'
    (out / f'prefill-{k}k.txt').write_text(prompt)
    (out / f'document-{k}k.txt').write_text(tok.decode(chosen))
    print(k, len(tok.encode(prompt)), flush=True)
