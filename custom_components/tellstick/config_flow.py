"""Config flow for Tellstick (local telldusd only, no Telldus Live)."""

from __future__ import annotations

import logging
from typing import Any

from tellcore.telldus import TelldusCore
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import CONF_SIGNAL_REPETITIONS, DEFAULT_SIGNAL_REPETITIONS, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _test_local_connection() -> int:
    """Try to reach a local telldusd and return how many devices it knows about.

    Raises OSError if telldusd isn't reachable (mirrors the original
    integration's own error handling around TelldusCore()).
    """
    return len(TelldusCore().devices())


class TellstickConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tellstick (local telldusd only)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a local telldusd is reachable, then create the entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(_test_local_connection)
            except OSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Tellstick",
                    data={},
                    options={CONF_SIGNAL_REPETITIONS: DEFAULT_SIGNAL_REPETITIONS},
                )

        return self.async_show_form(step_id="user", errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the signal repeat count for an existing entry.

        Local mode has no host/port to change, so this is the only setting
        worth reconfiguring.
        """
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            return self.async_update_reload_and_abort(
                reconfigure_entry,
                options={
                    CONF_SIGNAL_REPETITIONS: user_input[CONF_SIGNAL_REPETITIONS]
                },
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SIGNAL_REPETITIONS,
                        default=reconfigure_entry.options.get(
                            CONF_SIGNAL_REPETITIONS, DEFAULT_SIGNAL_REPETITIONS
                        ),
                    ): vol.Coerce(int),
                }
            ),
        )

    async def async_step_import(
        self, import_data: ConfigType
    ) -> ConfigFlowResult:
        """Import legacy YAML config (`tellstick:`) into a config entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if CONF_HOST in import_data:
            # Old YAML pointed at a Telldus Live / tellcore-net host. This
            # fork is local-only (telldusd via USB), so don't silently create
            # an entry that ignores what the YAML actually asked for.
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "yaml_net_mode_unsupported",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="yaml_net_mode_unsupported",
                learn_more_url="https://github.com/pallemannen/hass_tellstick",
            )
            return self.async_abort(reason="yaml_net_mode_unsupported")

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
            data={},
            options={CONF_SIGNAL_REPETITIONS: signal_repetitions},
        )
