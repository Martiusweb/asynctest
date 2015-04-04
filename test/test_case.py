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

    @aiotest.ignore_loop
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
        @aiotest.ignore_loop
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

    def test_coroutinefunction_executed(self):
        class CoroutineFunctionTest(aiotest.TestCase):
            ran = False

            @asyncio.coroutine
            def runTest(self):
                self.ran = True
                yield from []

        for method in self.run_methods:
            with self.subTest(method=method):
                case = CoroutineFunctionTest()
                getattr(case, method)()
                self.assertTrue(case.ran)

    def test_coroutine_returned_executed(self):
        class CoroutineTest(aiotest.TestCase):
            ran = False

            def runTest(self):
                return asyncio.coroutine(lambda: setattr(self, 'ran', True))()

        for method in self.run_methods:
            with self.subTest(method=method):
                case = CoroutineTest()
                getattr(case, method)()
                self.assertTrue(case.ran)

    def test_fails_when_loop_didnt_run(self):
        with self.assertRaisesRegex(AssertionError, 'Loop did not run during the test'):
            Test.FooTestCase().debug()

        result = Test.FooTestCase().run()
        self.assertEqual(1, len(result.failures))

    def test_passes_when_ignore_loop_or_loop_run(self):
        @aiotest.ignore_loop
        class IgnoreLoopClassTest(Test.FooTestCase):
            pass

        class IgnoreLoopMethodTest(aiotest.TestCase):
            @aiotest.ignore_loop
            def runTest(self):
                pass

        class WithCoroutineTest(aiotest.TestCase):
            @asyncio.coroutine
            def runTest(self):
                yield from []

        class WithFunctionCallingLoopTest(aiotest.TestCase):
            def runTest(self):
                fut = asyncio.Future()
                self.loop.call_soon(fut.set_result, None)
                self.loop.run_until_complete(fut)

        for test in (IgnoreLoopClassTest, IgnoreLoopMethodTest,
                     WithCoroutineTest, WithFunctionCallingLoopTest):
            with self.subTest(test=test):
                test().debug()

                result = test().run()
                self.assertEqual(0, len(result.failures))


if __name__ == "__main__":
    unittest.main()
