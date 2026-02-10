import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Webhook signal for data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"


# Sensor definitions with metadata: (key, name, unit, required_permission)
SENSOR_DEFINITIONS = [
    ("batteryLevel", "Battery Level", "%", "read_battery"),
    ("chargingStatus", "Charging Status", None, "read_charge"),
    ("plugStatus", "Plug Status", None, "read_charge"),
    ("odometer", "Odometer", "km", "read_odometer"),
    ("range", "Range", "km", "read_battery"),
    ("tirePressure", "Tire Pressure", "kPa", "read_tires"),
    ("doorStatus", "Door Status", None, "read_security"),
    ("windowStatus", "Window Status", None, "read_security"),
    ("lastUpdate", "Last Update", None, None),  # Always available
    ("climateStatus", "Climate Status", None, "read_climate"),
    ("location", "Location", None, "read_location"),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA sensors for each vehicle and status data point.

    Creates a sensor entity for each relevant vehicle status field
    (battery, charging, odometer, etc.) that the vehicle actually supports.
    Also sets up dynamic entity creation from webhook data.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    
    # Track created sensors per vehicle: {vehicle_id: {key: sensor}}
    if "sensors" not in data:
        data["sensors"] = {}

    for vehicle in vehicles:
        # Get permissions to determine what entities to create
        permissions = None
        try:
            permissions = await client.get_permissions(vehicle.id)
        except Exception:
            # If we can't get permissions, we'll be conservative and create entities
            pass

        # Fetch initial state from API on boot
        _LOGGER.info("Fetching initial state for vehicle %s", vehicle.id)
        try:
            status = await client.get_vehicle_status(vehicle.vin)
            _LOGGER.debug("Initial state for vehicle %s: %s", vehicle.id, status)
        except Exception as err:
            _LOGGER.error(
                "Failed to fetch initial state for vehicle %s: %s",
                vehicle.id,
                err,
            )
            # Use empty status if fetch fails, sensors will update via webhook
            status = {}
        
        # Initialize tracking dict for this vehicle
        if vehicle.id not in data["sensors"]:
            data["sensors"][vehicle.id] = {}

        # Create sensors based on permissions or data availability
        for key, name, unit, required_permission in SENSOR_DEFINITIONS:
            should_create = False

            # Always create if no permission required
            if required_permission is None:
                should_create = True
            # If we have a valid permission list
            elif permissions and len(permissions) > 0:
                # Create if permission is granted
                should_create = required_permission in permissions
            # If permission check failed or returned empty, be conservative
            else:
                # Create if data exists in status
                # (shows vehicle actually has this feature)
                should_create = key in status and status[key] is not None

            if should_create:
                sensor = NissanGenericSensor(
                    hass,
                    vehicle,
                    status,
                    key,
                    name,
                    unit,
                    config_entry.entry_id,
                )
                entities.append(sensor)
                # Track this sensor
                data["sensors"][vehicle.id][key] = sensor

    async_add_entities(entities)
    
    # Fetch fresh initial state for all sensors after adding them
    _LOGGER.info("Refreshing initial state for %d sensors", len(entities))
    for entity in entities:
        try:
            await entity.async_update()
        except Exception as err:
            _LOGGER.warning(
                "Failed to refresh initial state for sensor %s: %s",
                entity._attr_name,
                err,
            )
    
    # Set up webhook handler for dynamic entity creation
    async def handle_webhook_for_new_entities(vehicle_id: str, webhook_data: dict):
        """Create new entities if webhook contains data for keys we don't have sensors for."""
        if vehicle_id not in data["sensors"]:
            _LOGGER.debug("No sensor tracking for vehicle %s", vehicle_id)
            return
            
        existing_keys = set(data["sensors"][vehicle_id].keys())
        webhook_keys = set(webhook_data.keys())
        new_keys = webhook_keys - existing_keys
        
        if not new_keys:
            return  # No new sensors needed
            
        _LOGGER.info(
            "Creating new sensors for vehicle %s with keys: %s",
            vehicle_id,
            new_keys,
        )
        
        # Find the vehicle object
        vehicle = None
        for v in vehicles:
            if v.id == vehicle_id:
                vehicle = v
                break
                
        if not vehicle:
            _LOGGER.error("Vehicle %s not found for dynamic sensor creation", vehicle_id)
            return
            
        # Get current permissions
        permissions = None
        try:
            permissions = await client.get_permissions(vehicle_id)
        except Exception:
            pass
            
        new_entities = []
        # Check each new key against sensor definitions
        for key in new_keys:
            # Find definition for this key
            definition = None
            for def_key, def_name, def_unit, def_perm in SENSOR_DEFINITIONS:
                if def_key == key:
                    definition = (def_key, def_name, def_unit, def_perm)
                    break
                    
            if not definition:
                # Create generic sensor for unknown key
                _LOGGER.debug("Creating generic sensor for unknown key: %s", key)
                # Convert camelCase to Title Case for name
                import re
                name = re.sub(r'([A-Z])', r' \1', key).strip().title()
                definition = (key, name, None, None)
                
            def_key, def_name, def_unit, def_perm = definition
            
            # Check permissions
            should_create = False
            if def_perm is None:
                should_create = True
            elif permissions and len(permissions) > 0:
                should_create = def_perm in permissions
            else:
                # Be conservative - create if data exists
                should_create = key in webhook_data and webhook_data[key] is not None
                
            if should_create:
                sensor = NissanGenericSensor(
                    hass,
                    vehicle,
                    webhook_data,  # Use webhook data as initial status
                    def_key,
                    def_name,
                    def_unit,
                    config_entry.entry_id,
                )
                new_entities.append(sensor)
                data["sensors"][vehicle_id][def_key] = sensor
                _LOGGER.info(
                    "Created new sensor %s for vehicle %s",
                    def_name,
                    vehicle_id,
                )
                
        if new_entities:
            async_add_entities(new_entities)
            
    # Subscribe to webhook signals for each vehicle to create new entities
    # Use async callback that properly schedules the handler
    from homeassistant.core import callback
    
    for vehicle in vehicles:
        @callback
        def handle_webhook_signal(data: dict, vehicle_id: str = vehicle.id):
            """Callback to schedule async handler for webhook data."""
            hass.async_create_task(handle_webhook_for_new_entities(vehicle_id, data))
            
        async_dispatcher_connect(
            hass,
            f"{SIGNAL_WEBHOOK_DATA}_{vehicle.id}",
            handle_webhook_signal,
        )


class NissanGenericSensor(SensorEntity):
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

    def __init__(self, hass, vehicle, status, key, name, unit, entry_id):
        self.hass = hass
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
        self._unsub_dispatcher = None

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
            "Sensor %s subscribed to webhook updates for vehicle %s",
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
            "Webhook data received for %s: %d fields updated",
            self._attr_name,
            len(data) if isinstance(data, dict) else 0,
        )
        _LOGGER.debug(
            "Webhook fields: %s",
            list(data.keys()) if isinstance(data, dict) else "N/A",
        )
        
        # Update the status dict with webhook data
        # Webhook may contain partial updates, so merge with existing status
        if isinstance(data, dict):
            old_value = self._status.get(self._key)
            self._status.update(data)
            new_value = self._status.get(self._key)
            if old_value != new_value:
                _LOGGER.info(
                    "Sensor %s updated via webhook: %s -> %s",
                    self._attr_name,
                    old_value,
                    new_value,
                )
            # Trigger state update
            self.async_write_ha_state()
            _LOGGER.debug("State written for sensor %s", self._attr_name)
        else:
            _LOGGER.warning(
                "Invalid webhook data type for %s: %s",
                self._attr_name,
                type(data),
            )

    @property
    def should_poll(self):
        """Disable polling - we rely on webhooks for updates."""
        return False

    async def async_update(self):
        """Fetch the latest status from the vehicle.
        
        This method can be called manually to refresh sensor state,
        or automatically on boot to ensure fresh initial data.
        """
        try:
            # Get the client from hass.data
            client = self.hass.data[DOMAIN][self._entry_id]["client"]
            # Update the status dictionary with fresh data
            new_status = await client.get_vehicle_status(self._vehicle.id)
            self._status.update(new_status)
            _LOGGER.debug(
                "Successfully updated sensor %s with fresh data",
                self._attr_name,
            )
        except Exception as err:
            _LOGGER.error("Failed to update sensor %s: %s", self._attr_name, err)

    @property
    def native_value(self):
        """
        Return the current value of the sensor.
        Extracts numeric values from nested API responses.
        For location, returns a "lat,lon" string if available.
        """
        value = self._status.get(self._key)
        if not value:
            return None
            
        # Handle location specially - return formatted lat,lon
        if self._key == "location" and isinstance(value, dict):
            lat = value.get("lat")
            lon = value.get("lon")
            return f"{lat},{lon}" if lat and lon else None
        
        # For dict values with numeric data, extract the main value
        # API returns nested structures like: {'distance': 6218.5, 'meta': {...}}
        if isinstance(value, dict):
            # Try common numeric value keys
            for key in ["distance", "value", "amount"]:
                if key in value and isinstance(value[key], (int, float)):
                    return value[key]
            # If no standard key found, return None for dict values
            return None
        
        # Return the value as-is if it's already a scalar (string, number, bool)
        return value

    @property
    def unique_id(self):
        """Return a unique ID for the sensor entity."""
        return f"{self._vehicle.vin}_{self._key}"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement for the sensor, if any."""
        return self._unit

    @property
    def device_info(self):
        """Return device information to link this entity to a device."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
        }
