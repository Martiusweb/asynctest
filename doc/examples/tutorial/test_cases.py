# coding: utf-8
import asyncio
import asynctest


class MinimalExample(asynctest.TestCase):
    def test_that_true_is_true(self):
        self.assertTrue(True)


class AnExampleWithSetup(asynctest.TestCase):
    async def a_coroutine(self):
        return "I worked"

    def test_that_a_coroutine_runs(self):
        my_loop = asyncio.new_event_loop()
        try:
            result = my_loop.run_until_complete(self.a_coroutine())
            self.assertIn("worked", result)
        finally:
            my_loop.close()


class AnExampleWithSetupMethod(asynctest.TestCase):
    async def a_coroutine(self):
        return "I worked"

    def setUp(self):
        self.my_loop = asyncio.new_event_loop()

    def test_that_a_coroutine_runs(self):
        result = self.my_loop.run_until_complete(self.a_coroutine())
        self.assertIn("worked", result)

    def tearDown(self):
        self.my_loop.close()


class AnExampleWithSetupAndCleanup(asynctest.TestCase):
    async def a_coroutine(self):
        return "I worked"

    def setUp(self):
        self.my_loop = asyncio.new_event_loop()
        self.addCleanup(self.my_loop.close)

    def test_that_a_coroutine_runs(self):
        result = self.my_loop.run_until_complete(self.a_coroutine())
        self.assertIn("worked", result)


class AnExampleWithTestCaseLoop(asynctest.TestCase):
    async def a_coroutine(self):
        return "I worked"

    def test_that_a_coroutine_runs(self):
        result = self.loop.run_until_complete(self.a_coroutine())
        self.assertIn("worked", result)


class AnExampleWithTestCaseAndCoroutines(asynctest.TestCase):
    async def a_coroutine(self):
        return "I worked"

    async def test_that_a_coroutine_runs(self):
        self.assertIn("worked", await self.a_coroutine())


class AnExampleWithAsynchronousSetUp(asynctest.TestCase):
    async def setUp(self):
        self.queue = asyncio.Queue(maxsize=1)
        await self.queue.put("I worked")

    async def test_that_a_lock_is_acquired(self):
        self.assertTrue(self.queue.full())

    async def tearDown(self):
        while not self.queue.empty():
            await self.queue.get()


class AnExempleWhichDetectsPendingCallbacks(asynctest.TestCase):
    def i_must_run(self):
        pass  # do something

    @asynctest.fail_on(active_handles=True)
    async def test_missing_a_callback(self):
        self.loop.call_later(1, self.i_must_run)
