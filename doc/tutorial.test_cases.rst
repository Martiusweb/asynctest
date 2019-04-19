Test cases
==========

Writing and running a first test
--------------------------------

Tests are written in classes inheriting :class:`~asynctest.TestCase`. A test
case consists of:

* some set-up which prepares the environment and the resources required for the
  test to run,
* a list of assertions, usually as a list of checks that must be verified to
  mark the test as successful,
* some finalization code which cleans the resources used during the test. It
  should revert the environment back to its state before the set-up.

Let's look at a minimal example:

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: MinimalExample

In this example, we created a test which contains only one assertion: it
ensures that ``True`` is, well, true.

:meth:`~unittest.TestCase.assertTrue` is a method of
:class:`~asynctest.TestCase`. If the test is successful, it does nothing. Else,
it raises an :exc:`AssertionError`.

The documentation of :mod:`unittest` lists :py:ref:`assertion methods
<assert-methods>` implemented by :class:`unittest.TestCase`.
:class:`asynctest.TestCase` adds some more for asynchronous code.

We can run it by creating an instance of our test case, its constructor takes
the name of the test method as argument:

>>> test_case = MinimalExample("test_that_true_is_true")
>>> test_case.run()
<unittest.result.TestResult run=1 errors=0 failures=0>

To make things more convenient, :mod:`unittest` provides a test runner
script. The runner discovers test methods in a module (or package, or class) by
looking up methods with a name prefixed by ``test_`` in
:class:`~unittest.TestCase` subclasses::

    $ python -m unittest test_cases
    .
    ----------------------------------------------------------------------
    Ran 1 test in 0.001s

    OK

The runner will create and run an instance of the test case (as shown in the
code above) for each method that it finds. This means that you can add as many
test methods to your :class:`~asynctest.TestCase` class as you want.

Test setup
----------

Let's work on a slightly more complex example:

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: AnExampleWithSetup

Here, we create a loop that will run a coroutine, ensure that the result of
this coroutine is as expected (it should return an object containing the string
``"worked"`` somewhere). Then we close the loop, even if an exception was
raised.

If we happen to write several test methods, the set-up and clean-up will likely
be repeated several times. It's probably more convenient to move these parts
into their own methods.

We can override two methods of the :class:`~asynctest.TestCase` class:
:meth:`~unittest.TestCase.setUp` and :meth:`~unittest.TestCase.tearDown` which
will be respectively called before the test method and after the test method:

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: AnExampleWithSetupMethod

Both examples are very similar: :class:`~asynctest.TestCase` will run
:meth:`~asynctest.TestCase.tearDown` even if an exception is raised in the test
method.

However, if an exception is raised in :meth:`~unittest.TestCase.setUp`, the
test execution is aborted and :meth:`~unittest.TestCase.tearDown` will never
run. If the setup fails in between the initialization of several resources,
some of them will never be cleaned.

This problem can be solved by registering clean-up callbacks which will always
be executed. A clean-up callback is a function without (required) arguments
that is passed to :meth:`~unittest.TestCase.addCleanup`.

Using this feature, we can rewrite our previous example:

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: AnExampleWithSetupAndCleanup

Tests should always run isolated from the others, this is why tests should only
rely on local resources created for the test itself. This ensures that a test
will not impact the execution of other tests, and can greatly help to get an
accurate diagnostic when debugging a failing test.

It's also worth noting that the order in which tests are executed by the test
runner is undefined. It can lead to unpredictable behaviors if tests share some
resources.

Testing asynchronous code
-------------------------

Speaking of tests isolation, it's usually preferable to create one loop per
test. If the loop is shared, one test could (for instance) schedule a task and
never await its result, the task would then run (and possibly trigger
unexpected side effects) in another test.

:class:`asynctest.TestCase` will create (and clean) an event loop for each test
that will run. This loop is set in the :class:`~asynctest.TestCase.loop`
attribute. We can use this feature and rewrite the previous example:

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: AnExampleWithTestCaseLoop

Tests functions can be coroutines. :class:`~asynctest.TestCase` will schedule
them on the loop.

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: AnExampleWithTestCaseAndCoroutines

:meth:`~unittest.TestCase.setUp` and :meth:`~unittest.TestCase.tearDown` can
also be coroutines, they will all run in the same loop.

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: AnExampleWithAsynchronousSetUp


.. note::

   The functions :meth:`~unittest.TestCase.setUpClass`,
   :meth:`~unittest.setUpModule` and their ``tearDown`` counterparts can not be
   coroutine. This is because the loop only exists in an instance of
   :class:`~asynctest.TestCase`.

   In practice, these methods should be avoided because they will not allow to
   reset the environment between tests.

Automated checks
----------------

Asynchronous code introduces a class of subtle bugs which can be hard to
detect. In particular, clean-up of resources is often performed asynchronously
and can be missed in tests.

:class:`~asynctest.TestCase` can check and fail if some callbacks or resources
are still pending at the end of a test.

These checks can be configured with the decorator :meth:`~asynctest.fail_on`.

.. literalinclude:: examples/tutorial/test_cases.py
   :pyobject: AnExempleWhichDetectsPendingCallbacks

This test will fail because the test don't wait long enough or doesn't cancel
the callback ``i_must_run()``, scheduled to run in 1 second::

   ======================================================================
   FAIL: test_missing_a_callback (tutorial.test_cases.AnExempleWhichDetectsPendingCallbacks)
   ----------------------------------------------------------------------
   Traceback (most recent call last):
     File "/home/martius/Code/python/asynctest/asynctest/case.py", line 300, in run
       self._tearDown()
     File "/home/martius/Code/python/asynctest/asynctest/case.py", line 262, in _tearDown
       self._checker.check_test(self)
     File "/home/martius/Code/python/asynctest/asynctest/_fail_on.py", line 90, in check_test
       getattr(self, check)(case)
     File "/home/martius/Code/python/asynctest/asynctest/_fail_on.py", line 111, in active_handles
       case.fail("Loop contained unfinished work {!r}".format(handles))
   AssertionError: Loop contained unfinished work (<TimerHandle when=3064.258340775 AnExempleWhichDetectsPendingCallbacks.i_must_run()>,)

   ----------------------------------------------------------------------

Some convenient decorators can be used to enable of disable all checks:
:func:`~asynctest.strict` and :func:`~asynctest.lenient`.

All decorators can be used on a class or test function.

Conclusion
----------

:class:`~asynctest.TestCase` provides handy features to test coroutines and
asynchronous code.

In the next section, we will talk about mocks. Mocks are objects simulating the
behavior of other objects.
