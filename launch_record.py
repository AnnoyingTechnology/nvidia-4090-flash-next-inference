"""Record the actual image and non-secret engine profile used for each launch."""
import hashlib
import datetime
import json
from pathlib import Path
import subprocess
import sys
import os

root = Path(os.environ.get('ULMUS_ROOT', Path(__file__).resolve().parent))
root.joinpath('results').mkdir(exist_ok=True)
name, image = sys.argv[1:]
path = root / 'profiles' / (name + '.json')
cfg = json.loads(path.read_text())
stamp = datetime.datetime.now(datetime.timezone.utc)
shared_path = path.with_suffix('.shared-settings.json')
record = {'observed_at': stamp.isoformat(), 'profile': name, 'profile_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'image': image, 'image_id': subprocess.check_output([
              'docker', 'image', 'inspect', image, '--format', '{{.Id}}'], text=True).strip(),
          'engine_args': cfg['args'], 'vision': cfg.get('vision'),
          'sampling': cfg.get('sampling'),
          'shared_defaults': json.loads(shared_path.read_text()) if shared_path.exists() else None,
          'shared_defaults_sha256': hashlib.sha256(shared_path.read_bytes()).hexdigest() if shared_path.exists() else None,
          'experimental_env': {k: os.environ[k] for k in
              ['ULMUS_VERIFY_PROFILE', 'ULMUS_DECODE_TIMING', 'ULMUS_POOL_QUANT_THRESH'] if k in os.environ}}
(root / 'results' / f'launch-{name}.json').write_text(json.dumps(record, indent=2))
history = root / 'results' / 'launches'
history.mkdir(exist_ok=True)
(history / (stamp.strftime('%Y%m%dT%H%M%S%fZ') + '-' + name + '.json')).write_text(json.dumps(record, indent=2))
