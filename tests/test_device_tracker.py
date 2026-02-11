"""Comprehensive tests for device_tracker.py to achieve 90%+ coverage"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from homeassistant.components.device_tracker import SourceType
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.nissan_na.device_tracker import (
    NissanVehicleTracker,
    async_setup_entry,
    SIGNAL_WEBHOOK_DATA,
)
from custom_components.nissan_na.const import DOMAIN


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function"""
    
    @pytest.mark.asyncio
    async def test_setup_entry_creates_trackers_for_vehicles(self):
        """Test that setup creates tracker for each vehicle"""
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "client": Mock()
                }
            }
        }
        
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry_id"
        
        mock_vehicle1 = Mock()
        mock_vehicle1.id = "vehicle_1"
        mock_vehicle1.vin = "VIN123"
        mock_vehicle1.nickname = "Car 1"
        
        mock_vehicle2 = Mock()
        mock_vehicle2.id = "vehicle_2"
        mock_vehicle2.vin = "VIN456"
        mock_vehicle2.nickname = "Car 2"
        
        mock_client = mock_hass.data[DOMAIN]["test_entry_id"]["client"]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle1, mock_vehicle2])
        mock_client.get_permissions = AsyncMock(return_value=["read_location", "read_battery"])
        mock_client.get_vehicle_status = AsyncMock(return_value={"location": {"lat": 37.0, "lon": -122.0}})
        
        mock_add_entities = Mock()
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Should create 2 trackers
        mock_add_entities.assert_called_once()
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 2
        assert isinstance(entities[0], NissanVehicleTracker)
        assert isinstance(entities[1], NissanVehicleTracker)
    
    @pytest.mark.asyncio
    async def test_setup_entry_skips_vehicle_without_location_permission(self):
        """Test that setup skips vehicle without read_location permission"""
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "client": Mock()
                }
            }
        }
        
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry_id"
        
        mock_vehicle1 = Mock()
        mock_vehicle1.id = "vehicle_1"
        mock_vehicle1.vin = "VIN123"
        mock_vehicle1.nickname = "Car 1"
        
        mock_vehicle2 = Mock()
        mock_vehicle2.id = "vehicle_2"
        mock_vehicle2.vin = "VIN456"
        mock_vehicle2.nickname = "Car 2"
        
        mock_client = mock_hass.data[DOMAIN]["test_entry_id"]["client"]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle1, mock_vehicle2])
        
        # First vehicle has location, second doesn't
        async def get_permissions_side_effect(vehicle_id):
            if vehicle_id == "vehicle_1":
                return ["read_location", "read_battery"]
            else:
                return ["read_battery", "control_security"]  # No read_location
        
        mock_client.get_permissions = AsyncMock(side_effect=get_permissions_side_effect)
        mock_client.get_vehicle_status = AsyncMock(return_value={"location": {"lat": 37.0, "lon": -122.0}})
        
        mock_add_entities = Mock()
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Should only create 1 tracker (vehicle_1)
        mock_add_entities.assert_called_once()
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert entities[0]._vehicle.id == "vehicle_1"
    
    @pytest.mark.asyncio
    async def test_setup_entry_creates_tracker_on_permission_check_failure(self):
        """Test that setup creates tracker if permission check fails"""
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "client": Mock()
                }
            }
        }
        
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry_id"
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_1"
        mock_vehicle.vin = "VIN123"
        mock_vehicle.nickname = "Car 1"
        
        mock_client = mock_hass.data[DOMAIN]["test_entry_id"]["client"]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_permissions = AsyncMock(side_effect=Exception("API error"))
        mock_client.get_vehicle_status = AsyncMock(return_value={"location": {"lat": 37.0, "lon": -122.0}})
        
        mock_add_entities = Mock()
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Should create tracker (conservative approach on error)
        mock_add_entities.assert_called_once()
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 1
    
    @pytest.mark.asyncio
    async def test_setup_entry_creates_tracker_with_empty_permissions(self):
        """Test that setup creates tracker when permissions list is empty"""
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "client": Mock()
                }
            }
        }
        
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry_id"
        
        mock_vehicle = Mock()
        mock_vehicle.id = "vehicle_1"
        mock_vehicle.vin = "VIN123"
        mock_vehicle.nickname = "Car 1"
        
        mock_client = mock_hass.data[DOMAIN]["test_entry_id"]["client"]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_permissions = AsyncMock(return_value=[])  # Empty list
        mock_client.get_vehicle_status = AsyncMock(return_value={"location": {"lat": 37.0, "lon": -122.0}})
        
        mock_add_entities = Mock()
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Should create tracker (empty list doesn't definitively exclude location)
        mock_add_entities.assert_called_once()
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 1


class TestAsyncAddedToHass:
    """Tests for async_added_to_hass lifecycle method"""
    
    @pytest.mark.asyncio
    async def test_async_added_to_hass_subscribes_to_webhook(self):
        """Test that entity subscribes to webhook updates when added"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        with patch('custom_components.nissan_na.device_tracker.async_dispatcher_connect') as mock_connect:
            mock_connect.return_value = Mock()
            
            await tracker.async_added_to_hass()
            
            # Should subscribe to webhook signal
            mock_connect.assert_called_once()
            call_args = mock_connect.call_args
            assert call_args[0][0] == mock_hass
            assert call_args[0][1] == f"{SIGNAL_WEBHOOK_DATA}_vehicle_123"
            assert callable(call_args[0][2])
            
            # Should store unsubscribe callback
            assert tracker._unsub_dispatcher is not None


class TestAsyncWillRemoveFromHass:
    """Tests for async_will_remove_from_hass lifecycle method"""
    
    @pytest.mark.asyncio
    async def test_async_will_remove_unsubscribes(self):
        """Test that entity unsubscribes when removed"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        # Set up a mock unsubscribe callback
        mock_unsub = Mock()
        tracker._unsub_dispatcher = mock_unsub
        
        await tracker.async_will_remove_from_hass()
        
        # Should call unsubscribe
        mock_unsub.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_will_remove_handles_no_subscription(self):
        """Test that removal works when no subscription exists"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        tracker._unsub_dispatcher = None
        
        # Should not raise error
        await tracker.async_will_remove_from_hass()


class TestHandleWebhookData:
    """Tests for _handle_webhook_data method"""
    
    def test_handle_webhook_data_updates_status(self):
        """Test that webhook data updates status dict"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        initial_status = {"location": {"lat": 37.0, "lon": -122.0}}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, initial_status, "test_entry_id")
        tracker.async_write_ha_state = Mock()
        
        webhook_data = {"location": {"lat": 38.0, "lon": -123.0}}
        tracker._handle_webhook_data(webhook_data)
        
        # Status should be updated
        assert tracker._status["location"]["lat"] == 38.0
        assert tracker._status["location"]["lon"] == -123.0
        
        # State should be written
        tracker.async_write_ha_state.assert_called_once()
    
    def test_handle_webhook_data_location_change_logged(self):
        """Test that location changes are logged"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        initial_status = {"location": {"lat": 37.0, "lon": -122.0}}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, initial_status, "test_entry_id")
        tracker.async_write_ha_state = Mock()
        
        webhook_data = {"location": {"lat": 38.0, "lon": -123.0, "latitude": 38.0, "longitude": -123.0}}
        
        with patch('custom_components.nissan_na.device_tracker._LOGGER') as mock_logger:
            tracker._handle_webhook_data(webhook_data)
            
            # Should log location update
            assert any("location updated" in str(call).lower() for call in mock_logger.info.call_args_list)
    
    def test_handle_webhook_data_invalid_type(self):
        """Test handling of invalid webhook data type"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        tracker.async_write_ha_state = Mock()
        
        with patch('custom_components.nissan_na.device_tracker._LOGGER') as mock_logger:
            tracker._handle_webhook_data("invalid_string_data")
            
            # Should log warning
            mock_logger.warning.assert_called()
            
            # Should not write state
            tracker.async_write_ha_state.assert_not_called()
    
    def test_handle_webhook_data_no_location_change(self):
        """Test webhook data with no location change"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        initial_status = {"location": {"lat": 37.0, "lon": -122.0}, "battery": 85}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, initial_status, "test_entry_id")
        tracker.async_write_ha_state = Mock()
        
        # Update with different data but same location
        webhook_data = {"battery": 84}
        tracker._handle_webhook_data(webhook_data)
        
        # Should still write state
        tracker.async_write_ha_state.assert_called_once()
        # Battery should be updated
        assert tracker._status["battery"] == 84


class TestShouldPoll:
    """Tests for should_poll property"""
    
    def test_should_poll_returns_false(self):
        """Test that should_poll returns False (webhook-based)"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        assert tracker.should_poll is False


class TestAsyncUpdate:
    """Tests for async_update method"""
    
    @pytest.mark.asyncio
    async def test_async_update_success(self):
        """Test successful async_update"""
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "client": Mock()
                }
            }
        }
        
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        initial_status = {"location": {"lat": 37.0, "lon": -122.0}}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, initial_status, "test_entry_id")
        
        mock_client = mock_hass.data[DOMAIN]["test_entry_id"]["client"]
        mock_client.get_vehicle_status = AsyncMock(return_value={
            "location": {"lat": 38.0, "lon": -123.0},
            "battery": 85
        })
        
        await tracker.async_update()
        
        # Status should be updated
        assert tracker._status["location"]["lat"] == 38.0
        assert tracker._status["location"]["lon"] == -123.0
        assert tracker._status["battery"] == 85
    
    @pytest.mark.asyncio
    async def test_async_update_error_handling(self):
        """Test async_update error handling"""
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "client": Mock()
                }
            }
        }
        
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        mock_client = mock_hass.data[DOMAIN]["test_entry_id"]["client"]
        mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("API error"))
        
        with patch('custom_components.nissan_na.device_tracker._LOGGER') as mock_logger:
            await tracker.async_update()
            
            # Should log error
            mock_logger.error.assert_called()


class TestLatitudeLongitudeProperties:
    """Tests for latitude and longitude properties"""
    
    def test_latitude_with_valid_location(self):
        """Test latitude property with valid location data"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        status = {"location": {"lat": 37.7749, "lon": -122.4194}}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, status, "test_entry_id")
        
        assert tracker.latitude == 37.7749
    
    def test_latitude_with_no_location(self):
        """Test latitude property when no location data"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        assert tracker.latitude is None
    
    def test_latitude_with_non_dict_location(self):
        """Test latitude property when location is not a dict"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        status = {"location": "invalid"}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, status, "test_entry_id")
        
        assert tracker.latitude is None
    
    def test_longitude_with_valid_location(self):
        """Test longitude property with valid location data"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        status = {"location": {"lat": 37.7749, "lon": -122.4194}}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, status, "test_entry_id")
        
        assert tracker.longitude == -122.4194
    
    def test_longitude_with_no_location(self):
        """Test longitude property when no location data"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        assert tracker.longitude is None
    
    def test_longitude_with_non_dict_location(self):
        """Test longitude property when location is not a dict"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        status = {"location": "invalid"}
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, status, "test_entry_id")
        
        assert tracker.longitude is None


class TestSourceTypeProperty:
    """Tests for source_type property"""
    
    def test_source_type_returns_gps(self):
        """Test that source_type returns GPS"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        assert tracker.source_type == SourceType.GPS


class TestDeviceInfo:
    """Tests for device_info property"""
    
    def test_device_info_returns_correct_structure(self):
        """Test that device_info returns proper structure"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        device_info = tracker.device_info
        
        assert "identifiers" in device_info
        assert (DOMAIN, "TEST123VIN") in device_info["identifiers"]
    
    def test_device_info_uses_vehicle_vin(self):
        """Test that device_info uses vehicle VIN for identifier"""
        mock_hass = Mock()
        mock_vehicle = Mock()
        mock_vehicle.vin = "UNIQUEVIN789"
        mock_vehicle.id = "vehicle_456"
        mock_vehicle.nickname = "My Car"
        
        tracker = NissanVehicleTracker(mock_hass, mock_vehicle, {}, "test_entry_id")
        
        device_info = tracker.device_info
        
        assert (DOMAIN, "UNIQUEVIN789") in device_info["identifiers"]
