"""The Tellstick integration (local telldusd only, config-entry based)."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from tellcore.telldus import AsyncioCallbackDispatcher, TelldusCore
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_SIGNAL_REPETITIONS,
    DEFAULT_SIGNAL_REPETITIONS,
    DOMAIN,
    SIGNAL_TELLCORE_CALLBACK,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.COVER, Platform.LIGHT, Platform.SENSOR, Platform.SWITCH]

# extra=ALLOW_EXTRA so old net-mode YAML (host/port) doesn't fail validation
# outright -- async_step_import decides what to do with it.
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(
                    CONF_SIGNAL_REPETITIONS, default=DEFAULT_SIGNAL_REPETITIONS
                ): vol.Coerce(int),
            },
            extra=vol.ALLOW_EXTRA,
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass
class TellstickData:
    """Runtime data for a Tellstick config entry."""

    tellcore_lib: TelldusCore
    devices: dict[int, object]
    signal_repetitions: int
    callback_id: int | None


type TellstickConfigEntry = ConfigEntry[TellstickData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Tellstick from YAML, if present -- hands off to the import flow."""
    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
        )
    )
    return True


def _connect(hass: HomeAssistant) -> TelldusCore:
    """Connect to the local telldusd. Runs in the executor."""
    return TelldusCore(callback_dispatcher=AsyncioCallbackDispatcher(hass.loop))


async def async_setup_entry(hass: HomeAssistant, entry: TellstickConfigEntry) -> bool:
    """Set up Tellstick from a config entry."""
    signal_repetitions = entry.options.get(
        CONF_SIGNAL_REPETITIONS, DEFAULT_SIGNAL_REPETITIONS
    )

    try:
        tellcore_lib = await hass.async_add_executor_job(_connect, hass)
    except OSError as err:
        raise ConfigEntryNotReady("Could not connect to local telldusd") from err

    tellcore_devices = await hass.async_add_executor_job(tellcore_lib.devices)
    devices = {device.id: device for device in tellcore_devices}

    @callback
    def async_handle_callback(tellcore_id, tellcore_command, tellcore_data, cid):
        """Forward a tellcore device event onto the dispatcher."""
        async_dispatcher_send(
            hass,
            SIGNAL_TELLCORE_CALLBACK,
            tellcore_id,
            tellcore_command,
            tellcore_data,
        )

    callback_id = await hass.async_add_executor_job(
        tellcore_lib.register_device_event, async_handle_callback
    )

    entry.runtime_data = TellstickData(
        tellcore_lib=tellcore_lib,
        devices=devices,
        signal_repetitions=signal_repetitions,
        callback_id=callback_id,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TellstickConfigEntry) -> bool:
    """Unload a Tellstick config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.runtime_data.callback_id is not None:
        await hass.async_add_executor_job(
            entry.runtime_data.tellcore_lib.unregister_callback,
            entry.runtime_data.callback_id,
        )
    return unload_ok
