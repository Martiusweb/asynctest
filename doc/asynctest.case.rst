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
    .. decorator:: asynctest.ignore_loop

       By default, a test fails if the loop did not run during the test
       (including set up and tear down), unless the
       :class:`~asynctest.TestCase` class or test function is decorated by
       :func:`~asynctest.ignore_loop`.
