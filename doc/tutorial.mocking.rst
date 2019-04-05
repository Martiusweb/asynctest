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

By default, the attributes of a mock object are themselves mocks. We call them
*child mocks*. In the above example, ``client.get_users`` is configured to
return an empty list when called. By default, a new mock object would have been
returned instead.

Later, ``client.get_users.assert_called()`` verifies that the method has been
called. ``client.increase_nb_users_cached.assert_called_once_with(1)`` verifies
that this method has been called, and that the right arguments have been
provided.

Mocks are powerful and can be configured in many ways. Unfortunatly, they can
be somewhat complex to use.

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

:class:`~asynctest.Mock` can be configured with the arguments of its
constructor. The value of ``spec`` defines the list of attributes of the mock.
:mod:`asynctest.Mock` will also detect which attributes are coroutine functions
and mock these attributes accordingly.

It means that in the previous example, it was not required to assign
:class:`~asynctest.CoroutineMock` objects to ``get_users()`` and
``increase_nb_users_cached()``.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestUsingCoroutineMockAndSpec.test_no_users_to_add

.. note::

   :mod:`asynctest` will mock an attribute as a :class:`~CoroutineMock` if the
   function is a native coroutine (``async def`` function) or a decorated
   generator (using :func:`asyncio.coroutine``, before Python 3.5).

   Some libraries document function or methods as coroutines, while they are
   actually implemented as simple functions returning an awaitable object (like
   :class:`asyncio.Future`).

   In this case, :mod:`asynctest` can not detect that it should be mocked with
   :class:`~asynctest.CoroutineMock`.

``spec`` defines the attributes of the mock, but isn't passed to child mocks.
In particular, using a class as ``spec`` will not reproduce the behavior of a
constructor::

   >>> ClientMock = asynctest.Mock(Client)
   <Mock spec='Client' id='140657386768816'>
   >>> ClientMock()
   <Mock name='mock()' id='140657394808144'>
   >>> ClientMock().get_users
   <Mock name='mock().get_users' id='140657394808144'>

In this example, ``ClientMock`` should mock the ``Client`` class, but
``ClientMock()`` doesn't return a mock specified as a ``Client`` instance, and
thus, ``ClientMock().get_users`` is not mocked as a coroutine. Autospeccing
solves this problem.

Autospeccing
------------

As the documentation of :mod:`unittest` says it,
:func:`~asynctest.create_autospec()` creates mock objects that have the same
attributes and methods as the objects they are replacing. Any functions and
methods (including constructors) have the same call signature as the real
object.

It is the best solution to configure mocks to behave accurately like the object
they replace.

The mock of a function or coroutine must be called with the right arguments:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestAutoSpec.test_functions_and_coroutines_arguments_are_checked

.. note::

   This example also shows the use of
   :meth:`~unittest.TestCase.assertRaises()`, which is successful only if an
   exception is raised in the ``with`` block.

   :meth:`~unittest.TestCase.subTest()` is used to document in a human-readable
   format which case is tested. It doesn't change the outcome of the test. The
   message is displayed if an assertion fails, which is especially useful to
   understand faster which part of the test breaks.

:func:`~asynctest.create_autospec()` will mock the constructor of a class as
expected. When called, it returns a mock with the spec of the class:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestAutoSpec.test_create_autospec_on_a_class


Controlling the result of :class:`~asynctest.CoroutineMock`
-----------------------------------------------------------

TODO return value, side effect, wraps

asynchronous iterators and context managers
-------------------------------------------

TODO

Patching
--------

TODO

Scope of the patch
~~~~~~~~~~~~~~~~~~

TODO
