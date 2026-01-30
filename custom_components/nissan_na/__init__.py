"""
Home Assistant custom integration for Nissan North America vehicles using Smartcar API.
"""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REDIRECT_URI,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)
from .nissan_api import SmartcarApiClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Nissan NA from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Extract configuration
    client_id = config_entry.data[CONF_CLIENT_ID]
    client_secret = config_entry.data[CONF_CLIENT_SECRET]
    redirect_uri = config_entry.data[CONF_REDIRECT_URI]
    access_token = config_entry.data.get(CONF_ACCESS_TOKEN)
    refresh_token = config_entry.data.get(CONF_REFRESH_TOKEN)

    # Initialize Smartcar client
    client = SmartcarApiClient(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    # Store client in hass data
    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": client,
        "vehicles": [],
    }

    # Get initial vehicle list
    try:
        vehicles = await client.get_vehicle_list()
        hass.data[DOMAIN][config_entry.entry_id]["vehicles"] = vehicles
        _LOGGER.info("Found %d vehicle(s)", len(vehicles))
    except Exception as err:
        _LOGGER.error("Failed to get vehicle list: %s", err)
        return False

    # Periodic update interval (default 15 minutes, can be changed in options)
    update_minutes = config_entry.options.get("update_interval", 15)

    async def async_update_all_vehicles(now):
        """Update all vehicles periodically."""
        try:
            # Refresh access token if needed
            await client.refresh_access_token()

            # Update vehicle data
            vehicles = hass.data[DOMAIN][config_entry.entry_id]["vehicles"]
            for vehicle in vehicles:
                try:
                    await client.get_vehicle_status(vehicle.id)
                    _LOGGER.debug("Updated vehicle %s", vehicle.vin)
                except Exception as err:
                    _LOGGER.error("Failed to update vehicle %s: %s", vehicle.vin, err)
        except Exception as err:
            _LOGGER.error("Failed to refresh token: %s", err)

    # Schedule periodic updates
    async_track_time_interval(
        hass, async_update_all_vehicles, timedelta(minutes=update_minutes)
    )

    # Register services
    async def handle_lock_doors(call):
        """Handle lock doors service call."""
        vehicle_id = call.data.get("vehicle_id")
        try:
            await client.lock_doors(vehicle_id)
            _LOGGER.info("Locked doors for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to lock doors: %s", err)

    async def handle_unlock_doors(call):
        """Handle unlock doors service call."""
        vehicle_id = call.data.get("vehicle_id")
        try:
            await client.unlock_doors(vehicle_id)
            _LOGGER.info("Unlocked doors for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to unlock doors: %s", err)

    async def handle_start_charge(call):
        """Handle start charging service call."""
        vehicle_id = call.data.get("vehicle_id")
        try:
            await client.start_charge(vehicle_id)
            _LOGGER.info("Started charging for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to start charging: %s", err)

    async def handle_stop_charge(call):
        """Handle stop charging service call."""
        vehicle_id = call.data.get("vehicle_id")
        try:
            await client.stop_charge(vehicle_id)
            _LOGGER.info("Stopped charging for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to stop charging: %s", err)

    async def handle_refresh_status(call):
        """Handle refresh status service call."""
        vehicle_id = call.data.get("vehicle_id")
        try:
            await client.get_vehicle_status(vehicle_id)
            _LOGGER.info("Refreshed status for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to refresh status: %s", err)

    # Register all services
    hass.services.async_register(DOMAIN, "lock_doors", handle_lock_doors)
    hass.services.async_register(DOMAIN, "unlock_doors", handle_unlock_doors)
    hass.services.async_register(DOMAIN, "start_charge", handle_start_charge)
    hass.services.async_register(DOMAIN, "stop_charge", handle_stop_charge)
    hass.services.async_register(DOMAIN, "refresh_status", handle_refresh_status)

    # Set up platforms (sensor, lock, climate, device_tracker)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        # Remove data
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
