"""Coordinator for Traeger integration (push-first, poll as fallback)."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TraegerCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Hold a snapshot of grill state; MQTT pushes updates frequently."""

    def __init__(self, hass: HomeAssistant, client: Any, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN} coordinator",
            update_interval=timedelta(seconds=60),  # safe fallback
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        # No network: return a shallow copy of the client's current cache
        snap = dict(self.client.grill_status)
        _LOGGER.debug("Manually updated traeger coordinator data")
        return snap
