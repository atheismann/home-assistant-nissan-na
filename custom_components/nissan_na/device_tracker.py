from homeassistant.components.device_tracker import SourceType, TrackerEntity

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA device tracker entities for each vehicle.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    for vehicle in vehicles:
        status = await client.get_vehicle_status(vehicle.vin)
        entities.append(NissanVehicleTracker(vehicle, status))
    async_add_entities(entities)


class NissanVehicleTracker(TrackerEntity):
    """
    Device tracker entity for the vehicle's GPS location.

    Args:
        vehicle: Vehicle object.
        status: Status dictionary for the vehicle.
    """

    def __init__(self, vehicle, status):
        self._vehicle = vehicle
        self._status = status
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
