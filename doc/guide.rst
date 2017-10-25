Guide
=====

This guide serves two purposes: it is an introduction to write and run unit
tests with :mod:`asynctest` and a presentation of :mod:`asynctest`:
:class:`~asynctest.TestCase` configuration, mocks, advanced features.

If you are familiar with :mod:`unittest`, you can probably skip the first part
as it avoids speaking about asyncio too much. We will use a small library as
an example througout this guide, you should review it before diving into
specifics though.


A dummy library we want to test
-------------------------------

Let me introduce you the library we wrote and want to test. It is a quite new
project, our ``piedpiper`` package only contains one module so far, called
``network``::

    .
    ├── piedpiper
    │   ├── __init__.py
    │   ├── network.py
    │   └── ...
    ├── README
    └── setup.py


This module contains one class, called ``ResourceDownloader``, it downloads
a given resource (identified by an URL) from an HTTP(S) server and stores it
in memory. It can optionally refresh the resource content periodically, which
can be useful to poll updates on the resource.

Here is its interface::

    class ResourceDownloader:
        """
        Tool that downloads a resource on an HTTP(S) server.

        :param url: URL of the resource.
        """

        def __init__(self, url):
            ...

        def get_parsed_url(self):
            """
            Return a tuple ``host, port, query, ssl`` where ``host`` and
            ``port`` are the ports on which the connection must be established,
            ``query`` the full query path to the resource, and ``ssl``
            a boolean value set to ``True`` if the scheme is ``https``.

            If :attr:`url` is not an absolute URL (scheme and hostname are
            required) or is invalid according to RFC3986, :exc:ValueError is
            raised.

            >>> ResourceDownloader("http://piedpiper.com/foo").get_parsed_url()
            ("piedpiper.com", 80, "/foo", False)
            """
            ...

        async def download(self):
            """
            Download the resource and updates :attr:`data`.

            The value of :attr:`data` is returned.

            When the resource URL is invalid, :exc:`ValueError` is raised.
            When the response from the server can not be parsed or is not usable,
            :exc:`RuntimeError` is raised.

            Other standard exceptions may be raised (:exc:`OSError`, etc).
            """

        def _build_request(self, host, query):
            """
            Return a simple HTTP/1.1 GET request for the resource as
            a :class:`bytes` string.
            """

        def _parse_response_headers(self, response_headers):
            """
            Return a pair of integer values ``code, payload_size`` where
            ``code`` is the HTTP response code and ``payload_size`` the
            expected size of the body of the response.

            If the payload should be retrieved until the connection is closed
            (because the payload size is unknown), the value of
            ``payload_size`` is set to ``-1``.

            A chunked body is not supported and raise an exception.
            Parsing errors raise a :exc:`RuntimeError`.

            :param response_headers: bytes string containing the headers of the
                HTTP response
            """

        def refresh(self, period, loop=None):
            """
            Refresh the resource data (re-download it) every ``period``
            seconds.

            If period is ``None``, disable the automatic refresh, if a refresh
            is in progress asynchronously, it will finish.

            :attr period: refresh period in seconds, disable auto refresh if
                ``None``
            :attr loop: optional loop on which the callbacks are scheduled, if
                unspecified or ``None``, the default loop is used.
            """


- Introduction
  - Dummy project used in this guide
  - the first part will not talk about asyncio
- Writing unit tests
  - TestCase
    - organize your code
    - Simple case
    - assertions
    - run the case (python -m unnitest)
    - good practices: isolation
- Testing asyncio code
  - TestCase
    - setUp, tearDown
    - not setUpClass
    - addCleanup
  - Mocking
  - Patching
    - patch instances, objects, etc
    - patch scope
  - Control time with Clocked Test Case
    - simple example
    - advanced example: schedule multiple calls
- Advanced topics
  - testing asyncio libraries
  - Use your own loop (TestCase.use_default_loop)
  - low-level: selector and file mocks
  - limitations
    - can not mock functions returning awaitable objects
    - works with the native loop only so far
    - versions support: 3.3 is not supported, 3.4 and @coroutine will
      eventually be dropped (for 1.0 release?)
