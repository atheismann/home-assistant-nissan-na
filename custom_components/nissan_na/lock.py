from homeassistant.components.lock import LockEntity

from .const import DOMAIN


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
            entities.append(
                NissanDoorLockEntity(vehicle, client, config_entry.entry_id)
            )

    async_add_entities(entities)


class NissanDoorLockEntity(LockEntity):
    """
    Lock entity representing the vehicle's door lock state.

    Args:
        vehicle: Vehicle object.
        client: NissanNAApiClient instance.
        entry_id: Config entry ID for device linking.
    """

    def __init__(self, vehicle, client, entry_id):
        self._vehicle = vehicle
        self._client = client
        self._entry_id = entry_id
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
        self._is_locked = None

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
            "via_device": (DOMAIN, self._entry_id),
        }
