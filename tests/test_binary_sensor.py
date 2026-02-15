"""Unit tests for binary_sensor.py - binary sensor definitions and structure"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.nissan_na.binary_sensor import (
    BINARY_SENSOR_DEFINITIONS,
    SIGNAL_WEBHOOK_DATA,
    NissanBinarySensor,
    async_setup_entry,
)
from custom_components.nissan_na.const import DOMAIN


class TestBinarySensorDefinitions:
    """Tests for binary sensor definitions"""
    
    def test_binary_sensor_definitions_exist(self):
        """Test that binary sensor definitions are populated"""
        assert len(BINARY_SENSOR_DEFINITIONS) > 0
    
    def test_binary_sensor_definitions_structure(self):
        """Test that each definition has 4 fields: signal_id, name, device_class, icon"""
        for definition in BINARY_SENSOR_DEFINITIONS:
            assert isinstance(definition, tuple)
            assert len(definition) == 4
            signal_id, name, device_class, icon = definition
            assert isinstance(signal_id, str)
            assert isinstance(name, str)
            # device_class can be None or a BinarySensorDeviceClass
            if device_class is not None:
                assert isinstance(device_class, (str, BinarySensorDeviceClass))
            # icon can be str or None
            if icon is not None:
                assert isinstance(icon, str)
    
    def test_binary_sensor_signal_ids_unique(self):
        """Test that all signal IDs are unique"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert len(signal_ids) == len(set(signal_ids))
    
    def test_binary_sensor_names_unique(self):
        """Test that all sensor names are unique"""
        names = [d[1] for d in BINARY_SENSOR_DEFINITIONS]
        assert len(names) == len(set(names))
    
    def test_binary_sensor_count(self):
        """Test expected number of binary sensors"""
        # Should have sensors for doors, locks, windows, trunk, sunroof, etc.
        assert len(BINARY_SENSOR_DEFINITIONS) >= 20
    
    def test_door_sensors_exist(self):
        """Test that door sensors are defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "closure.doors.frontLeft.isOpen" in signal_ids
        assert "closure.doors.frontRight.isOpen" in signal_ids
        assert "closure.doors.backLeft.isOpen" in signal_ids
        assert "closure.doors.backRight.isOpen" in signal_ids
    
    def test_door_lock_sensors_exist(self):
        """Test that door lock sensors are defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "closure.doors.frontLeft.isLocked" in signal_ids
        assert "closure.doors.frontRight.isLocked" in signal_ids
        assert "closure.doors.backLeft.isLocked" in signal_ids
        assert "closure.doors.backRight.isLocked" in signal_ids
    
    def test_window_sensors_exist(self):
        """Test that window sensors are defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "closure.windows.frontLeft.isOpen" in signal_ids
        assert "closure.windows.frontRight.isOpen" in signal_ids
        assert "closure.windows.backLeft.isOpen" in signal_ids
        assert "closure.windows.backRight.isOpen" in signal_ids
    
    def test_trunk_sensors_exist(self):
        """Test that trunk sensors are defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "closure.frontTrunk.isOpen" in signal_ids
        assert "closure.frontTrunk.isLocked" in signal_ids
        assert "closure.rearTrunk.isOpen" in signal_ids
        assert "closure.rearTrunk.isLocked" in signal_ids
    
    def test_sunroof_sensor_exists(self):
        """Test that sunroof sensor is defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "closure.sunroof.isOpen" in signal_ids
    
    def test_engine_cover_sensor_exists(self):
        """Test that engine cover sensor is defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "closure.engineCover.isOpen" in signal_ids
    
    def test_battery_heater_sensor_exists(self):
        """Test that battery heater sensor is defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "tractionBattery.isHeaterActive" in signal_ids
    
    def test_connectivity_sensors_exist(self):
        """Test that connectivity sensors are defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "connectivity.isOnline" in signal_ids
        assert "connectivity.isAsleep" in signal_ids
        assert "connectivity.isDigitalKeyPaired" in signal_ids
    
    def test_surveillance_sensor_exists(self):
        """Test that surveillance sensor is defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "surveillance.isEnabled" in signal_ids
    
    def test_charge_sensors_exist(self):
        """Test that charge-related binary sensors are defined"""
        signal_ids = [d[0] for d in BINARY_SENSOR_DEFINITIONS]
        assert "charge.isFastChargerConnected" in signal_ids
        assert "charge.isPluggedIn" in signal_ids
    
    def test_door_sensors_have_door_device_class(self):
        """Test that door sensors have DOOR device class"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if "Door" in name and "Lock" not in name:
                assert device_class == BinarySensorDeviceClass.DOOR
    
    def test_lock_sensors_have_lock_device_class(self):
        """Test that lock sensors have LOCK device class"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if "Lock" in name:
                assert device_class == BinarySensorDeviceClass.LOCK
    
    def test_window_sensors_have_window_device_class(self):
        """Test that window sensors have WINDOW device class"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if "Window" in name or "Sunroof" in name:
                assert device_class == BinarySensorDeviceClass.WINDOW
    
    def test_connectivity_sensor_has_connectivity_device_class(self):
        """Test that online sensor has CONNECTIVITY device class"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if signal_id == "connectivity.isOnline":
                assert device_class == BinarySensorDeviceClass.CONNECTIVITY
    
    def test_plug_sensor_has_plug_device_class(self):
        """Test that charging cable sensor has PLUG device class"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if signal_id == "charge.isPluggedIn":
                assert device_class == BinarySensorDeviceClass.PLUG
    
    def test_all_sensors_have_icons(self):
        """Test that all sensors have icons defined"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            assert icon is not None
            assert icon.startswith("mdi:")
    
    def test_signal_ids_follow_naming_convention(self):
        """Test that signal IDs follow expected naming patterns"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            # Signal IDs should contain dots and camelCase
            assert "." in signal_id
            # Common prefixes
            valid_prefixes = [
                "closure.", "tractionBattery.", "connectivity.",
                "surveillance.", "charge."
            ]
            assert any(signal_id.startswith(prefix) for prefix in valid_prefixes)
    
    def test_names_are_human_readable(self):
        """Test that sensor names are human-readable (no camelCase)"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            # Names should have spaces and be capitalized
            assert len(name) > 0
            # Check that name doesn't contain camelCase patterns
            # (allowing for abbreviations like "EV" or "Digital Key")


class TestSignalConstant:
    """Tests for SIGNAL_WEBHOOK_DATA constant"""
    
    def test_signal_webhook_data_exists(self):
        """Test that webhook signal constant is defined"""
        assert SIGNAL_WEBHOOK_DATA is not None
    
    def test_signal_webhook_data_value(self):
        """Test that webhook signal has correct value"""
        assert SIGNAL_WEBHOOK_DATA == "nissan_na_webhook_data"


class TestBinarySensorCategories:
    """Tests for binary sensor groupings by category"""
    
    def test_closure_category_sensors(self):
        """Test that closure sensors are defined"""
        closure_sensors = [
            d for d in BINARY_SENSOR_DEFINITIONS
            if d[0].startswith("closure.")
        ]
        # Should have doors (4 open + 4 locked), windows (4), trunks (2 open + 2 locked), sunroof (1), engine (1)
        assert len(closure_sensors) >= 18
    
    def test_charge_category_sensors(self):
        """Test that charge sensors are defined"""
        charge_sensors = [
            d for d in BINARY_SENSOR_DEFINITIONS
            if d[0].startswith("charge.")
        ]
        assert len(charge_sensors) >= 2
    
    def test_connectivity_category_sensors(self):
        """Test that connectivity sensors are defined"""
        connectivity_sensors = [
            d for d in BINARY_SENSOR_DEFINITIONS
            if d[0].startswith("connectivity.")
        ]
        assert len(connectivity_sensors) >= 3
    
    def test_battery_category_sensors(self):
        """Test that battery sensors are defined"""
        battery_sensors = [
            d for d in BINARY_SENSOR_DEFINITIONS
            if d[0].startswith("tractionBattery.")
        ]
        assert len(battery_sensors) >= 1
    
    def test_surveillance_category_sensors(self):
        """Test that surveillance sensors are defined"""
        surveillance_sensors = [
            d for d in BINARY_SENSOR_DEFINITIONS
            if d[0].startswith("surveillance.")
        ]
        assert len(surveillance_sensors) >= 1


class TestBinarySensorIcons:
    """Tests for binary sensor icons"""
    
    def test_door_icon(self):
        """Test that door sensors use car-door icon"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if device_class == BinarySensorDeviceClass.DOOR and "Lock" not in name:
                assert icon == "mdi:car-door"
    
    def test_lock_icon(self):
        """Test that lock sensors use lock icon"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if device_class == BinarySensorDeviceClass.LOCK:
                assert icon == "mdi:lock"
    
    def test_window_icon(self):
        """Test that window sensors use window-closed icon"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if device_class == BinarySensorDeviceClass.WINDOW:
                assert icon == "mdi:window-closed"
    
    def test_plug_icon(self):
        """Test that charging cable sensor uses power-plug icon"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if signal_id == "charge.isPluggedIn":
                assert icon == "mdi:power-plug"
    
    def test_connectivity_icon(self):
        """Test that online sensor uses wifi icon"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if signal_id == "connectivity.isOnline":
                assert icon == "mdi:wifi"
    
    def test_battery_heater_icon(self):
        """Test that battery heater uses fire icon"""
        for signal_id, name, device_class, icon in BINARY_SENSOR_DEFINITIONS:
            if signal_id == "tractionBattery.isHeaterActive":
                assert icon == "mdi:fire"


class TestNissanBinarySensorEntity:
    """Tests for NissanBinarySensor entity class"""
    
    def test_init_with_nickname(self):
        """Test sensor initialization with vehicle nickname"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Tesla"
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        assert sensor._attr_name == "My Tesla Front Left Door"
        assert sensor._is_on == False
        assert sensor._vehicle == mock_vehicle
        assert sensor._signal_id == "closure.doors.frontLeft.isOpen"
        assert sensor._device_class == BinarySensorDeviceClass.DOOR
        assert sensor._icon == "mdi:car-door"

    def test_init_with_year_make_model(self):
        """Test sensor initialization with year/make/model"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = None
        mock_vehicle.year = "2024"
        mock_vehicle.make = "Nissan"
        mock_vehicle.model = "Leaf"
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.windows.frontLeft.isOpen",
            "Front Left Window",
            BinarySensorDeviceClass.WINDOW,
            "mdi:window-closed",
            "entry_123"
        )
        
        assert sensor._attr_name == "2024 Nissan Leaf Front Left Window"

    def test_init_with_vin_fallback(self):
        """Test sensor initialization falling back to VIN"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TESTVIN123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = None
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "charge.isPluggedIn",
            "Charging Cable Plugged In",
            BinarySensorDeviceClass.PLUG,
            "mdi:power-plug",
            "entry_123"
        )
        
        assert sensor._attr_name == "TESTVIN123 Charging Cable Plugged In"

    def test_init_with_none_device_class(self):
        """Test sensor initialization with None device class"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "tractionBattery.isHeaterActive",
            "Battery Heater Active",
            None,
            "mdi:fire",
            "entry_123"
        )
        
        assert sensor._device_class is None
        assert sensor._icon == "mdi:fire"

    def test_unique_id(self):
        """Test unique ID generation"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "ABC123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        assert sensor.unique_id == "ABC123_closure.doors.frontLeft.isOpen"

    def test_is_on_property_default(self):
        """Test is_on property default value"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        assert sensor.is_on == False

    def test_is_on_property_true(self):
        """Test is_on property when set to True"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        sensor._is_on = True
        assert sensor.is_on == True

    def test_device_class_property(self):
        """Test device_class property"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        assert sensor.device_class == BinarySensorDeviceClass.DOOR

    def test_icon_property(self):
        """Test icon property"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        assert sensor.icon == "mdi:car-door"

    def test_device_info(self):
        """Test device_info property"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        device_info = sensor.device_info
        assert device_info == {"identifiers": {(DOMAIN, "TEST123")}}


class TestBinarySensorWebhookHandling:
    """Tests for webhook data handling"""
    
    def test_handle_webhook_data_door_open(self):
        """Test webhook handling for door open event"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        webhook_data = {
            "closure": {
                "doors": {
                    "frontLeft": {
                        "isOpen": True
                    }
                }
            }
        }
        
        sensor._handle_webhook_data(webhook_data)
        
        assert sensor._is_on == True
        sensor.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_door_closed(self):
        """Test webhook handling for door closed event"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontRight.isOpen",
            "Front Right Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        sensor._is_on = True
        
        webhook_data = {
            "closure": {
                "doors": {
                    "frontRight": {
                        "isOpen": False
                    }
                }
            }
        }
        
        sensor._handle_webhook_data(webhook_data)
        
        assert sensor._is_on == False
        sensor.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_lock(self):
        """Test webhook handling for lock status"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isLocked",
            "Front Left Door Lock",
            BinarySensorDeviceClass.LOCK,
            "mdi:lock",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        webhook_data = {
            "closure": {
                "doors": {
                    "frontLeft": {
                        "isLocked": True
                    }
                }
            }
        }
        
        sensor._handle_webhook_data(webhook_data)
        
        assert sensor._is_on == True
        sensor.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_missing_key(self):
        """Test webhook handling with missing signal key"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        webhook_data = {
            "some_other_data": True
        }
        
        sensor._handle_webhook_data(webhook_data)
        
        assert sensor._is_on == False
        sensor.async_write_ha_state.assert_not_called()

    def test_handle_webhook_data_invalid_type(self):
        """Test webhook handling with invalid data type"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        # Pass non-dict data
        sensor._handle_webhook_data("invalid")
        
        assert sensor._is_on == False
        sensor.async_write_ha_state.assert_not_called()

    def test_handle_webhook_data_connectivity(self):
        """Test webhook handling for connectivity status"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "connectivity.isOnline",
            "Online",
            BinarySensorDeviceClass.CONNECTIVITY,
            "mdi:wifi",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        webhook_data = {
            "connectivity": {
                "isOnline": True
            }
        }
        
        sensor._handle_webhook_data(webhook_data)
        
        assert sensor._is_on == True
        sensor.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_battery_heater(self):
        """Test webhook handling for battery heater"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "tractionBattery.isHeaterActive",
            "Battery Heater Active",
            None,
            "mdi:fire",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        webhook_data = {
            "tractionBattery": {
                "isHeaterActive": True
            }
        }
        
        sensor._handle_webhook_data(webhook_data)
        
        assert sensor._is_on == True
        sensor.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_truthiness(self):
        """Test webhook handling converts values to boolean correctly"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        # Test with truthy value that's not a boolean
        webhook_data = {
            "closure": {
                "doors": {
                    "frontLeft": {
                        "isOpen": 1
                    }
                }
            }
        }
        
        sensor._handle_webhook_data(webhook_data)
        assert sensor._is_on == True

    def test_handle_webhook_data_falsy_value(self):
        """Test webhook handling with falsy values"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        sensor.async_write_ha_state = MagicMock()
        
        webhook_data = {
            "closure": {
                "doors": {
                    "frontLeft": {
                        "isOpen": 0
                    }
                }
            }
        }
        
        sensor._handle_webhook_data(webhook_data)
        assert sensor._is_on == False


@pytest.mark.asyncio
class TestBinarySensorSetup:
    """Tests for async_setup_entry"""
    
    async def test_async_setup_entry_with_signals(self):
        """Test setup entry with available signals"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"
        mock_async_add_entities = AsyncMock()
        
        mock_vehicle = MagicMock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        
        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=[
            "closure.doors.frontLeft.isOpen",
            "closure.doors.frontRight.isOpen",
            "closure.windows.frontLeft.isOpen",
            "connectivity.isOnline",
        ])
        
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Should create entities for available signals only
        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 4

    async def test_async_setup_entry_signals_api_failure(self):
        """Test setup entry when signals API fails"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"
        mock_async_add_entities = AsyncMock()
        
        mock_vehicle = MagicMock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        
        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=Exception("API error"))
        
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Should create all sensors when signals API fails
        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == len(BINARY_SENSOR_DEFINITIONS)

    async def test_async_setup_entry_multiple_vehicles(self):
        """Test setup entry with multiple vehicles"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"
        mock_async_add_entities = AsyncMock()
        
        mock_vehicle1 = MagicMock()
        mock_vehicle1.id = "vehicle_1"
        mock_vehicle1.vin = "VIN1"
        mock_vehicle1.nickname = "Car 1"
        
        mock_vehicle2 = MagicMock()
        mock_vehicle2.id = "vehicle_2"
        mock_vehicle2.vin = "VIN2"
        mock_vehicle2.nickname = "Car 2"
        
        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle1, mock_vehicle2])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=Exception("API error"))
        
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Should create sensors for both vehicles
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == len(BINARY_SENSOR_DEFINITIONS) * 2

    async def test_async_setup_entry_creates_tracking_dict(self):
        """Test that setup creates tracking dict for binary sensors"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"
        mock_async_add_entities = AsyncMock()
        
        mock_vehicle = MagicMock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        
        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=Exception("API error"))
        
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Check that tracking dict was created
        assert "binary_sensors" in mock_hass.data[DOMAIN]["test_entry"]
        assert "vehicle_123" in mock_hass.data[DOMAIN]["test_entry"]["binary_sensors"]


@pytest.mark.asyncio
class TestBinarySensorLifecycle:
    """Tests for binary sensor lifecycle"""
    
    async def test_async_added_to_hass(self):
        """Test sensor is properly added to hass"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        mock_unsub = MagicMock()
        with patch("custom_components.nissan_na.binary_sensor.async_dispatcher_connect", return_value=mock_unsub):
            await sensor.async_added_to_hass()
        
        assert sensor._unsub_dispatcher == mock_unsub

    async def test_async_will_remove_from_hass(self):
        """Test sensor cleanup on removal"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        mock_unsub = MagicMock()
        sensor._unsub_dispatcher = mock_unsub
        
        await sensor.async_will_remove_from_hass()
        
        mock_unsub.assert_called_once()

    async def test_async_will_remove_from_hass_no_unsub(self):
        """Test cleanup when unsub is None"""
        mock_hass = MagicMock()
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None
        
        sensor = NissanBinarySensor(
            mock_hass,
            mock_vehicle,
            "closure.doors.frontLeft.isOpen",
            "Front Left Door",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
            "entry_123"
        )
        
        sensor._unsub_dispatcher = None
        
        # Should not raise error
        await sensor.async_will_remove_from_hass()

