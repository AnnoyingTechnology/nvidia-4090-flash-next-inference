import unittest
from summarize_chartqa import correct, number


class ChartScoringTests(unittest.TestCase):
    def test_units(self):
        for value, expected in [('41%', '41'), ('977,633 t', '977633'), ('2 years', '2'),
                                ('302.38% (2015)', '302.38'), ('62:29', '2.13')]:
            self.assertTrue(correct(value, expected))
        self.assertFalse(correct('1.9', '2.1'))
        self.assertFalse(correct('302.38%', '3.0238'))

    def test_no_number_fishing_or_boolean_coercion(self):
        for value in ['The answer is 41', 'wrong 41 right 39', True, 'NaN', '1:0']:
            self.assertIsNone(number(value))
        self.assertFalse(correct('Yes, yes', 'No'))
        self.assertTrue(correct('No, 46% is less than 58%.', 'No'))


if __name__ == '__main__':
    unittest.main()
