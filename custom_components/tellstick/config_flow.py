"""Config flow for Tellstick.

Supports local mode (talk to telldusd directly, e.g. via a USB TellStick)
and network mode (tellcorenet.TellCoreClient bridging to a telldusd
reachable over TCP -- NOT Telldus Live/cloud, just a remote telldusd's
local socket API exposed over the network, e.g. via socat).
"""

from __future__ import annotations

import logging
from typing import Any

from tellcore.telldus import TelldusCore
from tellcorenet import TellCoreClient
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_SIGNAL_REPETITIONS,
    DEFAULT_SIGNAL_REPETITIONS,
    DOMAIN,
    SUBENTRY_TYPE_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

# HA's frontend can't render a voluptuous vol.All(cv.ensure_list, ...) list-of-2
# schema as a form field (it crashes the schema serializer with "Unable to
# convert schema"), even though that shape is fine for plain YAML validation.
# So the interactive form uses two separate scalar port fields instead, and
# the two are combined back into the [client, events] list this integration
# stores/uses internally (see _ports_from_input below).
CONF_PORT_CLIENT = "port_client"
CONF_PORT_EVENTS = "port_events"

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Inclusive(CONF_HOST, "net"): cv.string,
        vol.Inclusive(CONF_PORT_CLIENT, "net"): cv.port,
        vol.Inclusive(CONF_PORT_EVENTS, "net"): cv.port,
    }
)


def _ports_from_input(user_input: dict[str, Any]) -> list[int] | None:
    """Combine the two form port fields back into the internal [client, events] shape."""
    port_client = user_input.get(CONF_PORT_CLIENT)
    port_events = user_input.get(CONF_PORT_EVENTS)
    if port_client is None or port_events is None:
        return None
    return [port_client, port_events]


def _test_connection(host: str | None, ports: list[int] | None) -> None:
    """Try to connect, local or network depending on what's given.

    Raises OSError if unreachable (mirrors the original integration's
    error handling around TelldusCore()).
    """
    net_client = None
    if host:
        net_client = TellCoreClient(host=host, port_client=ports[0], port_events=ports[1])
        net_client.start()
    try:
        TelldusCore().devices()
    finally:
        if net_client:
            net_client.stop()


class TellstickConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tellstick."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentry types supported by this integration."""
        return {SUBENTRY_TYPE_SENSOR: SensorSubentryFlowHandler}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up a connection -- local (leave host/port blank) or network."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input.get(CONF_HOST)
            ports = _ports_from_input(user_input)
            try:
                await self.hass.async_add_executor_job(_test_connection, host, ports)
            except OSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Tellstick",
                    data={CONF_HOST: host, CONF_PORT: ports},
                    options={CONF_SIGNAL_REPETITIONS: DEFAULT_SIGNAL_REPETITIONS},
                )

        return self.async_show_form(
            step_id="user", data_schema=CONNECTION_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change connection settings and/or the signal repeat count."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input.get(CONF_HOST)
            ports = _ports_from_input(user_input)
            try:
                await self.hass.async_add_executor_job(_test_connection, host, ports)
            except OSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data={CONF_HOST: host, CONF_PORT: ports},
                    options={
                        CONF_SIGNAL_REPETITIONS: user_input[CONF_SIGNAL_REPETITIONS]
                    },
                )

        schema = CONNECTION_SCHEMA.extend(
            {
                vol.Required(
                    CONF_SIGNAL_REPETITIONS,
                    default=reconfigure_entry.options.get(
                        CONF_SIGNAL_REPETITIONS, DEFAULT_SIGNAL_REPETITIONS
                    ),
                ): vol.Coerce(int),
            }
        )
        suggested_values = dict(reconfigure_entry.data)
        if (existing_ports := suggested_values.pop(CONF_PORT, None)) is not None:
            suggested_values[CONF_PORT_CLIENT] = existing_ports[0]
            suggested_values[CONF_PORT_EVENTS] = existing_ports[1]

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, suggested_values),
            errors=errors,
        )

    async def async_step_import(self, import_data: ConfigType) -> ConfigFlowResult:
        """Import legacy YAML config (`tellstick:`) into a config entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            "deprecated_yaml",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            learn_more_url="https://github.com/pallemannen/hass_tellstick",
        )

        signal_repetitions = import_data.get(
            CONF_SIGNAL_REPETITIONS, DEFAULT_SIGNAL_REPETITIONS
        )

        return self.async_create_entry(
            title="Tellstick",
            data={
                CONF_HOST: import_data.get(CONF_HOST),
                CONF_PORT: import_data.get(CONF_PORT),
            },
            options={CONF_SIGNAL_REPETITIONS: signal_repetitions},
        )


class SensorSubentryFlowHandler(ConfigSubentryFlow):
    """Manage sensor subentries.

    Sensors are normally added automatically via the "new sensor detected"
    repair flow (see repairs.py) -- that's the primary path, since sensors
    self-identify only once they broadcast. This handler exists mainly so
    existing sensor subentries render/manage properly in the standard
    Settings -> Devices -> Tellstick -> sub-items UI (deletion is handled
    generically by core for any subentry type). Manual add isn't built.
    """

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Explain that sensors are added automatically, not manually."""
        return self.async_abort(reason="use_discovery")
