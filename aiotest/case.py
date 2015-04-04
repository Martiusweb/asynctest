# coding: utf-8
"""
Wrapper to unittest reducing the boilerplate when testing asyncio powered code.

Features currently supported:

  * a new loop is issued and set as the default loop before each test, and
    closed and disposed after,

  * a test method in a TestCase identified as a coroutine function or returning
    a coroutine will run on the loop,

  * a test fails if the loop did not run during the test.
"""

import asyncio
import functools
import types
import unittest.case


class TestCase(unittest.case.TestCase):
    """
    For each test, a new loop is created and is set as the default loop. Test
    authors can retrieve this loop with the self.loop property.

    A test which is a coroutine function or which returns a coroutine will run
    on the loop.

    Else, once the test returned, a final assertion on whether the loop ran or
    not is checked. This allows to detect cases where a test author assume its
    test will run tasks or callbacks on the loop, but it actually didn't. When
    the test author doesn't need this assertion to be verified, the test
    function or TestCase class can be decorated with @ignore_loop.
    """
    loop = None

    def _init_loop(self):
        self.loop = self._patch_loop(asyncio.new_event_loop())
        asyncio.set_event_loop(self.loop)

    def _unset_loop(self):
        self.loop.close()
        self.loop = None

    def _patch_loop(self, loop):
        loop.__aiotest_ran = False

        def wraps(method):
            @functools.wraps(method)
            def wrapper(self, *args, **kwargs):
                try:
                    return method(*args, **kwargs)
                finally:
                    loop.__aiotest_ran = True

            return types.MethodType(wrapper, loop)

        for method in ('run_forever', 'run_until_complete', ):
            setattr(loop, method, wraps(getattr(loop, method)))

        return loop

    def _setUp(self):
        self._init_loop()

        try:
            self.setUp()
        except:
            self._unset_loop()
            raise

    def _tearDown(self):
        self.tearDown()
        self._unset_loop()

    # Override unittest.TestCase methods which call setUp() and tearDown()
    def run(self, result=None):
        orig_result = result
        if result is None:
            result = self.defaultTestResult()
            startTestRun = getattr(result, 'startTestRun', None)
            if startTestRun is not None:
                startTestRun()

        result.startTest(self)

        testMethod = getattr(self, self._testMethodName)
        if (getattr(self.__class__, "__unittest_skip__", False) or
                getattr(testMethod, "__unittest_skip__", False)):
            # If the class or method was skipped.
            try:
                skip_why = (getattr(self.__class__, '__unittest_skip_why__', '') or
                            getattr(testMethod, '__unittest_skip_why__', ''))
                self._addSkip(result, self, skip_why)
            finally:
                result.stopTest(self)
            return
        expecting_failure = getattr(testMethod,
                                    "__unittest_expecting_failure__", False)
        outcome = unittest.case._Outcome(result)
        try:
            self._outcome = outcome

            with outcome.testPartExecutor(self):
                self._setUp()
            if outcome.success:
                outcome.expecting_failure = expecting_failure
                with outcome.testPartExecutor(self, isTest=True):
                    self._run_test_method(testMethod)
                outcome.expecting_failure = False
                with outcome.testPartExecutor(self):
                    self._tearDown()

            self.doCleanups()
            for test, reason in outcome.skipped:
                self._addSkip(result, test, reason)
            self._feedErrorsToResult(result, outcome.errors)
            if outcome.success:
                if expecting_failure:
                    if outcome.expectedFailure:
                        self._addExpectedFailure(result, outcome.expectedFailure)
                    else:
                        self._addUnexpectedSuccess(result)
                else:
                    result.addSuccess(self)
            return result
        finally:
            result.stopTest(self)
            if orig_result is None:
                stopTestRun = getattr(result, 'stopTestRun', None)
                if stopTestRun is not None:
                    stopTestRun()

            # explicitly break reference cycles:
            # outcome.errors -> frame -> outcome -> outcome.errors
            # outcome.expectedFailure -> frame -> outcome -> outcome.expectedFailure
            outcome.errors.clear()
            outcome.expectedFailure = None

            # clear the outcome, no more needed
            self._outcome = None

    def debug(self):
        self._setUp()
        try:
            self._run_test_method(getattr(self, self._testMethodName))
            self._tearDown()
        except Exception:
            self._unset_loop()
            raise

        while self._cleanups:
            function, args, kwargs = self._cleanups.pop(-1)
            function(*args, **kwargs)

    def _run_test_method(self, method):
        # If the method is a coroutine or returns a coroutine, run it on the
        # loop
        result = method()
        if asyncio.iscoroutine(result):
            self.loop.run_until_complete(result)
            return

        if (getattr(self.__class__, "__aiotest_ignore_loop__", False) or
                getattr(method, "__aiotest_ignore_loop__", False)):
            return

        if not self.loop.__aiotest_ran:
            self.fail("Loop did not run during the test")


class FunctionTestCase(TestCase, unittest.FunctionTestCase):
    """
    Enables the same features as TestCase, but for FunctionTestCase.
    """


def ignore_loop(test):
    """
    Ignore the error case where the loop did not run during the test.
    """
    test.__aiotest_ignore_loop__ = True
    return test
