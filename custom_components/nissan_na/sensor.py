import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Webhook signal for data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"


# Sensor definitions mapping API keys to sensor info
# Format: (signal_id, field_name, sensor_name, unit, required_permission, icon, device_class)
# signal_id: Signal ID from Smartcar API (e.g., 'battery.percentRemaining')
# field_name: Field within that API response object to extract
# sensor_name: Human-readable sensor name
# unit: Unit of measurement (None if no unit)
# required_permission: OAuth permission required (fallback if signals API unavailable)
# icon: MDI icon name (None to use device_class icon)
# device_class: Home Assistant device class (None for custom entity)
SENSOR_DEFINITIONS = [
    # Battery sensors (from battery API response)
    ("battery.percentRemaining", "percentRemaining", "Battery", "%", "read_battery", None, SensorDeviceClass.BATTERY),
    ("battery.range", "range", "Range", "km", "read_battery", "mdi:battery-high", None),
    ("battery.capacityKwh", "capacityKwh", "Battery Capacity", "kWh", "read_battery", None, SensorDeviceClass.ENERGY_STORAGE),
    ("battery.lowBatteryPercentRemaining", "lowBatteryPercentRemaining", "Low Voltage Battery", "%", "read_battery", None, SensorDeviceClass.BATTERY),
    
    # Charging sensors (from charge API response)
    ("charge.isPluggedIn", "isPluggedIn", "Charging Cable Plugged In", None, "read_charge", "mdi:power-plug", None),
    ("charge.state", "state", "Charging Status", None, "read_charge", "mdi:power-plug", None),
    ("charge.voltage", "voltage", "Charging Voltage", "V", "read_charge", "mdi:lightning-bolt", SensorDeviceClass.VOLTAGE),
    ("charge.amperage", "amperage", "Charging Current", "A", "read_charge", "mdi:current-ac", SensorDeviceClass.CURRENT),
    ("charge.wattage", "wattage", "Charging Power", "kW", "read_charge", "mdi:lightning-bolt-circle", SensorDeviceClass.POWER),
    ("charge.timeToComplete", "timeToComplete", "Charging Time Remaining", "min", "read_charge", "mdi:battery-clock", None),
    ("charge.amperageMax", "amperageMax", "Charging Current Max", "A", "read_charge", "mdi:current-ac", SensorDeviceClass.CURRENT),
    
    # Odometer sensor
    ("odometer.distance", "distance", "Odometer", "km", "read_odometer", "mdi:speedometer", None),
    
    # Fuel sensors
    ("fuel.amountRemaining", "amountRemaining", "Fuel", "L", "read_fuel", "mdi:gas-cylinder", SensorDeviceClass.VOLUME),
    ("fuel.percentRemaining", "percentRemaining", "Fuel Level", "%", "read_fuel", "mdi:gas-cylinder", None),
    ("fuel.range", "range", "Fuel Range", "km", "read_fuel", "mdi:gas-cylinder", None),
    
    # Tire pressure sensors
    ("tires.frontLeft.pressure", "pressure", "Tire Pressure Front Left", "psi", "read_tires", "mdi:tire", SensorDeviceClass.PRESSURE),
    ("tires.frontRight.pressure", "pressure", "Tire Pressure Front Right", "psi", "read_tires", "mdi:tire", SensorDeviceClass.PRESSURE),
    ("tires.backLeft.pressure", "pressure", "Tire Pressure Back Left", "psi", "read_tires", "mdi:tire", SensorDeviceClass.PRESSURE),
    ("tires.backRight.pressure", "pressure", "Tire Pressure Back Right", "psi", "read_tires", "mdi:tire", SensorDeviceClass.PRESSURE),
    
    # Vehicle status sensors
    ("transmission.gear", "gear", "Gear State", None, "read_drivetrain", "mdi:car-shift-pattern", None),
    ("engine.oilLifeRemaining", "oilLifeRemaining", "Engine Oil Life", "%", "read_engine", "mdi:oil", None),
    ("connectivity.softwareVersion", "softwareVersion", "Firmware Version", None, None, "mdi:chip", None),
    
    # Location sensors (from location API response)
    ("location.latitude", "latitude", "Location Latitude", "°", "read_location", None, SensorDeviceClass.LATITUDE),
    ("location.longitude", "longitude", "longitude", "°", "read_location", None, SensorDeviceClass.LONGITUDE),
    
    # Connectivity sensors (webhook only)
    ("connectivity.isOnline", "isOnline", "Online", None, None, "mdi:wifi", None),
    ("connectivity.isAsleep", "isAsleep", "Asleep", None, None, "mdi:sleep", None),
    ("connectivity.isDigitalKeyPaired", "isDigitalKeyPaired", "Digital Key Paired", None, None, "mdi:key", None),
    
    # Surveillance sensors (webhook only)
    ("surveillance.isEnabled", "isEnabled", "Surveillance Enabled", None, None, "mdi:cctv", None),
    
    # Traction battery sensors (webhook only)
    ("tractionBattery.isHeaterActive", "isHeaterActive", "Battery Heater Active", None, None, "mdi:fire", None),
    
    # Charge limit sensor
    ("charge.limit", "limit", "Charge Limit", "%", "read_charge", None, None),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up Nissan NA sensors for each vehicle and status data point.

    Creates a sensor entity for each signal supported by the vehicle,
    using the Smartcar signals API to validate availability.
    Also sets up dynamic entity creation from webhook data.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    
    # Track created sensors per vehicle: {vehicle_id: {signal_id: sensor}}
    if "sensors" not in data:
        data["sensors"] = {}

    for vehicle in vehicles:
        _LOGGER.info("Setting up sensors for vehicle %s", vehicle.id)
        
        # Get available signals from Smartcar API
        available_signals = set()
        try:
            signals = await client.get_vehicle_signals(vehicle.id)
            available_signals = set(signals)
            _LOGGER.debug(
                "Vehicle %s supports %d signals: %s",
                vehicle.id,
                len(available_signals),
                signals,
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed to get vehicle signals for %s, will use permission fallback: %s",
                vehicle.id,
                err,
            )
            # Fall back to permission-based if signals API fails
            try:
                permissions = await client.get_permissions(vehicle.id)
                _LOGGER.debug("Vehicle %s permissions: %s", vehicle.id, permissions)
            except Exception:
                permissions = []
        
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

        # Create sensors based on available signals
        created_sensors = set()
        for definition in SENSOR_DEFINITIONS:
            signal_id = definition[0]
            field_name = definition[1]
            name = definition[2]
            unit = definition[3]
            required_permission = definition[4]
            icon = definition[5]
            device_class = definition[6]
            
            # Avoid duplicate sensors
            sensor_unique_id = f"{signal_id}_{field_name}"
            if sensor_unique_id in created_sensors:
                continue
            created_sensors.add(sensor_unique_id)
            
            should_create = False

            # Check if signal is available
            if available_signals:
                # If we have signals, use them as source of truth
                should_create = signal_id in available_signals
                if not should_create:
                    _LOGGER.debug(
                        "Signal %s not available for vehicle %s",
                        signal_id,
                        vehicle.id,
                    )
            elif required_permission:
                # Fall back to permission checking if signals API failed
                try:
                    permissions = await client.get_permissions(vehicle.id)
                    should_create = (
                        permissions and required_permission in permissions
                    )
                except Exception:
                    # If we can't check permissions, check if data exists
                    api_key = signal_id.split(".")[0]
                    should_create = api_key in status and status[api_key] is not None
            else:
                # No permission required, but signal might be webhook-only
                # Create if signals API succeeded (meaning we got a full list)
                # Or create if data exists in status
                if available_signals:
                    # Signals API worked, only create if signal is in the list
                    should_create = signal_id in available_signals
                else:
                    # Signals API didn't work, try data check
                    api_key = signal_id.split(".")[0]
                    should_create = api_key in status and status[api_key] is not None

            if should_create:
                _LOGGER.info(
                    "Creating sensor %s for vehicle %s (signal: %s)",
                    name,
                    vehicle.id,
                    signal_id,
                )
                sensor = NissanGenericSensor(
                    hass,
                    vehicle,
                    status,
                    signal_id,
                    field_name,
                    name,
                    unit,
                    icon,
                    device_class,
                    config_entry.entry_id,
                )
                entities.append(sensor)
                # Track this sensor by signal_id
                data["sensors"][vehicle.id][signal_id] = sensor

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
    # With signals API validation, all supported entities should be created at setup,
    # but this handles edge cases of new signals becoming available
    async def handle_webhook_for_new_entities(vehicle_id: str, webhook_data: dict):
        """Log webhook data for diagnostics (dynamic creation handled at setup)."""
        if vehicle_id not in data["sensors"]:
            _LOGGER.debug("No sensor tracking for vehicle %s", vehicle_id)
            return
        
        # With signals API, all supported sensors are created upfront
        # Webhook handler now just passes data to existing sensors
        _LOGGER.debug(
            "Webhook data for vehicle %s: %s fields updated",
            vehicle_id,
            len(webhook_data) if isinstance(webhook_data, dict) else 0,
        )
    
    # Subscribe to webhook signals for each vehicle
    # Use async callback that properly schedules the handler
    from homeassistant.core import callback
    
    for vehicle in vehicles:
        @callback
        def handle_webhook_signal(webhook_data: dict, vehicle_id: str = vehicle.id):
            """Callback to handle webhook data updates."""
            hass.async_create_task(handle_webhook_for_new_entities(vehicle_id, webhook_data))
            
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
        signal_id: Signal ID from Smartcar (e.g., 'battery.percentRemaining').
        field_name: Field within the API response to extract (e.g., 'percentRemaining').
        name: Human-readable name for the sensor.
        unit: Unit of measurement (if any).
        icon: MDI icon name (None to use device_class icon).
        device_class: Home Assistant sensor device class.
        entry_id: Config entry ID for device linking.
    """

    def __init__(self, hass, vehicle, status, signal_id, field_name, name, unit, icon, device_class, entry_id):
        self.hass = hass
        self._vehicle = vehicle
        self._status = status
        self._signal_id = signal_id  # Smartcar signal ID (e.g., 'battery.percentRemaining')
        self._api_key = signal_id.split(".")[0]  # Extract API key (e.g., 'battery')
        self._field_name = field_name
        self._entry_id = entry_id
        self._icon = icon
        self._device_class = device_class
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
            old_value = self.native_value
            # Deep merge webhook data into status
            for key, value in data.items():
                if key in self._status and isinstance(self._status[key], dict) and isinstance(value, dict):
                    # Merge nested dicts (e.g., {"battery": {"range": 300}} merges into existing battery)
                    self._status[key].update(value)
                else:
                    # Replace or add the value
                    self._status[key] = value
            new_value = self.native_value
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
        Extracts the specified field from the API response object.
        """
        # Get the API response object (e.g., battery, charge, odometer, location)
        api_response = self._status.get(self._api_key)
        
        if not api_response:
            _LOGGER.debug(
                "No data for sensor %s (api_key=%s)",
                self._attr_name,
                self._api_key,
            )
            return None
        
        # If it's a dict (API response object), extract the field
        if isinstance(api_response, dict):
            value = api_response.get(self._field_name)
            _LOGGER.debug(
                "Sensor %s: extracted %s from %s = %s",
                self._attr_name,
                self._field_name,
                self._api_key,
                value,
            )
            return value
        
        # If it's a namedtuple or object, try to get the attribute
        try:
            value = getattr(api_response, self._field_name, None)
            _LOGGER.debug(
                "Sensor %s: extracted attribute %s from %s = %s",
                self._attr_name,
                self._field_name,
                self._api_key,
                value,
            )
            return value
        except AttributeError:
            _LOGGER.debug(
                "Attribute %s not found on %s for sensor %s",
                self._field_name,
                self._api_key,
                self._attr_name,
            )
            return None

    @property
    def unique_id(self):
        """Return a unique ID for the sensor entity."""
        return f"{self._vehicle.vin}_{self._signal_id}"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement for the sensor, if any."""
        return self._unit

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def device_info(self):
        """Return device information to link this entity to a device."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
        }
