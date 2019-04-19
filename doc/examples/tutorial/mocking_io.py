# coding: utf-8
import asyncio
import socket

import asynctest


class TestMockASocket(asynctest.TestCase):
    async def test_read_and_write_from_socket(self):
        socket_mock = asynctest.SocketMock()
        socket_mock.type = socket.SOCK_STREAM

        recv_data = iter((
            b"some data read",
            b"some other",
            b" ...and the last",
        ))

        recv_buffer = bytearray()

        def recv_side_effect(max_bytes):
            nonlocal recv_buffer

            if not recv_buffer:
                try:
                    recv_buffer.extend(next(recv_data))
                    asynctest.set_read_ready(socket_mock, self.loop)
                except StopIteration:
                    # nothing left
                    pass

            data = recv_buffer[:max_bytes]
            recv_buffer = recv_buffer[max_bytes:]

            if recv_buffer:
                # Some more data to read
                asynctest.set_read_ready(socket_mock, self.loop)

            return data

        def send_side_effect(data):
            asynctest.set_read_ready(socket_mock, self.loop)
            return len(data)

        socket_mock.recv.side_effect = recv_side_effect
        socket_mock.send.side_effect = send_side_effect

        reader, writer = await asyncio.open_connection(sock=socket_mock)

        writer.write(b"a request?")
        self.assertEqual(b"some", await reader.read(4))
        self.assertEqual(b" data read", await reader.read(10))
        self.assertEqual(b"some other ...and the last", await reader.read())
