# coding: utf-8
import asyncio
import collections

import asynctest


class Client:
    def add_user(self, user):
        raise NotImplementedError

    def get_users(self):
        raise NotImplementedError

    def increase_nb_users_cached(self, nb_cached):
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
