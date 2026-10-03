"""Publish canary verdicts and latency without model output or private runtime paths."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_status import status, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    runs = []
    cohort = None
    for source in args.runs:
        report = json.loads(source.read_text())
        selected = report['selected_cases']
        expected = {c['id'] for c in selected}
        identity = (report['source_sha256'], report['grader_image_id'], expected)
        if cohort is not None and identity != cohort:
            raise RuntimeError('Paired canary deck, grader or selection differs')
        cohort = identity
        ids = [r['id'] for r in report['results']]
        if len(expected) != 30 or len(ids) != len(set(ids)) or not set(ids) <= expected:
            raise RuntimeError('Invalid frozen practical30 selection')
        rows = [{'id': r['id'], 'status': status(r),
                 'passed': r['verdict'].get('pass') if status(r) in ['passed', 'failed'] else None,
                 'finish_reason': r['response']['finish_reason'],
                 'completion_tokens': r['response']['usage'].get('completion_tokens'),
                 'elapsed_s': r['response']['total_s'],
                 'reasoning_chars': len(r['response'].get('reasoning', '')),
                 'input_sha256': r['input_sha256']} for r in report['results']]
        times = [r['elapsed_s'] for r in rows if r['status'] in ['passed', 'failed']]
        controls = report['controls']
        if set(controls) != expected or not all(v['positive']['pass'] and not v['negative']['pass']
                                                for v in controls.values()):
            raise RuntimeError('Canary controls incomplete or invalid')
        runs.append({'label': report['label'], 'source': source.name,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'cases_sha256': report['source_sha256'], 'grader_image_id': report['grader_image_id'],
            'runtime_fingerprint': report['runtime']['fingerprint'], 'protocol': report['protocol'],
            'controls': {'expected': 30, 'positive_passed': sum(v['positive']['pass'] for v in controls.values()),
                         'negative_rejected': sum(not v['negative']['pass'] for v in controls.values())},
            'coverage': summary(report['results'], 30),
            'completed_answer_median_s': statistics.median(times) if times else None,
            'attempt_wall_s': sum(r['elapsed_s'] for r in rows), 'results': rows})
    paired = []
    for i, left in enumerate(runs):
        for right in runs[i+1:]:
            if left['protocol'] != right['protocol']: continue
            a, b = ({r['id']: r['input_sha256'] for r in run['results']} for run in [left,right])
            shared = set(a) & set(b)
            if any(a[k] != b[k] for k in shared): raise RuntimeError('Paired input hashes differ')
            paired.append({'left':left['label'],'right':right['label'],'matching_input_hashes':len(shared)})
    args.out.write_text(json.dumps({'scope': 'Thirty original executable DevOps/Python function canaries; '
        'bounded local tasks, not SWE-bench or repository-scale agent performance.',
        'completion_policy': 'Only natural stops graded; all thirty required for full-cohort accuracy.',
        'runs': runs, 'paired_request_checks':paired}, indent=2)+'\n')


if __name__ == '__main__':
    main()
