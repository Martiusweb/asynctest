# coding: utf-8
from .utils import run_coroutine

import asynctest.mock


# add a new-style coroutine to the Test class:
def patch_Test_Class(klass):
    class Test(klass):
        async def an_async_coroutine(self):
            pass

    return Test


# wrap the coro in a new-style coroutine
def transform(coro):
    async def a_coroutine(*a, **kw):
        return await coro(*a, **kw)

    return a_coroutine


# make a simple coroutine which invokes a function before awaiting on an
# awaitable and after
def build_simple_coroutine(before_func, after_func=None):
    async def a_coroutine(awaitable, *args, **kwargs):
        before = before_func(*args, **kwargs)
        await awaitable
        after = (after_func or before_func)(*args, **kwargs)
        return before, after

    return a_coroutine


class _Test_Mock_Of_Async_Magic_Methods:
    class WithAsyncContextManager:
        def __init__(self):
            self.entered = False
            self.exited = False

        async def __aenter__(self, *args, **kwargs):
            self.entered = True
            return self

        async def __aexit__(self, *args, **kwargs):
            self.exited = True

    def test_mock_magic_methods_are_coroutine_mocks(self, klass):
        instance = self.WithAsyncContextManager()
        mock_instance = asynctest.mock.MagicMock(instance)
        self.assertIsInstance(mock_instance.__aenter__,
                              asynctest.mock.CoroutineMock)
        self.assertIsInstance(mock_instance.__aexit__,
                              asynctest.mock.CoroutineMock)

    def test_mock_supports_async_context_manager(self, klass):
        called = False
        instance = self.WithAsyncContextManager()
        mock_instance = asynctest.mock.MagicMock(instance)

        async def use_context_manager():
            nonlocal called
            async with mock_instance as result:
                called = True

            return result

        result = run_coroutine(use_context_manager())
        self.assertFalse(instance.entered)
        self.assertFalse(instance.exited)
        self.assertTrue(called)
        self.assertTrue(mock_instance.__aenter__.called)
        self.assertTrue(mock_instance.__aexit__.called)
        self.assertIsNot(mock_instance, result)
        self.assertIsInstance(result, asynctest.mock.MagicMock)
