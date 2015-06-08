# coding: utf-8

import asyncio
import itertools
import unittest
import unittest.mock

import asynctest


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
        class CoroutineFunctionTest(asynctest.TestCase):
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
        class CoroutineTest(asynctest.TestCase):
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

    def test_fails_when_loop_ran_only_during_setup(self):
        class TestCase(Test.FooTestCase):
            def setUp(self):
                self.loop.run_until_complete(asyncio.sleep(0, loop=self.loop))

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
