"""Bounded startup check shared by the experiment runners."""
import json
import time
import urllib.error
import urllib.request

deadline = time.monotonic() + 300
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen('http://127.0.0.1:19623/health', timeout=3) as response:
            health = json.load(response)
        if health.get('loaded', True) and health.get('status') in ('ok', 'ready'):
            print(json.dumps(health), flush=True)
            break
    except (OSError, ValueError, urllib.error.HTTPError):
        pass
    time.sleep(1)
else:
    raise RuntimeError('The experiment did not become ready within 300 seconds')
