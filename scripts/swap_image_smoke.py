"""Send a new image, the same image again, then another new image; print latency and the answer start."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision_compare import local

cases = [json.loads(line) for line in Path('fixtures/vision15/cases.jsonl').read_text().splitlines()]
for case in [cases[0], cases[0], cases[1]]:
    r = local(case, Path(case['image']), 'http://127.0.0.1:19623', 'low')
    print(case['id'], round(r['ttft_s'], 3), r['finish_reason'], r['content'][:160].replace('\n', ' '), flush=True)
