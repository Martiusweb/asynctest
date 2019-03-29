Advanced Features
=================

TODO

Controlling time
----------------

TODO

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
