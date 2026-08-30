"""Support for Tellstick sensors.

The original core integration required pre-declaring every sensor's ID/name
via YAML (`only_named`) since raw 433MHz sensor broadcasts don't self-identify
with a name. There's no clean config-flow equivalent of a YAML list-of-dicts
field, so this fork auto-discovers every sensor telldusd currently knows
about and names it from its protocol/model/id -- rename it in the UI
afterwards if you want something nicer. `datatype_mask`/`temperature_scale`
are kept at the original defaults (all types, Celsius) rather than exposed
as options yet.
"""

from collections import namedtuple

import tellcore.constants as tellcore_constants

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TellstickConfigEntry

DatatypeDescription = namedtuple(  # noqa: PYI024
    "DatatypeDescription", ["name", "unit", "device_class"]
)

DEFAULT_DATATYPE_MASK = 127
DEFAULT_TEMPERATURE_SCALE = UnitOfTemperature.CELSIUS

SENSOR_VALUE_DESCRIPTIONS = {
    tellcore_constants.TELLSTICK_TEMPERATURE: DatatypeDescription(
        "temperature", DEFAULT_TEMPERATURE_SCALE, SensorDeviceClass.TEMPERATURE
    ),
    tellcore_constants.TELLSTICK_HUMIDITY: DatatypeDescription(
        "humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY
    ),
    tellcore_constants.TELLSTICK_RAINRATE: DatatypeDescription(
        "rain rate", "", None
    ),
    tellcore_constants.TELLSTICK_RAINTOTAL: DatatypeDescription(
        "rain total", "", None
    ),
    tellcore_constants.TELLSTICK_WINDDIRECTION: DatatypeDescription(
        "wind direction", "", None
    ),
    tellcore_constants.TELLSTICK_WINDAVERAGE: DatatypeDescription(
        "wind average", "", None
    ),
    tellcore_constants.TELLSTICK_WINDGUST: DatatypeDescription(
        "wind gust", "", None
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TellstickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tellstick sensors from a config entry, auto-discovering all of them."""
    tellcore_lib = entry.runtime_data.tellcore_lib
    tellcore_sensors = await hass.async_add_executor_job(tellcore_lib.sensors)

    entities = []
    for tellcore_sensor in tellcore_sensors:
        base_name = f"{tellcore_sensor.protocol} {tellcore_sensor.model} {tellcore_sensor.id}"
        base_uid = f"{tellcore_sensor.protocol}_{tellcore_sensor.model}_{tellcore_sensor.id}"
        for datatype, sensor_info in SENSOR_VALUE_DESCRIPTIONS.items():
            if datatype & DEFAULT_DATATYPE_MASK and tellcore_sensor.has_value(
                datatype
            ):
                entities.append(
                    TellstickSensor(
                        base_name, base_uid, tellcore_sensor, datatype, sensor_info
                    )
                )

    async_add_entities(entities, True)


class TellstickSensor(SensorEntity):
    """Representation of a Tellstick sensor."""

    _attr_should_poll = True

    def __init__(self, base_name, base_uid, tellcore_sensor, datatype, sensor_info):
        """Initialize the sensor."""
        self._datatype = datatype
        self._tellcore_sensor = tellcore_sensor
        self._attr_native_unit_of_measurement = sensor_info.unit or None
        self._attr_device_class = sensor_info.device_class
        self._attr_name = f"{base_name} {sensor_info.name}"
        self._attr_unique_id = f"{base_uid}_{datatype}"

    def update(self) -> None:
        """Update tellstick sensor."""
        self._attr_native_value = self._tellcore_sensor.value(self._datatype).value
