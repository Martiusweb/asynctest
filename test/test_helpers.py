# coding: utf-8

import asyncio
import unittest

import asynctest


class TestExhaust(asynctest.TestCase):
    @asyncio.coroutine
    def wait_for(self, coro):
        return (yield from asyncio.wait_for(coro, loop=self.loop, timeout=1))

    def test_exhaust_callbacks_nothing_to_wait(self):
        # Nothing ready, do nothing (must not timeout)
        yield from self.wait_for(asynctest.helpers.exhaust_callbacks(self.loop))

    def test_exhaust_callbacks_one_callback(self):
        fut = asyncio.Future(loop=self.loop)
        self.loop.call_soon(fut.set_result, None)

        # A callback has been scheduled
        yield from self.wait_for(asynctest.helpers.exhaust_callbacks(self.loop))
        self.assertTrue(fut.done())

    def test_exhaust_callbacks_cascading_callbacks(self):
        # A callback has been scheduled, then another (while the 1st is
        # running), we must wait for both
        fut = asyncio.Future(loop=self.loop)
        fut2 = asyncio.Future(loop=self.loop)

        fut.add_done_callback(lambda _: fut2.set_result(None))
        self.loop.call_soon(fut.set_result, None)
        yield from self.wait_for(asynctest.helpers.exhaust_callbacks(self.loop))
        self.assertTrue(fut.done())
        self.assertTrue(fut2.done())


if __name__ == "__main__":
    unittest.main()
