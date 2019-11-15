# coding: utf-8
"""
Module ``helpers``
------------------

Helper functions and coroutines for :mod:`asynctest`.
"""

import asyncio


async def exhaust_callbacks(loop):
    """
    Run the loop until all ready callbacks are executed.

    The coroutine doesn't wait for callbacks scheduled in the future with
    :meth:`~asyncio.BaseEventLoop.call_at()` or
    :meth:`~asyncio.BaseEventLoop.call_later()`.

    :param loop: event loop
    """
    while loop._ready:
        await asyncio.sleep(0, loop=loop)
