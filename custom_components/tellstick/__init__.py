"""The Tellstick integration, config-entry based."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging

from tellcore.telldus import AsyncioCallbackDispatcher, TelldusCore
from tellcorenet import TellCoreClient
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_SIGNAL_REPETITIONS,
    DEFAULT_SIGNAL_REPETITIONS,
    DOMAIN,
    ISSUE_NEW_SENSOR_PREFIX,
    SIGNAL_TELLCORE_CALLBACK,
    SUBENTRY_TYPE_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.COVER, Platform.LIGHT, Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Inclusive(CONF_HOST, "net"): cv.string,
                vol.Inclusive(CONF_PORT, "net"): vol.All(
                    cv.ensure_list, [cv.port], vol.Length(min=2, max=2)
                ),
                vol.Optional(
                    CONF_SIGNAL_REPETITIONS, default=DEFAULT_SIGNAL_REPETITIONS
                ): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass
class TellstickData:
    """Runtime data for a Tellstick config entry."""

    tellcore_lib: TelldusCore
    net_client: TellCoreClient | None
    devices: dict[int, object]
    signal_repetitions: int
    callback_id: int | None
    sensor_callback_id: int | None = None
    known_sensor_uids: set[str] = field(default_factory=set)


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


def _connect(
    hass: HomeAssistant, host: str | None, ports: list[int] | None
) -> tuple[TelldusCore, TellCoreClient | None]:
    """Connect, local or network depending on what's configured.

    Runs in the executor. Network mode bridges a remote telldusd's local
    socket API over TCP (e.g. via socat) -- NOT Telldus Live/cloud.
    """
    net_client = None
    if host:
        net_client = TellCoreClient(host=host, port_client=ports[0], port_events=ports[1])
        net_client.start()
    tellcore_lib = TelldusCore(callback_dispatcher=AsyncioCallbackDispatcher(hass.loop))
    return tellcore_lib, net_client


def _known_sensor_unique_ids(entry: TellstickConfigEntry) -> set[str]:
    """Unique IDs of sensors already accepted as subentries."""
    return {
        subentry.unique_id
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_SENSOR and subentry.unique_id
    }


async def async_setup_entry(hass: HomeAssistant, entry: TellstickConfigEntry) -> bool:
    """Set up Tellstick from a config entry."""
    signal_repetitions = entry.options.get(
        CONF_SIGNAL_REPETITIONS, DEFAULT_SIGNAL_REPETITIONS
    )
    host = entry.data.get(CONF_HOST)
    ports = entry.data.get(CONF_PORT)

    try:
        tellcore_lib, net_client = await hass.async_add_executor_job(
            _connect, hass, host, ports
        )
    except OSError as err:
        raise ConfigEntryNotReady("Could not connect to telldusd") from err

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

    data = TellstickData(
        tellcore_lib=tellcore_lib,
        net_client=net_client,
        devices=devices,
        signal_repetitions=signal_repetitions,
        callback_id=callback_id,
        known_sensor_uids=_known_sensor_unique_ids(entry),
    )
    entry.runtime_data = data

    # Live sensor discovery: TellStick reception is promiscuous/unauthenticated
    # (can pick up a neighbor's equipment), so a newly-heard sensor never gets
    # auto-added -- it raises a fixable repair issue with a confirm/ignore fix
    # flow (see repairs.py). Signature verified against the actual installed
    # tellcore-py's SENSOR_EVENT_FUNC ctypes prototype, not guessed:
    # (protocol, model, sensor_id, dataType, value, timestamp, cid, context).
    @callback
    def async_handle_sensor_event(
        protocol, model, sensor_id, data_type, value, timestamp, cid
    ):
        protocol_s = protocol.decode() if isinstance(protocol, bytes) else protocol
        model_s = model.decode() if isinstance(model, bytes) else model
        uid = f"{protocol_s}_{model_s}_{sensor_id}"
        if uid in data.known_sensor_uids:
            return

        issue_id = f"{ISSUE_NEW_SENSOR_PREFIX}_{uid}"

        # Defensive: don't rely on async_create_issue's own behavior toward
        # an already-ignored issue_id (unverified in this environment) --
        # explicitly skip re-creating one that's been dismissed, so ignoring
        # a sensor actually stays quiet on every subsequent broadcast.
        existing = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
        if existing is not None and existing.dismissed_version is not None:
            return

        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="new_sensor_discovered",
            translation_placeholders={
                "protocol": protocol_s,
                "model": model_s,
                "sensor_id": str(sensor_id),
            },
            data={
                "entry_id": entry.entry_id,
                "protocol": protocol_s,
                "model": model_s,
                "sensor_id": sensor_id,
                "unique_id": uid,
            },
        )

    data.sensor_callback_id = await hass.async_add_executor_job(
        tellcore_lib.register_sensor_event, async_handle_sensor_event
    )

    async def _async_update_listener(
        hass: HomeAssistant, entry: TellstickConfigEntry
    ) -> None:
        """Reload on any entry/subentry change (e.g. a sensor gets confirmed)."""
        hass.config_entries.async_schedule_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TellstickConfigEntry) -> bool:
    """Unload a Tellstick config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = entry.runtime_data
        if data.callback_id is not None:
            await hass.async_add_executor_job(
                data.tellcore_lib.unregister_callback, data.callback_id
            )
        if data.sensor_callback_id is not None:
            await hass.async_add_executor_job(
                data.tellcore_lib.unregister_callback, data.sensor_callback_id
            )
        if data.net_client is not None:
            await hass.async_add_executor_job(data.net_client.stop)
    return unload_ok
