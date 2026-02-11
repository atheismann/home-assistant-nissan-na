"""Tests for diagnostics.py to reach 100% coverage"""
import pytest
from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry


class TestAsyncGetConfigEntryDiagnostics:
    """Tests for async_get_config_entry_diagnostics function"""
    
    @pytest.mark.asyncio
    async def test_diagnostics_returns_dict(self):
        """Test diagnostics returns a dictionary with expected keys"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        from custom_components.nissan_na.const import DOMAIN
        
        mock_hass = Mock()
        mock_hass.data = {}
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {
            "webhook_id": "test_webhook_123",
            "webhook_url": "https://example.com/webhook",
            "access_token": "secret_token_123",
            "client_id": "client_secret_456"
        }
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert isinstance(result, dict)
        assert "config_entry" in result
        assert "webhook" in result
        assert "vehicles" in result
        assert "sensors" in result
    
    @pytest.mark.asyncio
    async def test_diagnostics_redacts_sensitive_data(self):
        """Test diagnostics redacts access_token and other sensitive fields"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        
        mock_hass = Mock()
        mock_hass.data = {}
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {
            "webhook_id": "test_webhook_123",
            "access_token": "secret_token_123",
            "refresh_token": "secret_refresh_456",
            "client_id": "client_id_789",
            "client_secret": "client_secret_abc",
            "token": "token_xyz"
        }
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        # Check that sensitive data is redacted (replaced with "**REDACTED**")
        config_data = result["config_entry"]
        assert config_data["access_token"] == "**REDACTED**"
        assert config_data["refresh_token"] == "**REDACTED**"
        assert config_data["client_id"] == "**REDACTED**"
        assert config_data["client_secret"] == "**REDACTED**"
        assert config_data["token"] == "**REDACTED**"
    
    @pytest.mark.asyncio
    async def test_diagnostics_includes_webhook_info(self):
        """Test diagnostics includes webhook ID and URL"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        from custom_components.nissan_na.const import CONF_WEBHOOK_ID
        
        mock_hass = Mock()
        mock_hass.data = {}
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {
            CONF_WEBHOOK_ID: "webhook_abc123",
            "webhook_url": "https://homeassistant.local/api/webhook/webhook_abc123"
        }
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["webhook"]["id"] == "webhook_abc123"
        assert result["webhook"]["url"] == "https://homeassistant.local/api/webhook/webhook_abc123"
    
    @pytest.mark.asyncio
    async def test_diagnostics_webhook_not_configured(self):
        """Test diagnostics handles missing webhook configuration"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        
        mock_hass = Mock()
        mock_hass.data = {}
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {}
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["webhook"]["id"] == "Not configured"
        assert result["webhook"]["url"] == "Not configured"
    
    @pytest.mark.asyncio
    async def test_diagnostics_zero_vehicles_when_no_data(self):
        """Test diagnostics returns 0 vehicles when hass.data is empty"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        
        mock_hass = Mock()
        mock_hass.data = {}
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {"webhook_id": "test"}
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["vehicles"] == 0
        assert result["sensors"] == 0
    
    @pytest.mark.asyncio
    async def test_diagnostics_counts_vehicles_from_hass_data(self):
        """Test diagnostics counts vehicles from hass.data"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        from custom_components.nissan_na.const import DOMAIN
        
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "vehicles": ["vehicle1", "vehicle2", "vehicle3"],
                    "sensors": {}
                }
            }
        }
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {"webhook_id": "test"}
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["vehicles"] == 3
    
    @pytest.mark.asyncio
    async def test_diagnostics_counts_sensors_from_hass_data(self):
        """Test diagnostics counts sensors from hass.data"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        from custom_components.nissan_na.const import DOMAIN
        
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "vehicles": [],
                    "sensors": {
                        "vehicle1": ["sensor1", "sensor2"],
                        "vehicle2": ["sensor3", "sensor4", "sensor5"]
                    }
                }
            }
        }
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {"webhook_id": "test"}
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["sensors"] == 5  # 2 + 3
    
    @pytest.mark.asyncio
    async def test_diagnostics_handles_missing_vehicles_key(self):
        """Test diagnostics handles missing vehicles key in hass.data"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        from custom_components.nissan_na.const import DOMAIN
        
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "sensors": {}
                }
            }
        }
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {"webhook_id": "test"}
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["vehicles"] == 0
    
    @pytest.mark.asyncio
    async def test_diagnostics_handles_missing_sensors_key(self):
        """Test diagnostics handles missing sensors key in hass.data"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        from custom_components.nissan_na.const import DOMAIN
        
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "vehicles": ["vehicle1"]
                }
            }
        }
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {"webhook_id": "test"}
        mock_config_entry.entry_id = "test_entry_id"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["sensors"] == 0
    
    @pytest.mark.asyncio
    async def test_diagnostics_with_complete_data(self):
        """Test diagnostics with complete vehicle and sensor data"""
        from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics
        from custom_components.nissan_na.const import DOMAIN, CONF_WEBHOOK_ID
        
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                "entry_123": {
                    "vehicles": ["vin_abc", "vin_xyz"],
                    "sensors": {
                        "vin_abc": ["battery", "range", "odometer"],
                        "vin_xyz": ["battery", "range"]
                    }
                }
            }
        }
        
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {
            CONF_WEBHOOK_ID: "hook_123",
            "webhook_url": "https://test.local/webhook/hook_123",
            "access_token": "secret",
            "refresh_token": "secret2"
        }
        mock_config_entry.entry_id = "entry_123"
        
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
        
        assert result["vehicles"] == 2
        assert result["sensors"] == 5
        assert result["webhook"]["id"] == "hook_123"
        assert result["config_entry"]["access_token"] == "**REDACTED**"
        assert result["config_entry"]["refresh_token"] == "**REDACTED**"


class TestToRedactConstant:
    """Tests for TO_REDACT constant"""
    
    def test_to_redact_contains_expected_fields(self):
        """Test TO_REDACT contains all sensitive field names"""
        from custom_components.nissan_na.diagnostics import TO_REDACT
        
        assert "access_token" in TO_REDACT
        assert "refresh_token" in TO_REDACT
        assert "client_id" in TO_REDACT
        assert "client_secret" in TO_REDACT
        assert "token" in TO_REDACT
    
    def test_to_redact_is_set(self):
        """Test TO_REDACT is a set"""
        from custom_components.nissan_na.diagnostics import TO_REDACT
        
        assert isinstance(TO_REDACT, set)
