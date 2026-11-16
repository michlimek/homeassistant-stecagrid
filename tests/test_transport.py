"""Regression tests for Steca serial-over-TCP framing."""

import asyncio
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "stecagrid" / "steca.py"
spec = importlib.util.spec_from_file_location("steca_transport_test", MODULE_PATH)
steca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(steca)


class TestTransport(unittest.IsolatedAsyncioTestCase):
    async def test_split_tcp_frame_is_reassembled(self):
        """Incomplete TCP chunks must not be interpreted as failed frames."""
        reply = bytes.fromhex("02 01 00 14 7b 01 43 65 00 00 05 f1 0a 58 24 4c 18 dc 46 03")
        reader = asyncio.StreamReader()
        writer = MagicMock()
        writer.drain = AsyncMock()
        writer.wait_closed = AsyncMock()
        reader.feed_data(reply[:3])
        reader.feed_data(reply[3:8])
        reader.feed_data(reply[8:])
        reader.feed_eof()
        connector = steca.StecaConnector("127.0.0.1", 4196)
        with patch.object(steca.asyncio, "open_connection", AsyncMock(return_value=(reader, writer))):
            result = await connector.PollInverter(b"request")
        self.assertEqual(result, reply)
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()

    async def test_early_disconnect_raises_incomplete_read(self):
        reader = asyncio.StreamReader()
        reader.feed_data(bytes.fromhex("02 01 00 14 7b"))
        reader.feed_eof()
        writer = MagicMock()
        writer.drain = AsyncMock()
        writer.wait_closed = AsyncMock()
        connector = steca.StecaConnector("127.0.0.1", 4196)
        with patch.object(steca.asyncio, "open_connection", AsyncMock(return_value=(reader, writer))):
            with self.assertRaises(asyncio.IncompleteReadError):
                await connector.PollInverter(b"request")
        writer.close.assert_called_once()

    async def test_connection_error_is_not_converted_to_zero(self):
        connector = steca.StecaConnector("127.0.0.1", 4196)
        with patch.object(steca.asyncio, "open_connection", AsyncMock(side_effect=ConnectionRefusedError("offline"))):
            with self.assertRaises(ConnectionRefusedError):
                await connector.PollInverter(b"request")


if __name__ == "__main__":
    unittest.main()
