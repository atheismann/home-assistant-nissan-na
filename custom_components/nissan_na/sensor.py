from homeassistant.helpers.entity import Entity

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA sensors for each vehicle and status data point.

    Creates a sensor entity for each relevant vehicle status field
    (battery, charging, odometer, etc.).
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    for vehicle in vehicles:
        status = await client.get_vehicle_status(vehicle.vin)
        # Add sensors for all relevant data points
        entities.extend(
            [
                NissanGenericSensor(
                    vehicle,
                    status,
                    "batteryLevel",
                    "Battery Level",
                    "%",
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle,
                    status,
                    "chargingStatus",
                    "Charging Status",
                    None,
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle,
                    status,
                    "plugStatus",
                    "Plug Status",
                    None,
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle, status, "odometer", "Odometer", "km", config_entry.entry_id
                ),
                NissanGenericSensor(
                    vehicle, status, "range", "Range", "km", config_entry.entry_id
                ),
                NissanGenericSensor(
                    vehicle,
                    status,
                    "tirePressure",
                    "Tire Pressure",
                    "kPa",
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle,
                    status,
                    "doorStatus",
                    "Door Status",
                    None,
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle,
                    status,
                    "windowStatus",
                    "Window Status",
                    None,
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle,
                    status,
                    "lastUpdate",
                    "Last Update",
                    None,
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle,
                    status,
                    "climateStatus",
                    "Climate Status",
                    None,
                    config_entry.entry_id,
                ),
                NissanGenericSensor(
                    vehicle, status, "location", "Location", None, config_entry.entry_id
                ),
            ]
        )
    async_add_entities(entities)


class NissanGenericSensor(Entity):
    """
    Generic sensor for a Nissan vehicle status data point.

    Args:
        vehicle: Vehicle object.
        status: Status dictionary for the vehicle.
        key: Key in the status dict to expose as a sensor.
        name: Human-readable name for the sensor.
        unit: Unit of measurement (if any).
        entry_id: Config entry ID for device linking.
    """

    def __init__(self, vehicle, status, key, name, unit, entry_id):
        self._vehicle = vehicle
        self._status = status
        self._key = key
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
        self._attr_name = f"{display_name} {name}"
        self._unit = unit

    @property
    def state(self):
        """
        Return the current value of the sensor.
        For location, returns a "lat,lon" string if available.
        """
        value = self._status.get(self._key)
        if self._key == "location" and value:
            lat = value.get("lat")
            lon = value.get("lon")
            return f"{lat},{lon}" if lat and lon else None
        return value

    @property
    def unique_id(self):
        """Return a unique ID for the sensor entity."""
        return f"{self._vehicle.vin}_{self._key}"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor, if any."""
        return self._unit

    @property
    def device_info(self):
        """Return device information to link this entity to a device."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
            "via_device": (DOMAIN, self._entry_id),
        }
