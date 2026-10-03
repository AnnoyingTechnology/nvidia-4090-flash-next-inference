"""Freeze a small published human-authored chart screen before any model responses."""
import hashlib
import json
from pathlib import Path
import random
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = '044eabfc306abfe9340c5741f0093aefc5973d06'
BASE = f'https://raw.githubusercontent.com/vis-nlp/ChartQA/{REVISION}/'
SEED = 31191


def main():
    out = ROOT/'eval/chartqa'
    out.mkdir(parents=True, exist_ok=True)
    questions = out/'test_human.json'
    if not questions.exists():
        questions.write_bytes(urllib.request.urlopen(BASE+'ChartQA%20Dataset/test/test_human.json', timeout=30).read())
    rows = json.loads(questions.read_text())
    groups = {'lookup': [], 'comparison': [], 'counting': []}
    for index, row in enumerate(rows):
        query = row['query'].lower()
        if re.search(r'\b(sum|difference|ratio|average|median|product|subtract|multiply|divid|decrease|increase)\w*\b', query):
            continue
        if query.startswith('how many') and 'percent' not in query and 'more' not in query:
            group = 'counting'
        elif re.search(r'\b(highest|lowest|largest|smallest|least|most|peak|bottom|top|greater|lower)\b', query):
            group = 'comparison'
        else:
            group = 'lookup'
        groups[group].append((index, row))
    rng = random.Random(SEED)
    selected, images = [], set()
    for category, candidates in groups.items():
        rng.shuffle(candidates)
        for index, row in candidates:
            if row['imgname'] in images:
                continue
            selected.append((category, index, row))
            images.add(row['imgname'])
            if sum(c == category for c, _, _ in selected) == 5:
                break
    assert len(selected) == 15
    deck, provenance = [], []
    for category, index, row in selected:
        image = out/'png'/row['imgname']
        image.parent.mkdir(parents=True, exist_ok=True)
        image_url = BASE + urllib.parse.quote('ChartQA Dataset/test/png/'+row['imgname'])
        if not image.exists():
            image.write_bytes(urllib.request.urlopen(image_url, timeout=30).read())
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        prompt = row['query'] + ' Return exactly one JSON object with the key answer and a short string value. No Markdown.'
        deck.append({'id': 'chartqa-human-'+str(index), 'category': category,
            'image': str(image.relative_to(ROOT)), 'image_sha256': digest,
            'prompt': prompt, 'expected': {'answer': row['label']},
            'source': {'repository': 'vis-nlp/ChartQA', 'revision': REVISION, 'human_test_index': index}})
        provenance.append({'id': deck[-1]['id'], 'category': category, 'human_test_index': index,
            'image_url': image_url, 'image_sha256': digest,
            'query_sha256': hashlib.sha256(row['query'].encode()).hexdigest(),
            'label_sha256': hashlib.sha256(row['label'].encode()).hexdigest()})
    target = out/'cases.jsonl'
    content = ''.join(json.dumps(row)+'\n' for row in deck)
    if target.exists() and target.read_text() != content:
        raise RuntimeError('Refuse to replace a different frozen deck')
    target.write_text(content)
    manifest = {'repository': 'vis-nlp/ChartQA', 'revision': REVISION,
        'human_test_sha256': hashlib.sha256(questions.read_bytes()).hexdigest(),
        'cases_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'seed': SEED,
        'selection': 'Five lookup, five comparison, five counting; unique images; no arithmetic-heavy queries; '
                     'pinned source order and seeded shuffle. Chosen before model requests.',
        'scope': 'Small human ChartQA screen, not the full benchmark or general vision qualification.',
        'redistribution': 'Dataset images/questions remain local; published provenance permits source reconstruction.',
        'cases': provenance}
    (ROOT/'results/chartqa15-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Frozen:', [(c, i, r['label']) for c, i, r in selected])
    # A separately frozen steering follow-up covers ordinary visual arithmetic.
    arithmetic = []
    rng = random.Random(38471)
    for operation, pattern in [('addition', r'\bsum\b'), ('subtraction', r'\bdifference\b'),
                               ('multiplication', r'\bproduct\b'), ('division', r'\bratio\b'),
                               ('average', r'\baverage\b')]:
        candidates = [(index, row) for index, row in enumerate(rows)
                      if re.search(pattern, row['query'], re.IGNORECASE) and row['imgname'] not in images]
        index, row = rng.choice(candidates)
        images.add(row['imgname'])
        image = out/'png'/row['imgname']
        if not image.exists():
            image.write_bytes(urllib.request.urlopen(BASE+urllib.parse.quote(
                'ChartQA Dataset/test/png/'+row['imgname']), timeout=30).read())
        arithmetic.append({'id': 'chartqa-human-'+str(index), 'category': 'arithmetic/'+operation,
            'image': str(image.relative_to(ROOT)), 'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
            'prompt': row['query']+' Return exactly one JSON object with the key answer and a short string value. No Markdown.',
            'expected': {'answer': row['label']},
            'source': {'repository': 'vis-nlp/ChartQA', 'revision': REVISION, 'human_test_index': index}})
    for name, items in [('arithmetic5', arithmetic), ('combined20', deck+arithmetic)]:
        target = out/(name+'.jsonl')
        content = ''.join(json.dumps(row)+'\n' for row in items)
        if target.exists() and target.read_text() != content:
            raise RuntimeError('Refuse to replace a different frozen arithmetic deck')
        target.write_text(content)
    arithmetic_manifest = {'revision': REVISION, 'seed': 38471,
        'selection': 'One seeded human test question per operation, distinct images, selected before arithmetic runs.',
        'cases_sha256': hashlib.sha256((out/'arithmetic5.jsonl').read_bytes()).hexdigest(),
        'combined_sha256': hashlib.sha256((out/'combined20.jsonl').read_bytes()).hexdigest(),
        'cases': [{k: v for k, v in case.items() if k not in ['prompt', 'expected', 'image']} for case in arithmetic]}
    (ROOT/'results/chartqa-arithmetic5-manifest.json').write_text(json.dumps(arithmetic_manifest, indent=2)+'\n')
    print('Frozen arithmetic:', [(c['category'], c['id'], c['expected']) for c in arithmetic])
    # The word "product" in index 834 describes software, not multiplication.
    # Keep its original request/results and add an actual multiplication task.
    row = rows[41]
    image = out/'png'/row['imgname']
    if not image.exists():
        image.write_bytes(urllib.request.urlopen(BASE+urllib.parse.quote(
            'ChartQA Dataset/test/png/'+row['imgname']), timeout=30).read())
    case = {'id': 'chartqa-human-41', 'category': 'arithmetic/multiplication',
        'image': str(image.relative_to(ROOT)), 'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
        'prompt': row['query']+' Return exactly one JSON object with the key answer and a short string value. No Markdown.',
        'expected': {'answer': row['label']},
        'source': {'repository': 'vis-nlp/ChartQA', 'revision': REVISION, 'human_test_index': 41}}
    (out/'multiplication1.jsonl').write_text(json.dumps(case)+'\n')


if __name__ == '__main__':
    main()
