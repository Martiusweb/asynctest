# coding: utf-8
"""
Mock of selectors and compatible objects performing asynchronous IO.

This module provides classes to mock objects performing IO (files, sockets,
etc). These mocks are compatible with TestSelector, which can simulate the
behavior of a selector on the mock objects, or forward actual work to a real
selector.
"""

import selectors
import socket

from . import mock


class FileDescriptor(int):
    next_fd = 0

    def __new__(cls, *args, **kwargs):
        if not args and not kwargs:
            s = super().__new__(cls, FileDescriptor.next_fd)
        else:
            s = super().__new__(cls, *args, **kwargs)

        FileDescriptor.next_fd = max(FileDescriptor.next_fd + 1, s + 1)

        return s

    def __hash__(self):
        # Return a different hash than the int so we can register both a
        # FileDescriptor object and an int of the same value
        return hash('__FileDescriptor_{}'.format(self))


def fd(fileobj):
    """
    Return the FileDescriptor value of fileobj.

    If fileobj is a FileDescriptor, fileobj is returned, else fileobj.fileno()
    is returned instead.
    """
    try:
        return fileobj if isinstance(fileobj, FileDescriptor) else fileobj.fileno()
    except Exception:
        raise ValueError from None


def isfilemock(obj):
    """
    Return True if the obj or obj.fileno() is a FileDescriptor.
    """
    try:
        return (isinstance(obj, FileDescriptor) or
                isinstance(obj.fileno(), FileDescriptor))
    except AttributeError:
        # obj has no attribute fileno()
        return False


class FileMock(mock.Mock):
    """
    Mock a file-like object.

    A FileMock is an intelligent mock which can work with TestSelector to
    simulate IO events during tests.
    """
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fileno.return_value = FileDescriptor()

    def _get_child_mock(self, *args, **kwargs):
        # A FileMock returns a Mock by default, not a FileMock
        return mock.Mock(**kwargs)


class SocketMock(FileMock):
    """
    Mock a socket.
    """
    def __init__(self, side_effect=None, return_value=mock.DEFAULT,
                 wraps=None, name=None, spec_set=None, parent=None,
                 **kwargs):
        super().__init__(socket.socket, side_effect=side_effect,
                         return_value=return_value, wraps=wraps, name=name,
                         spec_set=spec_set, parent=parent, **kwargs)


class TestSelector(selectors._BaseSelectorImpl):
    """
    A selector which supports IOMock objects.

    It can wrap an actual implementation of a selector, so the selector will
    work both with mocks and real file-like objects.
    """
    def __init__(self, selector=None):
        """
        Args:
            selector: optional, if provided, this selector will be used to work
            with real file-like objects.
        """
        super().__init__()
        self._selector = selector

    def _fileobj_lookup(self, fileobj):
        if isfilemock(fileobj):
            return fd(fileobj)

        return super()._fileobj_lookup(fileobj)

    def register(self, fileobj, events, data=None):
        """
        Register a file object or a FileMock.

        If a real selector object has been supplied to the TestSelector object
        and fileobj is not a FileMock or a FileDescriptor returned by
        FileMock.fileno(), the object will be registered to the real selector.

        See the documentation of selectors.BaseSelector.
        """
        if isfilemock(fileobj) or self._selector is None:
            key = super().register(fileobj, events, data)
        else:
            key = self._selector.register(fileobj, events, data)

            if key:
                self._fd_to_key[key.fd] = key

        return key

    def unregister(self, fileobj):
        """
        Unregister a file object or a FileMock.

        See the documentation of selectors.BaseSelector.
        """
        if isfilemock(fileobj) or self._selector is None:
            key = super().unregister(fileobj)
        else:
            key = self._selector.unregister(fileobj)

            if key and key.fd in self._fd_to_key:
                del self._fd_to_key[key.fd]

        return key

    def modify(self, fileobj, events, data=None):
        if isfilemock(fileobj) or self._selector is None:
            key = super().modify(fileobj, events, data)
        else:
            # del the key first because modify() fails if events is incorrect
            if fd(fileobj) in self._fd_to_key:
                del self._fd_to_key[fd(fileobj)]

            key = self._selector.modify(fileobj, events, data)

            if key:
                self._fd_to_key[key.fd] = key

        return key

    def select(self, timeout=None):
        """
        Perfom the selection.

        This method is a no-op if no actual selector has been supplied.
        """
        if self._selector is None:
            return []

        return self._selector.select(timeout)

    def close(self):
        """
        Close the selector.

        Close the actual selector if supplied, unregister all mocks.
        """
        if self._selector is not None:
            self._selector.close()

        super().close()
