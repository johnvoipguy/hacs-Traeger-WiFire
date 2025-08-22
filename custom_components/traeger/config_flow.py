from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS
from .traeger import traeger

# The rest of the file content remains unchanged