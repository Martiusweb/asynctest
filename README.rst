=======
aiotest
=======

The package aiotest is built on top of the standard unittest module and brings
features which ease and cut boilerplate code when testing libraries for
asyncio.

Currently, aiotest only supports Python 3.4.

Author & license
-------

Authored by Martin Richard <martius@martiusweb.net> and licensed under the
Apache 2 license.

Features
--------

TestCase and FunctionTestCase
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  - Initialize and close a loop created for each test,
  - if the test function is a coroutine function or returns a coroutine, it
    will run on the loop,
  - TestCase.setUp() and TestCase.tearDown() can be coroutine functions,
  - a test fails if the loop did not run during the test.


Mock and CoroutineMock
~~~~~~~~~~~~~~~~~~~~~~

  - CoroutineMock is a new Mock class which mocks a coroutine function, and
    returns a coroutine when called,

  - NonCallableMock, Mock and CoroutineMock can return CoroutineMock objects
    when its attributes are get if there is a matching attribute in the spec
    (or spec_set) object which is a coroutine function,

  - patch(), patch.object(), patch.multiple() return a MagickMock or
    CoroutineMock object by default, according to the patched target,

  - all the patch() methods can decorate coroutine functions,

  - mock_open() returns a MagickMock object by default.


Helpers
~~~~~~~

  - the coroutine exhaust_callbacks(loop) returns once all the callbacks which
    should be called immediatly are executed, which is useful when the test
    author needs to assert things which are not yet executed by the loop.


Tests
-----

How to run the tests?

::

$ PYTHONPATH=. python -m unittest test
