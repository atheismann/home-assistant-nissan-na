"""Tests for api.py to reach 90%+ coverage"""
import pytest
from unittest.mock import Mock

from custom_components.nissan_na.api import SmartcarOAuth2Implementation


class TestSmartcarOAuth2Implementation:
    """Tests for SmartcarOAuth2Implementation class"""
    
    def test_extra_authorize_data_returns_dict(self):
        """Test extra_authorize_data returns a dictionary"""
        # Create instance with minimal required params
        impl = SmartcarOAuth2Implementation(
            Mock(),  # hass
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        
        assert isinstance(extra_data, dict)
        assert "scope" in extra_data
        assert "make" in extra_data
        assert "single_select" in extra_data
    
    def test_extra_authorize_data_includes_required_scopes(self):
        """Test extra_authorize_data includes required scopes"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        scope = extra_data["scope"]
        
        # Check for required scopes
        assert "required:read_vehicle_info" in scope
        assert "required:read_location" in scope
        assert "required:read_odometer" in scope
        assert "required:control_security" in scope
    
    def test_extra_authorize_data_includes_battery_scopes(self):
        """Test extra_authorize_data includes battery/charge scopes"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        scope = extra_data["scope"]
        
        # Check for EV/Battery scopes
        assert "read_battery" in scope
        assert "read_charge" in scope
        assert "control_charge" in scope
        assert "read_charge_locations" in scope
        assert "read_charge_records" in scope
    
    def test_extra_authorize_data_includes_general_vehicle_scopes(self):
        """Test extra_authorize_data includes general vehicle data scopes"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        scope = extra_data["scope"]
        
        # Check for general vehicle data scopes
        assert "read_fuel" in scope
        assert "read_vin" in scope
        assert "read_security" in scope
        assert "read_tires" in scope
        assert "read_engine_oil" in scope
    
    def test_extra_authorize_data_includes_climate_scopes(self):
        """Test extra_authorize_data includes climate control scopes"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        scope = extra_data["scope"]
        
        # Check for climate scopes
        assert "read_climate" in scope
        assert "control_climate" in scope
    
    def test_extra_authorize_data_includes_advanced_scopes(self):
        """Test extra_authorize_data includes advanced feature scopes"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        scope = extra_data["scope"]
        
        # Check for advanced scopes
        assert "read_alerts" in scope
        assert "read_diagnostics" in scope
        assert "read_extended_vehicle_info" in scope
        assert "read_service_history" in scope
    
    def test_extra_authorize_data_includes_control_scopes(self):
        """Test extra_authorize_data includes additional control scopes"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        scope = extra_data["scope"]
        
        # Check for control scopes
        assert "control_navigation" in scope
        assert "control_trunk" in scope
    
    def test_extra_authorize_data_make_is_nissan(self):
        """Test extra_authorize_data sets make to NISSAN"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        
        assert extra_data["make"] == "NISSAN"
    
    def test_extra_authorize_data_single_select_is_true(self):
        """Test extra_authorize_data sets single_select to true"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        
        assert extra_data["single_select"] == "true"
    
    def test_extra_authorize_data_scopes_are_space_separated(self):
        """Test extra_authorize_data scopes are joined with spaces"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        extra_data = impl.extra_authorize_data
        scope = extra_data["scope"]
        
        # Should be space-separated, not comma or other delimiter
        assert " " in scope
        assert "," not in scope
        # Should contain multiple scopes
        scopes_list = scope.split(" ")
        assert len(scopes_list) > 10
    
    def test_inherits_from_local_oauth2_implementation(self):
        """Test SmartcarOAuth2Implementation inherits from LocalOAuth2Implementation"""
        from homeassistant.helpers import config_entry_oauth2_flow
        
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token"
        )
        
        assert isinstance(impl, config_entry_oauth2_flow.LocalOAuth2Implementation)
