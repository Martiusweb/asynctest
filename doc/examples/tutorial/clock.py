# coding: utf-8
import time

import asynctest


def is_time_around(expected_time, loop=None, delta=.01):
    """
    Checks that the time is equal to ``expected_time`` (within the range of +/-
    ``delta``).

    If ``loop`` is provided, the clock of the loop is used.
    """
    now = loop.time() if loop else time.time()
    return (expected_time - delta) <= now <= (expected_time + delta)


class TestAdvanceTime(asynctest.ClockedTestCase):
    async def test_advance_time(self):
        base_loop_time = self.loop.time()
        base_wall_time = time.time()

        await self.advance(10)

        self.assertEqual(base_loop_time + 10, self.loop.time())
        self.assertTrue(is_time_around(base_wall_time))


class TestWithClockAndCallbacks(asynctest.ClockedTestCase):
    results = None

    def runs_at(self, expected_time):
        self.results.append(is_time_around(expected_time, self.loop))

    @asynctest.fail_on(active_handles=True)
    async def test_callbacks_executed_when_expected(self):
        self.results = []

        base_time = self.loop.time()
        self.loop.call_later(1, self.runs_at, base_time + 1)
        self.loop.call_at(base_time + 7, self.runs_at, base_time + 7)

        # This shows that the callback didn't run yet
        self.assertEqual(0, len(self.results))

        await self.advance(10)

        # This shows that the callbacks ran...
        self.assertEqual(2, len(self.results))
        # ...when expected
        self.assertTrue(all(self.results))
