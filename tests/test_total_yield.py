"""Tests for StecaGrid lifetime energy protocol support."""

import asyncio
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import AsyncMock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "stecagrid"
    / "steca.py"
)
SPEC = importlib.util.spec_from_file_location("steca_protocol_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def total_response(value_wh):
    """Build the observed 0x65/0xF1 reply shape for the total-yield field."""
    payload = bytearray(bytes.fromhex("02 01 00 14 7b 01 43 65 00 00 05 f1"))
    payload.extend(struct.pack("<f", value_wh))
    payload.extend(bytes.fromhex("18 dc 46 03"))
    return bytes(payload)


class TestTotalYield(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connector = MODULE.StecaConnector("127.0.0.1", 4196)

    async def test_request_uses_upload_by_id_service(self):
        self.connector.PollInverter = AsyncMock(return_value=total_response(43081768.0))
        self.assertAlmostEqual(await self.connector.GetTotalYield(), 43081.768, places=3)
        request = self.connector.PollInverter.await_args.args[0]
        self.assertEqual(request[7:13], bytes.fromhex("64 03 00 01 f1 46"))

    async def test_unavailable_instead_of_false_zero(self):
        self.connector.PollInverter = AsyncMock(return_value=0.0)
        self.assertIsNone(await self.connector.GetTotalYield())

    async def test_wrong_topic_rejected(self):
        wrong = bytearray(total_response(43081768.0))
        wrong[11] = 0x3C
        self.connector.PollInverter = AsyncMock(return_value=bytes(wrong))
        self.assertIsNone(await self.connector.GetTotalYield())

    async def test_invalid_nonfinite_rejected(self):
        self.connector.PollInverter = AsyncMock(return_value=total_response(float("nan")))
        self.assertIsNone(await self.connector.GetTotalYield())


if __name__ == "__main__":
    unittest.main()
