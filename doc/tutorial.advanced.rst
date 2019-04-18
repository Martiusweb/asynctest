Advanced Features
=================

This chapter describes miscellaneous features of :mod:`asynctest` which can be
leveraged in specific use cases.

Controlling time
----------------

Tests running calls to :func:`asyncio.sleep` will take as long as the sum of
all these calls. These calls are frequent when testing for timeouts, for
instance.

In many cases, this will add a useless delay to the execution of the test
suite, and encourage the test authors to deactivate or ignore these tests.

:class:`~asynctest.ClockedTestCase` is a subclass of
:class:`~asynctest.TestCase` which allows a to advance the clock of the loop in
a test with the coroutine :meth:`~asynctest.ClockedTestCase.advance`.

This will not affect the wall clock: functions like :func:`time.time` or
:meth:`datetime.datetime.now()` will return the regular date and time of the
system.

.. literalinclude:: examples/tutorial/clock.py
   :pyobject: TestAdvanceTime

Internally, :class:`~asynctest.ClockedTestCase` will ensure that the loop is
executed as if time was passing *fast*, instead of jumping the clock to the
target time.

.. literalinclude:: examples/tutorial/clock.py
   :pyobject: TestWithClockAndCallbacks

This example schedules function calls to be executed later by the loop.
Each call will verify that it runs at the expected time.
``@fail_on(active_handles=True)`` ensures that the callbacks have been executed
when the test finishes.

The source code of ``is_time_around()`` can be found in the example file
:doc:`examples/tutorial/clock.py`.

Helpers
-------

TODO

Mocking I/O
-----------

Selector mock etc TODO

Testing with event loop policies
--------------------------------

Advanced users may not be able to use the loop provided by
:class:`~asyncio.TestCase` because they use a customized event loop policy (see
:py:ref:`asyncio-policies`). It is often the case when using an alternative
implementation (like `uvloop <https://uvloop.readthedocs.io/>`_) or need to
integrate their tests with a framework.

It is possible to force the :class:`~asynctest.TestCase` to use the loop
provided by the policy by setting the class attribute
:attr:`~asynctest.TestCase.use_default_loop`.

Conversely, authors of libraries may not want to assume which loop they should
use and let users explicitly pass the loop as argument to a function call. For
instance, this is the case with most of the high-level functions of
:py:mod:`asyncio` (see :py:ref:`asyncio-streams`, for instance).

:attr:`~asynctest.TestCase.forbid_get_event_loop` forbids the use of
:meth:`asyncio.get_event_loop()`, which helps developers to test this case.

.. note::

   The behavior of :meth:`asyncio.get_event_loop()` changed over time.
   Explicitly passing the loop is not the recommended practice anymore.
