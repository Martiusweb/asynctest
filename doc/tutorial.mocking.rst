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


.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestUsingMock

By default, a mock can be called like a function, and it behaves as an object
whose attributes are also mocks. In the above example, ``client.get_users`` is
itself a mock. It has been configured to return an empty list when called. By
default, a new mock object would have been returned instead.

Later, ``client.get_users.assert_called()`` verifies that the method has been
called.

.. warning::

   Since accessing the attribute never raises an :exc:`AttributeError` by
   default, and that a mock can be called, it's easy to miss a mispelled call
   to :meth:`~unittest.mock.assert_called()`.

   For instance::

      asyctest.Mock().assert_is_called()

   will not fail, because this expression returns a new mock object.

   Configuring more precisely a mock object avoids these problems.

Mocks are powerful and can be configured in many ways. Unfortunatly, they are
somewhat complex to use.

The next sections of this chapter will present the features of
:class:`asynctest.Mock` related to :mod:`asyncio`. It is recommended to be
familiar with the module :mod:`unittest.mock` before reading the rest of this
chapter.

Mocking of coroutines
---------------------

TODO CoroutineMock mocks the coroutine, not the function
TODO how a coroutine is detected

Mocking of other objects
------------------------

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
