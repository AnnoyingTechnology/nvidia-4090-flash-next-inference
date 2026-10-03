"""Publish completion-aware coding evidence without benchmark questions or tests."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics

from evaluation_status import status, summary

ROOT = Path(__file__).resolve().parents[1]


def summarize(deck, sources, legacy_selections=None):
    digest = hashlib.sha256(deck.read_bytes()).hexdigest()
    cases = {c['id']: c for line in deck.read_text().splitlines()
             if (c := json.loads(line))['suite'] == 'lcb-v6-screen'}
    runs = []
    for source in sources:
        report = json.loads(source.read_text())
        if report['cases_sha256'] != digest:
            raise ValueError('Coding deck provenance mismatch: ' + source.name)
        selected = report.get('selected_cases')
        if selected:
            expected_ids = {r['id'] for r in selected}
            selection_source = 'Run selected_cases metadata'
        else:
            legacy = (legacy_selections or {}).get(source.name)
            if not legacy:
                raise ValueError('Explicit legacy selection required: ' + source.name)
            expected_ids = set(legacy['ids'])
            selection_source = legacy['evidence']
        ids = [r['id'] for r in report['results']]
        if len(set(ids)) != len(ids) or not set(ids) <= expected_ids or not expected_ids <= set(cases):
            raise ValueError('Invalid selected cases: ' + source.name)
        rows = []
        grouped = defaultdict(list)
        for row in report['results']:
            response = row['response']
            state = status(row)
            difficulty = cases[row['id']]['data']['difficulty']
            grouped[difficulty].append(row)
            rows.append({'id': row['id'], 'difficulty': difficulty, 'status': state,
                'passed': row['verdict'].get('pass') if state in ['passed', 'failed'] else None,
                'finish_reason': response['finish_reason'],
                'completion_tokens': response['usage'].get('completion_tokens'),
                'elapsed_s': response['total_s'], 'reasoning_chars': len(response.get('reasoning', '')),
                'answer_chars': len(response.get('content', '')),
                'decode_tok_s': response.get('timings', {}).get('predicted_per_second'),
                'input_sha256': row['input_sha256'], 'token_cap': row['token_cap']})
        times = [r['elapsed_s'] for r in rows if r['status'] in ['passed', 'failed']]
        controls = report['controls']
        runs.append({'source': source.name,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'protocol': report['protocol'], 'cases_sha256': digest,
            'selection_source': selection_source,
            'runtime_fingerprint': report.get('runtime', {}).get('fingerprint'),
            'runtime_identity_status': 'captured' if report.get('runtime') else
                'Historical launch evidence only; no runtime fingerprint captured by that evaluator version',
            'grader_image_id': report['grader_image_id'],
            'grader_controls': {'correct_program_passed': controls['correct_program']['pass'],
                               'public_only_program_rejected': not controls['public_only_program']['pass']},
            'coverage': summary(report['results'], len(expected_ids)),
            'difficulty': {key: summary(value, sum(cases[i]['data']['difficulty'] == key for i in expected_ids))
                           for key, value in grouped.items()},
            'completed_answer_median_s': statistics.median(times) if times else None,
            'attempt_wall_s': sum(r['elapsed_s'] for r in rows), 'results': rows})
    return {'scope': 'Frozen 24-case LiveCodeBench v6 screen; a diagnostic subset, never an official score.',
            'completion_policy': 'Capped runs are incomplete, neither correct nor incorrect. Accuracy is withheld '
                'until every selected case completes naturally and is graded. Survivor counts are diagnostics '
                'and cannot replace the full-cohort score. No forced thinking closure is used.',
            'scorer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'runs': runs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', type=Path, default=ROOT/'eval/cases.jsonl')
    ap.add_argument('--runs', nargs='+', type=Path, required=True)
    ap.add_argument('--out', type=Path, default=ROOT/'results/coding-checkpoint.json')
    ap.add_argument('--legacy-selections', type=Path)
    args = ap.parse_args()
    legacy = json.loads(args.legacy_selections.read_text()) if args.legacy_selections else None
    report = summarize(args.cases, args.runs, legacy)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    for run in report['runs']:
        print(run['source'], run['coverage'])


if __name__ == '__main__':
    main()
