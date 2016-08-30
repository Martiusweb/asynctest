# coding: utf-8
"""
Mock objects
------------

Wrapper to unittest.mock reducing the boilerplate when testing asyncio powered
code.

A mock can behave as a coroutine, as specified in the documentation of
:class:`~asynctest.mock.Mock`.
"""

import asyncio
import asyncio.coroutines
import contextlib
import enum
import functools
import inspect
import sys
import types
import unittest.mock


def _raise(exception):
    raise exception


def _is_started(patching):
    if isinstance(patching, _patch_dict):
        return patching._is_started
    else:
        return unittest.mock._is_started(patching)


class FakeInheritanceMeta(type):
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

    def __instancecheck__(cls, obj):
        # That's tricky, each type(mock) is actually a subclass of the actual
        # Mock type (see __new__)
        if super().__instancecheck__(obj):
            return True

        _type = type(obj)
        if issubclass(cls, NonCallableMock):
            if issubclass(_type, (NonCallableMagicMock, Mock, )):
                return True

        if issubclass(cls, Mock) and not issubclass(cls, CoroutineMock):
            if issubclass(_type, (MagicMock, )):
                return True

        return False


def _get_is_coroutine(self):
    return self.__dict__['_mock_is_coroutine']


def _set_is_coroutine(self, value):
    # property setters and getters are overriden by Mock(), we need to
    # update the dict to add values
    self.__dict__['_mock_is_coroutine'] = bool(value)


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


class MockMetaMixin(FakeInheritanceMeta):
    def __new__(meta, name, base, namespace):
        if not any((isinstance(baseclass, meta) for baseclass in base)):
            namespace.update({
                '_mock_add_spec': _mock_add_spec,
                '_get_child_mock': _get_child_mock,
            })

        return super().__new__(meta, name, base, namespace)


class IsCoroutineArgMeta(MockMetaMixin):
    def __new__(meta, name, base, namespace):
        if not any((isinstance(baseclass, meta) for baseclass in base)):
            namespace.update({
                '_asynctest_get_is_coroutine': _get_is_coroutine,
                '_asynctest_set_is_coroutine': _set_is_coroutine,
                'is_coroutine': property(_get_is_coroutine, _set_is_coroutine,
                                         "True if the object mocked is a coroutine"),
                '_is_coroutine': property(_get_is_coroutine),
            })

            def __setattr__(self, name, value):
                if name == 'is_coroutine':
                    self._asynctest_set_is_coroutine(value)
                else:
                    return base[0].__setattr__(self, name, value)

            namespace['__setattr__'] = __setattr__

        return super().__new__(meta, name, base, namespace)


# Notes about unittest.mock:
#  - MagicMock > Mock > NonCallableMock (where ">" means inherits from)
#  - when a mock instance is created, a new class (type) is created
#    dynamically,
#  - we *must* use magic or object's internals when we want to add our own
#    properties, and often override __getattr__/__setattr__ which are used
#    in unittest.mock.NonCallableMock.
class NonCallableMock(unittest.mock.NonCallableMock,
                      metaclass=IsCoroutineArgMeta):
    """
    Enhance :class:`unittest.mock.NonCallableMock` with features allowing to
    mock a coroutine function.

    If ``is_coroutine`` is set to ``True``, the :class:`NonCallableMock`
    object will behave so :func:`asyncio.iscoroutinefunction` will return
    ``True`` with ``mock`` as parameter.

    If ``spec`` or ``spec_set`` is defined and an attribute is get,
    :class:`~asynctest.CoroutineMock` is returned instead of
    :class:`~asynctest.Mock` when the matching spec attribute is a coroutine
    function.

    The test author can also specify a wrapped object with ``wraps``. In this
    case, the :class:`~asynctest.Mock` object behavior is the same as with an
    :class:`unittest.mock.Mock` object: the wrapped object may have methods
    defined as coroutine functions.

    See :class:`unittest.mock.NonCallableMock`
    """
    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 is_coroutine=None, parent=None, **kwargs):
        super().__init__(spec=spec, wraps=wraps, name=name, spec_set=spec_set,
                         parent=parent, **kwargs)

        self._asynctest_set_is_coroutine(is_coroutine)


class NonCallableMagicMock(unittest.mock.NonCallableMagicMock,
                           metaclass=IsCoroutineArgMeta):
    """
    A version of :class:`~asynctest.MagicMock` that isn't callable.
    """
    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 is_coroutine=None, parent=None, **kwargs):

        super().__init__(spec=spec, wraps=wraps, name=name, spec_set=spec_set,
                         parent=parent, **kwargs)

        self._asynctest_set_is_coroutine(is_coroutine)


class Mock(unittest.mock.Mock, metaclass=MockMetaMixin):
    """
    Enhance :class:`unittest.mock.Mock` so it returns
    a :class:`~asynctest.CoroutineMock` object instead of
    a :class:`~asynctest.Mock` object where a method on a ``spec`` or
    ``spec_set`` object is a coroutine.

    For instance:

    >>> class Foo:
    ...     @asyncio.coroutine
    ...     def foo(self):
    ...         pass
    ...
    ...     def bar(self):
    ...         pass

    >>> type(asynctest.mock.Mock(Foo()).foo)
    <class 'asynctest.mock.CoroutineMock'>

    >>> type(asynctest.mock.Mock(Foo()).bar)
    <class 'asynctest.mock.Mock'>

    The test author can also specify a wrapped object with ``wraps``. In this
    case, the :class:`~asynctest.Mock` object behavior is the same as with an
    :class:`unittest.mock.Mock` object: the wrapped object may have methods
    defined as coroutine functions.

    If you want to mock a coroutine function, use :class:`CoroutineMock`
    instead.

    See :class:`~asynctest.NonCallableMock` for details about :mod:`asynctest`
    features, and :mod:`unittest.mock` for the comprehensive documentation
    about mocking.
    """


class MagicMock(unittest.mock.MagicMock, metaclass=MockMetaMixin):
    """
    Enhance :class:`unittest.mock.MagicMock` so it returns
    a :class:`~asynctest.CoroutineMock` object instead of
    a :class:`~asynctest.Mock` object where a method on a ``spec`` or
    ``spec_set`` object is a coroutine.

    If you want to mock a coroutine function, use :class:`CoroutineMock`
    instead.

    see :class:`~asynctest.Mock`.
    """


class CoroutineMock(Mock):
    """
    Enhance :class:`~asynctest.mock.Mock` with features allowing to mock
    a coroutine function.

    The :class:`~asynctest.CoroutineMock` object will behave so the object is
    recognized as coroutine function, and the result of a call as a coroutine:

    >>> mock = CoroutineMock()
    >>> asyncio.iscoroutinefunction(mock)
    True
    >>> asyncio.iscoroutine(mock())
    True


    The result of ``mock()`` is a coroutine which will have the outcome of
    ``side_effect`` or ``return_value``:

    - if ``side_effect`` is a function, the coroutine will return the result
      of that function,
    - if ``side_effect`` is an exception, the coroutine will raise the
      exception,
    - if`` side_effect`` is an iterable, the coroutine will return the next
      value of the iterable, however, if the sequence of result is exhausted,
      ``StopIteration`` is raised immediatly,
    - if ``side_effect`` is not defined, the coroutine will return the value
      defined by ``return_value``, hence, by default, the coroutine returns
      a new :class:`~asynctest.CoroutineMock` object.

    If the outcome of ``side_effect`` or ``return_vaule`` is a coroutine, the
    mock coroutine obtained when the mock object is called will be this
    coroutine itself (and not a coroutine returning a coroutine).

    The test author can also specify a wrapped object with ``wraps``. In this
    case, the :class:`~asynctest.Mock` object behavior is the same as with an
    :class:`unittest.mock.Mock` object: the wrapped object may have methods
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
    A helper function to create a mock to replace the use of :func:`open()`. It
    works for :func:`open()` called directly or used as a context manager.

    :param mock: mock object to configure, by default
                 a :class:`~asynctest.MagicMock` object is
                 created with the API limited to methods or attributes
                 available on standard file handles.

    :param read_data: string for the :func:`read()` and :func:`readlines()` of
                      the file handle to return. This is an empty string by
                      default.
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


PatchScope = enum.Enum('PatchScope', 'LIMITED GLOBAL')

#: Value of ``scope``, deactivating a patch when a decorated generator or
#: a coroutine pauses (``yield`` or ``await``).
LIMITED = PatchScope.LIMITED

#: Value of ``scope``, activating a patch until the decorated generator or
#: coroutine returns or raises an exception.
GLOBAL = PatchScope.GLOBAL


def _decorate_callable(func, new_patching):
    if hasattr(func, 'patchings'):
        func.patchings.append(new_patching)
        return func

    is_generator_func = inspect.isgeneratorfunction(func)
    is_coroutine_func = asyncio.iscoroutinefunction(func)
    if not (is_generator_func or is_coroutine_func):
        return None

    @functools.wraps(func)
    def patched(*args, **keywargs):
        extra_args = []
        patchers_to_exit = []
        patch_dict_with_limited_scope = []

        exc_info = tuple()
        try:
            for patching in patched.patchings:
                arg = patching.__enter__()
                if patching.scope == LIMITED:
                    patchers_to_exit.append(patching)
                if isinstance(patching, _patch_dict):
                    if patching.scope == GLOBAL:
                        for limited_patching in patch_dict_with_limited_scope:
                            if limited_patching.in_dict is patching.in_dict:
                                limited_patching._keep_global_patch(patching)
                    else:
                        patch_dict_with_limited_scope.append(patching)
                else:
                    if patching.attribute_name is not None:
                        keywargs.update(arg)
                        if patching.new is DEFAULT:
                            patching.new = arg[patching.attribute_name]
                    elif patching.new is DEFAULT:
                        patching.mock_to_reuse = arg
                        extra_args.append(arg)

            args += tuple(extra_args)
            gen = func(*args, **keywargs)
            return _PatchedGenerator(gen, patched.patchings,
                                     asyncio.iscoroutinefunction(func))
        except:
            if patching not in patchers_to_exit and _is_started(patching):
                # the patcher may have been started, but an exception
                # raised whilst entering one of its additional_patchers
                patchers_to_exit.append(patching)
            # Pass the exception to __exit__
            exc_info = sys.exc_info()
            # re-raise the exception
            raise
        finally:
            for patching in reversed(patchers_to_exit):
                patching.__exit__(*exc_info)

    patched.patchings = [new_patching]

    if is_generator_func:
        # wrap the patched object in a generator so
        # inspect.isgeneratorfunction() returns True
        @functools.wraps(func)
        def patched_generator(*args, **kwargs):
            return (yield from patched(*args, **kwargs))

        patched_generator.patchings = patched.patchings

        if is_coroutine_func:
            return asyncio.coroutine(patched_generator)
        else:
            return patched_generator
    else:
        return functools.wraps(func)(patched)


class _PatchedGenerator(asyncio.coroutines.CoroWrapper):
    # Inheriting from asyncio.CoroWrapper gives us a comprehensive wrapper
    # implementing one or more workarounds for cpython bugs
    def __init__(self, gen, patchings, is_coroutine):
        self.gen = gen
        self._is_coroutine = is_coroutine
        self.__name__ = getattr(gen, '__name__', None)
        self.__qualname__ = getattr(gen, '__qualname__', None)
        self.patchings = patchings

        # GLOBAL patches have been started in the _patch/patched() wrapper

    def __repr__(self):
        return repr(self.generator)

    def __next__(self):
        try:
            with contextlib.ExitStack() as stack:
                [stack.enter_context(patching) for patching in self.patchings
                    if patching.scope == LIMITED]
                return self.gen.send(None)
        except:
            # the generator/coroutine terminated, stop the patchings
            for patching in reversed(self.patchings):
                if patching.scope == GLOBAL and _is_started(patching):
                    patching.stop()
            raise

    def send(self, value):
        with contextlib.ExitStack() as stack:
            [stack.enter_context(patching) for patching in self.patchings
                if patching.scope == LIMITED]
            return super().send(value)

    def throw(self, exc):
        with contextlib.ExitStack() as stack:
            [stack.enter_context(patching) for patching in self.patchings
                if patching.scope == LIMITED]
            return self.gen.throw(exc)

    def __del__(self):
        # The generator/coroutine is deleted before it terminated, we must
        # still stop the patchings
        for patching in reversed(self.patchings):
            if patching.scope == GLOBAL and _is_started(patching):
                patching.stop()


class _patch(unittest.mock._patch):
    def __init__(self, *args, scope=GLOBAL, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope = scope
        self.mock_to_reuse = None

    def copy(self):
        patcher = _patch(
            self.getter, self.attribute, self.new, self.spec,
            self.create, self.spec_set,
            self.autospec, self.new_callable, self.kwargs,
            scope=self.scope)
        patcher.attribute_name = self.attribute_name
        patcher.additional_patchers = [
            p.copy() for p in self.additional_patchers
        ]
        return patcher

    def __enter__(self):
        # When patching a coroutine, we reuse the same mock object
        if self.mock_to_reuse is not None:
            self.target = self.getter()
            self.temp_original, self.is_local = self.get_original()
            setattr(self.target, self.attribute, self.mock_to_reuse)
            if self.attribute_name is not None:
                for patching in self.additional_patchers:
                    patching.__enter__()
            return self.mock_to_reuse
        else:
            return super().__enter__()

    def decorate_callable(self, func):
        wrapped = _decorate_callable(func, self)
        if wrapped is None:
            return super().decorate_callable(func)
        else:
            return wrapped


def patch(target, new=DEFAULT, spec=None, create=False, spec_set=None,
          autospec=None, new_callable=None, scope=GLOBAL, **kwargs):
    """
    A context manager, function decorator or class decorator which patch the
    target with the value given by ther new argument.

    If new isn't provided, the default is a :class:`~asynctest.CoroutineMock`
    if the patched object is a coroutine, or a :class:`~asynctest.MagicMock`
    object.

    It is a replacement to :func:`unittest.mock.patch`, but using
    :mod:`asynctest.mock` objects.

    When a generator or a coroutine is patched using the decorator, the patch
    is activated or deactivated according to the ``scope`` argument value:

      * :const:`asynctest.GLOBAL`: the default, enables the patch until the
        generator or the coroutine finishes (returns or raises an exception),

      * :const:`asynctest.LIMITED`: the patch will be activated when the
        generator or coroutine is being executed, and deactivated when it
        yields a value and pauses its execution (with ``yield``, ``yield from``
        or ``await``).

    The behavior differs from :func:`unittest.mock.patch` for generators.

    When used as a context manager, the patch is still active even if the
    generator or coroutine is paused, which may affect concurrent tasks::

        @asyncio.coroutine
        def coro():
            with asynctest.mock.patch("module.function"):
                yield from asyncio.get_event_loop().sleep(1)

        @asyncio.coroutine
        def independent_coro():
            assert not isinstance(module.function, asynctest.mock.Mock)

        asyncio.create_task(coro())
        asyncio.create_task(independent_coro())
        # this will raise an AssertionError(coro() is scheduled first)!
        loop.run_forever()

    :param scope: :const:`asynctest.GLOBAL` or :const:`asynctest.LIMITED`,
        controls when the patch is activated on generators and coroutines

    see :func:`unittest.mock.patch()`.

    .. versionadded:: 0.6 patch into generators and coroutines with
                      a decorator.
    """
    getter, attribute = unittest.mock._get_target(target)
    patcher = _patch(getter, attribute, new, spec, create, spec_set, autospec,
                     new_callable, kwargs, scope=scope)

    return _update_new_callable(patcher, new, new_callable)


def _patch_object(target, attribute, new=DEFAULT, spec=None, create=False,
                  spec_set=None, autospec=None, new_callable=None,
                  scope=GLOBAL, **kwargs):
    patcher = _patch(lambda: target, attribute, new, spec, create, spec_set,
                     autospec, new_callable, kwargs, scope=scope)

    return _update_new_callable(patcher, new, new_callable)


def _patch_multiple(target, spec=None, create=False, spec_set=None,
                    autospec=None, new_callable=None, scope=GLOBAL, **kwargs):
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
                     new_callable, {}, scope=scope)

    patcher.attribute_name = attribute
    for attribute, new in items[1:]:
        this_patcher = _patch(getter, attribute, new, spec, create, spec_set,
                              autospec, new_callable, {}, scope=scope)
        this_patcher.attribute_name = attribute
        patcher.additional_patchers.append(this_patcher)

    def _update(patcher):
        return _update_new_callable(patcher, patcher.new, new_callable)

    patcher = _update(patcher)
    patcher.additional_patchers = list(map(_update,
                                           patcher.additional_patchers))

    return patcher


class _patch_dict(unittest.mock._patch_dict):
    # documentation is in doc/asynctest.mock.rst
    def __init__(self, in_dict, values=(), clear=False, scope=GLOBAL,
                 **kwargs):
        super().__init__(in_dict, values, clear, **kwargs)
        self.scope = scope
        self._is_started = False
        self._global_patchings = []

    def _keep_global_patch(self, other_patching):
        self._global_patchings.append(other_patching)

    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if (attr.startswith(patch.TEST_PREFIX) and
                    hasattr(attr_value, "__call__")):
                decorator = _patch_dict(self.in_dict, self.values, self.clear)
                decorated = decorator(attr_value)
                setattr(klass, attr, decorated)
        return klass

    def __call__(self, func):
        if isinstance(func, type):
            return self.decorate_class(func)

        wrapper = _decorate_callable(func, self)
        if wrapper is None:
            return super().__call__(func)
        else:
            return wrapper

    def _patch_dict(self):
        self._is_started = True

        try:
            self._original = self.in_dict.copy()
        except AttributeError:
            # dict like object with no copy method
            # must support iteration over keys
            self._original = {}
            for key in self.in_dict:
                self._original[key] = self.in_dict[key]

        if self.clear:
            _clear_dict(self.in_dict)

        try:
            self.in_dict.update(self.values)
        except AttributeError:
            # dict like object with no update method
            for key in self.values:
                self.in_dict[key] = self.values[key]

    def _unpatch_dict(self):
        self._is_started = False

        if self.scope == LIMITED:
            # add to self.values the updated values which where not in
            # the original dict, as the patch may be reactivated
            for key in self.in_dict:
                if (key not in self._original or
                        self._original[key] is not self.in_dict[key]):
                    self.values[key] = self.in_dict[key]

        _clear_dict(self.in_dict)

        originals = [self._original]
        for patching in self._global_patchings:
            if patching._is_started:
                # keep the values of global patches
                originals.append(patching.values)

        for original in originals:
            try:
                self.in_dict.update(original)
            except AttributeError:
                for key in original:
                    self.in_dict[key] = original[key]


_clear_dict = unittest.mock._clear_dict

patch.object = _patch_object
patch.dict = _patch_dict
patch.multiple = _patch_multiple
patch.stopall = unittest.mock._patch_stopall
patch.TEST_PREFIX = 'test'


sentinel = unittest.mock.sentinel
call = unittest.mock.call
PropertyMock = unittest.mock.PropertyMock


def return_once(value, then=None):
    """
    Helper to use with ``side_effect``, so a mock will return a given value
    only once, then return another value.

    When used as a ``side_effect`` value, if one of ``value`` or ``then`` is an
    :class:`Exception` type, an instance of this exception will be raised.

    >>> mock.recv = Mock(side_effect=return_once(b"data"))
    >>> mock.recv()
    b"data"
    >>> repr(mock.recv())
    'None'
    >>> repr(mock.recv())
    'None'

    >>> mock.recv = Mock(side_effect=return_once(b"data", then=BlockingIOError))
    >>> mock.recv()
    b"data"
    >>> mock.recv()
    Traceback BlockingIOError

    :param value: value to be returned once by the mock when called.

    :param then: value returned for any subsequent call.

    .. versionadded:: 0.4
    """
    yield value
    while True:
        yield then
