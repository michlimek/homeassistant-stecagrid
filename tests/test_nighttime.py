"""Regression tests for the offline/night-time inverter policy."""

import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components" / "stecagrid" / "availability.py"
spec = importlib.util.spec_from_file_location("steca_availability", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestNighttimeReadings(unittest.TestCase):
    def test_offline_night_zeros_power_not_counters(self):
        values = {key: None for key in (
            "ac_power", "panel_power", "panel_current", "panel_voltage",
            "daily_yield", "total_yield", "time"
        )}
        actual = mod.normalize_offline_readings(values, "below_horizon")
        for name in ("ac_power", "panel_power", "panel_current"):
            self.assertEqual(actual[name], 0.0)
        for name in ("panel_voltage", "daily_yield", "total_yield", "time"):
            self.assertIsNone(actual[name])

    def test_daytime_network_outage_is_unavailable(self):
        readings = {"ac_power": None, "panel_power": None, "total_yield": None}
        self.assertEqual(mod.normalize_offline_readings(readings, "above_horizon"), readings)

    def test_missing_sun_integration_is_unavailable(self):
        readings = {"ac_power": None}
        self.assertEqual(mod.normalize_offline_readings(readings, None), readings)

    def test_valid_nighttime_measurements_are_not_overridden(self):
        readings = {"ac_power": 3.0, "panel_power": 59.0, "panel_current": 0.2}
        self.assertEqual(mod.normalize_offline_readings(readings, "below_horizon"), readings)

    def test_does_not_mutate_input(self):
        original = {"ac_power": None}
        mod.normalize_offline_readings(original, "below_horizon")
        self.assertIsNone(original["ac_power"])


if __name__ == "__main__":
    unittest.main()
