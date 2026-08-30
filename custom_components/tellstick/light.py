"""Support for Tellstick lights."""

from typing import override

from tellcore.constants import TELLSTICK_DIM

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TellstickConfigEntry
from .entity import TellstickDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TellstickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tellstick lights from a config entry."""
    data = entry.runtime_data
    async_add_entities(
        (
            TellstickLight(device, data.signal_repetitions)
            for device in data.devices.values()
            if device.methods(TELLSTICK_DIM)
        ),
        True,
    )


class TellstickLight(TellstickDevice, LightEntity):
    """Representation of a Tellstick light."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, tellcore_device, signal_repetitions):
        """Initialize the Tellstick light."""
        super().__init__(tellcore_device, signal_repetitions)

        self._brightness = 255

    @property
    @override
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @override
    def _parse_ha_data(self, kwargs):
        """Turn the value from HA into something useful."""
        return kwargs.get(ATTR_BRIGHTNESS)

    @override
    def _parse_tellcore_data(self, tellcore_data):
        """Turn the value received from tellcore into something useful."""
        if tellcore_data:
            return int(tellcore_data)  # brightness
        return None

    @override
    def _update_model(self, new_state, data):
        """Update the device entity state to match the arguments."""
        if new_state:
            if (brightness := data) is not None:
                self._brightness = brightness

            # _brightness is not defined when called from super
            try:
                self._attr_is_on = self._brightness > 0
            except AttributeError:
                self._attr_is_on = True
        else:
            self._attr_is_on = False

    @override
    def _send_device_command(self, requested_state, requested_data):
        """Let tellcore update the actual device to the requested state."""
        if requested_state:
            if requested_data is not None:
                self._brightness = int(requested_data)

            self._tellcore_device.dim(self._brightness)
        else:
            self._tellcore_device.turn_off()
