"""Platform for Stecagrid sensor integration."""

from dataclasses import dataclass
from datetime import timedelta
import logging
import math

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfEnergy, UnitOfPower, UnitOfElectricPotential
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity

from . import StecaGridCoordinator
from .lifetime_energy import retain_total_energy
from .const import DEFAULT_INVERTER_POLLRATE, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=DEFAULT_INVERTER_POLLRATE)


@dataclass
class StecaGridEntityDescription(SensorEntityDescription):
    """Describes Stecagrid sensor entity."""

    def __init__(
        self,
        key,
        name,
        icon,
        device_class,
        native_unit_of_measurement,
        value,
        format=None,
        state_class=None,
    ):
        super().__init__(key)
        self.key = key
        self.name = name
        self.icon = icon
        if device_class is not None:
            self.device_class = device_class
        self.native_unit_of_measurement = native_unit_of_measurement
        self.value = value
        self.format = format
        if state_class is not None:
            self.state_class = state_class


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Set up the sensor platform."""
    stecagrid = hass.data[DOMAIN][config.entry_id]

    entities: list[StecagridSensor] = [
        StecagridSensor(stecagrid._coordinator, sensor, stecagrid)
        for sensor in SENSORS_INVERTER
    ]

    async_add_entities(entities)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Code for setting up your platform inside of the event loop
    _LOGGER.debug("async_setup_platform")


class StecagridSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """Representation of a meter reading sensor."""

    def __init__(
        self,
        coordinator: StecaGridCoordinator,
        sensor: StecaGridEntityDescription,
        client,
    ):
        """Initialize the sensor."""
        self._data = client
        super().__init__(coordinator)
        self.entity_description: StecaGridEntityDescription = sensor
        self._attr_unique_id = f"{self.coordinator._alias}_{sensor.key}"
        self._attr_name = f"{self.coordinator._alias} {sensor.name}"

        _LOGGER.info(self._attr_unique_id)
        self._attr_native_value = None  # Initialize the native value

    @property
    def device_info(self):
        """Return device information about this entity."""
        _LOGGER.debug("StecaGrid: device_info")

        return {
            "identifiers": {(DOMAIN, self.coordinator._alias)},
            "manufacturer": "Steca",
            "model": "StecaGrid 8000+ 3ph",
            "name": self.coordinator._alias,
        }

    @property
    def should_poll(self):
        return False

    @property
    def friendly_name(self):
        return self.entity_description.name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._attr_native_value

    async def async_added_to_hass(self):
        """Restore the cumulative meter and subscribe to live updates."""
        await super().async_added_to_hass()
        if self.entity_description.key == "total_yield":
            last = await self.async_get_last_state()
            if last is not None:
                try:
                    value = float(last.state)
                    if math.isfinite(value) and value >= 0:
                        self._attr_native_value = value
                except (ValueError, TypeError):
                    pass
        if self.coordinator.data is not None:
            self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Publish each metric independently, without stale zero readings."""
        key = self.entity_description.key
        if key == "output":
            key = "ac_power"
        data = self.coordinator.data or {}
        value = data.get(key)
        if key == "total_yield":
            # Never replace the cumulative meter with a missing measurement.
            self._attr_native_value = retain_total_energy(self._attr_native_value, value)
        else:
            self._attr_native_value = value
        self._attr_available = self._attr_native_value is not None
        self.async_write_ha_state()

    @property
    def available(self):
        if self.entity_description.key == "total_yield":
            # Missing poll is not a reset of the non-volatile inverter counter.
            return self._attr_native_value is not None
        return super().available

    @property
    def extra_state_attributes(self):
        if "time" in self.entity_description.key:
            attributes = {}
            attributes["Status"] = self.coordinator.stecaApi.timestamp_status
            return attributes
        else:
            None


SENSORS_INVERTER: tuple[SensorEntityDescription, ...] = (
    StecaGridEntityDescription(
        key="output",
        name="Output power",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        value=lambda data, key: data[key],
    ),
    StecaGridEntityDescription(
        key="ac_power",
        name="Output AC power",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        value=lambda data, key: data[key],
    ),
    StecaGridEntityDescription(
        key="panel_power",
        name="Output Panel power",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        value=lambda data, key: data[key],
    ),
    StecaGridEntityDescription(
        key="panel_voltage",
        name="Panel voltage",
        icon="mdi:flash",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value=lambda data, key: data[key],
    ),
    StecaGridEntityDescription(
        key="panel_current",
        name="Panel current",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value=lambda data, key: data[key],
    ),
    StecaGridEntityDescription(
        key="daily_yield",
        name="Output today",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value=lambda data, key: data[key],
    ),
    StecaGridEntityDescription(
        key="total_yield",
        name="Total energy",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value=lambda data, key: data[key],
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    StecaGridEntityDescription(
        key="time",
        name="timestamp",
        icon="mdi:clock-digital",
        device_class=None,
        native_unit_of_measurement=None,
        value=lambda data, key: data[key],
    ),
)
