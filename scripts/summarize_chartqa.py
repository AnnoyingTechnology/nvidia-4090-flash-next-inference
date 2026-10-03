"""Retain source-annotation scores and derive a uniformly reviewed visual score."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = {
    'chartqa-human-937': {'expected': '2.1', 'reason':
        'Published label 10 counts the years. Blue line is about 28.2 in 2010 and 30.3 in 2019: about 2.1 points.'},
    'chartqa-human-74': {'expected': '302.38', 'reason':
        'Image displays 302.38%. Published 3.0238 stores the corresponding fraction.'},
    'chartqa-human-1081': {'exclude': True, 'reason':
        'Chart gives population shares summing to 100%, not absolute population; question omits the requested unit.'},
    'chartqa-human-834': {'category': 'lookup', 'reason':
        'Product means a software category. A separately frozen multiplication task (index 41) was added.'}}


def number(value):
    if type(value) in (int, float):
        return Decimal(str(value))
    if not isinstance(value, str):
        return None
    text = value.strip()
    # Accept units and presentation only, not extraction of arbitrary embedded numbers.
    text = re.sub(r'\s*\(\d{4}\)\s*$', '', text)
    text = re.sub(r'\s*(%|points?|years?|t)\s*$', '', text, flags=re.IGNORECASE)
    if re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?', text):
        text = text.replace(',', '')
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?', text):
        return Decimal(text)
    ratio = re.fullmatch(r'(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)', text)
    if ratio and Decimal(ratio[2]):
        return Decimal(ratio[1])/Decimal(ratio[2])
    return None


def correct(answer, expected):
    numeric = number(expected)
    if numeric is not None:
        actual = number(answer)
        if actual is None:
            return False
        return abs(actual-numeric) <= abs(numeric)*Decimal('.05') if numeric else actual == 0
    if not isinstance(answer, str):
        return False
    answer, expected = answer.strip().casefold(), expected.strip().casefold()
    if expected in ['yes', 'no']:
        return bool(re.fullmatch(expected+r'(?:\s*[,.:;]\s*.+)?', answer))
    return answer == expected


def main():
    decks = ['combined20.jsonl', 'multiplication1.jsonl']
    cases = [json.loads(line) for name in decks for line in (ROOT/'eval/chartqa'/name).read_text().splitlines()]
    sources = {'IQ3_S': ['chartqa20-iq3s-low.json', 'chartqa-multiplication1-iq3s-low.json'],
               'Terra': ['chartqa15-terra-low.json', 'chartqa-arithmetic5-terra-low.json', 'chartqa-multiplication1-terra-low.json'],
               'Sol': ['chartqa15-sol-low.json', 'chartqa-arithmetic5-sol-low.json', 'chartqa-multiplication1-sol-low.json']}
    report = {'audit': AUDIT, 'audit_scope': 'Manual source-image review after first responses; not blind. '
        'All corrections/exclusions applied to every model; original outputs and scores retained.',
        'semantic_method': 'Exact categories/leading yes-no; numeric strings, grouped thousands, ratios and '
        'percent/year/point/tonne units accepted; numeric tolerance 5%. No arbitrary number extraction.',
        'scope': '21 frozen published human-chart questions; 20 reviewed scorable cases. '
        'Not the official full ChartQA score or proof of broad model parity.',
        'scorer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'runs': []}
    for label, names in sources.items():
        reports = [json.loads((ROOT/'results'/name).read_text()) for name in names]
        rows = [row for source in reports for row in source['results']]
        by_id = {row['id']: row for row in rows}
        if len(rows) != len(cases) or set(by_id) != {c['id'] for c in cases}:
            raise RuntimeError('Missing or duplicate model response: '+label)
        derived = []
        for case in cases:
            row = by_id[case['id']]
            if (row['image_sha256'] != case['image_sha256'] or
                row['prompt_sha256'] != hashlib.sha256(case['prompt'].encode()).hexdigest() or
                row['expected'] != case['expected']):
                raise RuntimeError('Request provenance mismatch')
            audit = AUDIT.get(case['id'], {})
            actual = row['verdict'].get('answer')
            answer = actual.get('answer') if isinstance(actual, dict) else None
            expected = audit.get('expected', case['expected']['answer'])
            derived.append({'id': case['id'], 'category': audit.get('category', case['category']),
                'answer': answer, 'source_expected': case['expected']['answer'], 'reviewed_expected': expected,
                'excluded_from_reviewed': audit.get('exclude', False),
                'raw_annotation_match': row['verdict']['strict_correct'],
                'reviewed_correct': correct(answer, expected),
                'transport_error': 'error' in row['response'], 'capped': row['response']['finish_reason']=='length'})
        eligible = [r for r in derived if not r['excluded_from_reviewed']]
        report['runs'].append({'label': label, 'model': reports[0]['protocol']['model'], 'effort': 'low',
            'sources': {name: hashlib.sha256((ROOT/'results'/name).read_bytes()).hexdigest() for name in names},
            'summary': {'raw_annotation_correct': sum(r['raw_annotation_match'] for r in derived),
                'raw_total': len(derived), 'reviewed_correct': sum(r['reviewed_correct'] for r in eligible),
                'reviewed_total': len(eligible),
                'arithmetic_correct': sum(r['reviewed_correct'] for r in eligible if r['category'].startswith('arithmetic/')),
                'arithmetic_total': sum(r['category'].startswith('arithmetic/') for r in eligible),
                'transport_errors': sum(r['transport_error'] for r in derived), 'capped': sum(r['capped'] for r in derived)},
            'results': derived})
    (ROOT/'results/chartqa-comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    for run in report['runs']:
        print(run['label'], run['summary'])


if __name__ == '__main__':
    main()
