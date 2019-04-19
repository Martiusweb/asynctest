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

   a call to ``cache_users()`` must leave the cache empty.

Instead, it should be:

   knowing that:

     * ``client.get_users()`` will return an empty result,
     * and that the cache is empty,

   a call to ``cache_users()`` *must have queried the client* and must leaves
   the cache empty.

Mocks solve both of the issues discussed above. A mock can be configured to act
like an actual object, and provides assertion methods to verify how the object
has been used.

We can also leverage the mock to test another statement of the documentation
and make the test even more accurate. We will verify that the server is indeed
notified of the number of users added to the cache.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestUsingMock

In this example, client is a :class:`~asynctest.Mock`. This mock will reproduce
the interface of ``Client()`` (an instance of the ``Client`` class, ommited for
simplicity, available in the example file :doc:`examples/tutorial/mocking.py`).

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
not be caught if the test runs with asyncio's :ref:`asyncio-debug-mode`.

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
   :dedent: 4

.. note::

   :mod:`asynctest` will mock an attribute as a
   :class:`~asynctest.CoroutineMock` if the function is a native coroutine
   (``async def`` function) or a decorated generator (using
   :func:`asyncio.coroutine`, before Python 3.5).

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
thus, ``ClientMock().get_users`` is not mocked as a coroutine. We need
autospeccing to fix this.

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
   :dedent: 4

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
   :dedent: 4

Types of mocks
--------------

There are several types of mocks with slightly different features:

* :class:`~asynctest.Mock` is the base mock type.
* :class:`~asynctest.MagicMock`, it is very similar to :class:`~asynctest.Mock`,
  except that magic methods are also mocks, and can be configured::

   >>> asynctest.Mock().__hash__
   <method-wrapper '__hash__' of Mock object at 0x7fb514e3a748>
   >>> asynctest.MagicMock().__hash__
   <MagicMock name='mock.__hash__' id='140415716319528'>
   >>> asynctest.MagicMock().__hash__.return_value = "custom value"

* :class:`~asynctest.NonCallableMock` and
  :class:`~asynctest.NonCallableMagicMock` are their non-callable counterparts.
  It's usually better to use them when mocking objects or values.
* :class:`~asynctest.CoroutineMock` mocks a coroutine function (or, more
  generaly, any callable object returning an awaitable).

As mentioned before, a *child mock* is a mock attached to another mock. The
child mock is either an attribute of the parent mock, or the result of a call
to the parent mock. This relationship enables some features documented in the
documentation of :class:`unittest.mock.Mock`.

Attaching a child mock is just a matter of setting the right attribute::

   client_mock = asynctest.Mock()
   # manually attaching a child mock to get_users
   mock.get_users = asynctest.Mock()
   # manually attaching the returned child mock to get_users()
   mock.get_users.return_value = asynctest.NonCallableMock()

By default, the child mock is the result of the factory method
:meth:`~unittest.mock.Mock._get_child_mock()`, and its result depend on the
type of mock:

==========================================  ================================
 parent mock                                 child mock
==========================================  ================================
 :class:`~asynctest.Mock`                    :class:`~asynctest.Mock`
 :class:`~asynctest.MagicMock`               :class:`~asynctest.MagicMock`
 :class:`~asynctest.NonCallableMock`         :class:`~asynctest.Mock`
 :class:`~asynctest.NonCallableMagicMock`    :class:`~asynctest.MagicMock`
 :class:`~asynctest.CoroutineMock`           :class:`~asynctest.MagicMock`
==========================================  ================================

Controlling the result of :class:`~asynctest.CoroutineMock`
-----------------------------------------------------------

Calling a :class:`~asynctest.CoroutineMock` returns a coroutine which can be
awaited.

The result of this coroutine can be configured like the result of a call to a
mock.

``return_value``
~~~~~~~~~~~~~~~~

The simplest way to configure the result of a mock is to set its
``return_value`` attribute. This result will always be returned as it is.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCoroutineMockResult.test_result_set_with_return_value
   :dedent: 4

``side_effect``
~~~~~~~~~~~~~~~

The ``side_effect`` attribute of a mock enables more control over the result of
the mock. If set, it has priority over ``return_value``, which is ignored.

The value of ``side_effect`` can be a function. In this case, the call to the
mock is forwarded to this function, and its result is returned.


.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCoroutineMockResult.test_result_with_side_effect_function
   :dedent: 4

If the side effect is an exception object or class, this exception is raised.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCoroutineMockResult.test_result_with_side_effect_exception
   :dedent: 4

Last but not least, ``side_effect`` can be any iterable object. In this case,
the mock will return each value once, until the iterator is exhausted and
:exc:`StopIteration` is raised to the caller.

:func:`itertools.cycle` allows to repeat the iterator.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCoroutineMockResult.test_result_with_side_effect_iterable
   :dedent: 4

.. important::

   If the value of ``side_effect`` is a coroutine function or a generator
   function, it is treated as a regular function.

   The result of a call to this mock will be an instance of the coroutine or
   generator.

   As of asynctest 0.12, specifying a coroutine function as the side effect of
   :class:`~asynctest.CoroutineMock` is undefined and should be avoided.
   See `Github issue #31 <https://github.com/Martiusweb/asynctest/issues/31>`_.

Wrapped object
~~~~~~~~~~~~~~

A mock can also wrap an object. This wrapped object is defined as an argument
passed to the constructor of the mock.

When a mock or any of its attributes is called, the call is forwarded to the
wrapped object, like if it was the value of ``side_effect``. If ``side_effect``
or ``return_value`` are set for the mock, they will have priority over the
wrapper.

In practice, this is equivalent to adding the features of a
:class:`~asynctest.Mock` to a stub object.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCoroutineMockResult.test_result_with_wrapped_object
   :dedent: 4

Asynchronous iterators and context managers
-------------------------------------------

Python 3.5 introduced the support for asynchronous iterators and context
managers. They can be implemented with the magic methods ``__aiter__()``,
``__anext__()``, ``__aenter__()``, ``__aexit__()`` as described in
:pep:`0492#asynchronous-context-managers-and-async-with`.

:class:`~asynctest.MagicMock` will mock these methods and greatly simplify
their configuration.

In the example we used so far, we assumed that ``client.get_users()`` loads all
users from a database and store them in a list that it will return. This
implementation may consume a lot of memory if there are a lot of users to
return. We can instead use a *cursor*.

A cursor is an object *pointing to* the result of the query *get all users* on
the database. It keeps an open connection to the database and fetches the
objects lazily (only when they are really needed). It allows to load the users
one by one from the database, and avoid filling the memory with all users at
once.

It is also common to wrap several related queries to a database in a
transaction to ensure the sequence of calls is consistent. A better
implementation of ``cache_users()`` should keep the calls to ``get_users()``
and ``increase_nb_users_cached()`` in the same transaction.

The ``cache_users()`` implementation will look like this:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: cache_users_with_cursor

``client.new_transaction()`` returns a transaction object. Under the hood,
``async with`` calls its coroutine method ``__aenter__()`` and the result is
stored in the variable ``transaction``.

``users_cursor`` is an asynchronously iterable object. It implements the method
``__aiter__()``, which returns an asynchronous iterator. ``__aiter__()`` is a
function, not a coroutine. For each iteration of the ``async for`` loop,  the
coroutine method ``__anext__()`` of the asynchronous iterator is called and its
result is assigned to ``user``.

When the interpreter leaves the ``async with`` block, ``__aexit__()`` is
called.

A partial implementation of this logic can be found in the example file
:doc:`examples/tutorial/mocking.py`.

The next sections show how to use :class:`~asynctest.MagicMock` to test this
method.

Asynchronous context manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~asynctest.MagicMock` mocks ``__aenter__`` with a
:class:`~asynctest.CoroutineMock` returning a new child mock.

If an exception is raised in an ``async with`` block, this exception is passed
to ``__aexit__()``. In this case, the return value defines wether the
interpreter suppresses or propagates the exception, as described in the
documentation of :meth:`object.__exit__`.

:class:`~asynctest.MagicMock` mocks ``__aexit__`` with a
:class:`~asynctest.CoroutineMock` returning ``False`` by default, which means
that the exception is propagated.

By default, we can use a :class:`~asynctest.MagicMock` in an ``async with``
block without configuration, exceptions raised in this block are propagated:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestWithMagicMethods.test_context_manager
   :dedent: 4

However, in the example above, the ``transaction`` object exposes the same
methods as ``client``. In particular, We must configure this mock so
``transaction.increase_nb_users_cached()`` is a coroutine.

Asynchronous iterator
~~~~~~~~~~~~~~~~~~~~~

The method ``__aiter__()`` of a :class:`~asynctest.MagicMock` returns an
asynchronous iterator. By default, this iterator is empty.


.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestWithMagicMethods.test_empty_iterable
   :dedent: 4

The values yielded by the iterator can be configured by setting the
``return_value`` of ``__aiter__``. This value must be an iterable object, such
as a list or a generator:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestWithMagicMethods.test_iterable
   :dedent: 4

.. note::

   As of asynctest 0.12, it is not possible to use an asynchronously iterable
   object as ``return_value`` for ``__aiter__()``.

   Setting ``side_effect`` allows to override the behavior of
   :class:`~asynctest.MagicMock`.

Putting it all together
~~~~~~~~~~~~~~~~~~~~~~~

We can leverage  several features of :mod:`asynctest` when testing
``cache_users_with_cursor()``:

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCacheWithMagicMethods

This example deserve some explanation.

First, we use :func:`~asynctest.create_autospec()` to build a mock of the
class `AsyncClient`.

``transaction`` will be the object configured as a context manager. When called
with ``async with``, it must return an object with an interface as ``client``.
We set ``AsyncClientMock`` as a side effect to ``transaction.__aenter__``,
which means that a new mock of an instance of ``AsyncClient`` will be issued
each time ``transaction`` is used in an ``async width`` block.

``cursor`` will be used in the ``async for`` loop. The iterator will yield the
values of ``cursor.__aiter__.return_value``. We set to a list containing a
single ``User`` object. A new iterator is created each time an ``async for``
loop is called upon the cursor, it is safe to use this mock several times.

We then create ``client``, a mock created from ``AsyncClientMock``. We
configure it so the return values of ``client.new_transaction()`` and
``client.get_users_cursor()`` are the mocks we created above.

Note that we configured the behavior of ``client``'s attributes, not those of
``AsyncClientMock``. This is because the child mock of an autospecced class
will not inherit the behavior of the parent mock, only its spec.

Patching
--------

Patching is a mechanism allowing to temporarily replace a symbol (class,
object, function, attribute, …) by a mock, in-place. It is especially useful
when one need a mock, but can't pass it as a parameter of the function to be
tested.

For instance, if ``cache_users()`` didn't accept the ``client`` argument, but
instead created a new client, it would not be possible to replace it by a mock
like in all the previous examples.

When an object is hard to mock, it sometimes shows a limitation in the design:
a coupling that is too tight, the use of a global variable (or a singleton),
etc. However, it's not always possible or desirable to change the code to
accomodate the tests. A common situation where tight coupling is almost
invisible is when performing logging or monitoring. In this case, patching will
help.

A :func:`~asynctest.patch` can be used as a context manager. It will replace
the target (:func:`logging.debug`) with a mock during the lifetime of the
``with`` block.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCachingIsLogged.test_with_context_manager
   :dedent: 4

Alternatively, :func:`~asynctest.patch` can be used to decorate a test or a
test class (inheriting :class:`~asynctest.TestCase`). This second example is
roughly equivalent to the previous one. The main difference is that for all
tests affected by the patch (the decorated method or all test methods in a
decorated test class) must accept an additional argument which will receive
the mock object used by the patch.

Note that when using multiple decorators on a single method, the order of the
arguments is inversed compared to the order of the decorators. This is due to
the way decorators work in Python, a topic which we don't cover in this
documentation.

.. literalinclude:: examples/tutorial/mocking.py
   :pyobject: TestCachingIsLogged.test_with_decorator
   :dedent: 4

.. note::

   In practice, we should have used :meth:`unittest.TestCase.assertLogs()`. It
   asserts that a given message have been logged and makes more sense than
   manually patching :mod:`logging`.


There are variants of :func:`~asynctest.patch`:

* :func:`asynctest.patch.object` patches the attribute of a given
  object,
* :func:`asynctest.patch.multiple` patches several attributes of a given
  object,
* :func:`asynctest.patch.dict` patches the values in a ``dict`` for the given
  indices.

The official python documentation provide extensive details about how to define
the target of a patch in its section :ref:`where-to-patch`.

Scope of the patch
~~~~~~~~~~~~~~~~~~

There is one hidden catch in the examples above: what happens to the patch when
the interpreter reaches the ``await`` statement and pauses the coroutine?

When patch is used as a context manager, the patch stays active until the
interpreter reached the end of the ``with`` block.

When used as a decorator, the patch is activated right before the function (or
coroutine) is executed, and deactivated once it returned. This is equivalent to
englobing the body of the function in a ``with`` statement instead of using the
decorator.

However, since couroutines are asynchronous, the work performed by the
interpreter while the coroutine is paused is unpredictable. In some cases, the
patch can conflict with something else, and must only be active when
the patched coroutine is running.

It is possible to control when a :func:`asynctest.patch` must be active when
applied to a coroutine with the argument ``scope``.

If ``scope`` is set to :data:`asynctest.LIMITED`, the patch is active only when
the coroutine is running.

This situation is illustrated in the example bellow. The test case
``TestMustBePatched`` runs a task in background which fails if some patch is
active. It contains two tests: one which shows the test conflicting, and one
which uses the :data:`~asynctest.LIMITED` ``scope`` to deactivate the patch
outside of the test coroutine.

.. literalinclude:: examples/tutorial/patching.py
   :pyobject: TestMustBePatched

In this example, ``happened_once()`` pauses the coroutine until the background
task checked once that the patch is not active. The code of
``must_be_patched``, ``happened_once()`` and ``terminate_and_check_task()`` is
available in the example file :doc:`examples/tutorial/patching.py`.

``test_patching_conflicting()`` fails because the patch is still active when it
is paused and aways the ``self.checked`` event. While paused, the background
task runs, and crashes because the patch is still active.

In ``test_patching_not_conflicting()``, the patch is set with a
:data:`~asynctest.LIMITED` scope, and is active only when the coroutine runs.
When ``await must_be_patched.is_patched()`` runs, the patch is still active.
This coroutine runs in the scope of the outher coroutine (the test): indeed,
``must_be_patched.is_patched()`` is scheduled in the task running the test.

Conclusion
----------

This chapter showed most of the concepts and features of mock relevant when
testing asynchronous code. There are plenty of other features and subtleties
which are covered in the documentation of :mod:`unittest.mock`.
