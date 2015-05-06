# coding: utf-8
"""
Wrapper to unittest.mock reducing the boilerplate when testing asyncio powered
code.

Features currently supported:

  * A mock can behave as a coroutine, as specified in the documentation of
    Mock.
"""

import asyncio
import unittest.mock

from unittest.mock import *  # NOQA

DEFAULT = unittest.mock.DEFAULT


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


# Notes about unittest.mock:
#  - MagicMock > Mock > NonCallableMock (where ">" means inherits from)
#  - when a mock instance is created, a new class (type) is created
#    dynamically,
#  - we *must* use magic or object's internals when we want to add our own
#    properties, and often override __getattr__/__setattr__ which are used
#    in unittest.mock.NonCallableMock.
class NonCallableMock(unittest.mock.NonCallableMock):
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


class Mock(unittest.mock.Mock):
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

    >>> type(aiotest.mock.Mock(Foo()).foo)
    <class 'aiotest.mock.CoroutineMock'>

    >>> type(aiotest.mock.Mock(Foo()).bar)
    <class 'aiotest.mock.Mock'>

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
    Enhance aiotest.mock.Mock with features allowing to mock a coroutine
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
