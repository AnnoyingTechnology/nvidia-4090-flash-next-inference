"""Run the official LCB grader only in an isolated, resource-limited container."""
import base64
import contextlib
import io
import json
import pickle
import sys
import tempfile
import zlib

from testing_util import run_test

request = json.load(sys.stdin)
problem = request['problem']
public = json.loads(problem['public_test_cases'])
try:
    private = json.loads(problem['private_test_cases'])
except (ValueError, TypeError):
    # The official dataset stores a pickled JSON string, not an arbitrary Python object.
    class DataOnly(pickle.Unpickler):
        def find_class(self, *_):
            raise ValueError('Executable pickle content is forbidden')
    decoded = DataOnly(io.BytesIO(zlib.decompress(base64.b64decode(problem['private_test_cases'])))).load()
    if not isinstance(decoded, str):
        raise ValueError('Expected the published JSON string encoding')
    private = json.loads(decoded)
cases = public + private
sample = {'input_output': json.dumps({'inputs': [t['input'] for t in cases],
           'outputs': [t['output'] for t in cases],
           'fn_name': json.loads(problem['metadata']).get('func_name')})}
# faulthandler in the official evaluator requires a real stderr file descriptor.
with tempfile.TemporaryFile(mode='w+') as logs:
    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        results, metadata = run_test(sample, test=request['code'], timeout=6)
print(json.dumps({'pass': bool(results) and all(r == True for r in results),
                  'results': [int(r) for r in results], 'tests': len(cases),
                  'metadata': metadata}, default=str))
