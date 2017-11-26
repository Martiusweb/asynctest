# coding: utf-8

import asyncio
import copy
import selectors
import functools
import os
import socket
try:
    import ssl
except ImportError:
    ssl = None
import sys
import unittest

import asynctest


class Selector_TestCase(unittest.TestCase):
    def setUp(self):
        asynctest.selector.FileDescriptor.next_fd = 0


class Test_FileDescriptor(Selector_TestCase):
    def test_is_an_int(self):
        self.assertIsInstance(asynctest.selector.FileDescriptor(), int)

    def test_init_increments_value(self):
        self.assertEqual(0, asynctest.selector.FileDescriptor())
        self.assertEqual(1, asynctest.selector.FileDescriptor())

        self.assertNotEqual(asynctest.selector.FileDescriptor(),
                            asynctest.selector.FileDescriptor())

    def test_init_increments_value_with_fixed_value(self):
        self.assertEqual(5, asynctest.selector.FileDescriptor(5))
        self.assertEqual(6, asynctest.selector.FileDescriptor())


class Test_FileMock(Selector_TestCase):
    def test_fileno_returns_FileDescriptor(self):
        self.assertIsInstance(asynctest.selector.FileMock().fileno(),
                              asynctest.selector.FileDescriptor)


class Test_SocketMock(Selector_TestCase):
    def test_is_socket(self):
        self.assertIsInstance(asynctest.selector.SocketMock(), socket.socket)


if ssl:
    class Test_SSLSocketMock(Selector_TestCase):
        def test_is_ssl_socket(self):
            self.assertIsInstance(asynctest.selector.SSLSocketMock(),
                                  ssl.SSLSocket)


def selector_subtest(method):
    @functools.wraps(method)
    def wrapper(self):
        with self.subTest(test='without_selector'):
            method(self, asynctest.selector.TestSelector(), None)

        with self.subTest(test='with_selector'):
            mock = unittest.mock.Mock(selectors.BaseSelector)
            method(self, asynctest.selector.TestSelector(mock), mock)

    return wrapper


class Test_TestSelector(Selector_TestCase):
    @selector_subtest
    def test_register_mock(self, selector, selector_mock):
        mock = asynctest.selector.FileMock()
        key = selector.register(mock, selectors.EVENT_READ, "data")

        self.assertEqual(key, selector.get_map()[mock])

        if selector_mock:
            self.assertFalse(selector_mock.register.called)

    @selector_subtest
    def test_register_fileno(self, selector, selector_mock):
        with open(os.devnull, 'r') as devnull:
            if selector_mock:
                selector_mock.register.return_value = selectors.SelectorKey(
                    devnull, devnull.fileno(), selectors.EVENT_READ, "data"
                )

            key = selector.register(devnull, selectors.EVENT_READ, "data")

            self.assertEqual(key, selector.get_map()[devnull])

            if selector_mock:
                selector_mock.register.assert_called_with(devnull,
                                                          selectors.EVENT_READ,
                                                          "data")

    @selector_subtest
    def test_unregister_mock(self, selector, selector_mock):
        mock = asynctest.selector.FileMock()
        selector.register(mock, selectors.EVENT_READ, "data")

        selector.unregister(mock)

        self.assertNotIn(mock, selector.get_map())
        self.assertNotIn(mock.fileno(), selector.get_map())

        if selector_mock:
            self.assertFalse(selector_mock.unregister.called)

    @selector_subtest
    def test_unregister_fileno(self, selector, selector_mock):
        with open(os.devnull, 'r') as devnull:
            if selector_mock:
                key = selectors.SelectorKey(devnull, devnull.fileno(),
                                            selectors.EVENT_READ, "data")
                selector_mock.register.return_value = key
                selector_mock.unregister.return_value = key

            selector.register(devnull, selectors.EVENT_READ, "data")

            selector.unregister(devnull)

            self.assertNotIn(devnull, selector.get_map())
            self.assertNotIn(devnull.fileno(), selector.get_map())

    @selector_subtest
    def test_modify_mock(self, selector, selector_mock):
        mock = asynctest.selector.FileMock()

        original_key = selector.register(mock, selectors.EVENT_READ, "data")
        # modify may update the original key, keep a copy
        original_key = copy.copy(original_key)

        RW = selectors.EVENT_READ | selectors.EVENT_WRITE

        key = selector.modify(mock, RW, "data")

        self.assertNotEqual(original_key, key)
        self.assertEqual(key, selector.get_map()[mock])

    @selector_subtest
    def test_modify_fileno(self, selector, selector_mock):
        with open(os.devnull, 'r') as devnull:
            if selector_mock:
                selector_mock.modify.return_value = selectors.SelectorKey(
                    devnull, devnull.fileno(), selectors.EVENT_READ, "data2"
                )

            original_key = selector.register(devnull, selectors.EVENT_READ, "data")
            # modify may update the original key, keep a copy
            original_key = copy.copy(original_key)

            key = selector.modify(devnull, selectors.EVENT_READ, "data2")

            self.assertNotEqual(original_key, key)
            self.assertEqual(key, selector.get_map()[devnull])

            if selector_mock:
                selector_mock.modify.assert_called_with(devnull, selectors.EVENT_READ, "data2")

    @selector_subtest
    def test_modify_fd(self, selector, selector_mock):
        fd = 1

        if selector_mock:
            selector_mock.modify.return_value = selectors.SelectorKey(
                fd, fd, selectors.EVENT_READ, "data2"
            )

        original_key = selector.register(fd, selectors.EVENT_READ, "data")
        original_key = copy.copy(original_key)

        key = selector.modify(fd, selectors.EVENT_READ, "data2")

        self.assertNotEqual(original_key, key)
        self.assertEqual(key, selector.get_map()[fd])

        if selector_mock:
            selector_mock.modify.assert_called_with(fd, selectors.EVENT_READ, "data2")

    @selector_subtest
    def test_modify_but_selector_raises(self, selector, selector_mock):
        if not selector_mock:
            return

        exception = RuntimeError()
        selector_mock.modify.side_effect = exception

        with open(os.devnull, 'r') as devnull:
            selector.register(devnull, selectors.EVENT_READ, "data")

            with self.assertRaises(type(exception)) as ctx:
                selector.modify(devnull, selectors.EVENT_READ, "data2")

            self.assertIs(exception, ctx.exception)
            self.assertNotIn(devnull, selector.get_map())

    @selector_subtest
    def test_select(self, selector, selector_mock):
        if selector_mock:
            selector_mock.select.return_value = ["ProbeValue"]
            self.assertEqual(["ProbeValue"], selector.select(5))
            selector_mock.select.assert_called_with(5)
        else:
            self.assertEqual([], selector.select())

    @selector_subtest
    def test_close(self, selector, selector_mock):
        if not selector_mock:
            return

        selector.close()
        selector_mock.close.assert_called_with()


class Test_set_read_write_ready(Selector_TestCase):
    def setUp(self):
        super().setUp()

        self.loop = asyncio.new_event_loop()
        self.loop._selector = asynctest.selector.TestSelector(self.loop._selector)
        self.addCleanup(self.loop.close)
        self.mock = asynctest.selector.FileMock()

        # Older versions of asyncio may complain with PYTHONASYNCIODEBUG=1
        if sys.version_info < (3, 5):
            asyncio.set_event_loop(self.loop)

    def test_nothing_scheduled(self):
        # nothing will happen (no exception)
        for mode in ('read', 'write'):
            with self.subTest(mode=mode):
                getattr(asynctest.selector, 'set_{}_ready'.format(mode))(self.mock, self.loop)
                self.loop.run_until_complete(asyncio.sleep(0, loop=self.loop))

    def test_callback_scheduled(self):
        for mode in ('read', 'write'):
            with self.subTest(mode=mode):
                future = asyncio.Future(loop=self.loop)
                callback_mock = unittest.mock.Mock()

                # We need at least two iterations of the loop
                self.loop.call_soon(self.loop.call_soon, future.set_result, None)

                getattr(self.loop, 'add_{}er'.format(mode.strip('e')))(self.mock, callback_mock)
                getattr(asynctest.selector, 'set_{}_ready'.format(mode))(self.mock, self.loop)

                self.loop.run_until_complete(future)
                callback_mock.assert_called_with()

    def test_callback_scheduled_during_current_iteration(self):
        for mode in ('read', 'write'):
            with self.subTest(mode=mode):
                future = asyncio.Future(loop=self.loop)
                callback_mock = unittest.mock.Mock()

                # We need at least two iterations of the loop
                self.loop.call_soon(self.loop.call_soon, future.set_result, None)

                self.loop.call_soon(getattr(self.loop, 'add_{}er'.format(mode.strip('e'))),
                                    self.mock, callback_mock)
                getattr(asynctest.selector, 'set_{}_ready'.format(mode))(self.mock, self.loop)

                self.loop.run_until_complete(future)
                callback_mock.assert_called_with()


@unittest.mock.patch.dict('asynctest._fail_on.DEFAULTS', clear=True,
                          active_selector_callbacks=True)
class Test_fail_on_active_selector_callbacks(Selector_TestCase):
    def test_passes_without_callbacks_set(self):
        class TestCase(asynctest.TestCase):
            def runTest(self):
                pass

        TestCase().debug()

    def test_passes_when_no_callbacks_left(self):
        class TestCase(asynctest.TestCase):
            def runTest(self):
                mock = asynctest.selector.FileMock()
                self.loop.add_reader(mock, lambda: None)
                self.loop.remove_reader(mock)

        TestCase().debug()

    def test_events_watched_outside_test_are_ignored(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            mock = asynctest.selector.FileMock()
            loop.add_reader(mock, lambda: None)
            self.addCleanup(loop.remove_reader, mock)

            class TestCase(asynctest.TestCase):
                use_default_loop = False

                def runTest(self):
                    pass

            TestCase().debug()
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def test_fail_on_active_selector_callbacks_on_mock_files(self):
        class TestCase(asynctest.TestCase):
            def runTest(self):
                mock = asynctest.selector.FileMock()
                self.loop.add_reader(mock, lambda: None)
                # it's too late to check that during cleanup
                self.addCleanup(self.loop.remove_reader, mock)

        with self.assertRaisesRegex(AssertionError, "some events watched "
                                    "during the tests were not removed"):
            TestCase().debug()

    def test_fail_on_original_selector_callback(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with unittest.mock.patch.object(loop, "_selector") as mock:
                class TestCase(asynctest.TestCase):
                    use_default_loop = True

                    def runTest(self):
                        # add a dummy event
                        handle = asyncio.Handle(lambda: None, (), self.loop)
                        key = selectors.SelectorKey(1, 1, selectors.EVENT_READ,
                                                    (handle, None))
                        mock.get_map.return_value = {1: key}

                with self.assertRaisesRegex(AssertionError,
                                            "some events watched during the "
                                            "tests were not removed"):
                    TestCase().debug()
        finally:
            loop.close()
            asyncio.set_event_loop(None)
