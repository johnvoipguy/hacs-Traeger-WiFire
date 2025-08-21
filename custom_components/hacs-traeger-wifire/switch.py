"""Switch platform for Traeger."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import TraegerCoordinator
from .entity import TraegerBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up switch entities."""
    _LOGGER.debug("Setting up switch entities")

    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    coordinator: TraegerCoordinator | None = data.get("coordinator")

    entities: list[TraegerCommandSwitch] = []

    for grill in client.get_grills():
        grill_id = grill["thingName"]
        _LOGGER.debug(f"Setting up switch entities for grill {grill_id}")

        # Define command tokens and icons per switch
        switches_def = [
            # Super Smoke: ON=20, OFF=21
            {
                "key": "smoke",
                "name": "Super Smoke Enabled",
                "icon": "mdi:weather-fog",
                "on": "20",
                "off": "21",
            },
            # Keep Warm: ON=18, OFF=19
            {
                "key": "keepwarm",
                "name": "Keep Warm Enabled",
                "icon": "mdi:beach",
                "on": "18",
                "off": "19",
            },
        ]

        for cfg in switches_def:
            entities.append(
                TraegerCommandSwitch(
                    client=client,
                    grill_id=grill_id,
                    key=cfg["key"],
                    name=cfg["name"],
                    icon=cfg["icon"],
                    on_command=cfg["on"],
                    off_command=cfg["off"],
                    coordinator=coordinator,
                )
            )

    if entities:
        _LOGGER.debug(f"Adding {len(entities)} switch entities")
        async_add_entities(entities)


class TraegerCommandSwitch(TraegerBaseEntity, SwitchEntity):
    """Generic switch that sends single-string command payloads."""

    _attr_has_entity_name = True

    def __init__(
        self,
        *,
        client: Any,
        grill_id: str,
        key: str,
        name: str,
        icon: str | None,
        on_command: str | int,
        off_command: str | int,
        coordinator: TraegerCoordinator | None = None,
    ) -> None:
        super().__init__(client, grill_id, name, coordinator=coordinator)
        self._key = key
        self._on_cmd = str(on_command)
        self._off_cmd = str(off_command)
        self._attr_unique_id = f"{grill_id}_{key}"
        self.entity_id = f"switch.{slugify(grill_id)}_{slugify(name)}"
        self._attr_icon = icon
        # Do not set _attr_device_info here; base entity provides dynamic device info
        _LOGGER.debug(f"Initialized switch {self.entity_id} for grill {grill_id}")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.coordinator:
            self.async_on_remove(
                self.coordinator.async_add_listener(self.async_write_ha_state)
            )

    @property
    def available(self) -> bool:
        state = self.grill_state or {}
        return bool((state.get("status") or {}).get("connected", False))

    @property
    def is_on(self) -> bool:
        """Reflect current switch state from coordinator snapshot."""
        state = self.grill_state or {}
        status = state.get("status") or {}
        settings = state.get("settings") or {}
        val = status.get(self._key)
        if val is None:
            val = settings.get(self._key)
        return bool(val)

    async def _send_command(self, command: str) -> None:
        """Post a single command string as {'command': '<cmd>'} via the client."""
        _LOGGER.debug(f"Sending command {command} for {self.entity_id}")
        try:
            await self.client.send_command(self.grill_id, command)
        except AttributeError:
            # Fallback to legacy helper
            await self.client.set_switch(self.grill_id, command)

        if self.coordinator:
            await self.coordinator.async_request_refresh()
        else:
            self.async_schedule_update_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        await self._send_command(self._on_cmd)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send_command(self._off_cmd)
