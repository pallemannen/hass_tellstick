"""Support for Tellstick sensors.

Sensors are represented as subentries (one subentry per physical sensor,
identified by protocol+model+id) rather than YAML's `only_named` list --
see repairs.py for how a subentry gets created (via a confirm/ignore repair
flow triggered by live detection, never silently). Each subentry becomes one
HA device with one entity per datatype that sensor actually reports, exactly
matching the original integration's `sensor_value_descriptions`/`has_value()`
approach, plus a diagnostic "Last updated" timestamp entity. Protocol/model/id
are also set as the device's manufacturer/model/serial_number so that
identity survives the user renaming the device to something meaningful.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TellstickConfigEntry
from .const import SENSOR_VALUE_DESCRIPTIONS, SUBENTRY_TYPE_SENSOR


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TellstickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tellstick sensors, one HA device per confirmed sensor subentry."""
    tellcore_lib = entry.runtime_data.tellcore_lib
    tellcore_sensors = await hass.async_add_executor_job(tellcore_lib.sensors)
    sensors_by_uid = {
        f"{s.protocol}_{s.model}_{s.id}": s for s in tellcore_sensors
    }

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_SENSOR:
            continue

        tellcore_sensor = sensors_by_uid.get(subentry.unique_id)
        if tellcore_sensor is None:
            # Confirmed previously but hasn't broadcast since this restart --
            # nothing to attach entities to yet, it'll pick up next reload
            # after it's heard from again.
            continue

        device_info = DeviceInfo(
            identifiers={(entry.domain, subentry.unique_id)},
            name=subentry.title,
            # Protocol/model/id are only in the auto-generated device name --
            # once the user renames the device to something meaningful (e.g.
            # "Guest room"), that identity would otherwise be lost. These
            # static fields keep it visible on the device page regardless.
            manufacturer=tellcore_sensor.protocol,
            model=tellcore_sensor.model,
            serial_number=str(tellcore_sensor.id),
        )

        entities = [
            TellstickSensor(subentry.unique_id, tellcore_sensor, datatype, sensor_info, device_info)
            for datatype, sensor_info in SENSOR_VALUE_DESCRIPTIONS.items()
            if tellcore_sensor.has_value(datatype)
        ]
        entities.append(
            TellstickLastUpdated(subentry.unique_id, tellcore_sensor, device_info)
        )
        async_add_entities(entities, True, config_subentry_id=subentry.subentry_id)


class TellstickSensor(SensorEntity):
    """Representation of a Tellstick sensor."""

    _attr_should_poll = True
    _attr_has_entity_name = True

    def __init__(self, sensor_uid, tellcore_sensor, datatype, sensor_info, device_info):
        """Initialize the sensor."""
        self._datatype = datatype
        self._tellcore_sensor = tellcore_sensor
        self._attr_native_unit_of_measurement = sensor_info.unit or None
        self._attr_device_class = sensor_info.device_class
        self._attr_name = sensor_info.name.capitalize()
        self._attr_unique_id = f"{sensor_uid}_{datatype}"
        self._attr_device_info = device_info

    def update(self) -> None:
        """Update tellstick sensor."""
        self._attr_native_value = self._tellcore_sensor.value(self._datatype).value


class TellstickLastUpdated(SensorEntity):
    """Most recent time any datatype from this physical sensor was received.

    Useful independent of what the individual value entities show -- a
    sensor with a dead battery still reports its last known temperature
    forever, but this timestamp stops advancing.
    """

    _attr_should_poll = True
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Last updated"

    def __init__(self, sensor_uid, tellcore_sensor, device_info):
        """Initialize the last-updated sensor."""
        self._tellcore_sensor = tellcore_sensor
        self._attr_unique_id = f"{sensor_uid}_last_updated"
        self._attr_device_info = device_info

    def update(self) -> None:
        """Update to the newest timestamp across every datatype this sensor reports."""
        timestamps = [
            self._tellcore_sensor.value(datatype).timestamp
            for datatype in SENSOR_VALUE_DESCRIPTIONS
            if self._tellcore_sensor.has_value(datatype)
        ]
        if timestamps:
            self._attr_native_value = dt_util.utc_from_timestamp(max(timestamps))
