# coding: utf-8
"""
Helpers
-------

Helper functions and coroutines for :mod:`asynctest`.
"""

import asyncio
import os
from functools import partial, wraps
from .case import TestCase


@asyncio.coroutine
def exhaust_callbacks(loop):
    """
    Run the loop until all ready callbacks are executed.

    The coroutine doesn't wait for callbacks scheduled in the future with
    :meth:`~asyncio.BaseEventLoop.call_at()` or
    :meth:`~asyncio.BaseEventLoop.call_later()`.

    :param loop: event loop
    """
    while loop._ready:
        yield from asyncio.sleep(0, loop=loop)


try:
    DEFAULT_TIMEOUT = int(os.getenv('ASYNC_TIMEOUT', '10'))
except:
    DEFAULT_TIMEOUT = 10


def async_timeout(func=None, seconds=DEFAULT_TIMEOUT):
    """ Add timeout to a coroutine function and return it.

    .. code-block: python

        class TimedOutTestCase(TestCase):
            @async_timeout
            async def test_default_timeout(self):
                await asyncio.sleep(999, loop=self.loop)

            @async_timeout(seconds=1)
            async def test_custom_timeout(self):
                await asyncio.sleep(999, loop=self.loop)

    :param func: Coroutine function
    :param seconds: optional time limit in seconds. Default is 10.
    :type seconds: int
    :raises: TimeoutError if time limit is reached

    .. note:: Default timeout might be set as ``ASYNC_TIMEOUT`` environment variable.

    """
    if func is None:
        return partial(async_timeout, seconds=seconds)

    # convert function to coroutine anyway
    coro_func = asyncio.coroutine(func)

    @wraps(func)
    @asyncio.coroutine
    def wrap(self: TestCase, *args, **kwargs):
        task = self.loop.create_task(
            coro_func(self, *args, **kwargs)
        )  # type: asyncio.Task

        cancelled = False

        def on_timeout(task: asyncio.Task, loop: asyncio.AbstractEventLoop):
            nonlocal cancelled

            if task.done():
                return

            task.cancel()
            cancelled = True

            @asyncio.coroutine
            def waiter():
                yield from task

            loop.create_task(waiter())

        self.loop.call_later(seconds, on_timeout, task, self.loop)

        try:
            return (yield from task)
        except asyncio.CancelledError as e:
            if cancelled:
                raise TimeoutError from e
            raise

    return wrap
