import logging

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Webhook signal for data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA device tracker entities for each vehicle.
    Creates tracker entities unless we can confirm the vehicle doesn't support it.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []

    for vehicle in vehicles:
        # Default to creating the entity unless we have evidence it's not supported
        should_create = True

        try:
            permissions = await client.get_permissions(vehicle.id)
            # Only skip if we got a valid, non-empty permission list without read_location
            if (
                permissions
                and len(permissions) > 0
                and "read_location" not in permissions
            ):
                should_create = False
        except Exception:
            # If permission check fails, create the entity (conservative approach)
            pass

        if should_create:
            status = await client.get_vehicle_status(vehicle.vin)
            entities.append(
                NissanVehicleTracker(hass, vehicle, status, config_entry.entry_id)
            )

    async_add_entities(entities)


class NissanVehicleTracker(TrackerEntity):
    """
    Device tracker entity for the vehicle's GPS location.

    Args:
        hass: The Home Assistant instance.
        vehicle: Vehicle object.
        status: Status dictionary for the vehicle.
        entry_id: Config entry ID for device linking.
    """

    def __init__(self, hass, vehicle, status, entry_id):
        self.hass = hass
        self._vehicle = vehicle
        self._status = status
        self._entry_id = entry_id
        self._unsub_dispatcher = None
        nickname = getattr(vehicle, "nickname", None)
        if nickname:
            display_name = nickname
        else:
            # Use year/make/model if available, otherwise fall back to VIN
            year = getattr(vehicle, "year", "")
            make = getattr(vehicle, "make", "")
            model = getattr(vehicle, "model", "")
            if year and make and model:
                display_name = f"{year} {make} {model}"
            else:
                display_name = vehicle.vin
        self._attr_name = f"{display_name} Location"
        self._attr_unique_id = f"{vehicle.vin}_location"

    async def async_added_to_hass(self):
        """Subscribe to webhook updates when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Subscribe to webhook data updates for this vehicle
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_WEBHOOK_DATA}_{self._vehicle.id}",
            self._handle_webhook_data,
        )
        _LOGGER.debug(
            "Device tracker %s subscribed to webhook updates for vehicle %s",
            self._attr_name,
            self._vehicle.id,
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from updates when entity is removed."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
        await super().async_will_remove_from_hass()

    def _handle_webhook_data(self, data: dict):
        """Handle webhook data update from Smartcar.
        
        Args:
            data: Dictionary containing updated vehicle data from webhook
        """
        _LOGGER.debug(
            "Webhook data received for device tracker %s: %s",
            self._attr_name,
            data,
        )
        
        # Update the status dict with webhook data
        if isinstance(data, dict):
            self._status.update(data)
            # Trigger state update
            self.async_write_ha_state()

    @property
    def should_poll(self):
        """Disable polling - we rely on webhooks for updates."""
        return False

    async def async_update(self):
        """Fetch the latest location from the vehicle.
        
        This method can be called manually to refresh device tracker state,
        or automatically on boot to ensure fresh initial data.
        """
        try:
            # Get the client from hass.data
            client = self.hass.data[DOMAIN][self._entry_id]["client"]
            # Update the status dictionary with fresh data
            new_status = await client.get_vehicle_status(self._vehicle.id)
            self._status.update(new_status)
            _LOGGER.debug(
                "Successfully updated device tracker %s with fresh data",
                self._attr_name,
            )
        except Exception as err:
            _LOGGER.error("Failed to update device tracker %s: %s", self._attr_name, err)

    @property
    def latitude(self):
        """Return the latitude of the vehicle's last known location."""
        loc = self._status.get("location")
        return loc.get("lat") if loc else None

    @property
    def longitude(self):
        """Return the longitude of the vehicle's last known location."""
        loc = self._status.get("location")
        return loc.get("lon") if loc else None

    @property
    def source_type(self):
        """Return the source type (GPS)."""
        return SourceType.GPS

    @property
    def device_info(self):
        """Return device information to link this entity to a device."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
        }
