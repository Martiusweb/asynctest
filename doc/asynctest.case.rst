.. automodule:: asynctest.case

    .. toctree::
       :maxdepth: 2


    TestCases
    ~~~~~~~~~

    .. autoclass:: asynctest.TestCase
        :members:
        :undoc-members:
        :exclude-members: debug, run

        .. method:: setUp()

            Method or coroutine called to prepare the test fixture.

            see :py:meth:`unittest.TestCase.setUp()`

        .. method:: tearDown()

            Method called immediately after the test method has been called and
            the result recorded.

            see :py:meth:`unittest.TestCase.tearDown()`

    .. autoclass:: asynctest.FunctionTestCase
        :members:
        :undoc-members:

    .. autoclass:: asynctest.ClockedTestCase
        :members:
        :undoc-members:
        :exclude-members: setUp

    Decorators
    ~~~~~~~~~~
    .. decorator:: asynctest.fail_on(**checks)

        Enable checks on the loop state after a test ran to help testers to
        identify common mistakes.

        Enable or disable a check using a keywork argument with a boolean
        value::

            @asynctest.fail_on(unused_loop=False)
            class TestCase(asynctest.TestCase):
                ...

        Available checks are:

            * ``unused_loop``: enabled by default, checks that the loop ran at
              least once during the test. This check can not fail if the test
              method is a coroutine. This allows to detect cases where a test
              author assume its test will run tasks or callbacks on the loop,
              but it actually didn't.

        The decorator of a method has a greater priority than the decorator of
        a class. When :func:`~asynctest.fail_on` decorates a class and one of
        its methods with conflicting arguments, those of the class are
        overriden.

        Subclasses of a decorated :class:`~asynctest.TestCase` inherit of the
        checks enabled on the parent class.

        .. versionadded:: 0.8

    .. decorator:: strict

        Activate strict checking of the state of the loop after a test ran.

        It is a shortcut to :func:`~asynctest.fail_on` with all checks set to
        ``True``.

        Note that by definition, the behavior of :func:`strict` will change in
        the future when new checks will be added, and may break existing tests
        with new errors after an update of the library.

        .. versionadded:: 0.8

    .. decorator:: lenient

        Deactivate all checks performed after a test ran.

        It is a shortcut to :func:`~asynctest.fail_on` with all checks set to
        ``False``.

        .. versionadded:: 0.8

    .. decorator:: asynctest.ignore_loop

       By default, a test fails if the loop did not run during the test
       (including set up and tear down), unless the
       :class:`~asynctest.TestCase` class or test function is decorated by
       :func:`~asynctest.ignore_loop`.

        .. deprecated:: 0.8

            Use :func:`~asynctest.fail_on` with ``unused_loop=False`` instead.
