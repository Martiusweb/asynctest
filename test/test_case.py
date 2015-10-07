# coding: utf-8

import asyncio
import itertools
import unittest
import unittest.mock
import sys

import asynctest

if sys.version_info >= (3, 5):
    from . import test_case_await as _using_await
else:
    _using_await = None


class Test:
    class FooTestCase(asynctest.TestCase):
        def runTest(self):
            pass

        def test_foo(self):
            pass

    @asynctest.ignore_loop
    class LoggingTestCase(asynctest.TestCase):
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
        @asynctest.ignore_loop
        class LoopTest(asynctest.TestCase):
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
                mock_loop = unittest.mock.Mock(asyncio.AbstractEventLoop)
                mock.return_value = mock_loop

                case = LoopTest(test)
                try:
                    getattr(case, method)()
                except SystemError:
                    pass

                mock.assert_called_with()
                mock_loop.close.assert_called_with()
                self.assertFalse(case.failing)

    def create_default_loop(self):
        default_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(default_loop)
        self.addCleanup(default_loop.close)
        return default_loop

    def test_use_default_loop(self):
        default_loop = self.create_default_loop()

        class Using_Default_Loop_TestCase(asynctest.TestCase):
            use_default_loop = True

            @asynctest.ignore_loop
            def runTest(self):
                self.assertIs(default_loop, self.loop)

        for method in self.run_methods:
            with self.subTest(method=method):
                case = Using_Default_Loop_TestCase()
                result = getattr(case, method)()

                if result:
                    self.assertTrue(result.wasSuccessful())

            self.assertFalse(default_loop.is_closed())

    def test_coroutinefunction_executed(self):
        class CoroutineFunctionTest(asynctest.TestCase):
            ran = False

            @asyncio.coroutine
            def runTest(self):
                self.ran = True
                yield from []

        cases = [CoroutineFunctionTest()]
        if _using_await:
            cases.append(_using_await.CoroutineFunctionTest())

        for method in self.run_methods:
            with self.subTest(method=method):
                for case in cases:
                    with self.subTest(case=case):
                        getattr(case, method)()
                        self.assertTrue(case.ran)

    def test_coroutine_returned_executed(self):
        class CoroutineTest(asynctest.TestCase):
            ran = False

            def runTest(self):
                return asyncio.coroutine(lambda: setattr(self, 'ran', True))()

        cases = [CoroutineTest()]
        if _using_await:
            cases.append(_using_await.CoroutineTest())

        for method in self.run_methods:
            with self.subTest(method=method):
                for case in cases:
                    with self.subTest(case=case):
                        getattr(case, method)()
                        self.assertTrue(case.ran)

    def test_fails_when_loop_didnt_run(self):
        with self.assertRaisesRegex(AssertionError, 'Loop did not run during the test'):
            Test.FooTestCase().debug()

        result = Test.FooTestCase().run()
        self.assertEqual(1, len(result.failures))

    def test_fails_when_loop_didnt_run_using_default_loop(self):
        class TestCase(Test.FooTestCase):
            use_default_loop = True

        default_loop = self.create_default_loop()

        with self.assertRaisesRegex(AssertionError, 'Loop did not run during the test'):
            TestCase().debug()

        result = TestCase().run()
        self.assertEqual(1, len(result.failures))

        default_loop.run_until_complete(asyncio.sleep(0, loop=default_loop))

        with self.assertRaisesRegex(AssertionError, 'Loop did not run during the test'):
            TestCase().debug()

        default_loop.run_until_complete(asyncio.sleep(0, loop=default_loop))

        result = TestCase().run()
        self.assertEqual(1, len(result.failures))

    def test_fails_when_loop_ran_only_during_setup(self):
        for test_use_default_loop in (False, True):
            with self.subTest(use_default_loop=test_use_default_loop):
                if test_use_default_loop:
                    self.create_default_loop()

                class TestCase(Test.FooTestCase):
                    use_default_loop = test_use_default_loop

                    def setUp(self):
                        self.loop.run_until_complete(asyncio.sleep(0, loop=self.loop))

                with self.assertRaisesRegex(AssertionError, 'Loop did not run during the test'):
                    TestCase().debug()

                result = TestCase().run()
                self.assertEqual(1, len(result.failures))

    def test_fails_when_loop_ran_only_during_cleanup(self):
        for test_use_default_loop in (False, True):
            with self.subTest(use_default_loop=test_use_default_loop):
                if test_use_default_loop:
                    self.create_default_loop()

                class TestCase(Test.FooTestCase):
                    use_default_loop = test_use_default_loop

                    def setUp(self):
                        self.addCleanup(asyncio.coroutine(lambda: None))

                with self.assertRaisesRegex(AssertionError, 'Loop did not run during the test'):
                    TestCase().debug()

                result = TestCase().run()
                self.assertEqual(1, len(result.failures))

    def test_passes_when_ignore_loop_or_loop_run(self):
        @asynctest.ignore_loop
        class IgnoreLoopClassTest(Test.FooTestCase):
            pass

        class IgnoreLoopMethodTest(asynctest.TestCase):
            @asynctest.ignore_loop
            def runTest(self):
                pass

        class WithCoroutineTest(asynctest.TestCase):
            @asyncio.coroutine
            def runTest(self):
                yield from []

        class WithFunctionCallingLoopTest(asynctest.TestCase):
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

    def test_setup_teardown_may_be_coroutines(self):
        @asynctest.ignore_loop
        class WithSetupFunction(Test.FooTestCase):
            ran = False

            def setUp(self):
                WithSetupFunction.ran = True

        @asynctest.ignore_loop
        class WithSetupCoroutine(Test.FooTestCase):
            ran = False

            @asyncio.coroutine
            def setUp(self):
                WithSetupCoroutine.ran = True

        @asynctest.ignore_loop
        class WithTearDownFunction(Test.FooTestCase):
            ran = False

            def tearDown(self):
                WithTearDownFunction.ran = True

        @asynctest.ignore_loop
        class WithTearDownCoroutine(Test.FooTestCase):
            ran = False

            def tearDown(self):
                WithTearDownCoroutine.ran = True

        for method in self.run_methods:
            for call_mode in (WithSetupFunction, WithSetupCoroutine,
                              WithTearDownFunction, WithTearDownCoroutine):
                with self.subTest(method=method, case=call_mode.__name__):
                    case = call_mode()
                    call_mode.ran = False

                    getattr(case, method)()
                    self.assertTrue(case.ran)

    def test_cleanup_functions_can_be_coroutines(self):
        cleanup_normal_called = False
        cleanup_normal_called_too_soon = False
        cleanup_coro_called = False

        def cleanup_normal():
            nonlocal cleanup_normal_called
            cleanup_normal_called = True

        @asyncio.coroutine
        def cleanup_coro():
            nonlocal cleanup_coro_called
            cleanup_coro_called = True

        @asynctest.ignore_loop
        class TestCase(Test.FooTestCase):
            def setUp(self):
                nonlocal cleanup_normal_called, cleanup_normal_called_too_soon
                nonlocal cleanup_coro_called

                cleanup_normal_called = cleanup_coro_called = False

                self.addCleanup(cleanup_normal)
                cleanup_normal_called_too_soon = cleanup_normal_called

                self.addCleanup(cleanup_coro)

        for method in self.run_methods:
            with self.subTest(method=method):
                getattr(TestCase(), method)()
                self.assertTrue(cleanup_normal_called)
                self.assertTrue(cleanup_coro_called)

    def test_loop_uses_TestSelector(self):
        @asynctest.ignore_loop
        class CheckLoopTest(asynctest.TestCase):
            def runTest(self):
                # TestSelector is used
                self.assertIsInstance(self.loop._selector,
                                      asynctest.selector.TestSelector)

                # And wraps the original selector
                self.assertIsNotNone(self.loop._selector._selector)

        for method in self.run_methods:
            with self.subTest(method=method):
                case = CheckLoopTest()
                outcome = getattr(case, method)()

                if outcome:
                    self.assertTrue(outcome.wasSuccessful())


if __name__ == "__main__":
    unittest.main()
