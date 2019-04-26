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
suite, and encourage us to deactivate or ignore these tests.

:class:`~asynctest.ClockedTestCase` is a subclass of
:class:`~asynctest.TestCase` which replaces the clock of the loop in a test
with a manually-controlled one. The clock will only advance when calling
:meth:`~asynctest.ClockedTestCase.advance`.

This will not affect the wall clock: functions like :func:`time.time` or
:meth:`datetime.datetime.now` will return the regular date and time of the
system.

.. literalinclude:: examples/tutorial/clock.py
   :pyobject: TestAdvanceTime

This example is pretty self-explanatory: we verified that the clock of the loop
advanced as expected, without awaiting 10 actual seconds and changing the time
of the wall clock.

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
complex: these objects are outside of our control, since they are owned by the
kernel. It can be impossible to exactly predict their behavior and simulate
edge-cases, such as the ones happening in a real-world scenario in a large
network.

Even worse, using mocks in place of files will often raise :exc:`OSError`
because these obhjects are not compatible with the features of the system used
by the loop.

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

We can use :func:`asynctest.isfilemock()` to differenciate mocks from regular
objects.

As of :mod:`asynctest` 0.12, these mocks don't provide other features, and must
be configured to return expected values for calls to methods like ``read()`` or
``recv()``.

When configured, we still need to force the loop to detect that I/O is possible
on these mock files.

This is done with :func:`~asynctest.set_read_ready()` and
:func:`~asynctest.set_write_ready()`.

.. literalinclude:: examples/tutorial/mocking_io.py
   :pyobject: TestMockASocket

In this example, we configure a socket mock to simulate a simple
request-response scenario with a TCP (stream) socket. Some data is available to
read on the socket once a request has been written. ``recv_side_effect()``
makes as if the data is received in several packets, but it has no impact on
the high level :class:`~asyncio.StreamReader`.

It's common that while a read operation blocks until data is available, a write
is often successful. Thus, we didn't bother simulating the case where the
congestion control would block the write operation.

Testing with event loop policies
--------------------------------

Advanced users may not be able to use the loop provided by
:class:`~asyncio.TestCase` because they use a customized event loop policy (see
:py:ref:`asyncio-policies`). It is often the case when using an alternative
implementation (like `uvloop <https://uvloop.readthedocs.io/>`_) or if the
tests are integrated within a framework hidding the scheduling and management
of the loop.

It is possible to force the :class:`~asynctest.TestCase` to use the loop
provided by the policy by setting the class attribute
:attr:`~asynctest.TestCase.use_default_loop`.

Conversely, authors of libraries may not want to assume which loop they should
use and let users explicitly pass the loop as argument to a function call. For
instance, most of the high-level functions of :py:mod:`asyncio` (see
:py:ref:`asyncio-streams`, for instance) allow the caller to specify the loop
to use if it needs this kind of flexibility.

:attr:`~asynctest.TestCase.forbid_get_event_loop` forbids the use of
:meth:`asyncio.get_event_loop`. An exception is raised if the method is
called while a test is running. It helps developers to ensure they don't rely
on the default loop this their library.

.. note::

   The behavior of :meth:`asyncio.get_event_loop()` changed over time.
   Explicitly passing the loop is not the recommended practice anymore.
