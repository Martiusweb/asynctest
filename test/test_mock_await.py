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
