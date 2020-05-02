# coding: utf-8

import asyncio
import unittest

import asynctest


class TestExhaust(asynctest.TestCase):
    async def wait_for(self, coro):
        return await asyncio.wait_for(coro, timeout=1)

    async def test_exhaust_callbacks_nothing_to_wait(self):
        # Nothing ready, do nothing (must not timeout)
        await self.wait_for(asynctest.helpers.exhaust_callbacks(self.loop))

    async def test_exhaust_callbacks_one_callback(self):
        fut = asyncio.Future(loop=self.loop)
        self.loop.call_soon(fut.set_result, None)

        # A callback has been scheduled
        await self.wait_for(asynctest.helpers.exhaust_callbacks(self.loop))
        self.assertTrue(fut.done())

    async def test_exhaust_callbacks_cascading_callbacks(self):
        # A callback has been scheduled, then another (while the 1st is
        # running), we must wait for both
        fut = asyncio.Future(loop=self.loop)
        fut2 = asyncio.Future(loop=self.loop)

        fut.add_done_callback(lambda _: fut2.set_result(None))
        self.loop.call_soon(fut.set_result, None)
        await self.wait_for(asynctest.helpers.exhaust_callbacks(self.loop))
        self.assertTrue(fut.done())
        self.assertTrue(fut2.done())


if __name__ == "__main__":
    unittest.main()
