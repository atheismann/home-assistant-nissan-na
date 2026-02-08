"""Home Assistant custom integration for Nissan North America vehicles.

Uses Smartcar API for vehicle integration.
"""

import logging
from datetime import timedelta

from homeassistant.components import webhook as ha_webhook
from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow, device_registry as dr
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

    # Validate OAuth credentials are present
    if not client_id or not client_secret:
        _LOGGER.error(
            "OAuth credentials are not configured. "
            "Please configure Application Credentials for Nissan NA "
            "in Home Assistant settings, then remove and re-add this "
            "integration."
        )
        return False

    # Initialize Smartcar client
    client = SmartcarApiClient(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    async def refresh_and_update_token():
        """Refresh access token and update config entry."""
        try:
            _LOGGER.debug("Attempting to refresh access token")
            new_tokens = await client.refresh_access_token()

            # Update config entry with new tokens
            new_data = {**config_entry.data}

            # Update token dict if it exists, otherwise update direct keys
            if "token" in new_data:
                new_data["token"] = {
                    **new_data["token"],
                    "access_token": new_tokens["access_token"],
                    "refresh_token": new_tokens["refresh_token"],
                }
            else:
                new_data[CONF_ACCESS_TOKEN] = new_tokens["access_token"]
                new_data[CONF_REFRESH_TOKEN] = new_tokens["refresh_token"]

            hass.config_entries.async_update_entry(config_entry, data=new_data)
            _LOGGER.info("Successfully refreshed and saved access token")
            return True
        except Exception as refresh_err:
            _LOGGER.error("Failed to refresh token: %s", refresh_err)
            return False

    # Store client in hass data
    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": client,
        "vehicles": [],
        "refresh_token_func": refresh_and_update_token,
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
                year, make, model, vehicle.vin
            )
    except Exception as err:
        error_message = str(err)
        _LOGGER.error("Failed to get vehicle list: %s", error_message)

        # Check if it's an authentication error
        if (
            "AUTHENTICATION" in error_message
            or "authentication" in error_message.lower()
        ):
            _LOGGER.warning("Authentication error detected - attempting token refresh")

            # Try to refresh the token first
            if await refresh_and_update_token():
                # Retry getting vehicle list with new token
                try:
                    vehicles = await client.get_vehicle_list()
                    hass.data[DOMAIN][config_entry.entry_id]["vehicles"] = vehicles
                    _LOGGER.info(
                        "Successfully retrieved %d vehicle(s) after token refresh",
                        len(vehicles),
                    )
                except Exception as retry_err:
                    _LOGGER.error("Still failed after token refresh: %s", retry_err)
                    # Token refresh didn't help, trigger reauth
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
            else:
                # Token refresh failed, trigger reauth
                _LOGGER.warning("Token refresh failed - triggering reauth flow")
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
        else:
            return False

    # Periodic update interval (default 15 minutes, can be changed in options)
    update_minutes = config_entry.options.get("update_interval", 15)

    async def async_update_all_vehicles(now):
        """Update all vehicles periodically."""
        try:
            # Get client from hass.data
            data = hass.data[DOMAIN].get(config_entry.entry_id)
            if not data:
                _LOGGER.warning("Client not found for entry %s", config_entry.entry_id)
                return
            client = data["client"]

            # Refresh access token and save to config entry
            refresh_func = data.get("refresh_token_func")
            if refresh_func:
                await refresh_func()

            # Update vehicle data
            vehicles = data["vehicles"]
            for vehicle in vehicles:
                try:
                    await client.get_vehicle_status(vehicle.id)
                    _LOGGER.debug("Updated vehicle %s", vehicle.vin)
                except Exception as err:
                    error_msg = str(err)
                    _LOGGER.error(
                        "Failed to update vehicle %s: %s", vehicle.vin, error_msg
                    )

                    # Check for authentication errors
                    if (
                        "AUTHENTICATION" in error_msg
                        or "authentication" in error_msg.lower()
                    ):
                        _LOGGER.warning(
                            "Authentication error during update - trying token refresh"
                        )

                        # Try to refresh token
                        refresh_func = data.get("refresh_token_func")
                        if refresh_func and await refresh_func():
                            _LOGGER.info(
                                "Token refreshed successfully, continuing updates"
                            )
                            # Don't return, continue with other vehicles
                        else:
                            # Refresh failed, trigger reauth
                            _LOGGER.warning("Token refresh failed - triggering reauth")
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
                            return
        except Exception as err:
            error_msg = str(err)
            _LOGGER.error("Failed to refresh token: %s", error_msg)

            # Check for authentication errors during the main refresh attempt
            if "AUTHENTICATION" in error_msg or "authentication" in error_msg.lower():
                _LOGGER.warning(
                    "Authentication error during periodic refresh - triggering reauth"
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
