"""Policy for missing StecaGrid readings when the inverter sleeps at night."""

POWER_WHEN_ASLEEP = ("ac_power", "panel_power", "panel_current")


def normalize_offline_readings(readings: dict, sun_state: str | None) -> dict:
    """Only infer zero power after sunset; never manufacture energy readings.

    During daylight an inverter communication outage is *not* proof of
    zero generation. A valid measurement always wins over the fallback.
    """
    values = dict(readings)
    if sun_state == "below_horizon":
        for key in POWER_WHEN_ASLEEP:
            if values.get(key) is None:
                values[key] = 0.0
    return values
