"""Binary sensors for Nissan NA integration."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Webhook signal for data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"

# Binary sensor definitions
# Format: (signal_id, sensor_name, device_class, icon)
BINARY_SENSOR_DEFINITIONS = [
    # Door sensors (open status)
    ("closure.doors.frontLeft.isOpen", "Front Left Door", BinarySensorDeviceClass.DOOR, "mdi:car-door"),
    ("closure.doors.frontRight.isOpen", "Front Right Door", BinarySensorDeviceClass.DOOR, "mdi:car-door"),
    ("closure.doors.backLeft.isOpen", "Back Left Door", BinarySensorDeviceClass.DOOR, "mdi:car-door"),
    ("closure.doors.backRight.isOpen", "Back Right Door", BinarySensorDeviceClass.DOOR, "mdi:car-door"),
    
    # Door locks
    ("closure.doors.frontLeft.isLocked", "Front Left Door Lock", BinarySensorDeviceClass.LOCK, "mdi:lock"),
    ("closure.doors.frontRight.isLocked", "Front Right Door Lock", BinarySensorDeviceClass.LOCK, "mdi:lock"),
    ("closure.doors.backLeft.isLocked", "Back Left Door Lock", BinarySensorDeviceClass.LOCK, "mdi:lock"),
    ("closure.doors.backRight.isLocked", "Back Right Door Lock", BinarySensorDeviceClass.LOCK, "mdi:lock"),
    
    # Window sensors
    ("closure.windows.frontLeft.isOpen", "Front Left Window", BinarySensorDeviceClass.WINDOW, "mdi:window-closed"),
    ("closure.windows.frontRight.isOpen", "Front Right Window", BinarySensorDeviceClass.WINDOW, "mdi:window-closed"),
    ("closure.windows.backLeft.isOpen", "Back Left Window", BinarySensorDeviceClass.WINDOW, "mdi:window-closed"),
    ("closure.windows.backRight.isOpen", "Back Right Window", BinarySensorDeviceClass.WINDOW, "mdi:window-closed"),
    
    # Trunk sensors
    ("closure.frontTrunk.isOpen", "Front Trunk", BinarySensorDeviceClass.DOOR, "mdi:car-door"),
    ("closure.frontTrunk.isLocked", "Front Trunk Lock", BinarySensorDeviceClass.LOCK, "mdi:lock"),
    ("closure.rearTrunk.isOpen", "Rear Trunk", BinarySensorDeviceClass.DOOR, "mdi:car-door"),
    ("closure.rearTrunk.isLocked", "Rear Trunk Lock", BinarySensorDeviceClass.LOCK, "mdi:lock"),
    
    # Sunroof
    ("closure.sunroof.isOpen", "Sunroof", BinarySensorDeviceClass.WINDOW, "mdi:window-closed"),
    
    # Engine cover
    ("closure.engineCover.isOpen", "Engine Cover", BinarySensorDeviceClass.DOOR, "mdi:car-door"),
    
    # Battery heater (webhook only)
    ("tractionBattery.isHeaterActive", "Battery Heater Active", None, "mdi:fire"),
    
    # Online status (webhook only)
    ("connectivity.isOnline", "Online", BinarySensorDeviceClass.CONNECTIVITY, "mdi:wifi"),
    
    # Sleep status (webhook only)
    ("connectivity.isAsleep", "Asleep", None, "mdi:sleep"),
    
    # Digital key (webhook only)
    ("connectivity.isDigitalKeyPaired", "Digital Key Paired", None, "mdi:key"),
    
    # Surveillance (webhook only)
    ("surveillance.isEnabled", "Surveillance Enabled", None, "mdi:cctv"),
    
    # Fast charger connected (webhook only)
    ("charge.isFastChargerConnected", "Fast Charger Connected", None, "mdi:lightning-bolt"),
    
    # Charging cable plugged in
    ("charge.isPluggedIn", "Charging Cable Plugged In", BinarySensorDeviceClass.PLUG, "mdi:power-plug"),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Nissan NA binary sensors for each vehicle."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    
    # Track created binary sensors per vehicle
    if "binary_sensors" not in data:
        data["binary_sensors"] = {}

    for vehicle in vehicles:
        _LOGGER.info("Setting up binary sensors for vehicle %s", vehicle.id)
        
        # Get available signals from Smartcar API
        available_signals = set()
        try:
            signals = await client.get_vehicle_signals(vehicle.id)
            available_signals = set(signals)
            _LOGGER.debug(
                "Binary sensor signals for vehicle %s: %s",
                vehicle.id,
                [s for s in available_signals if any(d[0] == s for d in BINARY_SENSOR_DEFINITIONS)],
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed to get vehicle signals for binary sensors %s: %s",
                vehicle.id,
                err,
            )
        
        # Initialize tracking dict for this vehicle
        if vehicle.id not in data["binary_sensors"]:
            data["binary_sensors"][vehicle.id] = {}

        # Create binary sensors based on available signals
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            # Check if signal is available
            should_create = False
            if available_signals:
                should_create = signal_id in available_signals
            else:
                # If signals API failed, create all sensors (they'll show unavailable if not supported)
                # This is conservative but ensures features work when signals API is unavailable
                should_create = True
            
            if should_create:
                _LOGGER.info(
                    "Creating binary sensor %s for vehicle %s (signal: %s)",
                    name,
                    vehicle.id,
                    signal_id,
                )
                sensor = NissanBinarySensor(
                    hass,
                    vehicle,
                    signal_id,
                    name,
                    device_class,
                    icon,
                    config_entry.entry_id,
                )
                entities.append(sensor)
                data["binary_sensors"][vehicle.id][signal_id] = sensor
    
    async_add_entities(entities)
    
    # Set up webhook handler for updates
    async def handle_webhook_for_binary_sensors(vehicle_id: str, webhook_data: dict):
        """Update binary sensors from webhook data."""
        if vehicle_id not in data["binary_sensors"]:
            return
        
        _LOGGER.debug(
            "Webhook data for binary sensors on vehicle %s: %s fields",
            vehicle_id,
            len(webhook_data) if isinstance(webhook_data, dict) else 0,
        )
    
    from homeassistant.core import callback
    
    for vehicle in vehicles:
        @callback
        def handle_webhook_signal(webhook_data: dict, vehicle_id: str = vehicle.id):
            """Callback to handle webhook data updates."""
            hass.async_create_task(
                handle_webhook_for_binary_sensors(vehicle_id, webhook_data)
            )
        
        async_dispatcher_connect(
            hass,
            f"{SIGNAL_WEBHOOK_DATA}_{vehicle.id}",
            handle_webhook_signal,
        )


class NissanBinarySensor(BinarySensorEntity):
    """Binary sensor for a Nissan vehicle status point (doors, windows, etc)."""

    def __init__(self, hass, vehicle, signal_id, name, device_class, icon, entry_id):
        """Initialize binary sensor."""
        self.hass = hass
        self._vehicle = vehicle
        self._signal_id = signal_id
        self._entry_id = entry_id
        self._device_class = device_class
        self._icon = icon
        self._is_on = False
        
        # Build device name
        nickname = getattr(vehicle, "nickname", None)
        if nickname:
            display_name = nickname
        else:
            year = getattr(vehicle, "year", "")
            make = getattr(vehicle, "make", "")
            model = getattr(vehicle, "model", "")
            if year and make and model:
                display_name = f"{year} {make} {model}"
            else:
                display_name = vehicle.vin
        
        self._attr_name = f"{display_name} {name}"
        self._unsub_dispatcher = None

    async def async_added_to_hass(self):
        """Subscribe to webhook updates."""
        await super().async_added_to_hass()
        
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_WEBHOOK_DATA}_{self._vehicle.id}",
            self._handle_webhook_data,
        )
        _LOGGER.debug(
            "Binary sensor %s subscribed to webhook updates",
            self._attr_name,
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from updates."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
        await super().async_will_remove_from_hass()

    def _handle_webhook_data(self, data: dict):
        """Handle webhook data updates."""
        # Parse signal path to extract value from webhook data
        # e.g., "closure.doors.frontLeft.isOpen" -> data["closure"]["doors"]["frontLeft"]["isOpen"]
        if not isinstance(data, dict):
            return
        
        try:
            parts = self._signal_id.split(".")
            value = data
            for part in parts:
                value = value[part]
            
            self._is_on = bool(value)
            self.async_write_ha_state()
            _LOGGER.debug(
                "Binary sensor %s updated via webhook: %s",
                self._attr_name,
                self._is_on,
            )
        except (KeyError, TypeError):
            # Data doesn't contain this signal path, which is fine
            pass

    @property
    def unique_id(self):
        """Return unique ID for the entity."""
        return f"{self._vehicle.vin}_{self._signal_id}"

    @property
    def is_on(self):
        """Return True if sensor is on."""
        return self._is_on

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
        }
