# coding: utf-8

import asyncio
import itertools
import logging
import os
import unittest
import unittest.mock
import subprocess
import sys
import time

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

    class StartWaitProcessTestCase(asynctest.TestCase):
        @staticmethod
        @asyncio.coroutine
        def start_wait_process(loop):
            process = yield from asyncio.create_subprocess_shell(
                "true", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                loop=loop)

            try:
                out, err = yield from asyncio.wait_for(
                    process.communicate(), timeout=.1, loop=loop)
            except:
                process.kill()
                os.waitpid(process.pid, os.WNOHANG)
                raise

        @asyncio.coroutine
        def runTest(self):
            yield from self.start_wait_process(self.loop)


class _TestCase(unittest.TestCase):
    run_methods = ('run', 'debug', )

    def create_default_loop(self):
        default_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(default_loop)
        self.addCleanup(default_loop.close)
        return default_loop


class Test_TestCase(_TestCase):
    def test_init_and_close_loop_for_test(self):
        default_loop = self.create_default_loop()

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
                self.assertIs(default_loop, asyncio.get_event_loop())

    def test_default_loop_is_not_created_when_unused(self):
        policy = asyncio.get_event_loop_policy()

        @asynctest.ignore_loop
        class Dummy_TestCase(Test.FooTestCase):
            pass

        for method in self.run_methods:
            with self.subTest(method=method):
                with unittest.mock.patch.object(policy,
                                                "get_event_loop") as mock:
                    case = Dummy_TestCase()
                    getattr(case, method)()

                self.assertFalse(mock.called)

    def test_update_default_loop_works(self):
        a_loop = asyncio.new_event_loop()
        self.addCleanup(a_loop.close)

        class Update_Default_Loop_TestCase(asynctest.TestCase):
            @asynctest.ignore_loop
            def runTest(self):
                self.assertIs(self.loop, asyncio.get_event_loop())
                asyncio.set_event_loop(a_loop)
                self.assertIs(a_loop, asyncio.get_event_loop())

        for method in self.run_methods:
            with self.subTest(method=method):
                case = Update_Default_Loop_TestCase()
                result = getattr(case, method)()

                if result:
                    self.assertTrue(result.wasSuccessful())

                self.assertIs(a_loop, asyncio.get_event_loop())

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

                # assert that the original loop is reset after the test
                self.assertIs(default_loop, asyncio.get_event_loop())

                if result:
                    self.assertTrue(result.wasSuccessful())

            self.assertFalse(default_loop.is_closed())

    def test_forbid_get_event_loop(self):
        default_loop = self.create_default_loop()

        class Forbid_get_event_loop_TestCase(asynctest.TestCase):
            forbid_get_event_loop = True

            @asyncio.coroutine
            def runTest(self):
                with self.assertRaises(AssertionError):
                    asyncio.get_event_loop()

        for method in self.run_methods:
            with self.subTest(method=method):
                case = Forbid_get_event_loop_TestCase()
                result = getattr(case, method)()

                # assert that the original loop is reset after the test
                self.assertIs(default_loop, asyncio.get_event_loop())

                if result:
                    self.assertTrue(result.wasSuccessful())

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


@unittest.skipIf(sys.platform == "win32", "Tests specific to Unix")
class Test_TestCase_and_ChildWatcher(_TestCase):
    def test_watched_process_is_awaited(self):
        for method in self.run_methods:
            with self.subTest(method=method):
                case = Test.StartWaitProcessTestCase()
                outcome = getattr(case, method)()

                if outcome:
                    self.assertTrue(outcome.wasSuccessful())

    def test_original_watcher_works_outside_loop(self):
        default_loop = self.create_default_loop()

        # check if we can spawn and wait a subprocess before an after a test
        for method in self.run_methods:
            with self.subTest(method=method):
                coro = Test.StartWaitProcessTestCase.start_wait_process(
                    default_loop)
                default_loop.run_until_complete(coro)

                case = Test.StartWaitProcessTestCase()
                outcome = getattr(case, method)()

                if outcome:
                    self.assertTrue(outcome.wasSuccessful())

                coro = Test.StartWaitProcessTestCase.start_wait_process(
                    default_loop)
                default_loop.run_until_complete(coro)


class Test_ClockedTestCase(asynctest.ClockedTestCase):
    @asyncio.coroutine
    def advance(self, seconds):
        try:
            self.loop.set_debug(True)
            with self.assertLogs(level=logging.WARNING) as log:
                yield from self.loop.create_task(super().advance(seconds))

            self.assertTrue(any(filter(
                lambda o: 'took {:.3f} seconds'.format(seconds) in o,
                log.output)))
        finally:
            self.loop.set_debug(False)

    @asyncio.coroutine
    def test_advance(self):
        f = asyncio.Future(loop=self.loop)
        g = asyncio.Future(loop=self.loop)
        started_wall_clock = time.monotonic()
        started_loop_clock = self.loop.time()
        self.loop.call_later(1, f.set_result, None)
        self.loop.call_later(2, g.set_result, None)
        self.assertFalse(f.done())
        yield from self.advance(1)
        yield from f
        self.assertFalse(g.done())
        yield from self.advance(9)
        yield from g
        finished_wall_clock = time.monotonic()
        finished_loop_clock = self.loop.time()
        self.assertLess(
            finished_wall_clock - started_wall_clock,
            finished_loop_clock - started_loop_clock)

    def test_advance_with_run_until_complete(self):
        f = asyncio.Future(loop=self.loop)
        started_wall_clock = time.monotonic()
        started_loop_clock = self.loop.time()
        self.loop.call_later(1, f.set_result, None)
        self.loop.run_until_complete(self.advance(1))
        self.assertTrue(f.done())
        finished_wall_clock = time.monotonic()
        finished_loop_clock = self.loop.time()
        self.assertLess(
            finished_wall_clock - started_wall_clock,
            finished_loop_clock - started_loop_clock)

    @asyncio.coroutine
    def test_negative_advance(self):
        with self.assertRaisesRegex(ValueError, 'back in time'):
            yield from self.advance(-1)
        self.assertEqual(self.loop.time(), 0)


if __name__ == "__main__":
    unittest.main()
