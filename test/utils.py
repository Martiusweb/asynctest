# coding: utf-8
import asyncio
import contextlib


def run_coroutine(coroutine, loop=None):
    if loop is None:
        loop = asyncio.new_event_loop()
        close = True
    else:
        close = False

    with replace_loop(loop, close):
        return loop.run_until_complete(coroutine)


@contextlib.contextmanager
def replace_loop(loop, close=True):
    try:
        current_loop = asyncio.get_event_loop()
    except:
        current_loop = None

    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        if close:
            loop.close()

        asyncio.set_event_loop(current_loop)
