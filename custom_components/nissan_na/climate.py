from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA climate entities for each vehicle.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = [NissanClimateEntity(vehicle, client) for vehicle in vehicles]
    async_add_entities(entities)


class NissanClimateEntity(ClimateEntity):
    """
    Climate entity representing the vehicle's climate control.

    Args:
        vehicle: Vehicle object.
        client: NissanNAApiClient instance.
    """

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]

    def __init__(self, vehicle, client):
        self._vehicle = vehicle
        self._client = client
        self._attr_name = f"{vehicle.nickname or vehicle.vin} Climate"
        self._attr_unique_id = f"{vehicle.vin}_climate"
        self._hvac_mode = HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """
        Set the HVAC mode for the vehicle's climate control.
        Starts or stops climate based on the selected mode.
        """
        if hvac_mode == HVACMode.OFF:
            await self._client.stop_climate(self._vehicle.vin)
        else:
            await self._client.start_climate(self._vehicle.vin)
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return self._hvac_mode
