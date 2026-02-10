"""Diagnostics support for Nissan NA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_WEBHOOK_ID, DOMAIN

# Fields to redact in diagnostics
TO_REDACT = {
    "access_token",
    "refresh_token",
    "client_id",
    "client_secret",
    "token",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    webhook_id = config_entry.data.get(CONF_WEBHOOK_ID, "Not configured")
    webhook_url = config_entry.data.get("webhook_url", "Not configured")
    
    # Get vehicle count from hass.data if available
    vehicle_count = 0
    sensor_count = 0
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        data = hass.data[DOMAIN][config_entry.entry_id]
        vehicle_count = len(data.get("vehicles", []))
        
        # Count sensors
        sensors = data.get("sensors", {})
        sensor_count = sum(len(v) for v in sensors.values())
    
    return {
        "config_entry": async_redact_data(config_entry.data, TO_REDACT),
        "webhook": {
            "id": webhook_id,
            "url": webhook_url,
        },
        "vehicles": vehicle_count,
        "sensors": sensor_count,
    }
