"""Constants for Tellstick."""

from collections import namedtuple

import threading

import tellcore.constants as tellcore_constants

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature

DOMAIN = "tellstick"

CONF_SIGNAL_REPETITIONS = "signal_repetitions"
DEFAULT_SIGNAL_REPETITIONS = 1

SIGNAL_TELLCORE_CALLBACK = "tellstick_callback"

SUBENTRY_TYPE_SENSOR = "sensor"
ISSUE_NEW_SENSOR_PREFIX = "new_sensor"

DatatypeDescription = namedtuple(  # noqa: PYI024
    "DatatypeDescription", ["name", "unit", "device_class"]
)

DEFAULT_DATATYPE_MASK = 127

# Same mapping as the original core integration's sensor.py -- which
# datatypes to expose as entities, and how, when a sensor reports them
# (checked live via tellcore_sensor.has_value(datatype)).
SENSOR_VALUE_DESCRIPTIONS = {
    tellcore_constants.TELLSTICK_TEMPERATURE: DatatypeDescription(
        "temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE
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


# libtelldus-core is not thread-safe, and Home Assistant polls each entity in its
# own executor thread: two calls into it at once can segfault the whole Core
# process (seen 2026-11-17 in tdSensorValue). Every call into tellcore goes
# through this lock. Re-entrant, since a device command holds it while it
# sends the first repeat.
TELLCORE_LOCK = threading.RLock()
