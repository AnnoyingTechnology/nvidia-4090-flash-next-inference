"""Export an explicit evidence set; private machine captures/dataset payloads stay local."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/public'
FILES = [
    'owner-text-perf.json', 'owner-vision-perf.json', 'second-round-summary.json',
    'ple-iq4nl-perf.json', 'ple-bf16-perf.json', 'ple-iq4nl-confirmation-perf.json',
    'ple-bf16-gpuvision-perf.json', 'vision-iq3s-gpu-perf.json',
    'resume-iq3s-cpuquant.json', 'resume-iq3s-confirmation.json',
    'vision-owner-defaults.json', 'practical-iq3s-iq4nl-low.json',
    'practical-q4-iq4nl-low.json', 'practical-iq3s-bf16-low.json',
    'ple-iq4nl-agents.json', 'q4-agents.json', 'ple-bf16-agents.json',
    'quality-iq3s-v2-256k.json', 'conversations-iq3s.json',
    'sampled-iq3s-off.json', 'sampled-q4-report.json',
    'strata-q4-pfauto.json', 'strata-iq3s-pfauto.json',
]


def clean(value):
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items() if key != 'telemetry'}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r'/home/[^/\s]+/[^\s"\n]+', '<local-path>', value)
        return re.sub(r'(?<![\d.])192\.168\.\d+\.\d+(?![\d.])', '<host-address>', value)
    return value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {'method': 'Explicit allowlist; remove per-sample telemetry and local host paths',
                'private_exclusions': ['Host/container captures', 'Non-synthetic benchmark question/test payloads',
                                       'Downloaded binaries and model files', 'Private deployment logs'],
                'sources': {}}
    for name in FILES:
        source = ROOT / 'results' / name
        if not source.exists():
            continue
        payload = json.dumps(clean(json.loads(source.read_text())), indent=2) + '\n'
        target = OUT / name
        target.write_text(payload)
        manifest['sources'][name] = {'private_original_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                                    'public_export_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    summary = {}
    for name in ['owner-text-api.json', 'owner-vision-api.json']:
        source = ROOT / 'results' / name
        data = json.loads(source.read_text())
        summary[name] = {'profile': data['profile'], 'summary': data['summary'],
                         'checks': [{'name': x['name'], 'passed': x['passed']} for x in data['checks']],
                         'private_original_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    (OUT / 'api-contract.json').write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / 'export-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Exported', len(manifest['sources']), 'public evidence files')


if __name__ == '__main__':
    main()
