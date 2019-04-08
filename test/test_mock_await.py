# coding: utf-8


# make a simple coroutine which invokes a function before awaiting on an
# awaitable and after
def build_simple_coroutine(before_func, after_func=None):
    async def a_coroutine(awaitable, *args, **kwargs):
        before = before_func(*args, **kwargs)
        await awaitable
        after = (after_func or before_func)(*args, **kwargs)
        return before, after

    return a_coroutine
