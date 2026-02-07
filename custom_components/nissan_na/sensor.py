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
                    vehicle, status, "batteryLevel", "Battery Level", "%"
                ),
                NissanGenericSensor(
                    vehicle, status, "chargingStatus", "Charging Status", None
                ),
                NissanGenericSensor(vehicle, status, "plugStatus", "Plug Status", None),
                NissanGenericSensor(vehicle, status, "odometer", "Odometer", "km"),
                NissanGenericSensor(vehicle, status, "range", "Range", "km"),
                NissanGenericSensor(
                    vehicle, status, "tirePressure", "Tire Pressure", "kPa"
                ),
                NissanGenericSensor(vehicle, status, "doorStatus", "Door Status", None),
                NissanGenericSensor(
                    vehicle, status, "windowStatus", "Window Status", None
                ),
                NissanGenericSensor(vehicle, status, "lastUpdate", "Last Update", None),
                NissanGenericSensor(
                    vehicle, status, "climateStatus", "Climate Status", None
                ),
                NissanGenericSensor(vehicle, status, "location", "Location", None),
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
    """

    def __init__(self, vehicle, status, key, name, unit):
        self._vehicle = vehicle
        self._status = status
        self._key = key
        self._attr_name = f"{vehicle.nickname or vehicle.vin} {name}"
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
