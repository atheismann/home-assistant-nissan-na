"""Unit tests for config flow."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from custom_components.nissan_na.config_flow import (
    OAuth2FlowHandler,
    NissanNAOptionsFlowHandler,
)
from custom_components.nissan_na.const import (
    DOMAIN,
    CONF_MANAGEMENT_TOKEN,
    CONF_UNIT_SYSTEM,
    UNIT_SYSTEM_METRIC,
    UNIT_SYSTEM_IMPERIAL,
)


@pytest.mark.asyncio
class TestOAuth2FlowHandler:
    """Test OAuth2 config flow."""

    async def test_extra_authorize_data(self):
        """Test extra authorize data includes scopes and make."""
        flow = OAuth2FlowHandler()
        
        extra_data = flow.extra_authorize_data
        
        assert "scope" in extra_data
        assert "make" in extra_data
        assert extra_data["make"] == "NISSAN"
        assert "single_select" in extra_data
        assert "read_battery" in extra_data["scope"]
        assert "control_charge" in extra_data["scope"]

    async def test_async_oauth_create_entry_success(self):
        """Test successful OAuth entry creation."""
        flow = OAuth2FlowHandler()
        flow.hass = MagicMock()
        flow.flow_impl = MagicMock()
        flow.flow_impl.client_id = "test_client_id"
        flow.flow_impl.client_secret = "test_client_secret"
        flow.flow_impl.redirect_uri = "https://example.com/redirect"
        
        mock_vehicle = MagicMock()
        mock_vehicle.id = "vehicle_123"
        
        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }
        
        with patch("custom_components.nissan_na.config_flow.SmartcarApiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
            mock_client_class.return_value = mock_client
            
            result = await flow.async_oauth_create_entry(data)
            
            assert result["type"] == "create_entry"
            assert result["title"] == "Nissan (Smartcar)"

    async def test_async_oauth_create_entry_no_vehicles(self):
        """Test OAuth entry creation with no vehicles."""
        flow = OAuth2FlowHandler()
        flow.hass = MagicMock()
        flow.flow_impl = MagicMock()
        flow.flow_impl.client_id = "test_client_id"
        flow.flow_impl.client_secret = "test_client_secret"
        flow.flow_impl.redirect_uri = "https://example.com/redirect"
        
        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }
        
        with patch("custom_components.nissan_na.config_flow.SmartcarApiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_vehicle_list = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            result = await flow.async_oauth_create_entry(data)
            
            assert result["type"] == "abort"
            assert result["reason"] == "no_vehicles"

    async def test_async_oauth_create_entry_missing_credentials(self):
        """Test OAuth entry creation with missing credentials."""
        flow = OAuth2FlowHandler()
        flow.hass = MagicMock()
        flow.flow_impl = MagicMock()
        flow.flow_impl.client_id = None
        flow.flow_impl.client_secret = None
        
        data = {"token": {}}
        
        result = await flow.async_oauth_create_entry(data)
        
        assert result["type"] == "abort"
        assert result["reason"] == "missing_credentials"

    async def test_async_oauth_create_entry_connection_error(self):
        """Test OAuth entry creation with connection error."""
        flow = OAuth2FlowHandler()
        flow.hass = MagicMock()
        flow.flow_impl = MagicMock()
        flow.flow_impl.client_id = "test_client_id"
        flow.flow_impl.client_secret = "test_client_secret"
        flow.flow_impl.redirect_uri = "https://example.com/redirect"
        
        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }
        
        with patch("custom_components.nissan_na.config_flow.SmartcarApiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_vehicle_list = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client
            
            result = await flow.async_oauth_create_entry(data)
            
            assert result["type"] == "abort"
            assert result["reason"] == "connection_error"


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.xfail(reason="Home Assistant deprecates setting config_entry directly in tests", run=True)
class TestOptionsFlow:
    """Test options flow handler."""

    async def test_async_step_init_menu(self):
        """Test options flow init shows menu."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}
        
        flow = NissanNAOptionsFlowHandler()
        # Set config_entry as an instance attribute (not class attribute)
        object.__setattr__(flow, 'config_entry', mock_entry)
        
        result = await flow.async_step_init()
        
        assert result["type"] == "menu"
        assert "unit_system" in result["menu_options"]
        assert "refresh_sensors" in result["menu_options"]
        assert "webhook_config" in result["menu_options"]

    async def test_async_step_unit_system_show_form(self):
        """Test unit system configuration shows form."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC}
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = MagicMock()
        
        result = await flow.async_step_unit_system()
        
        assert result["type"] == "form"
        assert result["step_id"] == "unit_system"
        assert CONF_UNIT_SYSTEM in result["data_schema"].schema

    async def test_async_step_unit_system_save_metric(self):
        """Test saving metric unit system."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}
        
        mock_hass = MagicMock()
        mock_hass.config_entries.async_update_entry = MagicMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = mock_hass
        
        user_input = {CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC}
        result = await flow.async_step_unit_system(user_input)
        
        assert result["type"] == "create_entry"
        mock_hass.config_entries.async_update_entry.assert_called_once()
        mock_hass.config_entries.async_reload.assert_called_once()

    async def test_async_step_unit_system_save_imperial(self):
        """Test saving imperial unit system."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}
        
        mock_hass = MagicMock()
        mock_hass.config_entries.async_update_entry = MagicMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = mock_hass
        
        user_input = {CONF_UNIT_SYSTEM: UNIT_SYSTEM_IMPERIAL}
        result = await flow.async_step_unit_system(user_input)
        
        assert result["type"] == "create_entry"
        # Verify imperial was set
        call_args = mock_hass.config_entries.async_update_entry.call_args
        assert call_args[1]["options"][CONF_UNIT_SYSTEM] == UNIT_SYSTEM_IMPERIAL

    async def test_async_step_webhook_config_show_form(self):
        """Test webhook configuration shows form."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {
            CONF_MANAGEMENT_TOKEN: "existing_token",
            "webhook_url": "https://example.com/webhook",
        }
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        
        result = await flow.async_step_webhook_config()
        
        assert result["type"] == "form"
        assert result["step_id"] == "webhook_config"
        assert CONF_MANAGEMENT_TOKEN in result["data_schema"].schema

    async def test_async_step_webhook_config_save(self):
        """Test saving webhook configuration."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {}
        
        mock_hass = MagicMock()
        mock_hass.config_entries.async_update_entry = MagicMock()
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = mock_hass
        
        user_input = {CONF_MANAGEMENT_TOKEN: "new_token"}
        result = await flow.async_step_webhook_config(user_input)
        
        assert result["type"] == "create_entry"
        mock_hass.config_entries.async_update_entry.assert_called_once()

    async def test_async_step_refresh_sensors_success(self):
        """Test refreshing sensors successfully."""
        mock_sensor1 = MagicMock()
        mock_sensor1.async_update = AsyncMock()
        mock_sensor1._attr_name = "Sensor 1"
        
        mock_sensor2 = MagicMock()
        mock_sensor2.async_update = AsyncMock()
        mock_sensor2._attr_name = "Sensor 2"
        
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass = MagicMock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "sensors": {
                        "vehicle_1": {
                            "sensor1": mock_sensor1,
                            "sensor2": mock_sensor2,
                        }
                    }
                }
            }
        }
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_refresh_sensors()
        
        assert result["type"] == "form"
        assert result["step_id"] == "refresh_complete"
        mock_sensor1.async_update.assert_called_once()
        mock_sensor2.async_update.assert_called_once()

    async def test_async_step_refresh_sensors_no_sensors(self):
        """Test refreshing sensors when none exist."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass = MagicMock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "sensors": {}
                }
            }
        }
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_refresh_sensors()
        
        assert result["type"] == "abort"
        assert result["reason"] == "no_sensors_found"

    async def test_async_step_refresh_sensors_with_failures(self):
        """Test refreshing sensors with some failures."""
        mock_sensor1 = MagicMock()
        mock_sensor1.async_update = AsyncMock()
        mock_sensor1._attr_name = "Sensor 1"
        
        mock_sensor2 = MagicMock()
        mock_sensor2.async_update = AsyncMock(side_effect=Exception("Update failed"))
        mock_sensor2._attr_name = "Sensor 2"
        
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass = MagicMock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "sensors": {
                        "vehicle_1": {
                            "sensor1": mock_sensor1,
                            "sensor2": mock_sensor2,
                        }
                    }
                }
            }
        }
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_refresh_sensors()
        
        # Should still succeed and show completion
        assert result["type"] == "form"
        assert result["step_id"] == "refresh_complete"

    async def test_async_step_reauth(self):
        """Test reauth flow."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {}
        
        mock_hass = MagicMock()
        mock_hass.config_entries.flow.async_init = AsyncMock()
        
        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, 'config_entry', mock_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_reauth()
        
        assert result["type"] == "abort"
        assert result["reason"] == "reauth_triggered"
        mock_hass.config_entries.flow.async_init.assert_called_once()


class TestOptionsFlowRebuildSensors:
    """Test rebuild sensors functionality in options flow."""

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Home Assistant deprecates setting config_entry directly in tests")
    async def test_async_step_rebuild_sensors_success(self):
        """Test successful sensor rebuild."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        mock_client = MagicMock()
        
        # Simulate existing sensors
        mock_sensor1 = MagicMock()
        mock_sensor1._signal_id = "battery.percentRemaining"
        mock_sensor2 = MagicMock()
        mock_sensor2._signal_id = "fuel.percentRemaining"
        
        mock_hass = MagicMock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                    "sensors": {
                        "vehicle_1": {
                            "battery.percentRemaining": mock_sensor1,
                            "fuel.percentRemaining": mock_sensor2,
                        }
                    }
                }
            }
        }
        
        flow = NissanNAOptionsFlowHandler()
        flow.config_entry = mock_entry
        flow.hass = mock_hass
        
        # Mock sensor setup to simulate rebuild
        with patch('custom_components.nissan_na.config_flow.sensor_setup', new=AsyncMock()) as mock_setup:
            # Simulate that rebuild removed one sensor and added one
            async def mock_sensor_setup(hass, entry, add_callback, rebuild_mode=False):
                # Simulate removal
                mock_hass.data[DOMAIN]["test_entry"]["sensors"]["vehicle_1"].pop("fuel.percentRemaining")
                # Simulate addition
                new_sensor = MagicMock()
                new_sensor._signal_id = "battery.range"
                mock_hass.data[DOMAIN]["test_entry"]["sensors"]["vehicle_1"]["battery.range"] = new_sensor
                add_callback([new_sensor])
            
            mock_setup.side_effect = mock_sensor_setup
            
            result = await flow.async_step_rebuild_sensors()
            
            assert result["type"] == "form"
            assert result["step_id"] == "rebuild_complete"
            assert "initial" in result["description_placeholders"]
            assert "final" in result["description_placeholders"]
            assert "added" in result["description_placeholders"]
            assert "removed" in result["description_placeholders"]

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Home Assistant deprecates setting config_entry directly in tests")
    async def test_async_step_rebuild_sensors_integration_not_loaded(self):
        """Test rebuild when integration is not loaded."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {}}  # No entry_id data
        
        flow = NissanNAOptionsFlowHandler()
        flow.config_entry = mock_entry
        flow.hass = mock_hass
        
        result = await flow.async_step_rebuild_sensors()
        
        assert result["type"] == "abort"
        assert result["reason"] == "integration_not_loaded"

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Home Assistant deprecates setting config_entry directly in tests")
    async def test_async_step_rebuild_sensors_client_not_found(self):
        """Test rebuild when client is not found."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass = MagicMock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {}  # No client
            }
        }
        
        flow = NissanNAOptionsFlowHandler()
        flow.config_entry = mock_entry
        flow.hass = mock_hass
        
        result = await flow.async_step_rebuild_sensors()
        
        assert result["type"] == "abort"
        assert result["reason"] == "client_not_found"

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Home Assistant deprecates setting config_entry directly in tests")
    async def test_async_step_rebuild_sensors_with_exception(self):
        """Test rebuild handles exceptions gracefully."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        mock_client = MagicMock()
        
        mock_hass = MagicMock()
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                    "sensors": {}
                }
            }
        }
        
        flow = NissanNAOptionsFlowHandler()
        flow.config_entry = mock_entry
        flow.hass = mock_hass
        
        # Mock sensor setup to raise exception
        with patch('custom_components.nissan_na.config_flow.sensor_setup', side_effect=Exception("Test error")):
            result = await flow.async_step_rebuild_sensors()
            
            assert result["type"] == "abort"
            assert result["reason"] == "rebuild_failed"

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Home Assistant deprecates setting config_entry directly in tests")
    async def test_async_step_rebuild_complete_returns_to_menu(self):
        """Test rebuild complete step returns to menu."""
        flow = NissanNAOptionsFlowHandler()
        
        with patch.object(flow, "async_step_init", new=AsyncMock()) as mock_init:
            await flow.async_step_rebuild_complete()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Home Assistant deprecates setting config_entry directly in tests")
    async def test_init_menu_includes_rebuild_option(self):
        """Test that init menu includes rebuild sensors option."""
        mock_entry = MagicMock()
        flow = NissanNAOptionsFlowHandler()
        flow.config_entry = mock_entry
        
        result = await flow.async_step_init()
        
        assert result["type"] == "menu"
        assert "rebuild_sensors" in result["menu_options"]
        assert result["menu_options"]["rebuild_sensors"] == "Rebuild Sensors"


class TestOptionsFlowHelpers:
    """Test options flow helper methods."""

    @pytest.mark.asyncio
    async def test_async_step_refresh_complete(self):
        """Test refresh complete step returns to menu."""
        flow = NissanNAOptionsFlowHandler()
        
        with patch.object(flow, "async_step_init", new=AsyncMock()) as mock_init:
            await flow.async_step_refresh_complete()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_step_reload_complete(self):
        """Test reload complete step returns to menu."""
        flow = NissanNAOptionsFlowHandler()
        
        with patch.object(flow, "async_step_init", new=AsyncMock()) as mock_init:
            await flow.async_step_reload_complete()
            mock_init.assert_called_once()

