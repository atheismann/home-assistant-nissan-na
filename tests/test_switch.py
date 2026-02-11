"""Unit tests for switch.py - switch constants and structure"""
import pytest
from unittest.mock import Mock

from custom_components.nissan_na.switch import (
    SIGNAL_WEBHOOK_DATA,
    NissanChargingSwitch,
)
from custom_components.nissan_na.const import DOMAIN


class TestSwitchConstants:
    """Tests for switch constants"""
    
    def test_signal_webhook_data_exists(self):
        """Test that webhook signal constant is defined"""
        assert SIGNAL_WEBHOOK_DATA is not None
    
    def test_signal_webhook_data_value(self):
        """Test that webhook signal has correct value"""
        assert SIGNAL_WEBHOOK_DATA == "nissan_na_webhook_data"


class TestNissanChargingSwitchInit:
    """Tests for NissanChargingSwitch initialization"""
    
    def test_switch_init_with_nickname(self):
        """Test switch initialization with vehicle nickname"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert switch._vehicle == mock_vehicle
        assert switch._client == mock_client
        assert switch._entry_id == "test_entry_id"
        assert switch._is_on is False
        assert switch._available is True
        assert switch._attr_name == "My Nissan Charging"
    
    def test_switch_init_with_year_make_model(self):
        """Test switch initialization with year/make/model"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = None
        mock_vehicle.year = 2024
        mock_vehicle.make = "Nissan"
        mock_vehicle.model = "Leaf"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert switch._attr_name == "2024 Nissan Leaf Charging"
    
    def test_switch_init_with_vin_fallback(self):
        """Test switch initialization falling back to VIN"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = None
        mock_vehicle.year = ""
        mock_vehicle.make = ""
        mock_vehicle.model = ""
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert switch._attr_name == "TEST123VIN Charging"
    
    def test_switch_unsub_dispatcher_none(self):
        """Test that unsub_dispatcher is initialized as None"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert switch._unsub_dispatcher is None


class TestNissanChargingSwitchProperties:
    """Tests for NissanChargingSwitch properties"""
    
    def test_unique_id_property(self):
        """Test unique_id property"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert switch.unique_id == "TEST123VIN_charging_switch"
    
    def test_is_on_property_default_false(self):
        """Test is_on property defaults to False"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert switch.is_on is False
    
    def test_is_on_property_when_charging(self):
        """Test is_on property when charging"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        switch._is_on = True
        assert switch.is_on is True
    
    def test_icon_property_when_charging(self):
        """Test icon property when charging"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        switch._is_on = True
        assert switch.icon == "mdi:battery-charging"
    
    def test_icon_property_when_not_charging(self):
        """Test icon property when not charging"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        switch._is_on = False
        assert switch.icon == "mdi:battery"
    
    def test_available_property_default_true(self):
        """Test available property defaults to True"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert switch.available is True
    
    def test_available_property_when_unavailable(self):
        """Test available property when set to False"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        switch._available = False
        assert switch.available is False
    
    def test_device_info_property(self):
        """Test device_info property"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        device_info = switch.device_info
        assert "identifiers" in device_info
        assert (DOMAIN, "TEST123VIN") in device_info["identifiers"]


class TestNissanChargingSwitchWebhookHandling:
    """Tests for webhook data handling"""
    
    def test_handle_webhook_data_charging_state(self):
        """Test handling webhook data with charging state"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        # Mock the async_write_ha_state method
        switch.async_write_ha_state = Mock()
        
        # Initially not charging
        assert switch._is_on is False
        
        # Webhook data indicating charging
        webhook_data = {
            "charge": {
                "state": "CHARGING"
            }
        }
        
        switch._handle_webhook_data(webhook_data)
        assert switch._is_on is True
    
    def test_handle_webhook_data_not_charging_state(self):
        """Test handling webhook data with not charging state"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        # Mock the async_write_ha_state method
        switch.async_write_ha_state = Mock()
        
        # Set to charging
        switch._is_on = True
        
        # Webhook data indicating not charging
        webhook_data = {
            "charge": {
                "state": "NOT_CHARGING"
            }
        }
        
        switch._handle_webhook_data(webhook_data)
        assert switch._is_on is False
    
    def test_handle_webhook_data_invalid_format(self):
        """Test handling webhook data with invalid format"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        original_state = switch._is_on
        
        # Invalid data types
        switch._handle_webhook_data(None)
        assert switch._is_on == original_state
        
        switch._handle_webhook_data("invalid")
        assert switch._is_on == original_state
        
        switch._handle_webhook_data([])
        assert switch._is_on == original_state
    
    def test_handle_webhook_data_missing_charge_key(self):
        """Test handling webhook data without charge key"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        original_state = switch._is_on
        
        # Data without charge key
        webhook_data = {
            "battery": {
                "level": 0.85
            }
        }
        
        switch._handle_webhook_data(webhook_data)
        # State should not change
        assert switch._is_on == original_state
    
    def test_handle_webhook_data_missing_state_key(self):
        """Test handling webhook data without state key in charge"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        original_state = switch._is_on
        
        # Data with charge but no state
        webhook_data = {
            "charge": {
                "isPluggedIn": True
            }
        }
        
        switch._handle_webhook_data(webhook_data)
        # State should not change
        assert switch._is_on == original_state


class TestNissanChargingSwitchMultipleVehicles:
    """Tests for handling multiple vehicle scenarios"""
    
    def test_unique_id_different_for_different_vehicles(self):
        """Test that unique IDs are different for different vehicles"""
        mock_hass = Mock()
        mock_client = Mock()
        
        mock_vehicle1 = Mock()
        mock_vehicle1.vin = "VIN123"
        mock_vehicle1.id = "vehicle_1"
        mock_vehicle1.nickname = "Car 1"
        
        mock_vehicle2 = Mock()
        mock_vehicle2.vin = "VIN456"
        mock_vehicle2.id = "vehicle_2"
        mock_vehicle2.nickname = "Car 2"
        
        switch1 = NissanChargingSwitch(mock_hass, mock_vehicle1, mock_client, "entry1")
        switch2 = NissanChargingSwitch(mock_hass, mock_vehicle2, mock_client, "entry2")
        
        assert switch1.unique_id != switch2.unique_id
        assert switch1.unique_id == "VIN123_charging_switch"
        assert switch2.unique_id == "VIN456_charging_switch"
