# Revision: 2025-08-18 16:40:00
"""Select platform for Traeger."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import TraegerCoordinator
from .entity import TraegerBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up select platform for Traeger."""
    _LOGGER.debug("Setting up Select entities")
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    coordinator: TraegerCoordinator = data["coordinator"]

    entities: list[SelectEntity] = []
    for grill in client.get_grills():
        grill_id = grill["thingName"]
        _LOGGER.debug("Setting up Select entity for grill %s", grill_id)
        # Always add the select entity, even if state is missing
        entities.append(TraegerCustomCookSelect(client, grill_id, coordinator=coordinator))
    if entities:
        async_add_entities(entities)


class TraegerCustomCookSelect(TraegerBaseEntity, SelectEntity):
    """Select entity for Traeger custom cook cycles."""

    _attr_has_entity_name = True
    _attr_translation_key = "custom_cook_cycle"

    def __init__(
        self,
        client: Any,
        grill_id: str,
        coordinator: TraegerCoordinator | None = None,
    ) -> None:
        super().__init__(client, grill_id, name="Custom Cook cycle", coordinator=coordinator)
        self._attr_unique_id = f"{grill_id}_custom_cook_cycle"
        self.entity_id = f"select.{slugify(grill_id)}_custom_cook_cycle"
        _LOGGER.debug("Initialized select %s with name %s", self.entity_id, self._attr_name)

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        await super().async_added_to_hass()
        if self.coordinator:
            self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def name(self) -> str | None:
        """Return the entity name."""
        return self._attr_name

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID."""
        return self._attr_unique_id

    @property
    def available(self) -> bool:
        """Return True if grill is connected."""
        state = self.grill_state or {}
        status = state.get("status") or {}
        return bool(status.get("connected", False))

    @property
    def options(self) -> list[str]:
        """Return available custom cook cycles, always including 'None'."""
        state = self.grill_state or {}
        cycles = (state.get("custom_cook") or {}).get("cook_cycles", [])
        return ["None"] + [
            cycle.get("cycle_name", f"Slot {cycle.get('slot_num', '?')}")
            for cycle in cycles
            if cycle.get("populated")
        ]

    @property
    def current_option(self) -> str:
        """Return the currently selected cook cycle, or 'None'."""
        state = self.grill_state or {}
        if "status" not in state or "custom_cook" not in state:
            _LOGGER.debug(
                "No state for Select %s: grill_state=%s",
                self.entity_id,
                self.grill_state,
            )
            return "None"
        current_cycle = state["status"].get("current_cycle", 0)
        if current_cycle == 0:
            return "None"
        cycles = state["custom_cook"].get("cook_cycles", [])
        for cycle in cycles:
            if cycle.get("slot_num") == current_cycle and cycle.get("populated", 0) == 1:
                return cycle["cycle_name"]
        return "None"

    async def async_select_option(self, option: str) -> None:
        """Handle user selection of a cook cycle."""
        if option == "None":
            _LOGGER.debug("Setting %s to no cycle", self.entity_id)
            await self.client.set_custom_cook(self.grill_id, 0)
        else:
            cycles = (self.grill_state or {}).get("custom_cook", {}).get("cook_cycles", [])
            for cycle in cycles:
                if cycle.get("cycle_name") == option and cycle.get("populated", 0) == 1:
                    _LOGGER.debug(
                        "Setting %s to cycle %s, slot %s",
                        self.entity_id,
                        option,
                        cycle["slot_num"],
                    )
                    await self.client.set_custom_cook(self.grill_id, cycle["slot_num"])
                    break
        self.async_schedule_update_ha_state()
