# coding: utf-8

import asynctest


# test_coroutinefunction_executed
class CoroutineFunctionTest(asynctest.TestCase):
    ran = False

    async def noop(self):
        pass

    async def runTest(self):
        self.ran = True
        await self.noop()


# test_coroutine_returned_executed
class CoroutineTest(CoroutineFunctionTest):
    ran = False

    def runTest(self):
        return super().runTest()
