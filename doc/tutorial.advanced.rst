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

Mocking I/O
-----------

Testing libraries or functions dealing with low-level IO objects may be
complex. For instance, mocking a socket or a file-like object, because
simulating their behavior may require to know exactly how the tested library
will used them.

Even worse, using mocks in place of files will often raise :exc:`OSError`.

:mod:`asynctest` provides special mocks which can be used in place of actual
file-like objects. They are supported by the loop provided by
:class:`~asynctest.TestCase` if the loop uses a standard implementation with a
selector (Window's Proactor loop or uvloop are not supported).

These mocks are configured with a spec matching common file-like objects.

=================================== ========================================
  Mock                               ``spec``
=================================== ========================================
 :class:`~asynctest.FileMock`        a file object, implements ``fileno()``
 :class:`~asynctest.SocketMock`      :class:`socket.socket`
 :class:`~asynctest.SSLSocketMock`   :class:`ssl.SSLSocket`
=================================== ========================================

:func:`asynctest.isfilemock()` can be used to differenciate mocks from regular
objects.

As of :mod:`asynctest` 0.12, these mocks don't provide other features, and must
be configured to return expected values for calls to methods like ``read()`` or
``recv()``.

However, when configured, it is necessary to force the loop to detect that I/O
is possible on these mock files.

This is done with :func:`~asynctest.set_read_ready()` and
:func:`~asynctest.set_write_ready()`.


.. literalinclude:: examples/tutorial/mocking_io.py
   :pyobject: TestMockASocket

In this example a socket mock is configured to simulate a simple
request-response scenario. Some data is available to read on the socket once a
request has been written. ``recv_side_effect()`` makes as if the data is
received in several packets, but it has no impact on the high level
:class:`~asyncio.StreamReader`.

It's common that while a read operation blocks until data is available, a write
is often successful.  Thus, the case where the congestion control delays the
write has not been simulated.

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
