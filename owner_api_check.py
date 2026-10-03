"""Check effective profile defaults, client overrides and the real HTTP JSON contract."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request
from bench import request


def http(url, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url + path, data, {'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return {'status': response.status, 'body': json.load(response)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--profile', required=True)
    ap.add_argument('--vision', action='store_true')
    ap.add_argument('--url', default='http://127.0.0.1:19623')
    args = ap.parse_args()
    profile = Path('profiles') / (args.profile + '.json')
    report = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'profile': args.profile, 'profile_sha256': hashlib.sha256(profile.read_bytes()).hexdigest(),
              'checks': []}

    def check(name, passed, evidence):
        report['checks'].append({'name': name, 'passed': bool(passed), 'evidence': evidence})
        report['summary'] = {'passed': sum(x['passed'] for x in report['checks']),
                             'total': len(report['checks'])}
        Path(args.out).write_text(json.dumps(report, indent=2) + '\n')
        print(name, bool(passed), flush=True)
        if not passed:
            raise RuntimeError('Owner profile check failed: ' + name)

    status = http(args.url, '/v1/status')
    check('model-context-vision', status['status'] == 200 and status['body']['model'] == 'Qwen3.8-Flash-Next'
          and status['body']['context']['native'] == 262144
          and status['body']['vision']['enabled'] == args.vision, status)
    props = http(args.url, '/props?model=ulmus')
    params = props['body']['default_generation_settings']['params']
    expected = {'temperature': 1, 'top_p': .95, 'top_k': 20, 'min_p': 0,
                'presence_penalty': 0, 'repeat_penalty': 1, 'n_predict': 8192}
    check('sampling-and-output-defaults', props['status'] == 200 and
          all(params.get(k) == v for k, v in expected.items()), props)
    settings = http(args.url, '/settings')
    check('low-reasoning-default', settings['status'] == 200 and
          settings['body']['defaults'] == {'reasoning_effort': 'low', 'max_tokens': 8192}, settings)

    payload = {'model': 'ulmus', 'messages': [{'role': 'user', 'content':
        'In one sentence explain why nginx -t should precede reloading nginx.'}], 'stream': True,
        'stream_options': {'include_usage': True}}
    response = request(args.url, payload)
    check('implicit-low-request', response['finish_reason'] == 'stop' and response['reasoning'].strip()
          and response['content'].strip(), {'payload': payload, 'response': response})
    override = {**payload, 'messages': [{'role': 'user', 'content':
        'Return exactly READY and no other characters.'}], 'reasoning_effort': 'none',
        'temperature': 0, 'max_tokens': 32}
    response = request(args.url, override)
    check('explicit-none-override', response['finish_reason'] == 'stop' and not response['reasoning'].strip()
          and response['content'].strip() == 'READY', {'payload': override, 'response': response})

    schema = {'type': 'object', 'properties': {'action': {'enum': ['validate']},
              'apply': {'type': 'boolean', 'const': False}}, 'required': ['action', 'apply'],
              'additionalProperties': False}
    formatted = {**payload, 'messages': [{'role': 'user', 'content':
        'Describe a validation-only deployment plan. action must be validate and apply must be false.'}],
        'max_tokens': 2048, 'response_format': {'type': 'json_schema',
            'json_schema': {'name': 'validation_plan', 'strict': True, 'schema': schema}}}
    response = request(args.url, formatted)
    check('validated-json-schema-sse', json.loads(response['content']) == {'action': 'validate', 'apply': False}
          and response['finish_reason'] == 'stop', {'payload': formatted, 'response': response})
    invalid = {**formatted, 'stream': False, 'response_format': {'type': 'json_schema',
        'json_schema': {'name': 'invalid', 'schema': {'type': 'array'}}}}
    response = http(args.url, '/v1/chat/completions', invalid)
    check('invalid-root-schema-rejected', response['status'] == 400, response)
    combined = {**formatted, 'stream': False, 'tools': [{'type': 'function', 'function':
        {'name': 'read_status', 'parameters': {'type': 'object', 'properties': {}}}}]}
    response = http(args.url, '/v1/chat/completions', combined)
    check('unsupported-format-plus-tools-rejected', response['status'] == 400, response)
    bounded = {**override, 'messages': [{'role': 'user', 'content':
        'Explain DNS resolution in 1000 words.'}], 'max_tokens': 16}
    response = request(args.url, bounded)
    check('explicit-output-cap-override', response['finish_reason'] == 'length'
          and response['usage']['completion_tokens'] <= 16, {'payload': bounded, 'response': response})


if __name__ == '__main__':
    main()
