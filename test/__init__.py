import unittest

test_modules = (
    'test_case',
    'test_helpers',
    'test_mock',
    'test_selector'
)
test_suite = unittest.defaultTestLoader.loadTestsFromNames(('{}.{}'.format(__name__, m) for m in test_modules))


def load_tests(loader, tests, pattern):
    return test_suite
