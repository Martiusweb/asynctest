# coding: utf-8

import asyncio
import itertools
import unittest
import unittest.mock

import aiotest


class Test:
    class FooTestCase(aiotest.TestCase):
        def runTest(self):
            pass

        def test_foo(self):
            pass

    class LoggingTestCase(aiotest.TestCase):
        def __init__(self, calls):
            super().__init__()
            self.calls = calls

        def setUp(self):
            self.calls.append('setUp')

        def test_basic(self):
            self.events.append('test_basic')

        def tearDown(self):
            self.events.append('tearDown')


class Test_TestCase(unittest.TestCase):
    run_methods = ('run', 'debug', )

    def test_init_and_close_loop_for_test(self):
        class LoopTest(aiotest.TestCase):
            failing = False

            def runTest(self):
                try:
                    self.assertIsNotNone(self.loop)
                    self.assertFalse(self.loop.close.called)
                except Exception:
                    self.failing = True
                    raise

            def runFailingTest(self):
                self.runTest()
                raise SystemError()

        for method, test in itertools.product(self.run_methods, ('runTest', 'runFailingTest', )):
            with self.subTest(method=method, test=test), \
                    unittest.mock.patch('asyncio.new_event_loop') as mock:
                mock_loop = unittest.mock.Mock(asyncio.BaseEventLoop)
                mock.return_value = mock_loop

                case = LoopTest(test)
                try:
                    getattr(case, method)()
                except SystemError:
                    pass

                mock.assert_called_with()
                mock_loop.close.assert_called_with()
                self.assertFalse(case.failing)


if __name__ == "__main__":
    unittest.main()
