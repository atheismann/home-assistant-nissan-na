from homeassistant.components.lock import LockEntity
from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA lock entities for each vehicle.
    """
    client = hass.data[DOMAIN][config_entry.entry_id]
    vehicles = await client.get_vehicle_list()
    entities = [NissanDoorLockEntity(vehicle, client) for vehicle in vehicles]
    async_add_entities(entities)


class NissanDoorLockEntity(LockEntity):
    """
    Lock entity representing the vehicle's door lock state.

    Args:
        vehicle: Vehicle object.
        client: NissanNAApiClient instance.
    """

    def __init__(self, vehicle, client):
        self._vehicle = vehicle
        self._client = client
        self._attr_name = f"{vehicle.nickname or vehicle.vin} Door Lock"
        self._attr_unique_id = f"{vehicle.vin}_door_lock"
        self._is_locked = None

    async def async_lock(self, **kwargs):
        """Lock the vehicle doors via the Nissan API."""
        await self._client.lock_doors(self._vehicle.vin)
        self._is_locked = True
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs):
        """Unlock the vehicle doors via the Nissan API."""
        await self._client.unlock_doors(self._vehicle.vin)
        self._is_locked = False
        self.async_write_ha_state()

    @property
    def is_locked(self):
        """Return the current lock state."""
        return self._is_locked
