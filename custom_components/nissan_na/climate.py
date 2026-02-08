from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA climate entities for each vehicle.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = [NissanClimateEntity(vehicle, client, config_entry.entry_id) for vehicle in vehicles]
    async_add_entities(entities)


class NissanClimateEntity(ClimateEntity):
    """
    Climate entity representing the vehicle's climate control.

    This entity uses direct Smartcar API calls for climate control since
    the Python SDK does not expose these endpoints. Supports starting and
    stopping the vehicle's HVAC system.

    Note:
        - HEAT, COOL, and AUTO modes all start the climate system
        - Only OFF mode stops the climate system
        - Temperature control is not supported by Smartcar API

    Args:
        vehicle: Vehicle object.
        client: NissanNAApiClient instance.
    """

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

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
        self._attr_name = f"{display_name} Climate"
        self._attr_unique_id = f"{vehicle.vin}_climate"
        self._hvac_mode = HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """
        Set the HVAC mode for the vehicle's climate control.
        Starts or stops climate based on the selected mode.
        """
        if hvac_mode == HVACMode.OFF:
            await self._client.stop_climate(self._vehicle.id)
        else:
            await self._client.start_climate(self._vehicle.id)
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return self._hvac_mode

    @property
    def device_info(self):
        """Return device information to link this entity to a device."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
            "via_device": (DOMAIN, self._entry_id),
        }
