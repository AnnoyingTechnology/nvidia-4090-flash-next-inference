"""Keep unfinished generations out of accuracy, without hiding missing cases."""


def unfinished(response):
    finish = response.get('finish_reason')
    if finish == 'stop':
        return None
    return {'status': 'incomplete',
            'reason': 'output_limit' if finish == 'length' else f'finish_reason:{finish}'}


def status(row):
    if unfinished(row['response']):
        return 'incomplete'
    verdict = row['verdict']
    if verdict.get('status') == 'incomplete':
        return 'incomplete'
    if type(verdict.get('pass')) is not bool:
        return 'evaluator_error'
    return 'passed' if verdict['pass'] else 'failed'


def summary(rows, expected):
    counts = {key: sum(status(row) == key for row in rows)
              for key in ['passed', 'failed', 'incomplete', 'evaluator_error']}
    complete = counts['passed'] + counts['failed']
    qualified = len(rows) == expected and complete == expected
    return {'expected_cases': expected, 'attempted': len(rows), 'completed': complete,
            **counts, 'quality_score': {'passed': counts['passed'], 'total': expected,
                                      'accuracy': counts['passed'] / expected}
            if qualified and expected else None}
