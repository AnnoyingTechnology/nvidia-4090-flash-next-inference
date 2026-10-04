"""Derive common image-content scores without replacing original typed verdicts."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ['vision15-iq3s-none.json', 'vision15-iq3s-low.json',
           'vision15-luna-low.json', 'vision15-terra-low.json', 'vision15-sol-low.json']
PERCENT_FIELDS = {'use_percent', 'busy_percent'}


def equivalent(actual, expected, field=None):
    if isinstance(expected, bool):
        return type(actual) is bool and actual == expected
    if type(expected) in (int, float):
        if type(actual) in (int, float):
            return actual == expected
        if not isinstance(actual, str):
            return False
        number = actual.strip()
        if field in PERCENT_FIELDS and number.endswith('%'):
            number = number[:-1].strip()
        if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', number):
            return False
        return Decimal(number) == Decimal(str(expected))
    if isinstance(expected, str):
        return isinstance(actual, str) and actual.strip().casefold() == expected.strip().casefold()
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            equivalent(a, e, field) for a, e in zip(actual, expected))
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(
            equivalent(actual[k], v, k) for k, v in expected.items())
    return actual == expected


def score(content, expected):
    plain_json = True
    try:
        actual = json.loads(content)
    except json.JSONDecodeError:
        plain_json = False
        fenced = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', content.strip(), re.DOTALL)
        try:
            actual = json.loads(fenced[1]) if fenced else None
        except json.JSONDecodeError:
            actual = None
    fields = {k: isinstance(actual, dict) and k in actual and equivalent(actual[k], v, k)
              for k, v in expected.items()}
    return {'content_correct': equivalent(actual, expected), 'plain_json': plain_json,
            'field_correct': fields, 'answer': actual}


def summarize(deck, reports):
    cases = [json.loads(line) for line in deck.read_text().splitlines()]
    expected_ids = {c['id'] for c in cases}
    digest = hashlib.sha256(deck.read_bytes()).hexdigest()
    summaries = []
    for report_path in reports:
        report = json.loads(report_path.read_text())
        if report['protocol']['cases_sha256'] != digest:
            raise ValueError('Deck provenance mismatch: ' + str(report_path))
        rows = {r['id']: r for r in report['results']}
        if set(rows) != expected_ids or len(report['results']) != len(cases):
            raise ValueError('Incomplete or duplicated run: ' + str(report_path))
        derived = []
        for case in cases:
            row = rows[case['id']]
            if (row['image_sha256'] != case['image_sha256'] or
                row['prompt_sha256'] != hashlib.sha256(case['prompt'].encode()).hexdigest() or
                row['expected'] != case['expected']):
                raise ValueError('Case provenance mismatch: ' + case['id'])
            verdict = score(row['response'].get('content', ''), case['expected'])
            derived.append({'id': case['id'], 'category': case['category'], **verdict,
                            'original_typed_contract_correct': row['verdict']['strict_correct'],
                            'ttft_s': row['response'].get('ttft_s'), 'total_s': row['response'].get('total_s')})
        first = [r['ttft_s'] for r in derived if r['ttft_s'] is not None]
        summaries.append({'source': report_path.name,
            'source_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'model': report['protocol']['model'], 'effort': report['protocol']['effort'],
            'summary': {'image_content_correct': sum(r['content_correct'] for r in derived),
                'total': len(derived),
                'field_correct': sum(sum(r['field_correct'].values()) for r in derived),
                'field_total': sum(len(c['expected']) for c in cases),
                'typed_contract_correct': report['summary']['strict_correct'],
                'plain_json': sum(r['plain_json'] for r in derived),
                'access_or_transport_errors': report['summary']['access_or_transport_errors'],
                'capped': report['summary']['capped'],
                'first_token_median_s': statistics.median(first) if first else None,
                'first_token_max_s': max(first, default=None)}, 'results': derived})
    return {'cases_sha256': digest, 'scorer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'method': 'Post-run derivation, uniformly applied to every original response. Exact object keys; '
                  'typed booleans; exact numeric strings accepted; trailing % accepted only for '
                  'use_percent/busy_percent. Original typed verdicts and responses remain unchanged.',
        'reason': 'Frozen prompts request displayed numbers but do not mandate numeric JSON types.',
        'runs': summaries}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', type=Path, default=ROOT/'fixtures/vision15/cases.jsonl')
    ap.add_argument('--results', type=Path, default=ROOT/'results')
    ap.add_argument('--out', type=Path, default=ROOT/'results/vision15-comparison.json')
    ap.add_argument('--reports', nargs='+', default=REPORTS, help='Report names under --results')
    args = ap.parse_args()
    report = summarize(args.cases, [args.results/name for name in args.reports])
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    for run in report['runs']:
        print(run['model'], run['effort'], run['summary'])


if __name__ == '__main__':
    main()
