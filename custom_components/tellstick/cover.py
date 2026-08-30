"""Support for Tellstick covers."""

from typing import Any, override

from tellcore.constants import TELLSTICK_UP

from homeassistant.components.cover import CoverEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TellstickConfigEntry
from .entity import TellstickDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TellstickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tellstick covers from a config entry."""
    data = entry.runtime_data
    async_add_entities(
        (
            TellstickCover(device, data.signal_repetitions)
            for device in data.devices.values()
            if device.methods(TELLSTICK_UP)
        ),
        True,
    )


class TellstickCover(TellstickDevice, CoverEntity):
    """Representation of a Tellstick cover."""

    @property
    @override
    def is_closed(self) -> None:
        """Return the current position of the cover is not possible."""
        return None

    @property
    @override
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return True

    @override
    def close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self._tellcore_device.down()

    @override
    def open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self._tellcore_device.up()

    @override
    def stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        self._tellcore_device.stop()

    @override
    def _parse_tellcore_data(self, tellcore_data):
        """Turn the value received from tellcore into something useful."""

    @override
    def _parse_ha_data(self, kwargs):
        """Turn the value from HA into something useful."""

    @override
    def _update_model(self, new_state, data):
        """Update the device entity state to match the arguments."""
