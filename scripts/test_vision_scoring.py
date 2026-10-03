"""Guard the observed number/string ambiguity without accepting wrong visual answers."""
import unittest
from summarize_vision15 import equivalent, score


class VisionScoreTests(unittest.TestCase):
    def test_numbers(self):
        self.assertTrue(equivalent('480.00', 480))
        self.assertTrue(equivalent('5432', 5432))
        for wrong in ['481.00', 'total 480.00', 'NaN', '480 EUR', True]:
            self.assertFalse(equivalent(wrong, 480))

    def test_percent_units_are_field_specific(self):
        self.assertTrue(equivalent('91%', 91, 'use_percent'))
        self.assertFalse(equivalent('90%', 91, 'use_percent'))
        self.assertFalse(equivalent('91%', 91, 'total_due'))

    def test_booleans_are_not_numbers(self):
        self.assertFalse(equivalent(1, True))
        self.assertFalse(equivalent('true', True))
        self.assertFalse(equivalent(True, 1))

    def test_json_contract_and_content_are_separate(self):
        expected = {'total_due': 480}
        self.assertTrue(score('{"total_due":"480.00"}', expected)['plain_json'])
        fenced = score('```json\n{"total_due":480}\n```', expected)
        self.assertTrue(fenced['content_correct'])
        self.assertFalse(fenced['plain_json'])
        for wrong in ['{}', '{"total_due":480,"extra":1}', 'The total is 480']:
            self.assertFalse(score(wrong, expected)['content_correct'])


if __name__ == '__main__':
    unittest.main()
