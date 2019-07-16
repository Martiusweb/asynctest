.. image:: https://img.shields.io/pypi/v/asynctest.svg
    :target: https://pypi.python.org/pypi/asynctest
    :alt: PyPI
.. image:: https://travis-ci.org/Martiusweb/asynctest.svg?branch=master
    :target: https://travis-ci.org/Martiusweb/asynctest
    :alt: Travis
.. image:: https://ci.appveyor.com/api/projects/status/github/Martiusweb/asynctest?branch=master&svg=true
    :target: https://ci.appveyor.com/project/Martiusweb/asynctest/branch/master
    :alt: AppVeyor
.. image:: https://img.shields.io/pypi/pyversions/asynctest.svg
    :target: https://pypi.python.org/pypi/asynctest
    :alt: Supported Python versions
.. image:: https://img.shields.io/pypi/implementation/asynctest.svg
    :target: https://pypi.python.org/pypi/asynctest
    :alt: Supported Python implementations

=========
asynctest
=========

The package asynctest is built on top of the standard unittest module and
cuts down boilerplate code when testing libraries for asyncio.

Currently, asynctest targets the "selector" model, hence, some features
will not (yet?) work with Windows' proactor.

⚠️  Warning: **changes in 0.13**

Since asynctest 0.13, some major changes may impact you:

* Python 3.4 is not supported anymore: importing asynctest will raise a syntax
  error.
* ``@patch`` decorators used to re-use the mock object for each call of the
  coroutine, which is inconsistent with the behavior of ``@unittest.patch``.
  See `issue #121 <https://github.com/Martiusweb/asynctest/issues/121>`_ for
  the details.

Author & license
----------------

Authored by Martin Richard <martius@martiusweb.net> and licensed under the
Apache 2 license.

   Copyright 2019 Martin Richard


In addition, permission is explicitly granted to Python contributors to use,
copy, modify, (...) the code and documentation of asynctest for any project of
the Python Software Foundation. This gives the PSF the irrevocable and
perpetual rights that the PSD claims in its CLA.

This means that by contributing to asynctest, you agree that these
contributions may be included in any project of the Python Software Foundation,
and can be subject to re-licensing under the Python Software License.

See the AUTHORS file for a comprehensive list of the authors.

Documentation
-------------

.. image:: https://readthedocs.org/projects/asynctest/badge/
   :target: http://asynctest.readthedocs.org/en/latest/

Full documentation is available at http://asynctest.readthedocs.org/en/latest/.
It includes a tutorial with tested examples of how to use ``TestCase`` or
mocks.

Features
--------

TestCases
~~~~~~~~~

  - Initialize and close a loop created for each test (it can be
    configurated), if the loop uses a selector, it will be updated with
    a TestSelector object wrapping the original selector (see below),

  - if the test function is a coroutine function or returns a coroutine, it
    will run on the loop,

  - TestCase.setUp() and TestCase.tearDown() can be coroutine functions,

  - control post-test checks with `@fail_on`, for instance, the test fail if
    the loop didn't run, some optional checks can be activated,

  - ClockedTestCase allows to control the loop clock and run timed events
    without waiting the wall clock.

Mock and CoroutineMock
~~~~~~~~~~~~~~~~~~~~~~

  - CoroutineMock is a new Mock class which mocks a coroutine function, and
    returns a coroutine when called,

  - MagicMock supports asynchronous context managers and asynchronous
    iterators,

  - NonCallableMock, Mock and CoroutineMock can return CoroutineMock objects
    when its attributes are get if there is a matching attribute in the spec
    (or spec_set) object which is a coroutine function,

  - patch(), patch.object(), patch.multiple() return a MagickMock or
    CoroutineMock object by default, according to the patched target,

  - patch(), patch.object(), patch.multiple() handle generators and coroutines
    and their behavior can be controled when the generator or coroutine pauses,

  - all the patch() methods can decorate coroutine functions,

  - mock_open() returns a MagickMock object by default.

  - return_once() can be used with Mock.side_effect to return a value only
    once when a mock is called.

Selectors
~~~~~~~~~

The module asynctest.selector provides classes to mock objects performing IO
(files, sockets, etc).

  - FileMock is a special type of mock which represents a file.
    FileMock.fileno() returns a special value which allows to identify uniquely
    the mock,

  - SocketMock is a special type of FileMock which uses socket.socket as spec,

  - TestSelector is a custom selector able to wrap a real selector
    implementation and deal with FileMock objects, it can replace a selector
    loop by calling `loop._selector = TestSelector(loop._selector)`, and will
    intercept mock so they don't get registered to the actual selector.

  - set_read_ready() and set_write_ready() to force read and write event
    callbacks to be scheduled on the loop, as if the selector scheduled them.

Helpers
~~~~~~~

  - the coroutine exhaust_callbacks(loop) returns once all the callbacks which
    should be called immediately are executed, which is useful when the test
    author needs to assert things which are not yet executed by the loop.

Roadmap
-------

I hope I will find time to develop and release the following features:

- set of warnings against common mistakes
- proactor support

Tests
-----

asynctest is unit tested. You can run asynctest test suite with this command::

$ PYTHONPATH=. python -m unittest test
