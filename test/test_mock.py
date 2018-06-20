# coding: utf-8

import asyncio
import functools
import inspect
import unittest
import sys

import asynctest

from .utils import run_coroutine

if sys.version_info >= (3, 5):
    from . import test_mock_await as _using_await
else:
    _using_await = None


class Test:
    @asyncio.coroutine
    def a_coroutine(self):
        pass

    def a_function(self):
        pass

    def is_patched(self):
        return False

    def second_is_patched(self):
        return False

    a_dict = {'is_patched': False, 'second_is_patched': False}
    a_second_dict = {'is_patched': False}

    @asyncio.coroutine
    def a_coroutine_with_args(self, arg, arg2):
        return None

    @classmethod
    @asyncio.coroutine
    def a_classmethod_coroutine(cls):
        pass

    @staticmethod
    @asyncio.coroutine
    def a_staticmethod_coroutine():
        pass


class ProbeException(Exception):
    pass


if _using_await:
    Test = _using_await.patch_Test_Class(Test)


patch_is_patched = functools.partial(asynctest.mock.patch,
                                     'test.test_mock.Test.is_patched',
                                     new=lambda self: True)

patch_second_is_patched = functools.partial(
    asynctest.mock.patch, 'test.test_mock.Test.second_is_patched',
    new=lambda self: True)

patch_dict_is_patched = functools.partial(
    asynctest.mock.patch.dict, 'test.test_mock.Test.a_dict',
    values={"is_patched": True})

patch_dict_second_is_patched = functools.partial(
    asynctest.mock.patch.dict, 'test.test_mock.Test.a_dict',
    values={"second_is_patched": True})

patch_dict_second_dict_is_patched = functools.partial(
    asynctest.mock.patch.dict, 'test.test_mock.Test.a_second_dict',
    values={"is_patched": True})


def inject_class(obj):
    # Decorate _Test_* mixin classes so we can retrieve the mock class to test
    # with the last argument of the test function ("klass").
    if isinstance(obj, type):
        for attr_name in dir(obj):
            attr = getattr(obj, attr_name)
            if callable(attr) and attr_name.startswith('test_'):
                setattr(obj, attr_name, inject_class(attr))

        return obj
    else:
        @functools.wraps(obj)
        def wrapper(self):
            return obj(self, getattr(asynctest, self.class_to_test))

        return wrapper


@inject_class
class _Test_iscoroutinefunction:
    # Ensure that an instance of this mock type is seen as a coroutine function
    def test_asyncio_iscoroutinefunction(self, klass):
        with self.subTest(is_coroutine=False):
            mock = klass(is_coroutine=False)
            self.assertFalse(asyncio.iscoroutinefunction(mock))

        with self.subTest(is_coroutine=False):
            mock = klass(is_coroutine=True)
            self.assertTrue(asyncio.iscoroutinefunction(mock))


@inject_class
class _Test_is_coroutine_property:
    # Ensure an instance offers an is_coroutine property
    def test_is_coroutine_property(self, klass):
        mock = klass()
        self.assertFalse(mock.is_coroutine)

        mock.is_coroutine = True
        self.assertTrue(mock.is_coroutine)

        mock = klass(is_coroutine=True)
        self.assertTrue(mock.is_coroutine)


@inject_class
class _Test_subclass:
    # Ensure that the tested class is also a subclass of its counterpart in
    # the standard module unittest.mock
    def test_subclass(self, klass):
        unittest_klass = getattr(unittest.mock, self.class_to_test)

        self.assertTrue(issubclass(klass, unittest_klass))
        self.assertTrue(isinstance(klass(), unittest_klass))


@inject_class
class _Test_called_coroutine:
    # Ensure that an object mocking as a coroutine works
    def test_returns_coroutine(self, klass):
        mock = klass()

        coro = mock()
        # Suppress debug warning about non-running coroutine
        if isinstance(coro, asyncio.coroutines.CoroWrapper):
            coro.gen = None

        self.assertTrue(asyncio.iscoroutine(coro))

    def test_returns_coroutine_from_return_value(self, klass):
        mock = klass()
        mock.return_value = 'ProbeValue'

        self.assertEqual('ProbeValue', mock.return_value)
        self.assertEqual(mock.return_value, run_coroutine(mock()))

    def test_returns_coroutine_with_return_value_being_a_coroutine(self, klass):
        mock = klass()
        coroutine = asyncio.coroutine(lambda: 'ProbeValue')
        mock.return_value = coroutine()

        self.assertEqual('ProbeValue', run_coroutine(mock()))

    def test_returns_coroutine_from_side_effect(self, klass):
        mock = klass()
        mock.side_effect = lambda: 'ProbeValue'

        self.assertEqual('ProbeValue', run_coroutine(mock()))

    def test_returns_coroutine_from_side_effect_being_a_coroutine(self, klass):
        mock = klass()
        mock.side_effect = asyncio.coroutine(lambda: 'ProbeValue')

        self.assertEqual('ProbeValue', run_coroutine(mock()))

    def test_exception_side_effect_raises_in_coroutine(self, klass):
        mock = klass()
        mock.side_effect = ProbeException

        coroutine = mock()
        with self.assertRaises(ProbeException):
            run_coroutine(coroutine)

    def test_returns_coroutine_from_side_effect_being_an_iterable(self, klass):
        mock = klass()
        side_effect = ['Probe1', 'Probe2', 'Probe3']
        mock.side_effect = side_effect

        for expected in side_effect:
            self.assertEqual(expected, run_coroutine(mock()))

        with self.assertRaises(StopIteration):
            mock()


@inject_class
class _Test_Spec_Spec_Set_Returns_Coroutine_Mock:
    # Ensure that when a mock is configured with spec or spec_set, coroutines
    # are detected and mocked correctly
    def test_mock_returns_coroutine_according_to_spec(self, klass):
        spec = Test()

        for attr in ('spec', 'spec_set', ):
            with self.subTest(spec_type=attr):
                mock = klass(**{attr: spec})

                self.assertIsInstance(mock.a_function, (asynctest.Mock, asynctest.MagicMock))
                self.assertNotIsInstance(mock.a_function, asynctest.CoroutineMock)
                self.assertIsInstance(mock.a_coroutine, asynctest.CoroutineMock)
                self.assertIsInstance(mock.a_classmethod_coroutine, asynctest.CoroutineMock)
                self.assertIsInstance(mock.a_staticmethod_coroutine, asynctest.CoroutineMock)
                mock.a_coroutine.return_value = "PROBE"
                self.assertEqual("PROBE", run_coroutine(mock.a_coroutine()))

                if _using_await:
                    self.assertIsInstance(mock.an_async_coroutine, asynctest.CoroutineMock)
                    self.assertIsInstance(mock.an_async_classmethod_coroutine, asynctest.CoroutineMock)
                    self.assertIsInstance(mock.an_async_staticmethod_coroutine, asynctest.CoroutineMock)
                    mock.an_async_coroutine.return_value = "PROBE"
                    self.assertEqual("PROBE", run_coroutine(mock.an_async_coroutine()))

    # Ensure the name of the mock is correctly set, tests bug #49.
    def test_mock_has_correct_name(self, klass):
        spec = Test()

        for attr in ('spec', 'spec_set', ):
            with self.subTest(spec_type=attr):
                mock = klass(**{attr: spec})

                self.assertIn("{}='{}".format(attr, "Test"), repr(mock))
                self.assertIn("name='mock.a_coroutine'", repr(mock.a_coroutine))
                mock.a_coroutine()  # is a generator, not a Mock with a repr
                self.assertIn("name='mock.a_function()'", repr(mock.a_function()))
                self.assertEqual("call.a_coroutine()", repr(mock.mock_calls[0]))
                self.assertEqual("call.a_function()", repr(mock.mock_calls[1]))


@inject_class
class _Test_Spec_Spec_Set_Is_Function:
    def test_mock_is_not_coroutine_when_spec_is_function(self, klass):
        spec = Test.a_function

        for attr in ('spec', 'spec_set', ):
            with self.subTest(spec_type=attr):
                mock = klass(**{attr: spec})
                self.assertFalse(asyncio.iscoroutinefunction(mock))
                if hasattr(inspect, "iscoroutinefunction"):
                    self.assertFalse(inspect.iscoroutinefunction(mock))


@inject_class
class _Test_Future:
    # Ensure that a mocked Future is detected as a future
    def test_mock_a_future_is_a_future(self, klass):
        mock = klass(asyncio.Future())
        self.assertIsInstance(mock, asyncio.Future)

    def test_mock_from_create_future(self, klass):
        loop = asyncio.new_event_loop()

        try:
            if not (hasattr(loop, "create_future") and
                    hasattr(asyncio, "isfuture")):
                return

            mock = klass(loop.create_future())
            self.assertTrue(asyncio.isfuture(mock))
        finally:
            loop.close()


# Import mixins based on the support of async/await keywords
if _using_await:
    _Test_Mock_Of_Async_Magic_Methods = inject_class(
        _using_await._Test_Mock_Of_Async_Magic_Methods)
else:
    class _Test_Mock_Of_Async_Magic_Methods:
        pass


class Test_NonCallabableMock(unittest.TestCase, _Test_subclass,
                             _Test_iscoroutinefunction,
                             _Test_is_coroutine_property,
                             _Test_Spec_Spec_Set_Returns_Coroutine_Mock,
                             _Test_Spec_Spec_Set_Is_Function,
                             _Test_Future):
    class_to_test = 'NonCallableMock'


class Test_NonCallableMagicMock(unittest.TestCase, _Test_subclass,
                                _Test_iscoroutinefunction,
                                _Test_is_coroutine_property,
                                _Test_Spec_Spec_Set_Returns_Coroutine_Mock,
                                _Test_Spec_Spec_Set_Is_Function,
                                _Test_Future,
                                _Test_Mock_Of_Async_Magic_Methods):
    class_to_test = 'NonCallableMagicMock'


class Test_Mock(unittest.TestCase, _Test_subclass,
                _Test_Spec_Spec_Set_Returns_Coroutine_Mock,
                _Test_Spec_Spec_Set_Is_Function,
                _Test_Future):
    class_to_test = 'Mock'


class Test_MagicMock(unittest.TestCase, _Test_subclass,
                     _Test_Spec_Spec_Set_Returns_Coroutine_Mock,
                     _Test_Spec_Spec_Set_Is_Function,
                     _Test_Future, _Test_Mock_Of_Async_Magic_Methods):
    class_to_test = 'MagicMock'


class Test_CoroutineMock(unittest.TestCase, _Test_called_coroutine,
                         _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'CoroutineMock'

    def test_asyncio_iscoroutinefunction(self):
        mock = asynctest.mock.CoroutineMock()
        self.assertTrue(asyncio.iscoroutinefunction(mock))

    def test_called_CoroutineMock_returns_MagicMock(self):
        mock = asynctest.mock.CoroutineMock()
        self.assertIsInstance(run_coroutine(mock()), asynctest.mock.MagicMock)


class Test_CoroutineMock_awaited(asynctest.TestCase):
    @asynctest.fail_on(unused_loop=False)
    def test_awaited_delays_creation_of_condition(self):
        mock = asynctest.mock.CoroutineMock()
        self.assertIsNone(mock.awaited._condition)
        mock()
        self.assertIsNone(mock.awaited._condition)
        run_coroutine(mock())
        self.assertIsNotNone(mock.awaited._condition)

        @asyncio.coroutine
        def f():
            yield from mock.awaited._condition.acquire()
            yield from mock.awaited._condition.acquire()

        # Condition belongs to a loop created by run_coroutine, not current loop.
        with self.assertRaises(RuntimeError):
            run_coroutine(f())

    @asyncio.coroutine
    def test_awaited_CoroutineMock_sets_awaited(self):
        mock = asynctest.mock.CoroutineMock()
        yield from mock()
        self.assertTrue(mock.awaited)

        mock.reset_mock()
        self.assertFalse(mock.awaited)

        @asyncio.coroutine
        def side_effect():
            raise RuntimeError()

        mock = asynctest.mock.CoroutineMock(side_effect=side_effect)

        with self.assertRaises(RuntimeError):
            yield from mock()

    @asyncio.coroutine
    def test_awaited_CoroutineMock_counts(self):
        mock = asynctest.mock.CoroutineMock()
        yield from mock()
        yield from mock()
        self.assertEqual(mock.await_count, 2)

        mock.reset_mock()
        self.assertEqual(mock.await_count, 0)

        @asyncio.coroutine
        def side_effect():
            raise RuntimeError()

        mock = asynctest.mock.CoroutineMock(side_effect=side_effect)

        with self.assertRaises(RuntimeError):
            yield from mock()

        self.assertEqual(mock.await_count, 1)

        mock.reset_mock()
        mock.side_effect = RuntimeError

        with self.assertRaises(RuntimeError):
            yield from mock()

        self.assertEqual(mock.await_count, 1)

    @asyncio.coroutine
    def test_awaited_from_autospec_mock(self):
        mock = asynctest.mock.create_autospec(Test)
        self.assertFalse(mock.a_coroutine.awaited)
        self.assertEqual(0, mock.a_coroutine.await_count)

        yield from mock.a_coroutine()

        self.assertTrue(mock.a_coroutine.awaited)
        self.assertEqual(1, mock.a_coroutine.await_count)

    @asyncio.coroutine
    def test_awaited_wait(self):
        mock = asynctest.mock.CoroutineMock()
        t = asyncio.ensure_future(mock.awaited.wait())
        yield from mock()
        yield from mock()
        yield from t

        mock.reset_mock()
        t = asyncio.ensure_future(mock.awaited.wait(skip=1))
        yield from mock()
        self.assertFalse(t.done())
        yield from mock()
        yield from t

    @asyncio.coroutine
    def test_awaited_wait_next(self):
        mock = asynctest.mock.CoroutineMock()
        yield from mock()
        t = asyncio.ensure_future(mock.awaited.wait_next())
        yield from asyncio.sleep(0.01)
        self.assertFalse(t.done())
        yield from mock()
        yield from t

        mock.reset_mock()
        yield from mock()
        t = asyncio.ensure_future(mock.awaited.wait_next(skip=1))
        yield from asyncio.sleep(0.01)
        yield from mock()
        self.assertFalse(t.done())
        yield from mock()
        yield from t

    @asyncio.coroutine
    def test_await_args(self):
        with self.subTest('in order'):
            mock = asynctest.mock.CoroutineMock()
            t1 = mock('foo')
            t2 = mock('bar')
            yield from t1
            yield from t2
            self.assertEqual(mock.await_args, asynctest.call('bar'))

        with self.subTest('out of order'):
            mock = asynctest.mock.CoroutineMock()
            t1 = mock('foo')
            t2 = mock('bar')
            yield from t2
            yield from t1
            self.assertEqual(mock.await_args, asynctest.call('foo'))

    @asyncio.coroutine
    def test_await_args_list(self):
        with self.subTest('in order'):
            mock = asynctest.mock.CoroutineMock()
            t1 = mock('foo')
            t2 = mock('bar')
            yield from t1
            yield from t2
            self.assertEqual(mock.await_args_list, [asynctest.call('foo'), asynctest.call('bar')])

        with self.subTest('out of order'):
            mock = asynctest.mock.CoroutineMock()
            t1 = mock('foo')
            t2 = mock('bar')
            yield from t2
            yield from t1
            self.assertEqual(mock.await_args_list, [asynctest.call('bar'), asynctest.call('foo')])

    @asyncio.coroutine
    def test_assert_awaited(self):
        mock = asynctest.mock.CoroutineMock()

        with self.assertRaises(AssertionError):
            mock.assert_awaited()

        yield from mock()
        mock.assert_awaited()

    @asyncio.coroutine
    def test_assert_awaited_once(self):
        mock = asynctest.mock.CoroutineMock()

        with self.assertRaises(AssertionError):
            mock.assert_awaited_once()

        yield from mock()
        mock.assert_awaited_once()

        yield from mock()
        with self.assertRaises(AssertionError):
            mock.assert_awaited_once()

    @asyncio.coroutine
    def test_assert_awaited_with(self):
        mock = asynctest.mock.CoroutineMock()

        with self.assertRaises(AssertionError):
            mock.assert_awaited_with('foo')

        yield from mock('foo')
        mock.assert_awaited_with('foo')

        yield from mock('bar')
        with self.assertRaises(AssertionError):
            mock.assert_awaited_with('foo')

    @asyncio.coroutine
    def test_assert_awaited_once_with(self):
        mock = asynctest.mock.CoroutineMock()

        with self.assertRaises(AssertionError):
            mock.assert_awaited_once_with('foo')

        yield from mock('foo')
        mock.assert_awaited_once_with('foo')

        yield from mock('foo')
        with self.assertRaises(AssertionError):
            mock.assert_awaited_once_with('foo')

    @asyncio.coroutine
    def test_assert_any_wait(self):
        mock = asynctest.mock.CoroutineMock()

        with self.assertRaises(AssertionError):
            mock.assert_any_await('bar')

        yield from mock('foo')
        with self.assertRaises(AssertionError):
            mock.assert_any_await('bar')

        yield from mock('bar')
        mock.assert_any_await('bar')

        yield from mock('baz')
        mock.assert_any_await('bar')

    @asyncio.coroutine
    def test_assert_has_awaits(self):
        calls = [asynctest.call('bar'), asynctest.call('baz')]

        with self.subTest('any_order=False'):
            mock = asynctest.mock.CoroutineMock()

            with self.assertRaises(AssertionError):
                mock.assert_has_awaits(calls)

            yield from mock('foo')
            with self.assertRaises(AssertionError):
                mock.assert_has_awaits(calls)

            yield from mock('bar')
            with self.assertRaises(AssertionError):
                mock.assert_has_awaits(calls)

            yield from mock('baz')
            mock.assert_has_awaits(calls)

            yield from mock('qux')
            mock.assert_has_awaits(calls)

        with self.subTest('any_order=True'):
            mock = asynctest.mock.CoroutineMock()

            with self.assertRaises(AssertionError):
                mock.assert_has_awaits(calls, any_order=True)

            yield from mock('baz')
            with self.assertRaises(AssertionError):
                mock.assert_has_awaits(calls, any_order=True)

            yield from mock('foo')
            with self.assertRaises(AssertionError):
                mock.assert_has_awaits(calls, any_order=True)

            yield from mock('bar')
            mock.assert_has_awaits(calls, any_order=True)

            yield from mock('qux')
            mock.assert_has_awaits(calls, any_order=True)

    @asyncio.coroutine
    def test_assert_not_awaited(self):
        mock = asynctest.mock.CoroutineMock()

        mock.assert_not_awaited()

        yield from mock()
        with self.assertRaises(AssertionError):
            mock.assert_not_awaited()


class TestMockInheritanceModel(unittest.TestCase):
    to_test = {
        'NonCallableMagicMock': 'NonCallableMock',
        'Mock': 'NonCallableMock',
        'MagicMock': 'Mock',
        'CoroutineMock': 'Mock',
    }

    def test_Mock_is_not_CoroutineMock(self):
        self.assertNotIsInstance(asynctest.mock.Mock(), asynctest.mock.CoroutineMock)

    def test_MagicMock_is_not_CoroutineMock(self):
        self.assertNotIsInstance(asynctest.mock.MagicMock(), asynctest.mock.CoroutineMock)

    @staticmethod
    def make_inheritance_test(child, parent):
        def test(self):
            # Works in the common case
            self.assertIsInstance(getattr(asynctest.mock, child)(),
                                  getattr(asynctest.mock, parent))

            # Works with a custom spec
            self.assertIsInstance(getattr(asynctest.mock, child)(Test()),
                                  getattr(asynctest.mock, parent))

        return test


for child, parent in TestMockInheritanceModel.to_test.items():
    setattr(TestMockInheritanceModel,
            'test_{}_inherits_from_{}'.format(child, parent),
            TestMockInheritanceModel.make_inheritance_test(child, parent))

#
# mock_open()
#


class Test_mock_open(unittest.TestCase):
    def test_MagicMock_returned_by_default(self):
        self.assertIsInstance(asynctest.mock_open(), asynctest.MagicMock)

#
# Test patches
#


class Test_patch(unittest.TestCase):
    def test_patch_as_context_manager_uses_MagicMock(self):
        with asynctest.mock.patch('test.test_mock.Test') as mock:
            self.assertIsInstance(mock, asynctest.mock.MagicMock)

        with asynctest.mock.patch('test.test_mock.Test.a_function') as mock:
            self.assertIsInstance(mock, asynctest.mock.MagicMock)

    def test_patch_as_decorator_uses_MagicMock(self):
        called = []

        @asynctest.mock.patch('test.test_mock.Test')
        def test_mock_class(mock):
            self.assertIsInstance(mock, asynctest.mock.MagicMock)
            called.append("test_mock_class")

        @asynctest.mock.patch('test.test_mock.Test.a_function')
        def test_mock_function(mock):
            self.assertIsInstance(mock, asynctest.mock.MagicMock)
            called.append("test_mock_function")

        test_mock_class()
        test_mock_function()

        self.assertIn("test_mock_class", called)
        self.assertIn("test_mock_function", called)

    def test_patch_as_decorator_uses_CoroutineMock_on_coroutine_function(self):
        called = False

        @asynctest.mock.patch('test.test_mock.Test.a_coroutine')
        def test_mock_coroutine(mock):
            nonlocal called
            self.assertIsInstance(mock, asynctest.mock.CoroutineMock)
            called = True

        test_mock_coroutine()
        self.assertTrue(called)

    def test_patch_as_decorator_uses_CoroutineMock_on_classmethod_coroutine_function(self):
        called = False

        @asynctest.mock.patch("test.test_mock.Test.a_classmethod_coroutine")
        def test_mock_coroutine(mock):
            nonlocal called
            self.assertIsInstance(mock, asynctest.mock.CoroutineMock)
            called = True

        test_mock_coroutine()
        self.assertTrue(called)

    def test_patch_as_decorator_uses_CoroutineMock_on_staticmethod_coroutine_function(self):
        called = False

        @asynctest.mock.patch("test.test_mock.Test.a_staticmethod_coroutine")
        def test_mock_coroutine(mock):
            nonlocal called
            self.assertIsInstance(mock, asynctest.mock.CoroutineMock)
            called = True

        test_mock_coroutine()
        self.assertTrue(called)

    def test_patch_as_context_manager_uses_CoroutineMock_on_coroutine_function(self):
        with asynctest.mock.patch('test.test_mock.Test.a_coroutine') as mock:
            import test.test_mock
            self.assertIs(test.test_mock.Test.a_coroutine, mock)
            self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

    def test_patch_as_context_manager_uses_CoroutineMock_on_classmethod_coroutine_function(self):
        with asynctest.mock.patch('test.test_mock.Test.a_classmethod_coroutine') as mock:
            import test.test_mock
            self.assertIs(test.test_mock.Test.a_classmethod_coroutine, mock)
            self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

    def test_patch_as_context_manager_uses_CoroutineMock_on_staticmethod_coroutine_function(self):
        with asynctest.mock.patch('test.test_mock.Test.a_staticmethod_coroutine') as mock:
            import test.test_mock
            self.assertIs(test.test_mock.Test.a_staticmethod_coroutine, mock)
            self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

    if _using_await:
        def test_patch_as_context_manager_uses_CoroutineMock_on_async_coroutine_function(self):
            with asynctest.mock.patch('test.test_mock.Test.an_async_coroutine') as mock:
                import test.test_mock
                self.assertIs(test.test_mock.Test.an_async_coroutine, mock)
                self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

        def test_patch_as_context_manager_uses_CoroutineMock_on_async_classmethod_coroutine_function(self):
            with asynctest.mock.patch('test.test_mock.Test.an_async_classmethod_coroutine') as mock:
                import test.test_mock
                self.assertIs(test.test_mock.Test.an_async_classmethod_coroutine, mock)
                self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

        def test_patch_as_context_manager_uses_CoroutineMock_on_async_staticmethod_coroutine_function(self):
            with asynctest.mock.patch('test.test_mock.Test.an_async_staticmethod_coroutine') as mock:
                import test.test_mock
                self.assertIs(test.test_mock.Test.an_async_staticmethod_coroutine, mock)
                self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

        def test_patch_as_decorator_uses_CoroutineMock_on_async_coroutine_function(self):
            called = False

            @asynctest.mock.patch('test.test_mock.Test.an_async_coroutine')
            def test_mock_coroutine(mock):
                nonlocal called
                self.assertIsInstance(mock, asynctest.mock.CoroutineMock)
                called = True

            test_mock_coroutine()
            self.assertTrue(called)

        def test_patch_as_decorator_uses_CoroutineMock_on_async_classmethod_coroutine_function(self):
            called = False

            @asynctest.mock.patch('test.test_mock.Test.an_async_classmethod_coroutine')
            def test_mock_coroutine(mock):
                nonlocal called
                self.assertIsInstance(mock, asynctest.mock.CoroutineMock)
                called = True

            test_mock_coroutine()
            self.assertTrue(called)

        def test_patch_as_decorator_uses_CoroutineMock_on_async_staticmethod_coroutine_function(self):
            called = False

            @asynctest.mock.patch('test.test_mock.Test.an_async_staticmethod_coroutine')
            def test_mock_coroutine(mock):
                nonlocal called
                self.assertIsInstance(mock, asynctest.mock.CoroutineMock)
                called = True

            test_mock_coroutine()
            self.assertTrue(called)

    def test_patch_is_enabled_when_running_decorated_coroutine(self):
        @asyncio.coroutine
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().is_patched()

        coroutines = [a_coroutine]
        if _using_await:
            coroutines.append(_using_await.transform(a_coroutine))

        for coroutine in coroutines:
            with self.subTest(coroutine=coroutine):
                self.assertTrue(run_coroutine(patch_is_patched()(coroutine)()))

    def test_patch_is_enabled_when_running_decorated_function(self):
        @patch_is_patched()
        def a_function():
            import test.test_mock
            return test.test_mock.Test().is_patched()

        self.assertTrue(a_function())


class Test_patch_decorator_coroutine_or_generator(unittest.TestCase):
    def test_coroutine_type_when_patched(self):
        @asyncio.coroutine
        def a_coroutine():
            pass

        a_patched_coroutine = patch_is_patched()(a_coroutine)

        self.assertEqual(asyncio.iscoroutinefunction(a_patched_coroutine),
                         asyncio.iscoroutinefunction(a_coroutine))
        self.assertEqual(inspect.isgeneratorfunction(a_patched_coroutine),
                         inspect.isgeneratorfunction(a_coroutine))
        coro = a_coroutine()
        patched_coro = a_patched_coroutine()
        try:
            self.assertEqual(asyncio.iscoroutine(patched_coro),
                             asyncio.iscoroutine(coro))
        finally:
            run_coroutine(coro)
            run_coroutine(patched_coro)

        if not _using_await:
            return

        a_coroutine = _using_await.transform(a_coroutine)
        a_patched_coroutine = patch_is_patched()(a_coroutine)
        self.assertEqual(asyncio.iscoroutinefunction(a_patched_coroutine),
                         asyncio.iscoroutinefunction(a_coroutine))
        coro = a_coroutine()
        patched_coro = a_patched_coroutine()
        try:
            self.assertEqual(asyncio.iscoroutine(patched_coro),
                             asyncio.iscoroutine(coro))
        finally:
            run_coroutine(coro)
            run_coroutine(patched_coro)

    def test_generator_arg_is_default_mock(self):
        @asynctest.mock.patch('test.test_mock.Test')
        def a_generator(mock):
            self.assertIsInstance(mock, asynctest.mock.Mock)
            yield
            import test.test_mock
            self.assertIs(mock, test.test_mock.Test)

        for _ in a_generator():
            pass

    def test_coroutine_arg_is_default_mock(self):
        @asyncio.coroutine
        def tester(coroutine_function):
            loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)
            loop.call_soon(fut.set_result, None)
            before, after = yield from coroutine_function(fut)
            self.assertTrue(before)
            self.assertTrue(after)

        def is_instance_of_mock(obj):
            return isinstance(obj, asynctest.mock.Mock)

        def is_same_mock(obj):
            import test.test_mock
            return obj is test.test_mock.Test

        with self.subTest("old style coroutine"):
            @asynctest.mock.patch('test.test_mock.Test')
            def a_coroutine(fut, mock):
                before = is_instance_of_mock(mock)
                yield from fut
                after = is_same_mock(mock)
                return before, after

            run_coroutine(tester(a_coroutine))

        if not _using_await:
            return

        with self.subTest("new style coroutine"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                is_instance_of_mock, is_same_mock)
            a_new_style_coroutine = asynctest.mock.patch(
                'test.test_mock.Test')(a_new_style_coroutine)
            run_coroutine(tester(a_new_style_coroutine))


class Test_patch_object(unittest.TestCase):
    def test_patch_with_MagicMock(self):
        with asynctest.mock.patch.object(Test(), 'a_function') as mock:
            self.assertIsInstance(mock, asynctest.mock.MagicMock)

        obj = Test()
        obj.test = Test()
        with asynctest.mock.patch.object(obj, 'test') as mock:
            self.assertIsInstance(mock, asynctest.mock.MagicMock)

    def test_patch_coroutine_function_with_CoroutineMock(self):
        with asynctest.mock.patch.object(Test(), 'a_coroutine') as mock:
            self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

        if _using_await:
            with asynctest.mock.patch.object(Test(), 'an_async_coroutine') as mock:
                self.assertIsInstance(mock, asynctest.mock.CoroutineMock)

    def test_patch_decorates_coroutine(self):
        obj = Test()

        patch = functools.partial(asynctest.mock.patch.object,
                                  obj, 'is_patched', new=lambda: True)

        @asyncio.coroutine
        def a_coroutine():
            return obj.is_patched()

        coroutines = [a_coroutine]
        if _using_await:
            coroutines.append(_using_await.transform(a_coroutine))

        for coroutine in coroutines:
            with self.subTest(coroutine=coroutine):
                self.assertTrue(run_coroutine(patch()(coroutine)()))


class Test_patch_multiple(unittest.TestCase):
    def test_patch_with_MagicMock(self):
        default = asynctest.mock.DEFAULT
        with asynctest.mock.patch.multiple('test.test_mock', Test=default):
            import test.test_mock
            self.assertIsInstance(test.test_mock.Test, asynctest.mock.MagicMock)

    def test_patch_coroutine_function_with_CoroutineMock(self):
        default = asynctest.mock.DEFAULT

        also_patch = {}
        if _using_await:
            also_patch['an_async_coroutine'] = default

        with asynctest.mock.patch.multiple('test.test_mock.Test',
                                           a_function=default,
                                           a_coroutine=default,
                                           **also_patch):
            import test.test_mock
            obj = test.test_mock.Test()
            self.assertIsInstance(obj.a_function, asynctest.mock.MagicMock)
            self.assertIsInstance(obj.a_coroutine, asynctest.mock.CoroutineMock)

            if _using_await:
                self.assertIsInstance(obj.an_async_coroutine,
                                      asynctest.mock.CoroutineMock)

    def test_patch_decorates_coroutine(self):
        patch = functools.partial(asynctest.mock.patch.multiple,
                                  'test.test_mock.Test',
                                  is_patched=lambda self: True)

        @asyncio.coroutine
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().is_patched()

        coroutines = [a_coroutine]
        if _using_await:
            coroutines.append(_using_await.transform(a_coroutine))

        for coroutine in coroutines:
            with self.subTest(coroutine=coroutine):
                self.assertTrue(run_coroutine(patch()(coroutine)()))


class Test_patch_dict(unittest.TestCase):
    def test_patch_decorates_coroutine(self):
        @asyncio.coroutine
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().a_dict['is_patched']

        coroutines = [a_coroutine]

        if _using_await:
            coroutines.append(_using_await.transform(a_coroutine))

        for coroutine in coroutines:
            with self.subTest(coroutine=coroutine):
                self.assertTrue(run_coroutine(patch_dict_is_patched()(coroutine)()))

    def test_patch_decorates_function(self):
        @patch_dict_is_patched()
        def a_function():
            import test.test_mock
            return test.test_mock.Test().a_dict['is_patched']

        self.assertTrue(a_function())

    def test_patch_decorates_class(self):
        import test.test_mock

        @patch_dict_is_patched()
        class Patched:
            @asyncio.coroutine
            def test_a_coroutine(self):
                return test.test_mock.Test().a_dict['is_patched']

            def test_a_function(self):
                return test.test_mock.Test().a_dict['is_patched']

        instance = Patched()
        self.assertFalse(test.test_mock.Test().a_dict['is_patched'])
        self.assertTrue(instance.test_a_function())
        self.assertFalse(test.test_mock.Test().a_dict['is_patched'])
        self.assertTrue(run_coroutine(instance.test_a_coroutine()))
        self.assertFalse(test.test_mock.Test().a_dict['is_patched'])


class Test_patch_autospec(unittest.TestCase):
    test_class_path = "{}.Test".format(__name__)

    def test_autospec_coroutine(self):
        called = False

        @asynctest.mock.patch(self.test_class_path, autospec=True)
        def patched(mock):
            nonlocal called
            called = True
            self.assertIsInstance(mock.a_coroutine,
                                  asynctest.mock.CoroutineMock)

            self.assertIsInstance(mock().a_coroutine,
                                  asynctest.mock.CoroutineMock)

            self.assertIsInstance(mock.a_function, asynctest.mock.Mock)
            self.assertIsInstance(mock().a_function, asynctest.mock.Mock)

            if _using_await:
                self.assertIsInstance(mock.an_async_coroutine,
                                      asynctest.mock.CoroutineMock)
                self.assertIsInstance(mock().an_async_coroutine,
                                      asynctest.mock.CoroutineMock)

        patched()
        self.assertTrue(called)

    def test_patch_autospec_with_patches_on_top(self):
        called = False

        @asynctest.mock.patch("{}.{}".format(self.test_class_path, "is_patched"),
                              return_value=True)
        @asynctest.mock.patch("{}.{}".format(self.test_class_path, "a_coroutine"),
                              autospec=True)
        def patched_function(coroutine_mock, is_patched_mock):
            nonlocal called
            called = True

            self.assertIsInstance(Test.is_patched, asynctest.mock.Mock)
            self.assertTrue(Test.is_patched())
            self.assertTrue(asyncio.iscoroutinefunction(coroutine_mock))
            self.assertTrue(asyncio.iscoroutinefunction(Test.a_coroutine))

        patched_function()
        self.assertTrue(called)

    def test_patch_autospec_with_patches_under(self):
        called = False

        @asynctest.mock.patch("{}.{}".format(self.test_class_path, "a_coroutine"),
                              autospec=True)
        @asynctest.mock.patch("{}.{}".format(self.test_class_path, "is_patched"),
                              return_value=True)
        def patched_function(is_patched_mock, coroutine_mock):
            nonlocal called
            called = True

            self.assertIsInstance(Test.is_patched, asynctest.mock.Mock)
            self.assertTrue(Test.is_patched())
            self.assertTrue(asyncio.iscoroutinefunction(coroutine_mock))
            self.assertTrue(asyncio.iscoroutinefunction(Test.a_coroutine))

        patched_function()
        self.assertTrue(called)

    def test_patch_object_autospec(self):
        called = False

        @asynctest.mock.patch.object(Test, "a_coroutine_with_args", autospec=True)
        def patched_function(patched):
            nonlocal called
            called = True

            self.assertTrue(asyncio.iscoroutinefunction(Test.a_coroutine_with_args))
            with self.assertRaisesRegex(TypeError, "arg2"):
                run_coroutine(Test().a_coroutine_with_args("arg"))

            self.assertTrue(run_coroutine(Test().a_coroutine_with_args("arg", "arg2")))

        patched_function()
        self.assertTrue(called)

    def test_patch_multiple_autospec(self):
        called = False
        default = asynctest.mock.DEFAULT

        @asynctest.mock.patch.multiple(Test, autospec=True,
                                       a_coroutine=default,
                                       a_coroutine_with_args=default)
        def patched_function(**patched):
            nonlocal called
            called = True

            with self.assertRaisesRegex(TypeError, "arg2"):
                run_coroutine(Test().a_coroutine_with_args("arg"))

            test = Test()
            self.assertTrue(run_coroutine(test.a_coroutine()))
            self.assertTrue(run_coroutine(test.a_coroutine_with_args("arg", "arg2")))

        patched_function()
        self.assertTrue(called)

#
# patch scopes
#


class patch_scope_TestCase(unittest.TestCase):
    def is_patched(self):
        import test.test_mock
        return test.test_mock.Test().is_patched()

    def second_is_patched(self):
        import test.test_mock
        return test.test_mock.Test().second_is_patched()

    def _test_deactivate_patch_when_generator_init_fails(self, scope):
        @patch_is_patched(scope=scope)
        def a_generator(wrong_number_of_args):
            yield

        try:
            gen = a_generator()
            next(gen)
            self.fail("Exception must raise")
        except TypeError:
            pass

        self.assertFalse(self.is_patched())

    def _test_deactivate_patch_when_generator_exec_fails(self, scope):
        @patch_is_patched(scope=scope)
        @asyncio.coroutine
        def a_coroutine(missing_arg):
            return

        with self.subTest("old style coroutine"):
            @asyncio.coroutine
            def tester():
                try:
                    yield from a_coroutine()
                    self.fail("Exception must raise")
                except TypeError:
                    pass

                self.assertFalse(self.is_patched())

            run_coroutine(tester())

        if not _using_await:
            return

        with self.subTest("new style coroutine"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                lambda missing_arg: None)
            a_new_style_coroutine = patch_is_patched(scope=scope)(
                a_new_style_coroutine)

            @asyncio.coroutine
            def tester():
                try:
                    yield from a_new_style_coroutine()
                    self.fail("Exception must raise")
                except TypeError:
                    pass

                self.assertFalse(self.is_patched())

            run_coroutine(tester())


class patch_dict_scope_TestCase(unittest.TestCase):
    def is_patched(self):
        import test.test_mock
        return test.test_mock.Test().a_dict['is_patched']

    def second_is_patched(self):
        import test.test_mock
        return test.test_mock.Test().a_dict['second_is_patched']

    def second_dict_is_patched(self):
        import test.test_mock
        return test.test_mock.Test().a_second_dict['is_patched']


class Test_patch_dict_decorator_coroutine_or_generator_scope(
        patch_dict_scope_TestCase):
    def test_default_scope_is_global(self):
        @patch_dict_is_patched()
        def a_generator():
            yield self.is_patched()
            yield self.is_patched()

        gen = a_generator()
        self.assertTrue(next(gen))
        self.assertTrue(self.is_patched())
        self.assertTrue(next(gen))

    def test_scope_limited(self):
        @patch_dict_is_patched(scope=asynctest.LIMITED)
        def a_generator():
            yield self.is_patched()
            yield self.is_patched()

        gen = a_generator()
        self.assertTrue(next(gen))
        self.assertFalse(self.is_patched())
        self.assertTrue(next(gen))

    def test_patch_generator_with_multiple_scopes(self):
        with self.subTest("Outher: GLOBAL, inner: LIMITED"):
            @patch_dict_is_patched(scope=asynctest.GLOBAL)
            @patch_dict_second_dict_is_patched(scope=asynctest.LIMITED)
            def a_generator():
                yield (self.is_patched(), self.second_dict_is_patched())
                yield (self.is_patched(), self.second_dict_is_patched())

            gen = a_generator()
            self.assertEqual((True, True), next(gen))
            self.assertEqual(
                (True, False),
                (self.is_patched(), self.second_dict_is_patched()))
            self.assertEqual((True, True), next(gen))

        with self.subTest("Outher: LIMITED, inner: GLOBAL"):
            @patch_dict_is_patched(scope=asynctest.LIMITED)
            @patch_dict_second_dict_is_patched(scope=asynctest.GLOBAL)
            def a_generator():
                yield (self.is_patched(), self.second_dict_is_patched())
                yield (self.is_patched(), self.second_dict_is_patched())

            gen = a_generator()
            self.assertEqual((True, True), next(gen))
            self.assertEqual(
                (False, True),
                (self.is_patched(), self.second_dict_is_patched()))
            self.assertEqual((True, True), next(gen))

    def test_patch_generator_with_multiple_scopes_on_same_dict(self):
        import test.test_mock

        def tester():
            test.test_mock.Test.a_dict['overriden_value'] = True
            for _ in range(2):
                yield (
                    self.is_patched(), self.second_is_patched(),
                    test.test_mock.Test.a_dict.get('overriden_value', False))

        with self.subTest("Outher: GLOBAL, inner: LIMITED"):
            @patch_dict_is_patched(scope=asynctest.GLOBAL)
            @patch_dict_second_is_patched(scope=asynctest.LIMITED)
            def a_generator():
                yield from tester()

            gen = a_generator()
            self.assertEqual((True, True, True), next(gen))
            self.assertEqual((True, False),
                             (self.is_patched(), self.second_is_patched()))
            self.assertNotIn('overriden_value', test.test_mock.Test.a_dict)
            self.assertEqual((True, True, True), next(gen))

        with self.subTest("Outher: LIMITED, inner: GLOBAL"):
            @patch_dict_is_patched(scope=asynctest.LIMITED)
            @patch_dict_second_is_patched(scope=asynctest.GLOBAL)
            def a_generator():
                yield from tester()

            gen = a_generator()
            self.assertEqual((True, True, True), next(gen))
            self.assertEqual((False, True),
                             (self.is_patched(), self.second_is_patched()))
            self.assertNotIn('overriden_value', test.test_mock.Test.a_dict)
            self.assertEqual((True, True, True), next(gen))

    def test_patch_coroutine_with_multiple_scopes(self):
        def tester():
            return (self.is_patched(), self.second_dict_is_patched())

        @asyncio.coroutine
        def tester_couroutine(future):
            before = tester()
            yield from future
            after = tester()
            return before, after

        def run_test(a_coroutine):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                future = asyncio.Future(loop=loop)
                task = loop.create_task(a_coroutine(future))
                loop.call_soon(lambda: future.set_result(tester()))
                before, after = loop.run_until_complete(task)
            finally:
                loop.close()

            return before, future.result(), after

        with self.subTest("old style coroutine - Outher: GLOBAL, inner: LIMITED"):
            @patch_dict_is_patched(scope=asynctest.GLOBAL)
            @patch_dict_second_dict_is_patched(scope=asynctest.LIMITED)
            @asyncio.coroutine
            def a_coroutine(future):
                return (yield from tester_couroutine(future))

            before, between, after = run_test(a_coroutine)
            self.assertEqual((True, True), before)
            self.assertEqual((True, False), between)
            self.assertEqual((True, True), after)

        with self.subTest("old style coroutine - Outher: LIMITED, inner: GLOBAL"):
            @patch_dict_is_patched(scope=asynctest.LIMITED)
            @patch_dict_second_dict_is_patched(scope=asynctest.GLOBAL)
            @asyncio.coroutine
            def a_coroutine(future):
                return (yield from tester_couroutine(future))

            before, between, after = run_test(a_coroutine)
            self.assertEqual((True, True), before)
            self.assertEqual((False, True), between)
            self.assertEqual((True, True), after)

        if not _using_await:
            return

        tester_coroutine = _using_await.build_simple_coroutine(tester)

        with self.subTest("new style coroutine - Outher: GLOBAL, inner: LIMITED"):
            a_coroutine = patch_dict_is_patched(scope=asynctest.GLOBAL)(
                patch_dict_second_dict_is_patched(scope=asynctest.LIMITED)(
                    tester_coroutine))

            before, between, after = run_test(a_coroutine)
            self.assertEqual((True, True), before)
            self.assertEqual((True, False), between)
            self.assertEqual((True, True), after)

        with self.subTest("old style coroutine - Outher: LIMITED, inner: GLOBAL"):
            a_coroutine = patch_dict_is_patched(scope=asynctest.LIMITED)(
                patch_dict_second_dict_is_patched(scope=asynctest.GLOBAL)(
                    tester_coroutine))

            before, between, after = run_test(a_coroutine)
            self.assertEqual((True, True), before)
            self.assertEqual((False, True), between)
            self.assertEqual((True, True), after)


class Test_patch_and_patch_dict_scope(unittest.TestCase):
    def test_both_patch_and_patch_dict_with_scope_global(self):
        def test_result():
            import test.test_mock
            instance = test.test_mock.Test()
            return (instance.is_patched(), instance.a_dict['is_patched'])

        with self.subTest("patch and patch.dict"):
            @patch_dict_is_patched(scope=asynctest.GLOBAL)
            @patch_is_patched(scope=asynctest.GLOBAL)
            @asyncio.coroutine
            def a_coroutine():
                return test_result()

            self.assertEqual((True, True), run_coroutine(a_coroutine()))

        with self.subTest("patch.dict and patch"):
            @patch_is_patched(scope=asynctest.GLOBAL)
            @patch_dict_is_patched(scope=asynctest.GLOBAL)
            @asyncio.coroutine
            def a_coroutine():
                return test_result()

            self.assertEqual((True, True), run_coroutine(a_coroutine()))

    def test_both_patch_and_patch_dict_with_scope_limited(self):
        import test.test_mock
        instance = test.test_mock.Test()

        def test_result(instance):
            yield (instance.is_patched(), instance.a_dict['is_patched'])
            yield (instance.is_patched(), instance.a_dict['is_patched'])

        with self.subTest("patch and patch.dict"):
            @patch_dict_is_patched(scope=asynctest.LIMITED)
            @patch_is_patched(scope=asynctest.LIMITED)
            def a_generator(instance):
                yield from test_result(instance)

            gen = a_generator(instance)
            self.assertEqual((True, True), next(gen))
            self.assertEqual((False, False),
                             (instance.is_patched(),
                              instance.a_dict['is_patched']))
            self.assertEqual((True, True), next(gen))

        with self.subTest("patch.dict and patch"):
            @patch_is_patched(scope=asynctest.LIMITED)
            @patch_dict_is_patched(scope=asynctest.LIMITED)
            def a_generator(instance):
                yield from test_result(instance)

            gen = a_generator(instance)
            self.assertEqual((True, True), next(gen))
            self.assertEqual((False, False),
                             (instance.is_patched(),
                              instance.a_dict['is_patched']))
            self.assertEqual((True, True), next(gen))


class Test_patch_decorator_coroutine_or_generator_scope(patch_scope_TestCase):
    # Tests of patch() related to the use of scope=*, with several scopes used
    def test_default_scope_is_global(self):
        @patch_is_patched()
        def a_generator():
            yield self.is_patched()
            yield self.is_patched()

        gen = a_generator()
        self.assertTrue(next(gen))
        self.assertTrue(self.is_patched())
        self.assertTrue(next(gen))

    def test_patch_generator_with_multiple_scopes(self):
        def a_generator():
            yield (self.is_patched(), self.second_is_patched())
            yield (self.is_patched(), self.second_is_patched())

        with self.subTest("Outher: GLOBAL, inner: LIMITED"):
            @patch_is_patched(scope=asynctest.GLOBAL)
            @patch_second_is_patched(scope=asynctest.LIMITED)
            def patched():
                yield from a_generator()

            gen = patched()
            self.assertEqual((True, True), next(gen))
            self.assertTrue(self.is_patched())
            self.assertFalse(self.second_is_patched())
            self.assertEqual((True, True), next(gen))

        with self.subTest("Outher: LIMITED, inner: GLOBAL"):
            @patch_second_is_patched(scope=asynctest.LIMITED)
            @patch_is_patched(scope=asynctest.GLOBAL)
            def patched():
                yield from a_generator()

            gen = patched()
            self.assertEqual((True, True), next(gen))
            self.assertTrue(self.is_patched())
            self.assertFalse(self.second_is_patched())
            self.assertEqual((True, True), next(gen))

    def test_patch_coroutine_with_multiple_scopes(self):
        def set_fut_result(fut):
            fut.set_result((self.is_patched(), self.second_is_patched()))

        @asyncio.coroutine
        def tester(coro_function):
            loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)
            loop.call_soon(set_fut_result, fut)
            before, after = yield from coro_function(fut)
            self.assertEqual((True, True), before)
            self.assertEqual((True, False), fut.result())
            self.assertEqual((True, True), after)
            self.assertFalse(self.is_patched())
            self.assertFalse(self.second_is_patched())

        with self.subTest("old style coroutine - Outher: GLOBAL, inner: LIMITED"):
            @patch_is_patched(scope=asynctest.GLOBAL)
            @patch_second_is_patched(scope=asynctest.LIMITED)
            def a_coroutine(fut):
                before = (self.is_patched(), self.second_is_patched())
                yield from fut
                after = (self.is_patched(), self.second_is_patched())
                return before, after

            run_coroutine(tester(a_coroutine))

        with self.subTest("old style coroutine - Outher: LIMITED, inner: GLOBAL"):
            @patch_second_is_patched(scope=asynctest.LIMITED)
            @patch_is_patched(scope=asynctest.GLOBAL)
            def a_coroutine(fut):
                before = (self.is_patched(), self.second_is_patched())
                yield from fut
                after = (self.is_patched(), self.second_is_patched())
                return before, after

            run_coroutine(tester(a_coroutine))

        if not _using_await:
            return

        with self.subTest("new style coroutine - Outher: GLOBAL, inner: LIMITED"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                lambda: (self.is_patched(), self.second_is_patched()))
            a_new_style_coroutine = patch_second_is_patched(scope=asynctest.LIMITED)(
                a_new_style_coroutine)
            a_new_style_coroutine = patch_is_patched(scope=asynctest.GLOBAL)(
                a_new_style_coroutine)
            run_coroutine(tester(a_new_style_coroutine))

        with self.subTest("new style coroutine - Outher: LIMITED, inner: GLOBAL"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                lambda: (self.is_patched(), self.second_is_patched()))
            a_new_style_coroutine = patch_is_patched(scope=asynctest.GLOBAL)(
                a_new_style_coroutine)
            a_new_style_coroutine = patch_second_is_patched(scope=asynctest.LIMITED)(
                a_new_style_coroutine)
            run_coroutine(tester(a_new_style_coroutine))


class Test_patch_decorator_coroutine_or_generator_scope_GLOBAL(patch_scope_TestCase):
    # Tests of patch() using scope=GLOBAL
    def test_deactivate_patch_when_generator_init_fails(self):
        self._test_deactivate_patch_when_generator_init_fails(asynctest.GLOBAL)

    def test_deactivate_patch_when_generator_exec_fails(self):
        self._test_deactivate_patch_when_generator_exec_fails(asynctest.GLOBAL)

    def test_patch_generator_during_its_lifetime(self):
        @patch_is_patched(scope=asynctest.GLOBAL)
        def a_generator():
            yield self.is_patched()
            yield self.is_patched()

        gen = a_generator()
        self.assertTrue(next(gen))
        self.assertTrue(self.is_patched())
        self.assertTrue(next(gen))
        # exhaust the generator
        try:
            next(gen)
            self.fail("Coroutine must be stopped")
        except StopIteration:
            pass
        self.assertFalse(self.is_patched())

    def test_patch_coroutine_during_its_lifetime(self):
        def set_fut_result(fut):
            fut.set_result(self.is_patched())

        @asyncio.coroutine
        def tester(coro_function):
            loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)
            loop.call_soon(set_fut_result, fut)
            before, after = yield from coro_function(fut)
            self.assertTrue(before)
            self.assertTrue(fut.result())
            self.assertTrue(after)
            self.assertFalse(self.is_patched())

        with self.subTest("old style coroutine"):
            @patch_is_patched(scope=asynctest.GLOBAL)
            def a_coroutine(fut):
                before = self.is_patched()
                yield from fut
                after = self.is_patched()
                return before, after

            run_coroutine(tester(a_coroutine))

        if not _using_await:
            return

        with self.subTest("new style coroutine"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                self.is_patched)
            a_new_style_coroutine = patch_is_patched(scope=asynctest.GLOBAL)(
                a_new_style_coroutine)
            run_coroutine(tester(a_new_style_coroutine))

    # It's really hard to test this behavior for a coroutine, but I assume it's
    # fine as long as the implementation is shared with a generator. Also, it's
    # really hard to fall in a case like this one with a coroutine.
    def test_patch_stopped_when_generator_is_collected(self):
        @patch_is_patched(scope=asynctest.GLOBAL)
        def a_generator():
            yield self.is_patched()

        gen = a_generator()
        self.assertTrue(next(gen))
        self.assertTrue(self.is_patched())
        del gen
        self.assertFalse(self.is_patched())

    def test_multiple_patches_on_generator(self):
        @patch_second_is_patched(scope=asynctest.GLOBAL)
        @patch_is_patched(scope=asynctest.GLOBAL)
        def a_generator():
            yield self.is_patched() and self.second_is_patched()
            yield self.is_patched() and self.second_is_patched()

        gen = a_generator()
        self.assertTrue(next(gen))
        self.assertTrue(self.is_patched())
        self.assertTrue(self.second_is_patched())
        self.assertTrue(next(gen))
        # exhaust the generator
        try:
            next(gen)
            self.fail("Coroutine must be stopped")
        except StopIteration:
            pass
        self.assertFalse(self.is_patched())
        self.assertFalse(self.second_is_patched())

    def test_multiple_patches_on_coroutine(self):
        def set_fut_result(fut):
            fut.set_result((self.is_patched(), self.second_is_patched()))

        @asyncio.coroutine
        def tester(coro_function):
            loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)
            loop.call_soon(set_fut_result, fut)
            before, after = yield from coro_function(fut)
            self.assertEqual((True, True), before)
            self.assertEqual((True, True), fut.result())
            self.assertEqual((True, True), after)
            self.assertFalse(self.is_patched())
            self.assertFalse(self.second_is_patched())

        with self.subTest("old style coroutine"):
            @patch_second_is_patched(scope=asynctest.GLOBAL)
            @patch_is_patched(scope=asynctest.GLOBAL)
            def a_coroutine(fut):
                before = (self.is_patched(), self.second_is_patched())
                yield from fut
                after = (self.is_patched(), self.second_is_patched())
                return before, after

            run_coroutine(tester(a_coroutine))

        if not _using_await:
            return

        with self.subTest("new style coroutine"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                lambda: (self.is_patched(), self.second_is_patched()))
            a_new_style_coroutine = patch_second_is_patched(scope=asynctest.GLOBAL)(
                a_new_style_coroutine)
            a_new_style_coroutine = patch_is_patched(scope=asynctest.GLOBAL)(
                a_new_style_coroutine)
            run_coroutine(tester(a_new_style_coroutine))


class Test_patch_decorator_coroutine_or_generator_scope_LIMITED(patch_scope_TestCase):
    # Tests of patch() using scope=LIMITED
    def test_deactivate_patch_when_generator_init_fails(self):
        self._test_deactivate_patch_when_generator_init_fails(asynctest.LIMITED)

    def test_deactivate_patch_when_generator_exec_fails(self):
        self._test_deactivate_patch_when_generator_exec_fails(asynctest.LIMITED)

    def test_patch_generator_only_when_running(self):
        @patch_is_patched(scope=asynctest.LIMITED)
        def a_generator():
            yield self.is_patched()
            yield self.is_patched()

        gen = a_generator()
        self.assertTrue(next(gen))
        self.assertFalse(self.is_patched())
        self.assertTrue(next(gen))

    def test_patch_coroutine_only_when_running(self):
        def set_fut_result(fut):
            fut.set_result(self.is_patched())

        @asyncio.coroutine
        def tester(coro_function):
            loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)
            loop.call_soon(set_fut_result, fut)
            before, after = yield from coro_function(fut)
            self.assertTrue(before)
            self.assertFalse(fut.result())
            self.assertTrue(after)

        with self.subTest("old style coroutine"):
            @patch_is_patched(scope=asynctest.LIMITED)
            def a_coroutine(fut):
                before = self.is_patched()
                yield from fut
                after = self.is_patched()
                return before, after

            run_coroutine(tester(a_coroutine))

        if not _using_await:
            return

        with self.subTest("new style coroutine"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                self.is_patched)
            a_new_style_coroutine = patch_is_patched(scope=asynctest.LIMITED)(
                a_new_style_coroutine)
            run_coroutine(tester(a_new_style_coroutine))

    def test_patched_coroutine_with_mock_args(self):
        @asynctest.mock.patch('test.test_mock.Test', side_effect=lambda: None,
                              scope=asynctest.LIMITED)
        @asyncio.coroutine
        def a_coroutine(mock):
            loop = asyncio.get_event_loop()
            self.assertIs(mock, Test)
            yield from asyncio.sleep(0, loop=loop)
            self.assertIs(mock, Test)
            yield from asyncio.sleep(0, loop=loop)
            self.assertIs(mock, Test)

        run_coroutine(a_coroutine())

    def test_multiple_patches_on_coroutine(self):
        def set_fut_result(fut):
            fut.set_result((self.is_patched(), self.second_is_patched()))

        @asyncio.coroutine
        def tester(coro_function):
            loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)
            loop.call_soon(set_fut_result, fut)
            before, after = yield from coro_function(fut)
            self.assertEqual((True, True), before)
            self.assertEqual((False, False), fut.result())
            self.assertEqual((True, True), after)
            self.assertFalse(self.is_patched())
            self.assertFalse(self.second_is_patched())

        with self.subTest("old style coroutine"):
            @patch_second_is_patched(scope=asynctest.LIMITED)
            @patch_is_patched(scope=asynctest.LIMITED)
            def a_coroutine(fut):
                before = (self.is_patched(), self.second_is_patched())
                yield from fut
                after = (self.is_patched(), self.second_is_patched())
                return before, after

            run_coroutine(tester(a_coroutine))

        if not _using_await:
            return

        with self.subTest("new style coroutine"):
            a_new_style_coroutine = _using_await.build_simple_coroutine(
                lambda: (self.is_patched(), self.second_is_patched()))
            a_new_style_coroutine = patch_second_is_patched(scope=asynctest.LIMITED)(
                a_new_style_coroutine)
            a_new_style_coroutine = patch_is_patched(scope=asynctest.LIMITED)(
                a_new_style_coroutine)
            run_coroutine(tester(a_new_style_coroutine))


class Test_return_once(unittest.TestCase):
    def test_default_value(self):
        iterator = asynctest.mock.return_once("ProbeValue")
        self.assertEqual("ProbeValue", next(iterator))
        for _ in range(3):
            self.assertIsNone(next(iterator))

    def test_then(self):
        iterator = asynctest.mock.return_once("ProbeValue", "ThenValue")
        self.assertEqual("ProbeValue", next(iterator))
        for _ in range(2):
            self.assertEqual("ThenValue", next(iterator))

        iterator = asynctest.mock.return_once("ProbeValue", then="ThenValue")
        self.assertEqual("ProbeValue", next(iterator))
        self.assertEqual("ThenValue", next(iterator))

    def test_with_side_effect_default(self):
        mock = asynctest.Mock(side_effect=asynctest.mock.return_once("ProbeValue"))
        self.assertEqual("ProbeValue", mock())
        for _ in range(3):
            self.assertIsNone(mock())

    def test_with_side_effect_then(self):
        side_effect = asynctest.mock.return_once("ProbeValue", "ThenValue")
        mock = asynctest.Mock(side_effect=side_effect)
        self.assertEqual("ProbeValue", mock())
        for _ in range(2):
            self.assertEqual("ThenValue", mock())

    def test_with_side_effect_raises(self):
        mock = asynctest.mock.Mock(side_effect=asynctest.mock.return_once(Exception))
        self.assertRaises(Exception, mock)
        self.assertIsNone(mock())

    def test_with_side_effect_raises_then(self):
        side_effect = asynctest.mock.return_once("ProbeValue", BlockingIOError)
        mock = asynctest.mock.Mock(side_effect=side_effect)
        self.assertEqual("ProbeValue", mock())
        for _ in range(2):
            self.assertRaises(BlockingIOError, mock)

    def test_with_side_effect_raises_all(self):
        side_effect = asynctest.mock.return_once(Exception, BlockingIOError)
        mock = asynctest.mock.Mock(side_effect=side_effect)
        self.assertRaises(Exception, mock)
        for _ in range(2):
            self.assertRaises(BlockingIOError, mock)


class Test_create_autospec(unittest.TestCase):
    def test_generator_and_coroutine_is_instance_of_FunctionType(self):
        # this test is somewhat a forward compatibility test: if ever
        # unittest.mock.FunctionTypes doesn't detect generators and coroutines
        # as instance of these types, we need to fix it in asynctest.
        def gen():
            yield from range(10)

        @asyncio.coroutine
        def coroutine():
            yield from asyncio.sleep(0)

        self.assertIsInstance(gen, unittest.mock.FunctionTypes)
        self.assertIsInstance(coroutine, unittest.mock.FunctionTypes)
        if _using_await:
            self.assertIsInstance(_using_await.transform(coroutine),
                                  unittest.mock.FunctionTypes)

    # create_autospec:
    # * Ensure we check the signature of the coroutine function (and/or
    #   generator)
    # * Ensure a coroutine function attribute of a mock create with
    #   create_autospec is a CoroutineMock
    # * Ensure an instance of a class mocked from create_autospec will be an
    #   asynctest mock, and its coroutine attribute will be mocked by
    #   a CoroutineMock
    # * Ensure all expected create_autospec tests still run fine
    #
    # Also test cases where create_autospec is used (_patch, etc)
    def test_autospec_returns_asynctest_mocks(self):
        def a_generator():
            yield from range(10)

        cases = {
            "non callable": "Constant value",
            "callable class": Test,
            "non callable instance": Test(),
            "callable function": Test.a_function,
            "callable generator": a_generator,
        }

        for name, value in cases.items():
            with self.subTest(name):
                mock = asynctest.mock.create_autospec(value)
                unittest_mock = unittest.mock.create_autospec(value)
                try:
                    expected_type = getattr(asynctest.mock,
                                            type(unittest_mock).__name__)
                except AttributeError:
                    # The type of returned object is not readable as a mock
                    # This happens with mocks updated by _set_signature
                    expected_type = type(unittest_mock)
                self.assertIsInstance(mock, expected_type)
                self.assertNotIsInstance(mock, asynctest.mock.CoroutineMock)

    def test_autospec_of_coroutine_function_is_coroutinefunction(self):
        mock = asynctest.mock.create_autospec(Test.a_function)
        self.assertFalse(asyncio.iscoroutinefunction(mock))

        mock = asynctest.mock.create_autospec(Test.a_coroutine)
        self.assertTrue(asyncio.iscoroutinefunction(mock))

        mock = asynctest.mock.create_autospec(Test.a_classmethod_coroutine)
        self.assertTrue(asyncio.iscoroutinefunction(mock))

        mock = asynctest.mock.create_autospec(Test.a_staticmethod_coroutine)
        self.assertTrue(asyncio.iscoroutinefunction(mock))

        if _using_await:
            mock = asynctest.mock.create_autospec(Test.an_async_coroutine)
            self.assertTrue(asyncio.iscoroutinefunction(mock))

            mock = asynctest.mock.create_autospec(Test.an_async_classmethod_coroutine)
            self.assertTrue(asyncio.iscoroutinefunction(mock))

            mock = asynctest.mock.create_autospec(Test.an_async_staticmethod_coroutine)
            self.assertTrue(asyncio.iscoroutinefunction(mock))

    def test_autospec_attributes_being_coroutine_functions(self):
        mock = asynctest.mock.create_autospec(Test)
        self.assertFalse(asyncio.iscoroutinefunction(mock))
        self.assertFalse(asyncio.iscoroutinefunction(mock.a_function))
        self.assertTrue(asyncio.iscoroutinefunction(mock.a_coroutine))
        self.assertTrue(asyncio.iscoroutinefunction(mock.a_classmethod_coroutine))
        self.assertTrue(asyncio.iscoroutinefunction(mock.a_staticmethod_coroutine))
        if _using_await:
            self.assertTrue(asyncio.iscoroutinefunction(mock.an_async_coroutine))
            self.assertTrue(asyncio.iscoroutinefunction(mock.an_async_classmethod_coroutine))
            self.assertTrue(asyncio.iscoroutinefunction(mock.an_async_staticmethod_coroutine))

    def test_create_autospec_on_coroutine_with_return_value(self):
        mock = asynctest.mock.create_autospec(Test.a_coroutine,
                                              return_value="PROBE")
        self.assertEqual("PROBE", run_coroutine(mock(None)))

        if _using_await:
            mock = asynctest.mock.create_autospec(Test.an_async_coroutine,
                                                  return_value="PROBE")
            self.assertEqual("PROBE", run_coroutine(mock(None)))

    def test_create_autospec_on_coroutine_with_iterable_side_effect(self):
        coroutines = [Test.a_coroutine]
        if _using_await:
            coroutines.append(Test.an_async_coroutine)

        for a_coroutine in coroutines:
            mock = asynctest.mock.create_autospec(
                a_coroutine, side_effect=("PROBE1", "PROBE2"))
            self.assertEqual("PROBE1", run_coroutine(mock(None)))
            self.assertEqual("PROBE2", run_coroutine(mock(None)))

    def test_create_autospec_on_coroutine_with_exception_side_effect(self):
        coroutines = [Test.a_coroutine]
        if _using_await:
            coroutines.append(Test.an_async_coroutine)

        for a_coroutine in coroutines:
            mock = asynctest.mock.create_autospec(a_coroutine,
                                                  side_effect=ProbeException)
            with self.assertRaises(ProbeException):
                run_coroutine(mock(None))

    def test_create_autospec_on_coroutine_with_coroutine_side_effect(self):
        coroutines = [Test.a_coroutine]
        if _using_await:
            coroutines.append(Test.an_async_coroutine)

        for a_coroutine in coroutines:
            mock = asynctest.mock.create_autospec(
                a_coroutine, side_effect=asyncio.coroutine(lambda r: r))
            self.assertEqual("PROBE", run_coroutine(mock("PROBE")))

    def test_create_autospec_on_coroutine_with_instance_raises_RuntimeError(self):
        with self.assertRaises(RuntimeError):
            asynctest.mock.create_autospec(Test.a_coroutine, instance=True)


if __name__ == "__main__":
    unittest.main()
