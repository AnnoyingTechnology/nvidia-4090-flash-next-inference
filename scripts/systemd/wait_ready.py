"""Wait for an HTTP readiness endpoint, with a bounded startup deadline."""
import sys
import time
import urllib.request

url, seconds = sys.argv[1:]
deadline = time.monotonic() + float(seconds)
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status == 200:
                break
    except OSError:
        pass
    time.sleep(1)
else:
    raise SystemExit(f"Readiness deadline exceeded: {url}")
