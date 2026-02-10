"""Switch for Nissan NA integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Webhook signal for data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Nissan NA switches for each vehicle."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    
    # Track created switches per vehicle
    if "switches" not in data:
        data["switches"] = {}

    for vehicle in vehicles:
        _LOGGER.info("Setting up switches for vehicle %s", vehicle.id)
        
        # Get available signals from Smartcar API
        available_signals = set()
        try:
            signals = await client.get_vehicle_signals(vehicle.id)
            available_signals = set(signals)
        except Exception as err:
            _LOGGER.warning(
                "Failed to get vehicle signals for switches %s: %s",
                vehicle.id,
                err,
            )
        
        # Check permissions for charging control
        permissions = []
        try:
            permissions = await client.get_permissions(vehicle.id)
        except Exception:
            pass
        
        # Initialize tracking dict for this vehicle
        if vehicle.id not in data["switches"]:
            data["switches"][vehicle.id] = {}

        # Create charging switch if signal is available and permission granted
        if ("charge.state" in available_signals or not available_signals) and "control_charge" in permissions:
            _LOGGER.info(
                "Creating charging switch for vehicle %s",
                vehicle.id,
            )
            switch = NissanChargingSwitch(
                hass,
                vehicle,
                client,
                config_entry.entry_id,
            )
            entities.append(switch)
            data["switches"][vehicle.id]["charging"] = switch
    
    async_add_entities(entities)
    
    # Set up webhook handler for updates
    async def handle_webhook_for_switches(vehicle_id: str, webhook_data: dict):
        """Update switches from webhook data."""
        if vehicle_id not in data["switches"]:
            return
        
        _LOGGER.debug(
            "Webhook data for switches on vehicle %s: %s fields",
            vehicle_id,
            len(webhook_data) if isinstance(webhook_data, dict) else 0,
        )
    
    from homeassistant.core import callback
    
    for vehicle in vehicles:
        @callback
        def handle_webhook_signal(webhook_data: dict, vehicle_id: str = vehicle.id):
            """Callback to handle webhook data updates."""
            hass.async_create_task(
                handle_webhook_for_switches(vehicle_id, webhook_data)
            )
        
        async_dispatcher_connect(
            hass,
            f"{SIGNAL_WEBHOOK_DATA}_{vehicle.id}",
            handle_webhook_signal,
        )


class NissanChargingSwitch(SwitchEntity):
    """Switch to control vehicle charging."""

    def __init__(self, hass, vehicle, client, entry_id):
        """Initialize charging switch."""
        self.hass = hass
        self._vehicle = vehicle
        self._client = client
        self._entry_id = entry_id
        self._is_on = False
        self._available = True
        
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
        
        self._attr_name = f"{display_name} Charging"
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
            "Charging switch %s subscribed to webhook updates",
            self._attr_name,
        )
        
        # Fetch initial state
        try:
            status = await self._client.get_charge_status(self._vehicle.id)
            if status and "state" in status:
                self._is_on = status["state"] in ("CHARGING", "UNKNOWN")
        except Exception as err:
            _LOGGER.warning("Failed to fetch initial charging status: %s", err)

    async def async_will_remove_from_hass(self):
        """Unsubscribe from updates."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
        await super().async_will_remove_from_hass()

    def _handle_webhook_data(self, data: dict):
        """Handle webhook data updates."""
        if not isinstance(data, dict):
            return
        
        try:
            if "charge" in data and isinstance(data["charge"], dict):
                charge_data = data["charge"]
                if "state" in charge_data:
                    state = charge_data["state"]
                    old_value = self._is_on
                    self._is_on = state in ("CHARGING",)
                    if old_value != self._is_on:
                        _LOGGER.info(
                            "Charging switch updated via webhook: %s",
                            self._is_on,
                        )
                        self.async_write_ha_state()
        except (KeyError, TypeError):
            pass

    async def async_turn_on(self, **kwargs):
        """Turn on charging."""
        try:
            await self._client.start_charge(self._vehicle.id)
            self._is_on = True
            self.async_write_ha_state()
            _LOGGER.info("Started charging for vehicle %s", self._vehicle.id)
        except Exception as err:
            _LOGGER.error("Failed to start charging: %s", err)
            self._available = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off charging."""
        try:
            await self._client.stop_charge(self._vehicle.id)
            self._is_on = False
            self.async_write_ha_state()
            _LOGGER.info("Stopped charging for vehicle %s", self._vehicle.id)
        except Exception as err:
            _LOGGER.error("Failed to stop charging: %s", err)
            self._available = False
            self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return unique ID for the entity."""
        return f"{self._vehicle.vin}_charging_switch"

    @property
    def is_on(self):
        """Return True if charging is on."""
        return self._is_on

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:battery-charging" if self._is_on else "mdi:battery"

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._vehicle.vin)},
        }
