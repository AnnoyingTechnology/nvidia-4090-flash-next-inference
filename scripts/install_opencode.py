"""Install the owned model entry, with a private workspace-local rollback copy."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def merge(destination, source):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(destination.get(key), dict):
            merge(destination[key], value)
        else:
            destination[key] = value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, default=Path.home()/'.config/opencode/opencode.json')
    args = ap.parse_args()
    source = json.loads((ROOT/'docs/opencode-example.json').read_text())
    target = args.config
    config = json.loads(target.read_text()) if target.exists() else {'$schema': source['$schema']}
    rollback = ROOT/'client-private'
    rollback.mkdir(mode=0o700, exist_ok=True)
    rollback.chmod(0o700)
    if target.exists():
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = rollback/('opencode-before-'+stamp+'.json')
        shutil.copyfile(target, backup)
        backup.chmod(0o600)
    providers = config.setdefault('provider', {})
    merge(providers, source['provider'])
    # Remove our retired output-budget alias; it addresses the same backend model.
    providers['ai-ulmus-flash-next']['models'].pop('qwen3.8-flash-next-long', None)
    if config.get('model') == 'ai-ulmus-flash-next/qwen3.8-flash-next-long':
        config['model'] = 'ai-ulmus-flash-next/qwen3.8-flash-next'
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, prefix='.opencode-', delete=False) as temp:
        json.dump(config, temp, indent=2)
        temp.write('\n')
        temp.flush()
        os.fsync(temp.fileno())
        temporary = Path(temp.name)
    temporary.chmod(0o600)
    temporary.replace(target)
    print('Installed ai-ulmus-flash-next; existing model default:', config.get('model'))


if __name__ == '__main__':
    main()
