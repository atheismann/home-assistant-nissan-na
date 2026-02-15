from homeassistant.components.lock import LockEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .device_tracker import SIGNAL_WEBHOOK_DATA


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA lock entities for each vehicle.
    Creates lock entities unless we can confirm the vehicle doesn't support it.
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
            # Only skip if we got a valid, non-empty permission list without control_security
            if (
                permissions
                and len(permissions) > 0
                and "control_security" not in permissions
            ):
                should_create = False
        except Exception:
            # If permission check fails, create the entity (conservative approach)
            pass

        if should_create:
            # Get initial lock status
            try:
                status = await client.get_vehicle_status(vehicle.id)
                lock_status = status.get("lock", {})
            except Exception:
                lock_status = {}
            
            entities.append(
                NissanDoorLockEntity(vehicle, client, config_entry.entry_id, hass, lock_status)
            )

    async_add_entities(entities)


class NissanDoorLockEntity(LockEntity):
    """
    Lock entity representing the vehicle's door lock state.

    Args:
        vehicle: Vehicle object.
        client: NissanNAApiClient instance.
        entry_id: Config entry ID for device linking.
        hass: Home Assistant instance.
        lock_status: Initial lock status dict.
    """

    def __init__(self, vehicle, client, entry_id, hass, lock_status):
        self._vehicle = vehicle
        self._client = client
        self._entry_id = entry_id
        self._hass = hass
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
        self._attr_name = f"{display_name} Door Lock"
        self._attr_unique_id = f"{vehicle.vin}_door_lock"
        # Initialize with actual status from API
        self._is_locked = lock_status.get("is_locked")
        self._subscription = None

    async def async_added_to_hass(self):
        """Subscribe to webhook updates when entity is added to hass."""
        # Subscribe to webhook data updates for this vehicle
        self._subscription = async_dispatcher_connect(
            self._hass,
            f"{SIGNAL_WEBHOOK_DATA}_{self._vehicle.id}",
            self._handle_webhook_data,
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from webhook updates when entity is removed."""
        if self._subscription:
            self._subscription()
            self._subscription = None

    def _handle_webhook_data(self, data: dict):
        """Handle webhook data update from Smartcar.
        
        Args:
            data: Dictionary containing updated vehicle data from webhook
        """
        if isinstance(data, dict) and "lock" in data:
            lock_data = data["lock"]
            if isinstance(lock_data, dict) and "is_locked" in lock_data:
                self._is_locked = lock_data["is_locked"]
                self.async_write_ha_state()

    async def async_lock(self, **kwargs):
        """Lock the vehicle doors via the Nissan API."""
        await self._client.lock_doors(self._vehicle.id)
        self._is_locked = True
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs):
        """Unlock the vehicle doors via the Nissan API."""
        await self._client.unlock_doors(self._vehicle.id)
        self._is_locked = False
        self.async_write_ha_state()

    @property
    def is_locked(self):
        """Return the current lock state."""
        return self._is_locked

    @property
    def device_info(self):
        """Return device information to link this entity to a device."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
        }
