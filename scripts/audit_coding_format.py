"""Separately grade alternate fenced blocks; never overwrite the frozen score."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval import grade
from scripts.evaluation_status import status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', type=Path, required=True)
    ap.add_argument('--runs', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    cases = {c['id']: c for line in args.cases.read_text().splitlines() if (c := json.loads(line))}
    runs = []
    for source in args.runs:
        report = json.loads(source.read_text())
        if report['cases_sha256'] != hashlib.sha256(args.cases.read_bytes()).hexdigest():
            raise RuntimeError('Source deck differs')
        rows = []
        for row in report['results']:
            if status(row) != 'failed':
                continue
            blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', row['response']['content'], re.DOTALL)
            alternate = []
            for index, code in enumerate(blocks[1:], 2):
                verdict = grade(cases[row['id']]['data'], code)
                if type(verdict.get('pass')) is not bool:
                    raise RuntimeError('Alternate block grader failed')
                alternate.append({'block': index, 'passed': verdict['pass']})
            rows.append({'id': row['id'], 'complete_python_blocks': len(blocks),
                         'first_block_passed': False if blocks else None,
                         'alternate_blocks': alternate,
                         'error': row['verdict'].get('error')})
        runs.append({'source': source.name,
                     'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                     'grader_image_id': report['grader_image_id'], 'failures': rows})
    args.out.write_text(json.dumps({'scope': 'Diagnostic format audit; original first-block scores retained. '
        'No code repaired or prompts changed; alternate blocks graded separately.', 'runs': runs}, indent=2)+'\n')


if __name__ == '__main__':
    main()
