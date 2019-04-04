Mocking
=======

Mocks are objects whose behavior can be controlled and which record how they
are used. They are very commonly used to write tests. The next section presents
the concept of a mock with an example. The rest of the chapter presents the
features of :mod:`asynctest.mock`.

Using mocks
-----------

Let's have a look at a function to be tested.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: cache_users


Even if the implementation of this function is correct, it can fail. For
instance, ``client.get_users()`` performs calls to a distant server, which can
fail temporarily.

It would also be complicated to create multiple test cases if the result of
``client.get_users()`` can't be controlled inside the tests.

One can solve this problem by crafting a stub object:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: StubClient

Tests can be written with this object.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestUsingStub

This will work correctly but has a few downsides. One of them is very
practical: each time the interface of the stubbed class change, the stub must
be updated.

There is also a bigger problem. In our example, ``test_no_users_to_add()``
might miss a bug. If ``cache_users()`` doesn't call ``client.get_users()``, no
user is added to the cache, yet all the assertions in the test are checked.

In this example, the bug would be detected thanks to the other test. However,
it might not be the case with a more complex implementation. The key to write a
a better test is to enforce all the assumtions and requirements stated in the
documentation.

Currently, the test can be described this way:

   knowing that:

     * ``client.get_users()`` will return an empty result,
     * and that the cache is empty,

   a call to ``cache_user()`` must leave the cache empty.

Instead, it should be:

   knowing that:

     * ``client.get_users()`` will return an empty result,
     * and that the cache is empty,

   a call to ``cache_user()`` *must have queried the client* and must leaves
   the cache empty.

Mocks solve both of the issues discussed above. A mock can be configured to act
like an actual object, and provides assertion methods to verify how the object
has been used.

We can leverage the mock to test another statement of the documentation and
verify that the server is indeed notified of the number of users added to the
cache.


.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestUsingMock

In this example, client is a :class:`~asynctest.Mock`. This mock will reproduce
the interface of ``Client()`` (an instance of the ``Client`` class, ommited for
simplicity).

By default, the attributes of a mock object are themselves mocks. In the above
example, ``client.get_users`` is configured to return an empty list when
called. By default, a new mock object would have been returned instead.

Later, ``client.get_users.assert_called()`` verifies that the method has been
called. ``client.increase_nb_users_cached.assert_called_once_with(1)`` verifies
that this method has been called, and that the right arguments have been
provided.

Mocks are powerful and can be configured in many ways. Unfortunatly, they can
be somewhat complex to use.

.. warning::

   In the above example, ``client`` is specified as a mock of ``Client()``, but
   ``client.get_users`` is a new mock without sepcification.

   When unspecified, is it allowed to access any attribute of a mock object,
   even if it didn't exist yet. This attribute will itself be a mock.

   As a consequence, it's easy to miss a mispelled call to
   :meth:`~unittest.mock.assert_called()`.

   For instance::

      client.get_users.assert_is_called()

   will not fail, because accessing ``client.get_users.assert_is_called``
   doesn't raise an :exc:`AttributeError`.

The next sections of this chapter will present the features of
:class:`asynctest.Mock` related to :mod:`asyncio`. It is recommended to be
familiar with the module :mod:`unittest.mock` before reading the rest of this
chapter.

Mocking of coroutines
---------------------

Let's rewrite the previous example using asyncio.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: cache_users_async

A mock object can not be awaited (with the ``await`` keyword). There are
several ways to make ``client.get_users()`` awaitable. One approach is to
configure the mock to return a :class:`asyncio.Future` object:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestUsingFuture

``client.get_users()`` returns is a future which yields an empty list. It
works, but is fairly limited. For instance, if the original ``get_users()`` is
a coroutine function, this is not the case of its mock counterpart.

This test can also miss a new bug now: what if
``client.increase_nb_users_cached()`` is never awaited? The method has been
called, and since the result is a :class:`~asyncio.Future`, this mistake will
not be caught if the test run with asyncio's :ref:`asyncio-debug-mode`.

:class:`asynctest.CoroutineMock` is a type of mock which specializes in mocking
coroutine functions (defined with ``async def``). A
:class:`~asynctest.CoroutineMock` object is not awaitable, but it returns a
coroutine instance when called.

It provides assertion methods to ensure it has been awaited, as shown in this
example:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestUsingCoroutineMock

All the features of :class:`asynctest.CoroutineMock` are decribed in the
reference documentation.


Mocking of other objects
------------------------

TODO how a coroutine is detected
TODO

Auto-spec
---------

TODO

asynchronous iterators and context managers
-------------------------------------------

TODO

Patching
--------

TODO

Scope of the patch
~~~~~~~~~~~~~~~~~~

TODO
