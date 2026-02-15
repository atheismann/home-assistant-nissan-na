"""Unit tests for switch.py - switch constants and structure"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call

from custom_components.nissan_na.switch import (
    SIGNAL_WEBHOOK_DATA,
    NissanChargingSwitch,
    async_setup_entry,
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


@pytest.mark.asyncio
class TestAsyncSetupEntry:
    """Tests for async_setup_entry"""
    
    async def test_async_setup_entry_creates_charging_switch(self):
        """Test that async_setup_entry creates a charging switch"""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_entry": {}}}
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.state"])
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data[DOMAIN]["test_entry"]["client"] = mock_client
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, Mock(entry_id="test_entry"), async_add_entities)
        
        assert async_add_entities.called
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], NissanChargingSwitch)

    async def test_async_setup_entry_no_signals_available(self):
        """Test setup with no signals available"""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_entry": {}}}
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=[])
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data[DOMAIN]["test_entry"]["client"] = mock_client
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, Mock(entry_id="test_entry"), async_add_entities)
        
        # Should still create switch when no signals but has permission
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1

    async def test_async_setup_entry_no_permission(self):
        """Test setup without control_charge permission"""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_entry": {}}}
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.state"])
        mock_client.get_permissions = AsyncMock(return_value=[])  # No permissions
        
        mock_hass.data[DOMAIN]["test_entry"]["client"] = mock_client
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, Mock(entry_id="test_entry"), async_add_entities)
        
        # No switch should be created without permission
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 0

    async def test_async_setup_entry_get_signals_fails(self):
        """Test setup when get_vehicle_signals fails"""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_entry": {}}}
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=Exception("API Error"))
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data[DOMAIN]["test_entry"]["client"] = mock_client
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, Mock(entry_id="test_entry"), async_add_entities)
        
        # Should still create switch (signal check failed, but permission granted)
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1

    async def test_async_setup_entry_get_permissions_fails(self):
        """Test setup when get_permissions fails"""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_entry": {}}}
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.state"])
        mock_client.get_permissions = AsyncMock(side_effect=Exception("API Error"))
        
        mock_hass.data[DOMAIN]["test_entry"]["client"] = mock_client
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, Mock(entry_id="test_entry"), async_add_entities)
        
        # Should not create switch (permission check failed)
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 0

    async def test_async_setup_entry_multiple_vehicles(self):
        """Test setup with multiple vehicles"""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_entry": {}}}
        
        mock_vehicle1 = Mock()
        mock_vehicle1.id = "vehicle_1"
        mock_vehicle1.nickname = "Vehicle 1"
        mock_vehicle1.vin = "VIN1"
        
        mock_vehicle2 = Mock()
        mock_vehicle2.id = "vehicle_2"
        mock_vehicle2.nickname = "Vehicle 2"
        mock_vehicle2.vin = "VIN2"
        
        mock_client = Mock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle1, mock_vehicle2])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.state"])
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data[DOMAIN]["test_entry"]["client"] = mock_client
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, Mock(entry_id="test_entry"), async_add_entities)
        
        # Should create 2 switches
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 2


@pytest.mark.asyncio
class TestNissanChargingSwitchAsync:
    """Tests for async methods in NissanChargingSwitch"""
    
    async def test_async_added_to_hass_subscribes_to_webhook(self):
        """Test that async_added_to_hass subscribes to webhook updates"""
        mock_hass = Mock()
        mock_hass.async_create_task = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_charge_status = AsyncMock(return_value={"state": "NOT_CHARGING"})
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        with patch("custom_components.nissan_na.switch.async_dispatcher_connect") as mock_connect:
            await switch.async_added_to_hass()
            
            mock_connect.assert_called_once()
            call_args = mock_connect.call_args[0]
            assert call_args[0] == mock_hass
            assert "vehicle_123" in call_args[1]

    async def test_async_added_to_hass_fetches_initial_status_charging(self):
        """Test that async_added_to_hass fetches initial charging status"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_charge_status = AsyncMock(return_value={"state": "CHARGING"})
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        with patch("custom_components.nissan_na.switch.async_dispatcher_connect"):
            await switch.async_added_to_hass()
            
            assert switch._is_on is True

    async def test_async_added_to_hass_fetches_initial_status_unknown(self):
        """Test that async_added_to_hass handles UNKNOWN charging state"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_charge_status = AsyncMock(return_value={"state": "UNKNOWN"})
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        with patch("custom_components.nissan_na.switch.async_dispatcher_connect"):
            await switch.async_added_to_hass()
            
            assert switch._is_on is True

    async def test_async_added_to_hass_fetches_initial_status_not_charging(self):
        """Test that async_added_to_hass handles NOT_CHARGING state"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_charge_status = AsyncMock(return_value={"state": "NOT_CHARGING"})
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        with patch("custom_components.nissan_na.switch.async_dispatcher_connect"):
            await switch.async_added_to_hass()
            
            assert switch._is_on is False

    async def test_async_added_to_hass_fetch_status_fails(self):
        """Test that async_added_to_hass handles fetch status failure"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_charge_status = AsyncMock(side_effect=Exception("API Error"))
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        with patch("custom_components.nissan_na.switch.async_dispatcher_connect"):
            await switch.async_added_to_hass()
            
            # Should not fail, just log warning
            assert switch._is_on is False

    async def test_async_added_to_hass_no_state_in_response(self):
        """Test that async_added_to_hass handles missing state in response"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_charge_status = AsyncMock(return_value={"isPluggedIn": True})
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        with patch("custom_components.nissan_na.switch.async_dispatcher_connect"):
            await switch.async_added_to_hass()
            
            assert switch._is_on is False

    async def test_async_will_remove_from_hass_unsubscribes(self):
        """Test that async_will_remove_from_hass unsubscribes from updates"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.get_charge_status = AsyncMock(return_value={"state": "NOT_CHARGING"})
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        mock_unsub = Mock()
        
        with patch("custom_components.nissan_na.switch.async_dispatcher_connect", return_value=mock_unsub):
            await switch.async_added_to_hass()
            
            assert switch._unsub_dispatcher == mock_unsub
            
            await switch.async_will_remove_from_hass()
            
            mock_unsub.assert_called_once()

    async def test_async_will_remove_from_hass_no_unsub(self):
        """Test that async_will_remove_from_hass handles None unsub_dispatcher"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        
        # Should not raise error even with None unsub_dispatcher
        await switch.async_will_remove_from_hass()

    async def test_async_turn_on_success(self):
        """Test successful turn_on"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.start_charge = AsyncMock()
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        switch.async_write_ha_state = Mock()
        
        await switch.async_turn_on()
        
        mock_client.start_charge.assert_called_once_with("vehicle_123")
        assert switch._is_on is True
        switch.async_write_ha_state.assert_called_once()

    async def test_async_turn_on_fails(self):
        """Test turn_on when API call fails"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.start_charge = AsyncMock(side_effect=Exception("API Error"))
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        switch.async_write_ha_state = Mock()
        
        await switch.async_turn_on()
        
        # Should mark as unavailable on error
        assert switch._available is False
        switch.async_write_ha_state.assert_called()

    async def test_async_turn_off_success(self):
        """Test successful turn_off"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.stop_charge = AsyncMock()
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        switch.async_write_ha_state = Mock()
        switch._is_on = True
        
        await switch.async_turn_off()
        
        mock_client.stop_charge.assert_called_once_with("vehicle_123")
        assert switch._is_on is False
        switch.async_write_ha_state.assert_called_once()

    async def test_async_turn_off_fails(self):
        """Test turn_off when API call fails"""
        mock_hass = Mock()
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test Vehicle"
        mock_vehicle.vin = "TEST123VIN"
        
        mock_client = Mock()
        mock_client.stop_charge = AsyncMock(side_effect=Exception("API Error"))
        
        switch = NissanChargingSwitch(mock_hass, mock_vehicle, mock_client, "entry_id")
        switch.async_write_ha_state = Mock()
        
        await switch.async_turn_off()
        
        # Should mark as unavailable on error
        assert switch._available is False
        switch.async_write_ha_state.assert_called()
