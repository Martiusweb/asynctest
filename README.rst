=======
aiotest
=======

The package aiotest is built on top of the standard unittest module and brings
features which ease and cut boilerplate code when testing libraries for
asyncio.

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
