"""Support for Tellstick switches."""

from typing import override

from tellcore.constants import TELLSTICK_DIM, TELLSTICK_UP

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TellstickConfigEntry
from .entity import TellstickDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TellstickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tellstick switches from a config entry.

    A device is a switch if it can't dim and can't be raised/lowered --
    same "leftover" categorization the original discovery-based setup used.
    """
    data = entry.runtime_data
    async_add_entities(
        (
            TellstickSwitch(device, data.signal_repetitions)
            for device in data.devices.values()
            if not device.methods(TELLSTICK_UP) and not device.methods(TELLSTICK_DIM)
        ),
        True,
    )


class TellstickSwitch(TellstickDevice, SwitchEntity):
    """Representation of a Tellstick switch."""

    _attr_force_update = True

    @override
    def _parse_ha_data(self, kwargs):
        """Turn the value from HA into something useful."""

    @override
    def _parse_tellcore_data(self, tellcore_data):
        """Turn the value received from tellcore into something useful."""

    @override
    def _update_model(self, new_state, data):
        """Update the device entity state to match the arguments."""
        self._attr_is_on = new_state

    @override
    def _send_device_command(self, requested_state, requested_data):
        """Let tellcore update the actual device to the requested state."""
        if requested_state:
            self._tellcore_device.turn_on()
        else:
            self._tellcore_device.turn_off()
