# coding: utf-8
"""
Helper functions and coroutines for aiotest.
"""

import asyncio


@asyncio.coroutine
def exhaust_callbacks(loop):
    """
    Run the loop until all ready callbacks are executed.

    The coroutine doesn't wait for callbacks scheduled in the future with
    call_at() or call_later().

    Args:
        loop: event loop
    """
    while loop._ready:
        yield from asyncio.sleep(0)
