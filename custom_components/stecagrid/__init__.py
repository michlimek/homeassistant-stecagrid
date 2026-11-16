"""The StecaGrid integration."""

import asyncio
from datetime import timedelta
import logging
import time

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .steca import StecaConnector

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the StecaGrid component."""

    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up StecaGrid from a config entry."""
    inverter_host = entry.data["inverter_host"]
    inverter_port = entry.data["inverter_port"]
    inverter_scaninterval = entry.data["scan_interval"]
    inverter_alias = entry.data["alias"]

    stecaApi = StecaConnector(inverter_host, inverter_port)

    # Fetch initial data so we have data when entities subscribe
    coordinator = StecaGridCoordinator(
        hass, stecaApi, inverter_alias, inverter_scaninterval
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = HassStecaGrid(
        coordinator, inverter_host, inverter_port
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HassStecaGrid:
    def __init__(
        self, coordinator: DataUpdateCoordinator, inverter_host: str, inverter_port: int
    ):
        self._inverter_host = inverter_host
        self._inverter_port = inverter_port
        _LOGGER.debug("Stecagrid __init__" + self._inverter_host)

        # create an instance of StecaConnector
        self._coordinator = coordinator

    def get_name(self):
        return f"steca_grid_{self._inverter_host}_{str(self._inverter_port)}"

    def get_unique_id(self):
        return f"steca_grid_power_{self._inverter_host}_{str(self._inverter_port)}"


class StecaGridCoordinator(DataUpdateCoordinator):
    """StecaGrid coordinator."""

    def __init__(self, hass, stecaAPI: StecaConnector, alias: str, pollinterval: int):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=f"StecaGrid coordinator for '{alias}'",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=pollinterval),
        )
        self.stecaApi = stecaAPI
        self._alias = alias
        self._previous_failures = {}

    async def _async_update_data(self):
        """Poll independently, preserving other sensors when one query fails."""
        reads = (
            ("ac_power", self.stecaApi.GetACOutput),
            ("panel_power", self.stecaApi.GetPanelOutput),
            ("panel_voltage", self.stecaApi.GetPanelVoltage),
            ("panel_current", self.stecaApi.GetPanelCurrent),
            ("daily_yield", self.stecaApi.GetDailyYield),
            ("total_yield", self.stecaApi.GetTotalYield),
            ("time", self.stecaApi.GetInverterTime),
        )
        readings = {}
        failures = {}
        for name, read in reads:
            started = time.monotonic()
            try:
                # Each serial request has its own deadline; an optional
                # energy counter must not time out the entire update.
                readings[name] = await asyncio.wait_for(read(), timeout=2.5)
                if readings[name] is None:
                    failures[name] = "empty or unsupported response"
            except TimeoutError:
                readings[name] = None
                failures[name] = "timeout after 2.5s"
            except Exception as err:
                readings[name] = None
                failures[name] = f"{type(err).__name__}: {err}"
                _LOGGER.debug("StecaGrid %s read exception", name, exc_info=True)
            finally:
                _LOGGER.debug(
                    "StecaGrid %s poll took %.3fs", name, time.monotonic() - started
                )

        if failures != self._previous_failures:
            if failures:
                _LOGGER.warning(
                    "StecaGrid read issues: %s",
                    "; ".join(f"{key}: {value}" for key, value in failures.items()),
                )
            elif self._previous_failures:
                _LOGGER.info("StecaGrid communication fully restored")
            self._previous_failures = failures
        elif failures:
            _LOGGER.debug("StecaGrid repeated read failures: %s", failures)
        if all(value is None for value in readings.values()):
            raise UpdateFailed("All StecaGrid measurements failed")
        return readings
