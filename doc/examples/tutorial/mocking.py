# coding: utf-8
# pylama: ignore=C0103, ignore camel case variable name (AsyncClientMock)

import asyncio
import collections
import itertools
import logging

import asynctest


class Client:
    def add_user(self, user):
        raise NotImplementedError

    def get_users(self):
        raise NotImplementedError

    def increase_nb_users_cached(self, nb_cached):
        raise NotImplementedError


class AsyncClient:
    async def add_user(self, user, transaction=None):
        raise NotImplementedError

    async def get_users(self, transaction=None):
        raise NotImplementedError

    async def increase_nb_users_cached(self, nb_cached, transaction=None):
        raise NotImplementedError

    def get_users_cursor(self, transaction=None):
        return self.Cursor(transaction or self)

    def new_transaction(self):
        return self.Transaction(self)

    class Transaction:
        def __init__(self, client):
            self.client = client

        def __call__(self, funcname, *args, **kwargs):
            """
            Forwards the call to the client, with the argument ``transaction ``
            set.
            """
            method = getattr(self.client, funcname)
            return method(*args, transaction=self, **kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class Cursor:
        def __init__(self, transaction):
            self.transaction = transaction

        def __aiter__(self):
            return self

        async def __anext__(self):
            # if the request has not been started, do it there
            raise NotImplementedError


def cache_users(client, cache):
    """
    Load the list of users from a distant server accessed with ``client``,
    add them to ``cache``.

    Notify the server about the number of new users put in the cache, and
    returns this number.

    :param client: a connection to the distant server
    :param cache: a dict-like object
    """
    users = client.get_users()

    nb_users_cached = 0

    for user in users:
        if user.id not in cache:
            nb_users_cached += 1
            cache[user.id] = user

    client.increase_nb_users_cached(nb_users_cached)

    logging.debug("added %d users to the cache %r", nb_users_cached, cache)

    return nb_users_cached


class StubClient:
    User = collections.namedtuple("User", "id username")

    def __init__(self, *users_to_return):
        self.users_to_return = []
        self.users_to_return.extend(users_to_return)

        self.nb_users_cached = 0

    def add_user(self, user):
        self.users_to_return.append(user)

    def get_users(self):
        return self.users_to_return

    def increase_nb_users_cached(self, nb_cached):
        self.nb_users_cached += nb_cached


class TestUsingStub(asynctest.TestCase):
    def test_one_user_added_to_cache(self):
        user = StubClient.User(1, "a.dmin")
        client = StubClient(user)
        cache = {}

        # The user has been added to the cache
        nb_added = cache_users(client, cache)

        self.assertEqual(nb_added, 1)
        self.assertEqual(cache[1], user)

        # The user was already there
        nb_added = cache_users(client, cache)
        self.assertEqual(nb_added, 0)
        self.assertEqual(cache[1], user)

    def test_no_users_to_add(self):
        cache = {}
        nb_added = cache_users(StubClient(), cache)

        self.assertEqual(nb_added, 0)
        self.assertEqual(len(cache), 0)


class TestUsingMock(asynctest.TestCase):
    def test_no_users_to_add(self):
        client = asynctest.Mock(Client())
        client.get_users.return_value = []
        cache = {}

        nb_added = cache_users(client, cache)

        client.get_users.assert_called()
        self.assertEqual(nb_added, 0)
        self.assertEqual(len(cache), 0)

        client.increase_nb_users_cached.assert_called_once_with(0)


async def cache_users_async(client, cache):
    users = await client.get_users()

    nb_users_cached = 0

    for user in users:
        if user.id not in cache:
            nb_users_cached += 1
            cache[user.id] = user

    await client.increase_nb_users_cached(nb_users_cached)

    logging.debug("added %d users to the cache %r", nb_users_cached, cache)

    return nb_users_cached


class TestUsingFuture(asynctest.TestCase):
    async def test_no_users_to_add(self):
        client = asynctest.Mock(Client())

        client.get_users.return_value = asyncio.Future()
        client.get_users.return_value.set_result([])

        client.increase_nb_users_cached.return_value = asyncio.Future()
        client.increase_nb_users_cached.return_value.set_result(None)

        cache = {}

        nb_added = await cache_users_async(client, cache)

        client.get_users.assert_called()
        self.assertEqual(nb_added, 0)
        self.assertEqual(len(cache), 0)

        client.increase_nb_users_cached.assert_called_once_with(0)


class TestUsingCoroutineMock(asynctest.TestCase):
    async def test_no_users_to_add(self):
        client = asynctest.Mock(Client())
        client.get_users = asynctest.CoroutineMock(return_value=[])
        client.increase_nb_users_cached = asynctest.CoroutineMock()
        cache = {}

        nb_added = await cache_users_async(client, cache)

        client.get_users.assert_awaited()
        self.assertEqual(nb_added, 0)
        self.assertEqual(len(cache), 0)

        client.increase_nb_users_cached.assert_awaited_once_with(0)


class TestUsingCoroutineMockAndSpec(asynctest.TestCase):
    async def test_no_users_to_add(self):
        client = asynctest.Mock(AsyncClient())
        client.get_users.return_value = []
        cache = {}

        nb_added = await cache_users_async(client, cache)

        client.get_users.assert_awaited()
        self.assertEqual(nb_added, 0)
        self.assertEqual(len(cache), 0)

        client.increase_nb_users_cached.assert_awaited_once_with(0)


class TestAutoSpec(asynctest.TestCase):
    async def test_functions_and_coroutines_arguments_are_checked(self):
        client = asynctest.Mock(Client())
        cache = {}

        cache_users_mock = asynctest.create_autospec(cache_users_async)

        with self.subTest("create_autospec returns a regular mock"):
            await cache_users_mock(client, cache)
            cache_users_mock.assert_awaited_once_with(client, cache)

        with self.subTest("an exception is raised when the mock is called "
                          "with the wrong number of arguments"):
            with self.assertRaises(TypeError):
                await cache_users_mock("wrong", "number", "of", "args")

    async def test_create_autospec_on_a_class(self):
        AsyncClientMock = asynctest.create_autospec(AsyncClient)
        client = AsyncClientMock()

        with self.subTest("the mock of a class returns a mock instance of "
                          "the class"):
            self.assertIsInstance(client, AsyncClient)

        with self.subTest("attributes of the mock instance are correctly "
                          "mocked as coroutines"):
            await client.increase_nb_users_cached(1)


class TestCoroutineMockResult(asynctest.TestCase):
    async def test_result_set_with_return_value(self):
        coroutine_mock = asynctest.CoroutineMock()
        result = object()
        coroutine_mock.return_value = result

        # return the expected result
        self.assertIs(result, await coroutine_mock())
        # always return the same result
        self.assertIs(await coroutine_mock(), await coroutine_mock())

    async def test_result_with_side_effect_function(self):
        def uppercase_all(*args):
            return tuple(arg.upper() for arg in args)

        coroutine_mock = asynctest.CoroutineMock()
        coroutine_mock.side_effect = uppercase_all

        self.assertEqual(("FIRST", "CALL"),
                         await coroutine_mock("first", "call"))
        self.assertEqual(("A", "SECOND", "CALL"),
                         await coroutine_mock("a", "second", "call"))

    async def test_result_with_side_effect_exception(self):
        coroutine_mock = asynctest.CoroutineMock()
        coroutine_mock.side_effect = NotImplementedError

        # Raise an exception of the configured type
        with self.assertRaises(NotImplementedError):
            await coroutine_mock("any", "number", "of", "args")

        coroutine_mock.side_effect = Exception("an instance of exception")

        # Raise the exact specified object
        with self.assertRaises(Exception) as context:
            await coroutine_mock()

        self.assertIs(coroutine_mock.side_effect, context.exception)

    async def test_result_with_side_effect_iterable(self):
        coroutine_mock = asynctest.CoroutineMock()
        coroutine_mock.side_effect = ["one", "two", "three"]

        self.assertEqual("one", await coroutine_mock())
        self.assertEqual("two", await coroutine_mock())
        self.assertEqual("three", await coroutine_mock())

        coroutine_mock.side_effect = itertools.cycle(["odd", "even"])
        self.assertEqual("odd", await coroutine_mock())
        self.assertEqual("even", await coroutine_mock())
        self.assertEqual("odd", await coroutine_mock())
        self.assertEqual("even", await coroutine_mock())

    async def test_result_with_wrapped_object(self):
        stub = StubClient()
        mock = asynctest.Mock(stub, wraps=stub)
        cache = {}

        stub.add_user(StubClient.User(1, "a.dmin"))
        cache_users(mock, cache)

        mock.get_users.assert_called()
        self.assertEqual(stub.users_to_return, mock.get_users())


async def cache_users_with_cursor(client, cache):
    nb_users_cached = 0

    async with client.new_transaction() as transaction:
        users_cursor = transaction.get_users_cursor()

        async for user in users_cursor:
            if user.id not in cache:
                nb_users_cached += 1
                cache[user.id] = user

        await transaction.increase_nb_users_cached(nb_users_cached)

    logging.debug("added %d users to the cache %r", nb_users_cached, cache)

    return nb_users_cached


class TestWithMagicMethods(asynctest.TestCase):
    async def test_context_manager(self):
        with self.assertRaises(AssertionError):
            async with asynctest.MagicMock() as context:
                # context is a MagicMock
                context.assert_called()

    async def test_empty_iterable(self):
        loop_iterations = 0
        async for _ in asynctest.MagicMock():
            loop_iterations += 1

        self.assertEqual(0, loop_iterations)

    async def test_iterable(self):
        loop_iterations = 0
        mock = asynctest.MagicMock()
        mock.__aiter__.return_value = range(5)
        async for _ in mock:
            loop_iterations += 1

        self.assertEqual(5, loop_iterations)


class TestCacheWithMagicMethods(asynctest.TestCase):
    async def test_one_user_added_to_cache(self):
        user = StubClient.User(1, "a.dmin")

        AsyncClientMock = asynctest.create_autospec(AsyncClient)

        transaction = asynctest.MagicMock()
        transaction.__aenter__.side_effect = AsyncClientMock

        cursor = asynctest.MagicMock()
        cursor.__aiter__.return_value = [user]

        client = AsyncClientMock()
        client.new_transaction.return_value = transaction
        client.get_users_cursor.return_value = cursor

        cache = {}

        # The user has been added to the cache
        nb_added = await cache_users_with_cursor(client, cache)

        self.assertEqual(nb_added, 1)
        self.assertEqual(cache[1], user)

        # The user was already there
        nb_added = await cache_users_with_cursor(client, cache)
        self.assertEqual(nb_added, 0)
        self.assertEqual(cache[1], user)


class TestCachingIsLogged(asynctest.TestCase):
    async def test_with_context_manager(self):
        client = asynctest.Mock(AsyncClient())
        cache = {}

        with asynctest.patch("logging.debug") as debug_mock:
            await cache_users_async(client, cache)

        debug_mock.assert_called()

    @asynctest.patch("logging.error")
    @asynctest.patch("logging.debug")
    async def test_with_decorator(self, debug_mock, error_mock):
        client = asynctest.Mock(AsyncClient())
        cache = {}

        await cache_users_async(client, cache)

        debug_mock.assert_called()
        error_mock.assert_not_called()
