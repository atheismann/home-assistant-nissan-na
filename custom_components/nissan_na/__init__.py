"""Home Assistant custom integration for Nissan North America vehicles.

Uses Smartcar API for vehicle integration.
"""

import logging
from datetime import timedelta

from homeassistant.components import webhook as ha_webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.event import async_track_time_interval

from .api import SmartcarOAuth2Implementation
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)
from .nissan_api import SmartcarApiClient
from .webhook import (
    async_generate_webhook_url,
    async_register_webhook,
    async_unregister_webhook,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Nissan NA component."""
    # Register OAuth2 implementation
    config_entry_oauth2_flow.async_register_implementation(
        hass,
        DOMAIN,
        SmartcarOAuth2Implementation(
            hass,
            DOMAIN,
            config.get(DOMAIN, {}).get(CONF_CLIENT_ID, ""),
            config.get(DOMAIN, {}).get(CONF_CLIENT_SECRET, ""),
            "https://connect.smartcar.com/oauth/authorize",
            "https://connect.smartcar.com/oauth/token",
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Nissan NA from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Register webhook if webhook_id exists
    webhook_id = config_entry.data.get(CONF_WEBHOOK_ID)
    if webhook_id:
        async_register_webhook(hass, config_entry.entry_id, webhook_id)
        webhook_url = async_generate_webhook_url(hass, webhook_id)
        _LOGGER.info("Webhook registered at: %s", webhook_url)
        _LOGGER.info(
            "Configure this URL in your Smartcar Dashboard to receive real-time updates"
        )
    else:
        # Generate webhook ID for new setups
        webhook_id = ha_webhook.async_generate_id()
        webhook_url = async_generate_webhook_url(hass, webhook_id)

        # Update config entry with webhook ID
        hass.config_entries.async_update_entry(
            config_entry, data={**config_entry.data, CONF_WEBHOOK_ID: webhook_id}
        )

        async_register_webhook(hass, config_entry.entry_id, webhook_id)
        _LOGGER.info("Webhook registered at: %s", webhook_url)
        _LOGGER.info(
            "Configure this URL in your Smartcar Dashboard to receive real-time updates"
        )

    # Check if config entry has auth_implementation (OAuth2 flow)
    if "auth_implementation" not in config_entry.data:
        _LOGGER.error(
            "Config entry is missing auth_implementation. "
            "Please remove and re-add the integration."
        )
        return False

    # OAuth2 implementation stores tokens differently
    # Extract from token dict if present, otherwise fall back to direct keys
    token_data = config_entry.data.get("token", {})
    access_token = token_data.get("access_token") or config_entry.data.get(
        CONF_ACCESS_TOKEN
    )
    refresh_token = token_data.get("refresh_token") or config_entry.data.get(
        CONF_REFRESH_TOKEN
    )

    # Get client credentials from implementation
    try:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, config_entry
            )
        )
    except KeyError:
        _LOGGER.error(
            "OAuth implementation not found. "
            "Please remove and re-add the integration."
        )
        return False

    client_id = implementation.client_id
    client_secret = implementation.client_secret
    redirect_uri = implementation.redirect_uri

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
    # Unregister webhook
    webhook_id = config_entry.data.get(CONF_WEBHOOK_ID)
    if webhook_id:
        async_unregister_webhook(hass, webhook_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        # Remove data
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
