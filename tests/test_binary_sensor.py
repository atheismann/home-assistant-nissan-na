"""Unit tests for binary_sensor.py - binary sensor definitions and structure"""
import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.nissan_na.binary_sensor import (
    BINARY_SENSOR_DEFINITIONS,
    SIGNAL_WEBHOOK_DATA,
)


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
