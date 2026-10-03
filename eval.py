"""Paired, resumable quality evaluation; generated programs execute only in Docker."""
import argparse
from collections import defaultdict
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

from bench import request
from scripts.evaluation_status import unfinished, summary

GRADER = 'ulmus/eval:lcb-28fef95'
PROTOCOL = {'nonthinking': {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0.0,
                           'presence_penalty': 1.5, 'repetition_penalty': 1.0, 'seed': 42},
            'thinking': {'temperature': 1.0, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0,
                         'presence_penalty': 0.0, 'repetition_penalty': 1.0, 'seed': 42},
            'aime_tokens': 32768, 'mmlu_tokens': 64, 'code_tokens': 32768, 'version': 3,
            'completion_policy': 'Only natural stop is graded; full-cohort accuracy requires every case complete'}


def grade(problem, code, image=GRADER):
    name = 'ulmus-code-eval-' + uuid.uuid4().hex[:12]
    command = ['docker', 'run', '--rm', '--init', '--interactive', '--name', name,
               '--network', 'none', '--read-only', '--cap-drop', 'ALL',
               '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m',
               '--security-opt', 'no-new-privileges', '--memory', '512m',
               '--memory-swap', '512m', '--cpus', '1', '--pids-limit', '64',
               '--user', '1000:1000', image]
    try:
        run = subprocess.run(command, input=json.dumps({'problem': problem, 'code': code}),
                             text=True, capture_output=True, timeout=180)
        if run.returncode:
            raise RuntimeError(run.stderr[-2000:] or f'Grader exited {run.returncode}')
        return json.loads(run.stdout)
    except subprocess.TimeoutExpired:
        subprocess.run(['docker', 'rm', '--force', name], capture_output=True, timeout=15)
        return {'error': 'isolated grader exceeded 180 seconds'}


def control():
    problem = {'public_test_cases': json.dumps([{'input': '2 3\n', 'output': '5\n'}]),
               'private_test_cases': json.dumps([{'input': '40 2\n', 'output': '42\n'}]),
               'metadata': '{}'}
    good = grade(problem, 'print(sum(map(int, input().split())))')
    wrong = grade(problem, 'print(5)')
    if not good['pass'] or wrong['pass']:
        raise RuntimeError(f'Grader controls failed: good={good}, wrong={wrong}')
    return {'correct_program': good, 'public_only_program': wrong}


def prompt(case, effort='high'):
    row, suite = case['data'], case['suite']
    if suite == 'aime25':
        return ([{'role': 'system', 'content': 'Solve the mathematics problem carefully. '
                  'Give your final integer answer in \\boxed{...}.'},
                 {'role': 'user', 'content': row['problem']}], effort, PROTOCOL['aime_tokens'])
    if suite == 'mmlupro':
        choices = '\n'.join(f'{chr(65+i)}. {v}' for i, v in enumerate(row['options']))
        return ([{'role': 'system', 'content': 'Choose the correct answer. Reply with only '
                  'its single uppercase letter, without explanation.'},
                 {'role': 'user', 'content': row['question'] + '\n\n' + choices}],
                'none', PROTOCOL['mmlu_tokens'])
    starter = row['starter_code']
    formatting = ('Use the following starter code to implement the solution.' if starter else
                  'Read inputs from stdin, solve the problem, and write the answer to stdout. '
                  'Do not directly test on the sample inputs.')
    body = (f"### Question:\n{row['question_content']}\n\n### Format:\n{formatting}\n"
            f"Enclose the complete solution in a Python code block.\n```python\n"
            f"{starter or '# YOUR CODE HERE'}\n```\n\n### Answer:\n")
    return ([{'role': 'system', 'content': 'You are an expert Python programmer. Generate '
              'a correct Python program matching the specification and passing all tests.'},
             {'role': 'user', 'content': body}], effort, PROTOCOL['code_tokens'])


def score(case, response):
    incomplete = unfinished(response)
    if incomplete:
        return incomplete
    content = response['content'].strip()
    row, suite = case['data'], case['suite']
    if suite == 'aime25':
        values = re.findall(r'\\boxed\{\s*(\d+)\s*\}', content)
        answer = values[-1] if values else (content if re.fullmatch(r'\d+', content) else None)
        return {'pass': answer is not None and int(answer) == int(row['answer']),
                'answer': answer, 'expected': row['answer']}
    if suite == 'mmlupro':
        # Strict requested format; keep semantic extraction separate for diagnosis.
        exact = content if re.fullmatch(r'[A-J]', content) else None
        return {'pass': exact == row['answer'], 'answer': exact, 'expected': row['answer'],
                'category': row['category']}
    blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', content, re.DOTALL)
    if not blocks:
        return {'pass': False, 'error': 'No complete Python code block'}
    return grade(row, blocks[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    ap.add_argument('--cases', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--suites', nargs='*')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--control-only', action='store_true')
    ap.add_argument('--import-from', help='Reuse results only when the exact request hash and source deck match')
    ap.add_argument('--effort', choices=['none', 'low', 'medium', 'high'], default='low')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--presence-penalty', type=float,
                    help='Separate thinking-sampler experiment; never changes the frozen prompt')
    ap.add_argument('--code-tokens', type=int, default=32768,
                    help='Completion budget for coding cases, recorded in the run protocol')
    ap.add_argument('--ids', nargs='*')
    args = ap.parse_args()
    if args.code_tokens <= 0:
        ap.error('--code-tokens must be positive')
    PROTOCOL['code_tokens'] = args.code_tokens
    PROTOCOL['effort'] = args.effort
    for mode in ['nonthinking', 'thinking']:
        PROTOCOL[mode]['seed'] = args.seed
    if args.presence_penalty is not None:
        if args.effort == 'none' or not 0 <= args.presence_penalty <= 2:
            ap.error('--presence-penalty is a thinking experiment in the range [0, 2]')
        PROTOCOL['thinking']['presence_penalty'] = args.presence_penalty
    controls = control()
    if args.control_only:
        print(json.dumps(controls, indent=2))
        return
    case_path, path = Path(args.cases), Path(args.out)
    digest = hashlib.sha256(case_path.read_bytes()).hexdigest()
    grader_id = subprocess.check_output(['docker', 'image', 'inspect', GRADER,
                                         '--format', '{{.Id}}'], text=True).strip()
    report = {'label': args.label, 'protocol': PROTOCOL, 'cases_sha256': digest,
              'grader_image_id': grader_id, 'controls': controls, 'results': [],
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if path.exists():
        report = json.loads(path.read_text())
        if (report['label'], report['cases_sha256'], report['protocol'], report['grader_image_id']) != (
                args.label, digest, PROTOCOL, grader_id):
            raise RuntimeError('Resume provenance does not match')
    completed = {(r['suite'], r['id']) for r in report['results']}
    cases = [json.loads(line) for line in case_path.read_text().splitlines()]
    cases = [c for c in cases if not args.suites or c['suite'] in args.suites]
    if args.ids:
        cases = [c for c in cases if str(c['id']) in args.ids]
    if args.limit:
        cases = cases[:args.limit]
    expected = defaultdict(int)
    for case in cases:
        expected[case['suite']] += 1
    selected = {(c['suite'], c['id']) for c in cases}
    previous_selection = {(c['suite'], c['id']) for c in report.get('selected_cases', [])}
    if completed - selected or (previous_selection and previous_selection != selected):
        raise RuntimeError('Resume case selection differs')
    report['selected_cases'] = [{'suite': c['suite'], 'id': c['id']} for c in cases]
    prior = {}
    if args.import_from:
        old = json.loads(Path(args.import_from).read_text())
        if old['cases_sha256'] != digest or old['grader_image_id'] != grader_id:
            raise RuntimeError('Import source/grader differs')
        prior = {(r['suite'], r['id']): r for r in old['results']}
    for case in cases:
        if (case['suite'], case['id']) in completed:
            continue
        messages, effort, tokens = prompt(case, args.effort)
        sampling = PROTOCOL['nonthinking' if effort == 'none' else 'thinking']
        payload = {'model': 'ulmus', 'messages': messages, **sampling,
                   'max_tokens': tokens, 'reasoning_effort': effort, 'stream': True,
                   'stream_options': {'include_usage': True}}
        input_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        old = prior.get((case['suite'], case['id']))
        if old and old['input_sha256'] == input_hash:
            response = old['response']
            verdict = unfinished(response) or old['verdict']
        else:
            response = request(args.url, payload)
            try:
                verdict = score(case, response)
            except Exception as error:
                # An evaluator error stops the run; do not count it as a model failure.
                verdict = {'error': str(error)}
        item = {'suite': case['suite'], 'id': case['id'], 'verdict': verdict,
                'input_sha256': input_hash,
                'response': response, 'token_cap': tokens}
        if old and old['input_sha256'] == input_hash:
            item['imported_from'] = str(args.import_from)
        report['results'].append(item)
        groups = defaultdict(list)
        for result in report['results']:
            groups[result['suite']].append(result)
        report['scores'] = {s: summary(rows, expected[s]) for s, rows in groups.items()}
        path.write_text(json.dumps(report, indent=2))
        print(case['suite'], case['id'], verdict.get('pass'),
              response['usage'].get('completion_tokens'), response['finish_reason'],
              report['scores'][case['suite']], flush=True)
        if 'pass' not in verdict and verdict.get('status') != 'incomplete':
            raise RuntimeError(verdict['error'])


if __name__ == '__main__':
    main()
