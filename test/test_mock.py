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

    def is_patched(self):
        return False

    a_dict = {'is_patched': False}


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
class _Test_is_coroutine_property:
    def test_is_coroutine_property(self, klass):
        mock = klass()
        self.assertFalse(mock.is_coroutine)

        mock.is_coroutine = True
        self.assertTrue(mock.is_coroutine)

        mock = klass(is_coroutine=True)
        self.assertTrue(mock.is_coroutine)


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
                             _Test_is_coroutine_property,
                             _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'NonCallableMock'


@unittest.skip
class Test_NonCallableMagicMock(unittest.TestCase, _Test_subclass,
                                _Test_iscoroutinefunction,
                                _Test_is_coroutine_property,
                                _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'NonCallableMagicMock'


class Test_Mock(unittest.TestCase, _Test_subclass,
                _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'Mock'


class Test_MagicMock(unittest.TestCase, _Test_subclass,
                     _Test_Spec_Spec_Set_Returns_Coroutine_Mock):
    class_to_test = 'MagicMock'


class Test_CoroutineMock(unittest.TestCase, _Test_iscoroutinefunction,
                         _Test_called_coroutine):
    class_to_test = 'CoroutineMock'


class TestMockInheritanceModel(unittest.TestCase):
    to_test = {
        'NonCallableMagicMock': 'NonCallableMock',
        'Mock': 'NonCallableMock',
        'MagicMock': 'Mock',
        'CoroutineMock': 'Mock',
    }

    def test_Mock_is_not_CoroutineMock(self):
        self.assertNotIsInstance(aiotest.mock.Mock(), aiotest.mock.CoroutineMock)

    def test_MagicMock_is_not_CoroutineMock(self):
        self.assertNotIsInstance(aiotest.mock.MagicMock(), aiotest.mock.CoroutineMock)

    @staticmethod
    def make_inheritance_test(child, parent):
        def test(self):
            # Works in the common case
            self.assertIsInstance(getattr(aiotest.mock, child)(),
                                  getattr(aiotest.mock, parent))

            # Works with a custom spec
            self.assertIsInstance(getattr(aiotest.mock, child)(Test()),
                                  getattr(aiotest.mock, parent))

        return test

for child, parent in TestMockInheritanceModel.to_test.items():
    setattr(TestMockInheritanceModel,
            'test_{}_inherits_from_{}'.format(child, parent),
            TestMockInheritanceModel.make_inheritance_test(child, parent))


class Test_mock_open(unittest.TestCase):
    def test_MagicMock_returned_by_default(self):
        self.assertIsInstance(aiotest.mock_open(), aiotest.MagicMock)


class Test_patch(unittest.TestCase):
    def test_patch_with_MagicMock(self):
        with aiotest.mock.patch('test.test_mock.Test') as mock:
            self.assertIsInstance(mock, aiotest.mock.MagicMock)

        with aiotest.mock.patch('test.test_mock.Test.a_function') as mock:
            self.assertIsInstance(mock, aiotest.mock.MagicMock)

    def test_patch_coroutine_function_with_CoroutineMock(self):
        with aiotest.mock.patch('test.test_mock.Test.a_coroutine') as mock:
            self.assertIsInstance(mock, aiotest.mock.CoroutineMock)

    def test_patch_decorates_coroutine(self):
        @aiotest.mock.patch('test.test_mock.Test.is_patched', new=lambda self: True)
        @asyncio.coroutine
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().is_patched()

        self.assertTrue(dry_run_coroutine(a_coroutine()))

    def test_patch_decorates_function(self):
        @aiotest.mock.patch('test.test_mock.Test.is_patched', new=lambda self: True)
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().is_patched()

        self.assertTrue(a_coroutine())


class Test_patch_object(unittest.TestCase):
    def test_patch_with_MagicMock(self):
        with aiotest.mock.patch.object(Test(), 'a_function') as mock:
            self.assertIsInstance(mock, aiotest.mock.MagicMock)

        obj = Test()
        obj.test = Test()
        with aiotest.mock.patch.object(obj, 'test') as mock:
            self.assertIsInstance(mock, aiotest.mock.MagicMock)

    def test_patch_coroutine_function_with_CoroutineMock(self):
        with aiotest.mock.patch.object(Test(), 'a_coroutine') as mock:
            self.assertIsInstance(mock, aiotest.mock.CoroutineMock)

    def test_patch_decorates_coroutine(self):
        obj = Test()

        @aiotest.mock.patch.object(obj, 'is_patched', new=lambda: True)
        @asyncio.coroutine
        def a_coroutine():
            return obj.is_patched()

        self.assertTrue(dry_run_coroutine(a_coroutine()))


class Test_patch_multiple(unittest.TestCase):
    def test_patch_with_MagicMock(self):
        default = aiotest.mock.DEFAULT
        with aiotest.mock.patch.multiple('test.test_mock', Test=default):
            import test.test_mock
            self.assertIsInstance(test.test_mock.Test, aiotest.mock.MagicMock)

    def test_patch_coroutine_function_with_CoroutineMock(self):
        default = aiotest.mock.DEFAULT
        with aiotest.mock.patch.multiple('test.test_mock.Test',
                                         a_function=default,
                                         a_coroutine=default):
            import test.test_mock
            obj = test.test_mock.Test()
            self.assertIsInstance(obj.a_function, aiotest.mock.MagicMock)
            self.assertIsInstance(obj.a_coroutine, aiotest.mock.CoroutineMock)

    def test_patch_decorates_coroutine(self):
        @aiotest.mock.patch.multiple('test.test_mock.Test', is_patched=lambda self: True)
        @asyncio.coroutine
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().is_patched()

        self.assertTrue(dry_run_coroutine(a_coroutine()))


class Test_patch_dict(unittest.TestCase):
    def test_patch_decorates_coroutine(self):
        @aiotest.mock.patch.dict('test.test_mock.Test.a_dict', is_patched=True)
        @asyncio.coroutine
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().a_dict['is_patched']

        self.assertTrue(dry_run_coroutine(a_coroutine()))

    def test_patch_decorates_function(self):
        @aiotest.mock.patch.dict('test.test_mock.Test.a_dict', is_patched=True)
        def a_coroutine():
            import test.test_mock
            return test.test_mock.Test().a_dict['is_patched']

        self.assertTrue(a_coroutine())


if __name__ == "__main__":
    unittest.main()
