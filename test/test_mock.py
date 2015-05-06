# coding: utf-8

import asyncio
import functools
import unittest

import aiotest


def dry_run_coroutine(coroutine):
    try:
        while True:
            next(coroutine)
    except StopIteration as e:
        return e.value


class Test:
    @asyncio.coroutine
    def a_coroutine(self):
        pass

    def a_function(self):
        pass


def inject_class(obj):
    if isinstance(obj, type):
        for attr_name in dir(obj):
            attr = getattr(obj, attr_name)
            if callable(attr) and attr_name.startswith('test_'):
                setattr(obj, attr_name, inject_class(attr))

        return obj
    else:
        @functools.wraps(obj)
        def wrapper(self):
            return obj(self, getattr(aiotest, self.class_to_test))

        return wrapper


@inject_class
class _Test_iscoroutinefunction:
    def test_asyncio_iscoroutinefunction(self, klass):
        mock = klass()
        self.assertTrue(asyncio.iscoroutinefunction(mock))


@inject_class
class _Test_subclass:
    def test_subclass(self, klass):
        unittest_klass = getattr(unittest.mock, self.class_to_test)

        self.assertTrue(issubclass(klass, unittest_klass))
        self.assertTrue(isinstance(klass(), unittest_klass))


@inject_class
class _Test_called_coroutine:
    def test_returns_coroutine(self, klass):
        mock = klass()

        self.assertTrue(asyncio.iscoroutine(mock()))

    def test_returns_coroutine_from_return_value(self, klass):
        mock = klass()
        mock.return_value = 'ProbeValue'

        self.assertEqual('ProbeValue', mock.return_value)
        self.assertEqual(mock.return_value, dry_run_coroutine(mock()))

    def test_returns_coroutine_with_return_value_being_a_coroutine(self, klass):
        mock = klass()
        coroutine = asyncio.coroutine(lambda: 'ProbeValue')
        mock.return_value = coroutine()

        self.assertEqual('ProbeValue', dry_run_coroutine(mock()))

    def test_returns_coroutine_from_side_effect(self, klass):
        mock = klass()
        mock.side_effect = lambda: 'ProbeValue'

        self.assertEqual('ProbeValue', dry_run_coroutine(mock()))

    def test_returns_coroutine_from_side_effect_being_a_coroutine(self, klass):
        mock = klass()
        mock.side_effect = asyncio.coroutine(lambda: 'ProbeValue')

        self.assertEqual('ProbeValue', dry_run_coroutine(mock()))

    def test_exception_side_effect_raises_in_coroutine(self, klass):
        mock = klass()
        mock.side_effect = Exception

        coroutine = mock()
        with self.assertRaises(Exception):
            dry_run_coroutine(coroutine)

    def test_returns_coroutine_from_side_effect_being_an_iterable(self, klass):
        mock = klass()
        side_effect = ['Probe1', 'Probe2', 'Probe3']
        mock.side_effect = side_effect

        for expected in side_effect:
            self.assertEqual(expected, dry_run_coroutine(mock()))

        with self.assertRaises(StopIteration):
            mock()


@inject_class
class _Test_Spec_Spec_Set_Returns_Coroutine_Mock:
    def test_mock_returns_coroutine_according_to_spec(self, klass):
        spec = Test()

        for attr in ('spec', 'spec_set', ):
            with self.subTest(spec_type=attr):
                mock = klass(**{attr: spec})

                self.assertIsInstance(mock.a_function, (aiotest.Mock, aiotest.MagicMock))
                self.assertNotIsInstance(mock.a_function, aiotest.CoroutineMock)
                self.assertIsInstance(mock.a_coroutine, aiotest.CoroutineMock)


class Test_NonCallabableMock(unittest.TestCase, _Test_subclass,
                             _Test_iscoroutinefunction,
                             _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'NonCallableMock'

    def test_is_coroutine_property(self):
        klass = getattr(aiotest, self.class_to_test)

        mock = klass()
        self.assertFalse(mock.is_coroutine)

        mock.is_coroutine = True
        self.assertTrue(mock.is_coroutine)

        mock = klass(is_coroutine=True)
        self.assertTrue(mock.is_coroutine)


class Test_Mock(unittest.TestCase, _Test_subclass,
                _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'Mock'


class Test_MagicMock(unittest.TestCase, _Test_subclass,
                     _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'MagicMock'


class Test_CoroutineMock(unittest.TestCase, _Test_iscoroutinefunction,
                         _Test_called_coroutine):
    class_to_test = 'CoroutineMock'


if __name__ == "__main__":
    unittest.main()
