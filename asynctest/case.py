# coding: utf-8
"""
Module asynctest.case
---------------------

Enhance :class:`unittest.TestCase`:

* a new loop is issued and set as the default loop before each test, and
  closed and disposed after,

* if the loop uses a selector, it will be wrapped with
  :class:`asynctest.TestSelector`,

* a test method in a TestCase identified as a coroutine function or returning
  a coroutine will run on the loop,

* :meth:`~TestCase.setUp()` and :meth:`~TestCase.tearDown()` methods can be
  coroutine functions,

* cleanup functions registered with :meth:`~TestCase.addCleanup()` can be
  coroutine functions,

* a test fails if the loop did not run during the test.
"""

import asyncio
import functools
import types
import unittest.case

from unittest.case import *  # NOQA

import asynctest.selector


class TestCase(unittest.case.TestCase):
    """
    if :meth:`setUp()` and :meth:`tearDown()` are coroutine functions, they
    will run on the loop.

    A test which is a coroutine function or which returns a coroutine will run
    on the loop.

    Else, once the test returned, a final assertion on whether the loop ran or
    not is checked. This allows to detect cases where a test author assume its
    test will run tasks or callbacks on the loop, but it actually didn't. When
    the test author doesn't need this assertion to be verified, the test
    function or :class:`~asynctest.TestCase` class can be decorated with
    :func:`~asynctest.ignore_loop`.

    By default, a new loop is created and is set as the default loop before each
    test. Test authors can retrieve this loop with
    :attr:`~asynctest.TestCase.loop`.

    If :attr:`~asynctest.TestCase.use_default_loop` is set to True, the current
    default event loop is used instead. In this case, it is up to the test
    author to deal with the state of the loop in each test: the loop might be
    closed, callbacks and tasks may be scheduled by previous tests. It is also
    up to the test author to close the loop and dispose the related resources.

    This behavior should be configured when defining the test case class:

    ::

        class With_Reusable_Loop_TestCase(asynctest.TestCase):
            use_default_loop = True

            def test_something(self):
                pass


    .. versionadded:: 0.5

        attribute :attr:`~asynctest.TestCase.use_default_loop`.

    """
    #: If true, the loop used by the test case is the current default event
    #: loop returned by :func:`asyncio.get_event_loop()`. The loop will not be
    #: closed and recreated between tests.
    use_default_loop = False

    #: Event loop created and set as default event loop during the test.
    loop = None

    def _init_loop(self):
        if self.use_default_loop:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = asyncio.new_event_loop()

        self.loop = self._patch_loop(self.loop)
        asyncio.set_event_loop(self.loop)

    def _unset_loop(self):
        if not self.use_default_loop:
            self.loop.close()

        self.loop = None

    def _patch_loop(self, loop):
        if hasattr(loop, '__asynctest_ran'):
            # The loop is already patched
            return loop

        loop.__asynctest_ran = False

        def wraps(method):
            @functools.wraps(method)
            def wrapper(self, *args, **kwargs):
                try:
                    return method(*args, **kwargs)
                finally:
                    loop.__asynctest_ran = True

            return types.MethodType(wrapper, loop)

        for method in ('run_forever', 'run_until_complete', ):
            setattr(loop, method, wraps(getattr(loop, method)))

        if isinstance(loop, asyncio.selector_events.BaseSelectorEventLoop):
            loop._selector = asynctest.selector.TestSelector(loop._selector)

        return loop

    def _setUp(self):
        self._init_loop()
        self.addCleanup(self._unset_loop)

        if asyncio.iscoroutinefunction(self.setUp):
            self.loop.run_until_complete(self.setUp())
        else:
            self.setUp()

        # don't take into account if the loop ran during setUp
        self.loop.__asynctest_ran = False

    def _tearDown(self):
        if asyncio.iscoroutinefunction(self.tearDown):
            self.loop.run_until_complete(self.tearDown())
        else:
            self.tearDown()

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

        if (getattr(self.__class__, "__asynctest_ignore_loop__", False) or
                getattr(method, "__asynctest_ignore_loop__", False)):
            return

        if not self.loop.__asynctest_ran:
            self.fail("Loop did not run during the test")

    def addCleanup(self, function, *args, **kwargs):
        """
        Add a function, with arguments, to be called when the test is
        completed. If function is a coroutine function, it will run on the loop
        before it's cleaned.
        """
        if asyncio.iscoroutinefunction(function):
            return super().addCleanup(self.loop.run_until_complete,
                                      function(*args, **kwargs))

        return super().addCleanup(function, *args, **kwargs)


class FunctionTestCase(TestCase, unittest.FunctionTestCase):
    """
    Enables the same features as :class:`~asynctest.TestCase`, but for
    :class:`~asynctest.FunctionTestCase`.
    """


def ignore_loop(test):
    """
    Ignore the error case where the loop did not run during the test.
    """
    test.__asynctest_ignore_loop__ = True
    return test
