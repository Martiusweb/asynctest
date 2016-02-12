# coding: utf-8


# add a new-style coroutine to the Test class:
def patch_Test_Class(klass):
    class Test(klass):
        async def an_async_coroutine(self):
            pass

    return Test


# wrap the coro in a new-style coroutine
def transform(coro):
    async def a_coroutine(*a, **kw):
        return await coro(*a, **kw)

    return a_coroutine


# make a simple coroutine which invokes a function before awaiting on an
# awaitable and after
def build_simple_coroutine(before_func, after_func=None):
    async def a_coroutine(awaitable, *args, **kwargs):
        before = before_func(*args, **kwargs)
        await awaitable
        after = (after_func or before_func)(*args, **kwargs)
        return before, after

    return a_coroutine
