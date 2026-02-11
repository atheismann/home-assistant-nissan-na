"""Acceptance tests for end-to-end workflows."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.nissan_na.const import DOMAIN, CONF_UNIT_SYSTEM, UNIT_SYSTEM_METRIC, UNIT_SYSTEM_IMPERIAL


@pytest.mark.asyncio
class TestEndToEndSetup:
    """Test complete end-to-end setup workflows."""

    async def test_new_installation_with_single_vehicle(self, mock_hass, mock_config_entry):
        """Test new installation workflow with one vehicle."""
        # Mock Smartcar API client
        mock_vehicle = MagicMock()
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.vin = "TEST1234567890123"
        mock_vehicle.make = "NISSAN"
        mock_vehicle.model = "LEAF"
        mock_vehicle.year = 2024
        mock_vehicle.nickname = "My LEAF"
        
        mock_client = MagicMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=[
            "battery.percentRemaining",
            "battery.range",
            "charge.state",
            "charge.limit",
        ])
        mock_client.get_permissions = AsyncMock(return_value=[
            "read_battery",
            "read_charge",
            "control_charge",
        ])
        mock_client.get_vehicle_status = AsyncMock(return_value={
            "battery": {"percentRemaining": 0.85, "range": 250.0},
            "charge": {"state": "CHARGING", "limit": 80},
        })
        
        # Step 1: Setup integration
        from custom_components.nissan_na import async_setup_entry
        
        with patch("custom_components.nissan_na.SmartcarApiClient", return_value=mock_client):
            with patch.object(mock_hass.config_entries, "async_forward_entry_setups", new=AsyncMock()):
                result = await async_setup_entry(mock_hass, mock_config_entry)
                
                assert result is True
                assert DOMAIN in mock_hass.data
                assert "client" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]
        
        # Step 2: Setup sensor platform
        from custom_components.nissan_na.sensor import async_setup_entry as sensor_setup
        
        entities = []
        async def async_add_entities(new_entities):
            entities.extend(new_entities)
        
        await sensor_setup(mock_hass, mock_config_entry, async_add_entities)
        
        # Verify sensors were created
        assert len(entities) > 0
        battery_sensors = [e for e in entities if "Battery" in e._attr_name]
        assert len(battery_sensors) > 0
        
        # Step 3: Setup number platform
        from custom_components.nissan_na.number import async_setup_entry as number_setup
        
        number_entities = []
        async def async_add_number_entities(new_entities):
            number_entities.extend(new_entities)
        
        await number_setup(mock_hass, mock_config_entry, async_add_number_entities)
        
        # Verify charge limit number was created
        assert len(number_entities) == 1
        assert "Charge Limit" in number_entities[0]._attr_name

    async def test_unit_system_configuration_workflow(self, mock_hass, mock_config_entry, mock_client, mock_vehicle):
        """Test changing unit system configuration."""
        # Setup with metric units
        mock_config_entry.options = {CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC}
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.range"])
        mock_client.get_vehicle_status = AsyncMock(return_value={
            "battery": {"range": 250.0}
        })
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        # Step 1: Create sensors with metric units
        from custom_components.nissan_na.sensor import async_setup_entry as sensor_setup, NissanGenericSensor
        
        entities = []
        async def async_add_entities(new_entities):
            entities.extend(new_entities)
        
        await sensor_setup(mock_hass, mock_config_entry, async_add_entities)
        
        range_sensors = [e for e in entities if isinstance(e, NissanGenericSensor) and "Range" in e._attr_name]
        if range_sensors:
            range_sensor = range_sensors[0]
            assert range_sensor.native_value == 250.0
            assert range_sensor.native_unit_of_measurement == "km"
        
        # Step 2: Change to imperial units
        from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler
        
        options_flow = NissanNAOptionsFlowHandler()
        options_flow.config_entry = mock_config_entry
        options_flow.hass = mock_hass
        
        # Simulate user selecting imperial
        user_input = {CONF_UNIT_SYSTEM: UNIT_SYSTEM_IMPERIAL}
        
        with patch.object(mock_hass.config_entries, "async_update_entry"):
            with patch.object(mock_hass.config_entries, "async_reload", new=AsyncMock()):
                result = await options_flow.async_step_unit_system(user_input)
                
                assert result["type"] == "create_entry"
        
        # Step 3: Verify new sensors use imperial units
        mock_config_entry.options = {CONF_UNIT_SYSTEM: UNIT_SYSTEM_IMPERIAL}
        
        entities2 = []
        async def async_add_entities2(new_entities):
            entities2.extend(new_entities)
        
        await sensor_setup(mock_hass, mock_config_entry, async_add_entities2)
        
        range_sensors2 = [e for e in entities2 if isinstance(e, NissanGenericSensor) and "Range" in e._attr_name]
        if range_sensors2:
            range_sensor2 = range_sensors2[0]
            # 250 km should be converted to miles
            assert range_sensor2.native_value == pytest.approx(155.34, rel=0.01)
            assert range_sensor2.native_unit_of_measurement == "mi"

    async def test_webhook_data_update_workflow(self, mock_hass, mock_config_entry, mock_client, mock_vehicle):
        """Test receiving and processing webhook data."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining"])
        mock_client.get_vehicle_status = AsyncMock(return_value={
            "battery": {"percentRemaining": 0.80}
        })
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        # Step 1: Setup sensors
        from custom_components.nissan_na.sensor import async_setup_entry as sensor_setup, NissanGenericSensor
        
        entities = []
        async def async_add_entities(new_entities):
            entities.extend(new_entities)
        
        await sensor_setup(mock_hass, mock_config_entry, async_add_entities)
        
        battery_sensors = [e for e in entities if isinstance(e, NissanGenericSensor) and "Battery" in e._attr_name and "percentRemaining" in e._signal_id]
        assert len(battery_sensors) > 0
        
        battery_sensor = battery_sensors[0]
        assert battery_sensor.native_value == 0.80
        
        # Step 2: Simulate webhook update
        webhook_data = {"battery": {"percentRemaining": 0.90}}
        battery_sensor._handle_webhook_data(webhook_data)
        
        # Step 3: Verify sensor value updated
        assert battery_sensor.native_value == 0.90

    async def test_manual_sensor_refresh_workflow(self, mock_hass, mock_config_entry, mock_client, mock_vehicle):
        """Test manual sensor refresh via options flow."""
        # Setup mock sensors
        mock_sensor1 = MagicMock()
        mock_sensor1.async_update = AsyncMock()
        mock_sensor1._attr_name = "Battery Level"
        
        mock_sensor2 = MagicMock()
        mock_sensor2.async_update = AsyncMock()
        mock_sensor2._attr_name = "Range"
        
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "client": mock_client,
                    "sensors": {
                        mock_vehicle.id: {
                            "battery": mock_sensor1,
                            "range": mock_sensor2,
                        }
                    }
                }
            }
        }
        
        # Step 1: Open options flow
        from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler
        
        options_flow = NissanNAOptionsFlowHandler()
        options_flow.config_entry = mock_config_entry
        options_flow.hass = mock_hass
        
        # Step 2: Trigger refresh
        result = await options_flow.async_step_refresh_sensors()
        
        # Step 3: Verify all sensors were refreshed
        assert result["type"] == "form"
        assert result["step_id"] == "refresh_complete"
        mock_sensor1.async_update.assert_called_once()
        mock_sensor2.async_update.assert_called_once()

    async def test_charge_limit_control_workflow(self, mock_hass, mock_config_entry, mock_client, mock_vehicle):
        """Test setting charge limit via number entity."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.limit"])
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        
        # Step 1: Setup number entity
        from custom_components.nissan_na.number import async_setup_entry as number_setup
        
        entities = []
        async def async_add_entities(new_entities):
            entities.extend(new_entities)
        
        await number_setup(mock_hass, mock_config_entry, async_add_entities)
        
        assert len(entities) == 1
        charge_limit = entities[0]
        
        # Verify initial value
        assert charge_limit.native_value == 80
        
        # Step 2: Change charge limit
        mock_response = MagicMock()
        mock_response.status = 200
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            await charge_limit.async_set_value(90.0)
        
        # Step 3: Verify value updated
        assert charge_limit.native_value == 90

    async def test_complete_uninstall_workflow(self, mock_hass, mock_config_entry, mock_client):
        """Test complete integration uninstall."""
        # Step 1: Setup integration
        from custom_components.nissan_na import async_setup_entry, async_unload_entry
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[])
        
        with patch("custom_components.nissan_na.SmartcarApiClient", return_value=mock_client):
            with patch.object(mock_hass.config_entries, "async_forward_entry_setups", new=AsyncMock()):
                setup_result = await async_setup_entry(mock_hass, mock_config_entry)
                
                assert setup_result is True
                assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
        
        # Step 2: Unload integration
        with patch.object(mock_hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)):
            unload_result = await async_unload_entry(mock_hass, mock_config_entry)
            
            assert unload_result is True
            assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
