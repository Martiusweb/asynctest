# coding: utf-8
"""
Wrapper to unittest.mock reducing the boilerplate when testing asyncio powered
code.

Features currently supported:

  * A mock can behave as a coroutine, as specified in the documentation of
    Mock.
"""

import asyncio
import functools
import sys
import types
import unittest.mock


def _raise(exception):
    raise exception


def _mock_add_spec(self, spec, *args, **kwargs):
    unittest.mock.NonCallableMock._mock_add_spec(self, spec, *args, **kwargs)

    _spec_coroutines = []
    for attr in dir(spec):
        if asyncio.iscoroutinefunction(getattr(spec, attr)):
            _spec_coroutines.append(attr)

    self.__dict__['_spec_coroutines'] = _spec_coroutines


def _get_child_mock(self, *args, _new_name=None, **kwargs):
        if _new_name in self.__dict__['_spec_coroutines']:
            return CoroutineMock(*args, **kwargs)

        _type = type(self)
        if not issubclass(_type, unittest.mock.CallableMixin):
            if issubclass(_type, unittest.mock.NonCallableMagicMock):
                klass = MagicMock
            elif issubclass(_type, NonCallableMock):
                klass = Mock
        else:
            klass = _type.__mro__[1]

        return klass(**kwargs)


class FakeInheritance(type):
    """
    A metaclass which recreates the original inheritance model from
    unittest.mock.

    - NonCallableMock > NonCallableMagicMock
    - NonCallable > Mock
    - Mock > MagicMock
    """
    def __init__(self, name, bases, attrs):
        attrs['__new__'] = types.MethodType(self.__new, self)
        super().__init__(name, bases, attrs)

    @staticmethod
    def __new(cls, *args, **kwargs):
        new = type(cls.__name__, (cls, ), {'__doc__': cls.__doc__})
        return object.__new__(new)

    def __instancecheck__(self, obj):
        # That's tricky, each type(mock) is actually a subclass of the actual
        # Mock type (see __new__)
        if super().__instancecheck__(obj):
            return True

        _type = type(obj)
        if issubclass(self, NonCallableMock):
            if issubclass(_type, (NonCallableMagicMock, Mock, )):
                return True

        if issubclass(self, Mock) and not issubclass(self, CoroutineMock):
            if issubclass(_type, (MagicMock, )):
                return True

        return False


# Notes about unittest.mock:
#  - MagicMock > Mock > NonCallableMock (where ">" means inherits from)
#  - when a mock instance is created, a new class (type) is created
#    dynamically,
#  - we *must* use magic or object's internals when we want to add our own
#    properties, and often override __getattr__/__setattr__ which are used
#    in unittest.mock.NonCallableMock.
class NonCallableMock(unittest.mock.NonCallableMock, metaclass=FakeInheritance):
    """
    Enhance unittest.mock.NonCallableMock with features allowing to mock
    a coroutine function.

    If is_coroutine is set to True, the NonCallableMock object will behave so
    asyncio.iscoroutinefunction(mock) will return True.

    If spec or spec_set is defined and an attribute is get, CoroutineMock is
    returned instead of Mock when the matching spec attribute is a coroutine
    function.

    The test author can also specify a wrapped object (the the wraps argument
    of the constructor). In this case, the Mock object behavior is the same as
    with an unittest.mock.Mock object: the wrapped object may have methods
    defined as coroutine functions.
    """
    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 is_coroutine=None, parent=None, **kwargs):

        super().__init__(spec=spec, wraps=wraps, name=name, spec_set=spec_set,
                         parent=parent, **kwargs)

        self.__set_is_coroutine(is_coroutine)

    def __get_is_coroutine(self):
        return self.__dict__['_mock_is_coroutine']

    def __set_is_coroutine(self, value):
        # property setters and getters are overriden by Mock(), we need to
        # update the dict to add values
        self.__dict__['_mock_is_coroutine'] = bool(value)

    is_coroutine = property(__get_is_coroutine, __set_is_coroutine,
                            "True if the object mocked is a coroutine")

    # asyncio.iscoroutinefunction() checks this property to say if an object is
    # a coroutine
    _is_couroutine = property(__get_is_coroutine)

    def __setattr__(self, name, value):
        if name == 'is_coroutine':
            self.__set_is_coroutine(value)
        else:
            return super().__setattr__(name, value)

    def _mock_add_spec(self, *args, **kwargs):
        return _mock_add_spec(self, *args, **kwargs)

    def _get_child_mock(self, *args, **kwargs):
        return _get_child_mock(self, *args, **kwargs)


class NonCallableMagicMock(unittest.mock.NonCallableMagicMock):
    """
    A version of MagicMock that isn't callable.
    """
    # XXX Currently, I can't find a way to satisfy all the constraints I want
    # without duplicating code...
    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 is_coroutine=None, parent=None, **kwargs):

        super().__init__(spec=spec, wraps=wraps, name=name, spec_set=spec_set,
                         parent=parent, **kwargs)

        self.__set_is_coroutine(is_coroutine)

    def __get_is_coroutine(self):
        return self.__dict__['_mock_is_coroutine']

    def __set_is_coroutine(self, value):
        self.__dict__['_mock_is_coroutine'] = bool(value)

    is_coroutine = property(__get_is_coroutine, __set_is_coroutine,
                            "True if the object mocked is a coroutine")

    def __setattr__(self, name, value):
        if name == 'is_coroutine':
            self.__set_is_coroutine(value)
        else:
            return super().__setattr__(name, value)

    def _mock_add_spec(self, *args, **kwargs):
        return _mock_add_spec(self, *args, **kwargs)

    def _get_child_mock(self, *args, **kwargs):
        return _get_child_mock(self, *args, **kwargs)


class Mock(unittest.mock.Mock, metaclass=FakeInheritance):
    """
    Enhance unittest.mock.Mock so it returns a CoroutineMock object instead of
    a Mock object where a method on a spec or spec_set object is a coroutine.

    For instance:

    >>> class Foo:
    ...     @asyncio.couroutine
    ...     def foo(self):
    ...         pass
    ...
    ...     def bar(self):
    ...         pass

    >>> type(asynctest.mock.Mock(Foo()).foo)
    <class 'asynctest.mock.CoroutineMock'>

    >>> type(asynctest.mock.Mock(Foo()).bar)
    <class 'asynctest.mock.Mock'>

    The test author can also specify a wrapped object (the the wraps argument
    of the constructor). In this case, the Mock object behavior is the same as
    with an unittest.mock.Mock object: the wrapped object may have methods
    defined as coroutine functions.
    """
    def _mock_add_spec(self, *args, **kwargs):
        return _mock_add_spec(self, *args, **kwargs)

    def _get_child_mock(self, *args, **kwargs):
        return _get_child_mock(self, *args, **kwargs)


class MagicMock(unittest.mock.MagicMock):
    """
    Enhance unittest.mock.MagicMock so it returns a CoroutineMock object
    instead of a Mock object where a method on a spec or spec_set object is
    a coroutine.

    see Mock.
    """
    def _mock_add_spec(self, *args, **kwargs):
        return _mock_add_spec(self, *args, **kwargs)

    def _get_child_mock(self, *args, **kwargs):
        return _get_child_mock(self, *args, **kwargs)


class CoroutineMock(Mock):
    """
    Enhance asynctest.mock.Mock with features allowing to mock a coroutine
    function.

    The Mock object will behave so:

      * asyncio.iscoroutinefunction(mock) will return True,

      * asyncio.iscoroutine(mock()) will return True,

      * the result of mock() is a coroutine which will have the outcome of
        side_effect or return_value:

          - if side_effect is a function, the coroutine will return the result
            of that function,

          - if side_effect is an exception, the coroutine will raise the
            exception,

          - if side_effect is an iterable, the coroutine will return the next
            value of the iterable, however, if the sequence of result is
            exhausted, StopIteration is raised immediatly,

          - if side_effect is not defined, the coroutine will return the value
            defined by return_value, hence, by default, the coroutine returns
            a new CoroutineMock object.

      * if the outcome of side_effect or return_vaule is a coroutine, the mock
      coroutine obtained when the mock object is called will be this coroutine
      itself (and not a coroutine returning a coroutine).

    The test author can also specify a wrapped object (the the wraps argument
    of the constructor). In this case, the Mock object behavior is the same as
    with an unittest.mock.Mock object: the wrapped object may have methods
    defined as coroutine functions.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # asyncio.iscoroutinefunction() checks this property to say if an
        # object is a coroutine
        self._is_coroutine = True

    def _mock_call(_mock_self, *args, **kwargs):
        try:
            result = super()._mock_call(*args, **kwargs)

            if asyncio.iscoroutine(result):
                return result
            else:
                return asyncio.coroutine(lambda *a, **kw: result)()
        except StopIteration as e:
            side_effect = _mock_self.side_effect
            if side_effect is not None and not callable(side_effect):
                raise

            return asyncio.coroutine(_raise)(e)
        except BaseException as e:
            return asyncio.coroutine(_raise)(e)


def mock_open(mock=None, read_data=''):
    """
    A helper function to create a mock to replace the use of open(). It works
    for open() called directly or used as a context manager.

    Arguments:
        mock: mock object to configure, by default an asynctest.MagicMock is
        created with the API limited to methods or attributes available on
        standard file handles.

        read_data: string for the read() and readlines() of the file handle to
        return. This is an empty string by default.
    """
    if mock is None:
        mock = MagicMock(name='open', spec=open)

    return unittest.mock.mock_open(mock, read_data)


ANY = unittest.mock.ANY
DEFAULT = unittest.mock.sentinel.DEFAULT


def _update_new_callable(patcher, new, new_callable):
    if new == DEFAULT and not new_callable:
        if asyncio.iscoroutinefunction(patcher.get_original()[0]):
            patcher.new_callable = CoroutineMock
        else:
            patcher.new_callable = MagicMock

    return patcher


class _patch(unittest.mock._patch):
    def copy(self):
        patcher = _patch(
            self.getter, self.attribute, self.new, self.spec,
            self.create, self.spec_set,
            self.autospec, self.new_callable, self.kwargs
        )
        patcher.attribute_name = self.attribute_name
        patcher.additional_patchers = [
            p.copy() for p in self.additional_patchers
        ]
        return patcher

    def decorate_callable(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        if not asyncio.iscoroutinefunction(func):
            return super().decorate_callable(func)

        @functools.wraps(func)
        def patched(*args, **keywargs):
            extra_args = []
            entered_patchers = []

            exc_info = tuple()
            try:
                for patching in patched.patchings:
                    arg = patching.__enter__()
                    entered_patchers.append(patching)
                    if patching.attribute_name is not None:
                        keywargs.update(arg)
                    elif patching.new is DEFAULT:
                        extra_args.append(arg)

                args += tuple(extra_args)
                return (yield from func(*args, **keywargs))
            except:
                if patching not in entered_patchers and unittest.mock._is_started(patching):
                    # the patcher may have been started, but an exception
                    # raised whilst entering one of its additional_patchers
                    entered_patchers.append(patching)
                # Pass the exception to __exit__
                exc_info = sys.exc_info()
                # re-raise the exception
                raise
            finally:
                for patching in reversed(entered_patchers):
                    patching.__exit__(*exc_info)

        patched.patchings = [self]
        return patched


def patch(target, new=DEFAULT, spec=None, create=False, spec_set=None,
          autospec=None, new_callable=None, **kwargs):
    """
    A context manager, function decorator or class decorator which patch the
    target with the value given by ther new argument.

    If new isn't provided, the default is an asynctest.CoroutineMock if the
    patched object is a coroutine, or an asynctest.MagicMock object.

    It is a replacement to unittest.mock.patch, but using asynctest.Mock
    objects.

    see unittest.mock.patch().
    """

    getter, attribute = unittest.mock._get_target(target)
    patcher = _patch(getter, attribute, new, spec, create, spec_set, autospec,
                     new_callable, kwargs)

    return _update_new_callable(patcher, new, new_callable)


def _patch_object(target, attribute, new=DEFAULT, spec=None, create=False,
                  spec_set=None, autospec=None, new_callable=None, **kwargs):
    patcher = _patch(lambda: target, attribute, new, spec, create, spec_set,
                     autospec, new_callable, kwargs)

    return _update_new_callable(patcher, new, new_callable)


def _patch_multiple(target, spec=None, create=False, spec_set=None,
                    autospec=None, new_callable=None, **kwargs):
    if type(target) is str:
        def getter():
            return unittest.mock._importer(target)
    else:
        def getter():
            return target

    if not kwargs:
        raise ValueError('Must supply at least one keyword argument with '
                         'patch.multiple')

    items = list(kwargs.items())
    attribute, new = items[0]
    patcher = _patch(getter, attribute, new, spec, create, spec_set, autospec,
                     new_callable, {})

    patcher.attribute_name = attribute
    for attribute, new in items[1:]:
        this_patcher = _patch(getter, attribute, new, spec, create, spec_set,
                              autospec, new_callable, {})
        this_patcher.attribute_name = attribute
        patcher.additional_patchers.append(this_patcher)

    def _update(patcher):
        return _update_new_callable(patcher, patcher.new, new_callable)

    patcher = _update(patcher)
    patcher.additional_patchers = list(map(_update,
                                           patcher.additional_patchers))

    return patcher


class _patch_dict(unittest.mock._patch_dict):
    def __call__(self, f):
        if not asyncio.iscoroutinefunction(f):
            return super().__call__(f)

        @functools.wraps(f)
        def _inner(*args, **kw):
            self._patch_dict()
            try:
                return (yield from f(*args, **kw))
            finally:
                self._unpatch_dict()

        return _inner


patch.object = _patch_object
patch.dict = _patch_dict
patch.multiple = _patch_multiple
patch.stopall = unittest.mock._patch_stopall
patch.TEST_PREFIX = unittest.mock.patch.TEST_PREFIX


sentinel = unittest.mock.sentinel
call = unittest.mock.call
create_autospec = unittest.mock.create_autospec
# TODO create_autospec: call the original method and recreate the object
PropertyMock = unittest.mock.PropertyMock
