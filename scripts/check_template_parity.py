"""Run in the selected Strata container against a pinned official template file."""
import argparse
import hashlib
import json
from pathlib import Path
from serve.frontend import ChatTemplate, effort_kwargs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--official', required=True)
    ap.add_argument('--live', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    live, official = ChatTemplate(args.live), ChatTemplate(args.official)
    checks = []
    fixtures = [
        ('user', [{'role': 'user', 'content': 'Hello'}], None),
        ('system-user', [{'role': 'system', 'content': 'You are an expert Python programmer.'},
                         {'role': 'user', 'content': 'Return Python code.'}], None),
        ('multiturn', [{'role': 'system', 'content': 'Help.'}, {'role': 'user', 'content': 'Hello'},
                       {'role': 'assistant', 'reasoning_content': 'Brief thought', 'content': 'Hi'},
                       {'role': 'user', 'content': 'Continue'}], None),
        ('tools', [{'role': 'user', 'content': 'Check status'}], [{'type': 'function', 'function': {
            'name': 'status', 'description': 'Read status', 'parameters': {
                'type': 'object', 'properties': {}, 'required': []}}}]),
        ('image', [{'role': 'user', 'content': [{'type': 'image', 'image': 'example.png'},
                                              {'type': 'text', 'text': 'Read the chart'}]}], None)]
    for effort in ['low', 'none']:
        for name, messages, tools in fixtures:
            a = live.render(messages, tools, **effort_kwargs(effort))
            b = official.render(messages, tools, **effort_kwargs(effort))
            checks.append({'name': name, 'effort': effort, 'identical_rendered_utf8': a == b,
                'live_sha256': hashlib.sha256(a.encode()).hexdigest(),
                'official_sha256': hashlib.sha256(b.encode()).hexdigest(),
                'actual_newlines': a.count('\n'), 'literal_backslash_n': a.count('\\n')})
    result = {'scope': 'Ten rendered prompt fixtures, low/off; no native inference or quota applied.',
              'official_template_sha256': hashlib.sha256(official.source.encode()).hexdigest(),
              'live_template_sha256': hashlib.sha256(live.source.encode()).hexdigest(), 'checks': checks}
    Path(args.out).write_text(json.dumps(result, indent=2)+'\n')
    if not all(c['identical_rendered_utf8'] for c in checks):
        raise RuntimeError('Rendered template mismatch')
    print('Rendered template parity:', len(checks), '/', len(checks))


if __name__ == '__main__':
    main()
