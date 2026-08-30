"""Repair flows for Tellstick.

The only repair here is "a new sensor was just heard" -- TellStick reception
is promiscuous/unauthenticated (you can pick up a neighbor's equipment), so
new sensors always need an explicit confirm/ignore rather than being added
silently. Mirrors the real confirm/ignore repair flow pattern used by
synology_dsm's repairs.py in this same Core version.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import (
    ConfirmRepairFlow,
    RepairsFlow,
    RepairsFlowResult,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, SUBENTRY_TYPE_SENSOR


class NewSensorRepairFlow(RepairsFlow):
    """Confirm or ignore a newly detected sensor."""

    def __init__(self, issue_id: str, data: dict[str, Any]) -> None:
        """Store the sensor identity from the issue's data."""
        self.issue_id = issue_id
        self._entry_id = data["entry_id"]
        self._protocol = data["protocol"]
        self._model = data["model"]
        self._sensor_id = data["sensor_id"]
        self._unique_id = data["unique_id"]
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        """Offer confirm or ignore."""
        return self.async_show_menu(
            menu_options=["confirm", "ignore"],
            description_placeholders={
                "protocol": self._protocol,
                "model": self._model,
                "sensor_id": str(self._sensor_id),
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        """Add this sensor as a subentry -- its entities appear on the next reload."""
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        subentry = ConfigSubentry(
            data={},
            subentry_type=SUBENTRY_TYPE_SENSOR,
            title=f"{self._protocol} {self._model} {self._sensor_id}",
            unique_id=self._unique_id,
        )
        self.hass.config_entries.async_add_subentry(entry, subentry)
        return self.async_create_entry(data={})

    async def async_step_ignore(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        """Ignore this sensor -- won't re-prompt for the same identity."""
        ir.async_ignore_issue(self.hass, DOMAIN, self.issue_id, True)
        return self.async_abort(reason="ignored")


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create the fix flow for a Tellstick repair issue."""
    if data is not None and "unique_id" in data:
        return NewSensorRepairFlow(issue_id, data)
    return ConfirmRepairFlow()
