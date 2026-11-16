"""Preserve the last valid lifetime energy reading when the inverter sleeps."""

import math


def retain_total_energy(previous, measured):
    """Keep a measured cumulative value across missing/invalid polls."""
    if isinstance(measured, (int, float)) and not isinstance(measured, bool):
        if math.isfinite(measured) and measured >= 0:
            return measured
    return previous
