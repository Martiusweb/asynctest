# coding: utf-8
import asyncio
import unittest.mock

import asynctest


class MustBePatched:
    async def is_patched(self):
        """
        return ``False``, unless patched.
        """
        return False

    async def crash_if_patched(self, ran_event):
        """
        Verify that the method is not patched. The coroutine is put to sleep
        for a duration of 0, meaning it let the loop schedule other coroutines
        concurrently.

        Each time the check is performed, ``ran_event`` is set.
        """

        try:
            while True:
                try:
                    is_patched = await self.is_patched()
                    assert not is_patched

                    await asyncio.sleep(0)
                finally:
                    ran_event.set()
        except asyncio.CancelledError:
            pass


async def terminate_and_check_task(task):
    task.cancel()
    await task


async def happened_once(event):
    await event.wait()
    event.clear()


must_be_patched = MustBePatched()  # noqa


class TestMustBePatched(asynctest.TestCase):
    async def setUp(self):
        # Event used to track if the background task checked if the patch
        # is active
        self.checked = asyncio.Event()

        # This task checks if the object is patched continuously, and sets
        # the checked event everytime it does so.
        self.background_task = asyncio.create_task(
            must_be_patched.crash_if_patched(self.checked))

        # Any test will fail if the background task raises an exception
        self.addCleanup(terminate_and_check_task, self.background_task)

    @asynctest.patch.object(must_be_patched, "is_patched",
                            return_value=True)
    async def test_patching_conflicting(self, _):
        # This call blocks until the check happened once in background
        await happened_once(self.checked)
        self.assertTrue(await must_be_patched.is_patched())
        await happened_once(self.checked)

    @asynctest.patch.object(must_be_patched, "is_patched",
                            return_value=True, scope=asynctest.LIMITED)
    async def test_patching_not_conflicting(self, _):
        await happened_once(self.checked)
        self.assertTrue(await must_be_patched.is_patched())
        await happened_once(self.checked)
