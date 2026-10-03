import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eval as evaluator
from scripts.evaluation_status import summary


class CompletionTests(unittest.TestCase):
    def test_capped_valid_code_is_not_graded_or_counted_as_pass_or_failure(self):
        case = {'suite': 'lcb', 'data': {}}
        response = {'content': '```python\nprint(42)\n```', 'finish_reason': 'length'}
        with patch.object(evaluator, 'grade') as grader:
            verdict = evaluator.score(case, response)
            grader.assert_not_called()
        result = summary([{'response': response, 'verdict': verdict}], 1)
        self.assertEqual((result['passed'], result['failed'], result['incomplete']), (0, 0, 1))
        self.assertIsNone(result['quality_score'])

    def test_complete_wrong_answer_is_a_quality_failure(self):
        result = summary([{'response': {'finish_reason': 'stop'}, 'verdict': {'pass': False}}], 1)
        self.assertEqual(result['quality_score'], {'passed': 0, 'total': 1, 'accuracy': 0})

    def test_survivors_and_legacy_cap_verdicts_do_not_become_a_full_score(self):
        rows = [{'response': {'finish_reason': 'stop'}, 'verdict': {'pass': True}},
                {'response': {'finish_reason': 'length'}, 'verdict': {'pass': False}}]
        result = summary(rows, 2)
        self.assertEqual((result['completed'], result['incomplete']), (1, 1))
        self.assertIsNone(result['quality_score'])
        self.assertIsNone(summary(rows[:1], 2)['quality_score'])

    def test_grader_error_and_nonstandard_finish_withhold_accuracy(self):
        for row in [{'response': {'finish_reason': 'stop'}, 'verdict': {'error': 'grader crashed'}},
                    {'response': {'finish_reason': 'cancel'}, 'verdict': {'pass': True}}]:
            self.assertIsNone(summary([row], 1)['quality_score'])


if __name__ == '__main__':
    unittest.main()
