import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import CONF_UNIT_SYSTEM, DOMAIN, UNIT_SYSTEM_METRIC
from .unit_conversion import convert_value, get_display_unit

_LOGGER = logging.getLogger(__name__)

# Webhook signal for data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"


# Mapping from Smartcar v3 API signal codes (kebab-case) to sensor definition IDs (dot notation)
# This enables matching available signals from the API to sensor definitions
# Based on official Smartcar API schema: https://smartcar.com/docs/api-reference/signals/schema
API_SIGNAL_TO_DEFINITION_MAP = {
    # Fuel/ICE signals (InternalCombustionEngine)
    "internalcombustionengine-fuellevel": "fuel.percentRemaining",
    "internalcombustionengine-amountremaining": "fuel.amountRemaining",
    "internalcombustionengine-range": "fuel.range",
    "internalcombustionengine-oillife": "engine.oilLifeRemaining",

    # Odometer signals
    "odometer-traveleddistance": "odometer.distance",

    # Tire signals — wheel-tires gives per-tire data; diagnostics-tirepressure is a warning signal
    "wheel-tires": "tires.frontLeft",        # enables all four tire sensors
    "diagnostics-tirepressure": "tires.frontLeft",  # also enables tire sensors (same target)

    # Location signals
    "location-preciselocation": "location.latitude",  # enables both lat and lon sensors

    # Charge / EV signals
    "charge-timetocomplete": "charge.timeToComplete",
    "charge-voltage": "charge.voltage",
    "charge-wattage": "charge.wattage",
    "charge-amperagemax": "charge.amperageMax",
    "charge-ischarging": "charge.isCharging",
    "charge-ischargingcableconnected": "charge.isPluggedIn",
    "charge-detailedchargingstatus": "charge.state",
    "charge-chargetimers": None,

    # TractionBattery / EV signals
    "tractionbattery-stateofcharge": "battery.percentRemaining",
    "tractionbattery-range": "battery.range",
    "tractionbattery-nominalcapacity": "battery.capacityKwh",
    "tractionbattery-isheateractive": None,  # binary sensor — handled in binary_sensor.py

    # HVAC signals
    "hvac-cabintargettemperature": "hvac.targetTemperature",
    "hvac-iscabinhvacactive": None,  # binary sensor

    # Connectivity/Software signals
    "connectivitysoftware-currentfirmwareversion": "connectivity.softwareVersion",
    "connectivitystatus-isonline": None,   # binary sensor
    "connectivitystatus-isasleep": None,   # binary sensor
    "connectivitystatus-isdigitalkeypaired": None,  # binary sensor

    # Transmission
    "transmission-gearstate": "transmission.gear",

    # Surveillance
    "surveillance-isenabled": None,  # binary sensor

    # Closure / security signals — handled primarily in binary_sensor.py
    "closure-islocked": "security.isLocked",
    "closure-doors": None,       # binary sensor
    "closure-reartrunk": None,   # binary sensor
    "closure-fronttrunk": None,  # binary sensor
    "closure-enginecover": None, # binary sensor

    # Diagnostics — handled primarily in binary_sensor.py
    "diagnostics-mil": None,
    "diagnostics-abs": None,
    "diagnostics-brakefluid": None,
    "diagnostics-airbag": None,
    "diagnostics-oilpressure": None,

    # VehicleIdentification (not a sensor)
    "vehicleidentification-vin": None,
    "vehicleidentification-nickname": None,
}


def map_available_signals(api_signal_codes: list) -> set:
    """
    Map Smartcar capability codes (kebab-case) to sensor definition IDs (dot-notation).

    A capability code can map to a prefix that matches multiple definitions — e.g.
    'wheel-tires' → 'tires.frontLeft' enables all four tires.* sensors.

    Args:
        api_signal_codes: Capability codes from the v3 signals or compatibility API.

    Returns:
        set: Sensor definition signal_ids that should be created.
    """
    mapped_signals = set()

    for code in api_signal_codes:
        if "." in code:
            # Already in dot-notation — direct match
            mapped_signals.add(code)
            continue

        definition_prefix = API_SIGNAL_TO_DEFINITION_MAP.get(code.lower())
        if not definition_prefix:
            _LOGGER.debug("No sensor definition mapping for signal: %s", code)
            continue

        # Add every sensor definition whose signal_id equals or starts with this prefix
        for defn in SENSOR_DEFINITIONS:
            sid = defn[0]
            if sid == definition_prefix or sid.startswith(definition_prefix + "."):
                mapped_signals.add(sid)

    return mapped_signals


# Sensor definitions mapping API keys to sensor info
# Format: (signal_id, field_name, sensor_name, unit, required_permission, icon, device_class)
# signal_id: Signal ID from sensor definitions (e.g., 'battery.percentRemaining')
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
    ("charge.wattage", "wattage", "Charging Power", "W", "read_charge", "mdi:lightning-bolt-circle", SensorDeviceClass.POWER),
    ("charge.timeToComplete", "timeToComplete", "Charging Time Remaining", "min", "read_charge", "mdi:battery-clock", None),
    ("charge.amperageMax", "amperageMax", "Charging Current Max", "A", "read_charge", "mdi:current-ac", SensorDeviceClass.CURRENT),
    ("charge.limit", "limit", "Charge Limit", "%", "read_charge", None, None),
    
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
    ("location.latitude", "latitude", "Location Latitude", "°", "read_location", "mdi:map-marker", None),
    ("location.longitude", "longitude", "longitude", "°", "read_location", "mdi:map-marker", None),
    
    # Connectivity sensors (webhook only)
    ("connectivity.isOnline", "isOnline", "Online", None, None, "mdi:wifi", None),
    ("connectivity.isAsleep", "isAsleep", "Asleep", None, None, "mdi:sleep", None),
    ("connectivity.isDigitalKeyPaired", "isDigitalKeyPaired", "Digital Key Paired", None, None, "mdi:key", None),
    
    # Surveillance sensors (webhook only)
    ("surveillance.isEnabled", "isEnabled", "Surveillance Enabled", None, None, "mdi:cctv", None),
    
    # Traction battery sensors (EV only)
    ("tractionBattery.isHeaterActive", "isHeaterActive", "Battery Heater Active", None, None, "mdi:fire", None),
]


async def async_setup_entry(hass, config_entry, async_add_entities, rebuild_mode=False):
    """
    Set up Nissan NA sensors for each vehicle and status data point.

    Creates a sensor entity for each signal supported by the vehicle,
    using the Smartcar signals API to validate availability.
    Also sets up dynamic entity creation from webhook data.
    
    Args:
        rebuild_mode: If True, validates and removes unsupported sensors.
                     If False (default), only adds new sensors without removing existing.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    
    # Initialize caches
    if "sensors" not in data:
        data["sensors"] = {}
    if "vehicle_signals" not in data:
        data["vehicle_signals"] = {}

    for vehicle in vehicles:
        _LOGGER.info("Setting up sensors for vehicle %s", vehicle.id)
        
        # Get available signals from Smartcar API (cached)
        if vehicle.id not in data["vehicle_signals"]:
            try:
                signals = await client.get_vehicle_signals(vehicle.id, vehicle=vehicle)
                data["vehicle_signals"][vehicle.id] = signals
                _LOGGER.debug("Fetched signals for vehicle %s: %d codes", vehicle.id, len(signals))
            except Exception as err:
                _LOGGER.error(
                    "Failed to get vehicle signals for %s, skipping sensor setup: %s",
                    vehicle.id,
                    err,
                )
                # Skip this vehicle if we can't get signals
                continue
        else:
            signals = data["vehicle_signals"][vehicle.id]
            _LOGGER.debug("Using cached signals for vehicle %s: %d codes", vehicle.id, len(signals))
        
        # Map API signal codes to sensor definition IDs
        available_signals = map_available_signals(signals)
        _LOGGER.info(
            "Vehicle %s has %d available signals (mapped from %d API codes)",
            vehicle.id,
            len(available_signals),
            len(signals),
        )
        _LOGGER.debug(
            "Available signals for %s: %s",
            vehicle.id,
            sorted(available_signals),
        )
        
        # Fetch initial state from API on boot (blocking to ensure we have data for permission-based sensors)
        # Use empty status initially if fetch fails
        status = {}
        try:
            status = await client.get_vehicle_status(vehicle.id)
            _LOGGER.debug("Initial state for vehicle %s: %s", vehicle.id, status)
        except Exception as err:
            _LOGGER.debug(
                "Failed to fetch initial state for vehicle %s (will use webhook): %s",
                vehicle.id,
                err,
            )
        
        # Initialize tracking dict for this vehicle
        if vehicle.id not in data["sensors"]:
            data["sensors"][vehicle.id] = {}

        # In rebuild mode, remove any tracked sensors that are no longer available
        if rebuild_mode:
            registry = er.async_get(hass)
            to_remove = [sid for sid in list(data["sensors"][vehicle.id]) if sid not in available_signals]
            for sid in to_remove:
                sensor_to_remove = data["sensors"][vehicle.id][sid]
                _LOGGER.info("Rebuild: removing sensor %s (no longer available for vehicle %s)", sid, vehicle.id)
                entity_id = getattr(sensor_to_remove, "entity_id", None)
                if entity_id:
                    registry.async_remove(entity_id)
                del data["sensors"][vehicle.id][sid]

        # Create sensors based on available signals AND permission fallback
        # In rebuild mode: strict — only signals from the signals API are created.
        # In normal mode: also allow permission-based fallback for sensors with required permissions.
        created_sensors = set()
        skipped_count = 0
        added_count = 0

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

            # Determine how this sensor should be created
            is_in_signals_api = signal_id in available_signals
            has_permission_fallback = required_permission is not None

            # Decide whether to create this sensor
            should_create = False
            creation_method = None

            if is_in_signals_api:
                should_create = True
                creation_method = "signals API"
            elif has_permission_fallback and not rebuild_mode:
                # Permission fallback only in normal (non-rebuild) mode
                should_create = True
                creation_method = "permission fallback"
            else:
                _LOGGER.debug(
                    "Signal %s: not available via signals API%s, skipping",
                    signal_id,
                    " (rebuild mode)" if rebuild_mode else " and no permission fallback",
                )
                skipped_count += 1
                continue
            
            # Skip if sensor already exists (unless in rebuild mode)
            if signal_id in data["sensors"][vehicle.id] and not rebuild_mode:
                _LOGGER.debug(
                    "Sensor %s already exists for vehicle %s, skipping",
                    signal_id,
                    vehicle.id,
                )
                continue
            
            if should_create:
                _LOGGER.info(
                    "Creating sensor %s for vehicle %s (signal: %s, via %s)",
                    name,
                    vehicle.id,
                    signal_id,
                    creation_method,
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
                added_count += 1
            else:
                skipped_count += 1
        
        # Log sensor creation summary for this vehicle
        total_sensors = len(data["sensors"][vehicle.id])
        if rebuild_mode:
            _LOGGER.info(
                "Vehicle %s: %d total sensors, %d added this rebuild, %d skipped (not available)",
                vehicle.id,
                total_sensors,
                added_count,
                skipped_count,
            )
        else:
            _LOGGER.info(
                "Vehicle %s: %d total sensors, %d new sensors added, %d skipped (not available)",
                vehicle.id,
                total_sensors,
                added_count,
                skipped_count,
            )

    async_add_entities(entities)

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
        parts = signal_id.split(".")
        self._status_path = parts[:-1]  # All but last, used for nested dict navigation
        self._api_key = parts[0]        # Top-level key (kept for logging)
        self._field_name = field_name
        self._entry_id = entry_id
        self._icon = icon
        self._device_class = device_class
        self._metric_unit = unit  # Store original metric unit
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
        self._unsub_dispatcher = None
        
        # Get unit system from config entry options
        config_entry = self.hass.config_entries.async_get_entry(entry_id)
        self._unit_system = UNIT_SYSTEM_METRIC
        if config_entry:
            self._unit_system = config_entry.options.get(CONF_UNIT_SYSTEM, UNIT_SYSTEM_METRIC)

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
        # Navigate nested status dict using _status_path, e.g.
        # signal_id "tires.frontLeft.pressure" → path ["tires", "frontLeft"] → field "pressure"
        api_response = self._status
        for key in self._status_path:
            if not isinstance(api_response, dict):
                return None
            api_response = api_response.get(key)
            if api_response is None:
                _LOGGER.debug(
                    "No data for sensor %s (missing key %s in path %s)",
                    self._attr_name,
                    key,
                    self._status_path,
                )
                return None

        if not api_response:
            return None

        if isinstance(api_response, dict):
            value = api_response.get(self._field_name)
        else:
            value = getattr(api_response, self._field_name, None)

        _LOGGER.debug("Sensor %s: %s = %s", self._attr_name, self._signal_id, value)

        if value is not None and isinstance(value, (int, float)) and self._metric_unit:
            return convert_value(value, self._metric_unit, self._unit_system)

        return value

    @property
    def unique_id(self):
        """Return a unique ID for the sensor entity."""
        return f"{self._vehicle.vin}_{self._signal_id}"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement for the sensor, if any."""
        if self._metric_unit:
            return get_display_unit(self._metric_unit, self._unit_system)
        return None

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