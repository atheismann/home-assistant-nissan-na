"""Home Assistant custom integration for Nissan North America vehicles.

Uses Smartcar API for vehicle integration.
"""

import logging
from datetime import timedelta

from homeassistant.components import webhook as ha_webhook
from homeassistant.helpers.config_entry_oauth2_flow import (
    async_get_config_entry_implementation,
)
from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_USER_ID,
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
    # Application Credentials are handled automatically by Home Assistant
    # No need to manually register OAuth2 implementation
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
) -> bool:
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
        # Store webhook URL in config entry for easy access in UI
        hass.config_entries.async_update_entry(
            config_entry, data={**config_entry.data, "webhook_url": webhook_url}
        )
    else:
        # Generate webhook ID for new setups
        webhook_id = ha_webhook.async_generate_id()
        webhook_url = async_generate_webhook_url(hass, webhook_id)

        # Update config entry with webhook ID and URL
        hass.config_entries.async_update_entry(
            config_entry,
            data={
                **config_entry.data,
                CONF_WEBHOOK_ID: webhook_id,
                "webhook_url": webhook_url,
            },
        )

        async_register_webhook(hass, config_entry.entry_id, webhook_id)
        _LOGGER.info("Webhook registered at: %s", webhook_url)
        _LOGGER.info(
            "Configure this URL in your Smartcar Dashboard to receive real-time updates"
        )

    # Check for user_id — required for all API calls
    user_id = config_entry.data.get(CONF_USER_ID)
    if not user_id:
        _LOGGER.warning(
            "No user_id found in config entry — re-authorization required. "
            "Go to Settings → Integrations → Nissan"
            " → Configure → Re-authorize Integration."
        )
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": config_entry.entry_id,
                },
                data=config_entry.data,
            )
        )
        return False

    # Load client credentials from Application Credentials storage
    try:
        implementation = await async_get_config_entry_implementation(hass, config_entry)
    except KeyError:
        _LOGGER.error(
            "OAuth implementation not found. "
            "Please remove and re-add the integration."
        )
        return False

    client_id = implementation.client_id
    client_secret = implementation.client_secret

    if not client_id or not client_secret:
        _LOGGER.error(
            "API credentials are not configured. "
            "Please configure Application Credentials for Nissan NA."
        )
        return False

    # Initialize Smartcar client (uses client-credentials tokens automatically)
    client = SmartcarApiClient(
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
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

        # Create device for each vehicle
        device_registry = dr.async_get(hass)
        for vehicle in vehicles:
            # Get vehicle info for device details
            try:
                info = await client.get_vehicle_info(vehicle.id)
                make = info.get("make", "Nissan")
                model = info.get("model", "Unknown")
                year = info.get("year", "")
            except Exception:
                make = "Nissan"
                model = "Vehicle"
                year = ""

            device_registry.async_get_or_create(
                config_entry_id=config_entry.entry_id,
                identifiers={(DOMAIN, vehicle.vin)},
                manufacturer=make,
                model=f"{year} {model}" if year else model,
                name=f"{year} {make} {model}" if year else f"{make} {model}",
                sw_version=None,
            )
            _LOGGER.info(
                "Created device for vehicle: %s %s %s (VIN: %s)",
                year,
                make,
                model,
                vehicle.vin,
            )
    except Exception as err:
        _LOGGER.error("Failed to get vehicle list: %s", err)
        return False

    # Periodic update interval (default 60 minutes / 1 hour, can be changed in options)
    update_minutes = config_entry.options.get("update_interval", 60)

    async def async_update_all_vehicles(now):
        """Update all vehicles periodically from API and refresh sensor entities."""
        data = hass.data[DOMAIN].get(config_entry.entry_id)
        if not data:
            _LOGGER.warning(
                "Integration data not found for entry %s", config_entry.entry_id
            )
            return
        client = data["client"]

        for vehicle in data["vehicles"]:
            try:
                await client.get_vehicle_status(vehicle.id)
                _LOGGER.debug("Updated vehicle %s from API", vehicle.vin)

                if "sensors" in data and vehicle.id in data["sensors"]:
                    for sensor in data["sensors"][vehicle.id].values():
                        try:
                            await sensor.async_update()
                        except Exception as sensor_err:
                            _LOGGER.debug(
                                "Failed to update sensor %s: %s",
                                getattr(sensor, "_attr_name", "unknown"),
                                sensor_err,
                            )
            except Exception as err:
                _LOGGER.error("Failed to update vehicle %s: %s", vehicle.vin, err)

    # Schedule periodic updates and store unsub function
    update_listener = async_track_time_interval(
        hass, async_update_all_vehicles, timedelta(minutes=update_minutes)
    )
    hass.data[DOMAIN][config_entry.entry_id]["update_listener"] = update_listener

    # Register services
    async def handle_lock_doors(call):
        """Handle lock doors service call."""
        vehicle_id = call.data.get("vehicle_id")
        data = hass.data[DOMAIN].get(config_entry.entry_id)
        if not data:
            _LOGGER.error("Client not found for entry %s", config_entry.entry_id)
            return
        client = data["client"]
        try:
            await client.lock_doors(vehicle_id)
            _LOGGER.info("Locked doors for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to lock doors: %s", err)

    async def handle_unlock_doors(call):
        """Handle unlock doors service call."""
        vehicle_id = call.data.get("vehicle_id")
        data = hass.data[DOMAIN].get(config_entry.entry_id)
        if not data:
            _LOGGER.error("Client not found for entry %s", config_entry.entry_id)
            return
        client = data["client"]
        try:
            await client.unlock_doors(vehicle_id)
            _LOGGER.info("Unlocked doors for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to unlock doors: %s", err)

    async def handle_start_charge(call):
        """Handle start charging service call."""
        vehicle_id = call.data.get("vehicle_id")
        data = hass.data[DOMAIN].get(config_entry.entry_id)
        if not data:
            _LOGGER.error("Client not found for entry %s", config_entry.entry_id)
            return
        client = data["client"]
        try:
            await client.start_charge(vehicle_id)
            _LOGGER.info("Started charging for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to start charging: %s", err)

    async def handle_stop_charge(call):
        """Handle stop charging service call."""
        vehicle_id = call.data.get("vehicle_id")
        data = hass.data[DOMAIN].get(config_entry.entry_id)
        if not data:
            _LOGGER.error("Client not found for entry %s", config_entry.entry_id)
            return
        client = data["client"]
        try:
            await client.stop_charge(vehicle_id)
            _LOGGER.info("Stopped charging for vehicle %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Failed to stop charging: %s", err)

    async def handle_refresh_status(call):
        """Handle refresh status service call."""
        vehicle_id = call.data.get("vehicle_id")
        data = hass.data[DOMAIN].get(config_entry.entry_id)
        if not data:
            _LOGGER.error("Client not found for entry %s", config_entry.entry_id)
            return
        client = data["client"]
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


async def async_unload_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    # Cancel periodic update listener
    data = hass.data[DOMAIN].get(config_entry.entry_id, {})
    if "update_listener" in data:
        data["update_listener"]()

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
