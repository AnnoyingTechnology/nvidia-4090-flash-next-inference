"""Official Google IFEval prompt-strict scorer, with deterministic language detection."""
import json
import random
import sys
from langdetect import DetectorFactory
from instruction_following_eval import evaluation_lib

random.seed(20261003)
DetectorFactory.seed = 0
request = json.load(sys.stdin)
row = request['problem']
example = evaluation_lib.InputExample(**{k: row[k] for k in (
    'key', 'instruction_id_list', 'prompt', 'kwargs')})
result = evaluation_lib.test_instruction_following_strict(example, {row['prompt']: request['code']})
print(json.dumps({'pass': result.follow_all_instructions,
                  'instruction_results': result.follow_instruction_list,
                  'instructions': row['instruction_id_list']}))
