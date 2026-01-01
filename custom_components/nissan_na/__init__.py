from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
"""
Home Assistant custom integration for Nissan North America vehicles.
"""

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, PLATFORMS
from .nissan_api import NissanNAApiClient


async def async_setup_entry(hass, config_entry):
    """Set up Nissan NA from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    client = NissanNAApiClient(username, password)
    await client.authenticate()
    hass.data[DOMAIN][config_entry.entry_id] = client

    # Periodic update interval (user-configurable, default 15 minutes, can be changed in options)
    update_minutes = config_entry.options.get("update_interval") if config_entry.options else config_entry.data.get("update_interval", 15)
    async def async_update_all_vehicles(now):
        vehicles = await client.get_vehicle_list()
        for vehicle in vehicles:
            await client.refresh_vehicle_status(vehicle.vin)

    async_track_time_interval(
        hass,
        async_update_all_vehicles,
        timedelta(minutes=update_minutes)
    )

    # Register services
    async def handle_service(call):
        vin = call.data.get("vin")
        service = call.service
            if service == "lock_doors":
            await client.lock_doors(vin)
        elif service == "unlock_doors":
            await client.unlock_doors(vin)
            elif service == "start_engine":
                await client.start_engine(vin)
            elif service == "stop_engine":
                await client.stop_engine(vin)
        elif service == "find_vehicle":
            await client.find_vehicle(vin)
        elif service == "refresh_vehicle_status":
            await client.refresh_vehicle_status(vin)

    for service in [
        "lock_doors",
        "unlock_doors",
            "start_engine",
            "stop_engine",
        "find_vehicle",
        "refresh_vehicle_status",
    ]:
        hass.services.async_register(
            DOMAIN, service, handle_service
        )

    # Set up platforms (sensor, lock, climate, device_tracker)
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )
    return True
