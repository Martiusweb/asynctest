# coding: utf-8
import asyncio
import sys
import warnings

from .utils import run_coroutine

import asynctest.mock


# add a new-style coroutine to the Test class:
def patch_Test_Class(klass):
    class Test(klass):
        async def an_async_coroutine(self):
            pass

        @classmethod
        async def an_async_classmethod_coroutine(self):
            pass

        @staticmethod
        async def an_async_staticmethod_coroutine(self):
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
        for spec in (None, self.WithAsyncContextManager()):
            with self.subTest(spec=spec):
                mock_instance = asynctest.mock.MagicMock(spec)
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

    def test_mock_customize_async_context_manager(self, klass):
        instance = self.WithAsyncContextManager()
        mock_instance = asynctest.mock.MagicMock(instance)

        expected_result = object()
        mock_instance.__aenter__.return_value = expected_result

        async def use_context_manager():
            async with mock_instance as result:
                return result

        self.assertIs(run_coroutine(use_context_manager()), expected_result)

    def test_mock_customize_async_context_manager_with_coroutine(self, klass):
        enter_called = False
        exit_called = False

        async def enter_coroutine(*args):
            nonlocal enter_called
            enter_called = True

        async def exit_coroutine(*args):
            nonlocal exit_called
            exit_called = True

        instance = self.WithAsyncContextManager()
        mock_instance = asynctest.mock.MagicMock(instance)

        mock_instance.__aenter__ = enter_coroutine
        mock_instance.__aexit__ = exit_coroutine

        async def use_context_manager():
            async with mock_instance:
                pass

        run_coroutine(use_context_manager())
        self.assertTrue(enter_called)
        self.assertTrue(exit_called)

    def test_context_manager_raise_exception_by_default(self, klass):
        class InContextManagerException(Exception):
            pass

        async def raise_in(context_manager):
            async with context_manager:
                raise InContextManagerException()

        instance = self.WithAsyncContextManager()
        mock_instance = asynctest.mock.MagicMock(instance)
        with self.assertRaises(InContextManagerException):
            run_coroutine(raise_in(mock_instance))

    class WithAsyncIterator:
        def __init__(self):
            self.iter_called = False
            self.next_called = False
            self.items = ["foo", "bar", "baz"]

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return self.items.pop()
            except IndexError:
                pass

            raise StopAsyncIteration

    class WithAsyncIteratorDeprecated(WithAsyncIterator):
        # Before python 3.5.2, __aiter__ is specified as a coroutine, but it's
        # a design error, it should be a plain function.
        async def __aiter__(self):
            return super().__aiter__()

    def get_async_iterator_classes(self):
        # We assume that __aiter__ as a coroutine will not be available in
        # python 3.7, see: pep-0525#aiter-and-anext-builtins
        if sys.version_info >= (3, 7):
            return (self.WithAsyncIterator, )
        else:
            return (self.WithAsyncIterator, self.WithAsyncIteratorDeprecated, )

    def test_mock_aiter_and_anext(self, klass):
        classes = self.get_async_iterator_classes()

        for iterator_class in classes:
            with self.subTest(iterator_class=iterator_class.__name__):
                instance = iterator_class()
                mock_instance = asynctest.MagicMock(instance)

                self.assertEqual(asyncio.iscoroutine(instance.__aiter__),
                                 asyncio.iscoroutine(mock_instance.__aiter__))
                self.assertEqual(asyncio.iscoroutine(instance.__anext__),
                                 asyncio.iscoroutine(mock_instance.__anext__))

                iterator = instance.__aiter__()
                if asyncio.iscoroutine(iterator):
                    iterator = run_coroutine(iterator)

                mock_iterator = mock_instance.__aiter__()
                if asyncio.iscoroutine(mock_iterator):
                    mock_iterator = run_coroutine(mock_iterator)

                self.assertEqual(asyncio.iscoroutine(iterator.__aiter__),
                                 asyncio.iscoroutine(mock_iterator.__aiter__))
                self.assertEqual(asyncio.iscoroutine(iterator.__anext__),
                                 asyncio.iscoroutine(mock_iterator.__anext__))

    def test_mock_async_for(self, klass):
        async def iterate(iterator):
            accumulator = []
            # don't print the DeprecationWarning for __aiter__
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                async for item in iterator:
                    accumulator.append(item)

            return accumulator

        expected = ["FOO", "BAR", "BAZ"]
        specs = [None]
        specs.extend(i() for i in self.get_async_iterator_classes())
        for spec in specs:
            with self.subTest("iterate through default value"):
                mock_instance = asynctest.MagicMock(spec)
                self.assertEqual([], run_coroutine(iterate(mock_instance)))

            with self.subTest("iterate through set return_value"):
                mock_instance = asynctest.MagicMock(spec)
                mock_instance.__aiter__.return_value = expected[:]

                self.assertEqual(expected, run_coroutine(iterate(mock_instance)))

            with self.subTest("iterate through set return_value iterator"):
                mock_instance = asynctest.MagicMock(spec)
                mock_instance.__aiter__.return_value = iter(expected[:])

                self.assertEqual(expected, run_coroutine(iterate(mock_instance)))
