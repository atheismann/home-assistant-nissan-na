"""Number for Nissan NA integration."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Webhook signal for data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Nissan NA number entities for each vehicle."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client = data["client"]
    vehicles = await client.get_vehicle_list()
    entities = []
    
    # Track created number entities per vehicle
    if "numbers" not in data:
        data["numbers"] = {}

    for vehicle in vehicles:
        _LOGGER.info("Setting up number entities for vehicle %s", vehicle.id)
        
        # Get available signals from Smartcar API
        available_signals = set()
        try:
            signals = await client.get_vehicle_signals(vehicle.id)
            available_signals = set(signals)
        except Exception as err:
            _LOGGER.warning(
                "Failed to get vehicle signals for numbers %s: %s",
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
        if vehicle.id not in data["numbers"]:
            data["numbers"][vehicle.id] = {}

        # Create charge limit number if signal is available and permission granted
        if ("charge.limit" in available_signals or not available_signals) and "control_charge" in permissions:
            _LOGGER.info(
                "Creating charge limit number for vehicle %s",
                vehicle.id,
            )
            number = NissanChargeLimitNumber(
                hass,
                vehicle,
                client,
                config_entry.entry_id,
            )
            entities.append(number)
            data["numbers"][vehicle.id]["charge_limit"] = number
    
    async_add_entities(entities)
    
    # Set up webhook handler for updates
    async def handle_webhook_for_numbers(vehicle_id: str, webhook_data: dict):
        """Update numbers from webhook data."""
        if vehicle_id not in data["numbers"]:
            return
        
        _LOGGER.debug(
            "Webhook data for numbers on vehicle %s: %s fields",
            vehicle_id,
            len(webhook_data) if isinstance(webhook_data, dict) else 0,
        )
    
    from homeassistant.core import callback
    
    for vehicle in vehicles:
        @callback
        def handle_webhook_signal(webhook_data: dict, vehicle_id: str = vehicle.id):
            """Callback to handle webhook data updates."""
            hass.async_create_task(
                handle_webhook_for_numbers(vehicle_id, webhook_data)
            )
        
        async_dispatcher_connect(
            hass,
            f"{SIGNAL_WEBHOOK_DATA}_{vehicle.id}",
            handle_webhook_signal,
        )


class NissanChargeLimitNumber(NumberEntity):
    """Number entity for vehicle charge limit."""

    def __init__(self, hass, vehicle, client, entry_id):
        """Initialize charge limit number."""
        self.hass = hass
        self._vehicle = vehicle
        self._client = client
        self._entry_id = entry_id
        self._value = 80  # Default charge limit
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
        
        self._attr_name = f"{display_name} Charge Limit"
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
            "Charge limit number %s subscribed to webhook updates",
            self._attr_name,
        )

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
                if "limit" in charge_data:
                    limit = charge_data["limit"]
                    old_value = self._value
                    self._value = float(limit)
                    if old_value != self._value:
                        _LOGGER.info(
                            "Charge limit updated via webhook: %s%%",
                            self._value,
                        )
                        self.async_write_ha_state()
        except (KeyError, TypeError, ValueError):
            pass

    async def async_set_value(self, value: float) -> None:
        """Set the charge limit."""
        try:
            # Smartcar API expects integer 0-100
            limit = int(max(0, min(100, value)))
            # Make API call to set charge limit
            url = f"https://api.smartcar.com/v2.0/vehicles/{self._vehicle.id}/charge/limit"
            headers = {
                "Authorization": f"Bearer {self._client.access_token}"
            }
            data = {"limit": limit}
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status in (200, 204):
                        self._value = limit
                        self.async_write_ha_state()
                        _LOGGER.info(
                            "Set charge limit to %s%% for vehicle %s",
                            limit,
                            self._vehicle.id,
                        )
                    else:
                        _LOGGER.error(
                            "Failed to set charge limit: %s",
                            response.status,
                        )
                        self._available = False
                        self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error("Failed to set charge limit: %s", err)
            self._available = False
            self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return unique ID for the entity."""
        return f"{self._vehicle.vin}_charge_limit"

    @property
    def value(self):
        """Return the current charge limit."""
        return self._value

    @property
    def min_value(self):
        """Return the minimum charge limit."""
        return 0

    @property
    def max_value(self):
        """Return the maximum charge limit."""
        return 100

    @property
    def step(self):
        """Return the step size for the charge limit."""
        return 1

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:battery-charging-100"

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
