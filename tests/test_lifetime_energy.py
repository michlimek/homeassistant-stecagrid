"""Counter retention tests, independent from Home Assistant installation."""

import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components" / "stecagrid" / "lifetime_energy.py"
spec = importlib.util.spec_from_file_location("steca_lifetime_energy", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestLifetimeEnergy(unittest.TestCase):
    def test_fresh_measurement_wins(self):
        self.assertEqual(module.retain_total_energy(78797.1, 78797.2), 78797.2)

    def test_last_valid_value_survives_offline_read(self):
        self.assertEqual(module.retain_total_energy(78797.1, None), 78797.1)

    def test_no_value_is_not_fabricated(self):
        self.assertIsNone(module.retain_total_energy(None, None))

    def test_invalid_readings_never_reset_counter(self):
        for bad in (float("nan"), float("inf"), -1, True, "unavailable"):
            with self.subTest(value=bad):
                self.assertEqual(module.retain_total_energy(78797.1, bad), 78797.1)

    def test_valid_zero_is_not_automatically_rejected(self):
        self.assertEqual(module.retain_total_energy(0.0, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
