"""Unit tests for sensor platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from homeassistant.components.sensor import SensorDeviceClass
from custom_components.nissan_na.sensor import WebhookUrlSensor, NissanGenericSensor, async_setup_entry
from custom_components.nissan_na.const import DOMAIN


@pytest.mark.asyncio
class TestSensorDefinitions:
    """Test sensor definitions."""

    def test_sensor_definitions_exist(self):
        """Test that sensor definitions are properly defined."""
        from custom_components.nissan_na.sensor import SENSOR_DEFINITIONS
        
        assert len(SENSOR_DEFINITIONS) > 0
        assert len(SENSOR_DEFINITIONS) >= 30  # At least 30 sensor definitions

    def test_sensor_definitions_format(self):
        """Test that all sensor definitions have correct format."""
        from custom_components.nissan_na.sensor import SENSOR_DEFINITIONS
        
        for definition in SENSOR_DEFINITIONS:
            assert len(definition) == 7, f"Definition {definition[0]} has wrong length"
            signal_id, field_name, name, unit, permission, icon, device_class = definition
            assert isinstance(signal_id, str)
            assert isinstance(field_name, str)
            assert isinstance(name, str)
            assert unit is None or isinstance(unit, str)
            assert permission is None or isinstance(permission, str)
            assert icon is None or isinstance(icon, str)

    def test_sensor_definitions_battery_sensors(self):
        """Test that battery sensors are defined."""
        from custom_components.nissan_na.sensor import SENSOR_DEFINITIONS
        
        battery_sensors = [d for d in SENSOR_DEFINITIONS if d[0].startswith("battery")]
        assert len(battery_sensors) >= 3

    def test_sensor_definitions_charge_sensors(self):
        """Test that charge sensors are defined."""
        from custom_components.nissan_na.sensor import SENSOR_DEFINITIONS
        
        charge_sensors = [d for d in SENSOR_DEFINITIONS if d[0].startswith("charge")]
        assert len(charge_sensors) >= 5


class TestSensorSignalHandling:
    """Test signal handling in sensor module."""

    def test_signal_webhook_data_defined(self):
        """Test that webhook signal is defined."""
        from custom_components.nissan_na.sensor import SIGNAL_WEBHOOK_DATA
        
        assert SIGNAL_WEBHOOK_DATA == "nissan_na_webhook_data"
        assert isinstance(SIGNAL_WEBHOOK_DATA, str)



@pytest.mark.asyncio
class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.xfail(reason="Integration test requiring complex entity registration mocking")
    async def test_setup_with_vehicles_and_signals(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup creates sensors when signals are available."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining", "charge.state"])
        mock_client.get_vehicle_status = AsyncMock(return_value={"battery": {"percentRemaining": 0.85}})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        entities = []
        async def async_add_entities(new_entities):
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create sensors for available signals plus webhook sensor
        assert len(entities) > 0
        assert any(isinstance(e, WebhookUrlSensor) for e in entities)

    @pytest.mark.xfail(reason="Integration test requiring complex entity registration mocking")
    async def test_setup_without_signals_uses_permissions(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup falls back to permissions when signals API fails."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=Exception("API error"))
        mock_client.get_permissions = AsyncMock(return_value=["read_battery", "read_charge"])
        mock_client.get_vehicle_status = AsyncMock(return_value={"battery": {"percentRemaining": 0.85}})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        entities = []
        async def async_add_entities(new_entities):
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        assert len(entities) > 0

    @pytest.mark.xfail(reason="Integration test requiring complex entity registration mocking")
    async def test_setup_with_failed_status_fetch(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup continues when status fetch fails."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining"])
        mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("Status fetch failed"))
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        entities = []
        async def async_add_entities(new_entities):
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should still create entities with empty status
        assert len(entities) > 0


class TestNissanGenericSensor:
    """Test NissanGenericSensor class."""

    def test_sensor_initialization_with_nickname(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor initialization with vehicle nickname."""
        status = {"battery": {"percentRemaining": 0.85}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        assert sensor._attr_name == "Test Vehicle Battery Level"
        assert sensor.unique_id == "VIN123ABC_battery.percentRemaining"
        assert sensor._api_key == "battery"
        assert sensor._field_name == "percentRemaining"

    def test_sensor_initialization_without_nickname(self, mock_hass, mock_vehicle_no_nickname, mock_config_entry_metric):
        """Test sensor initialization with year/make/model."""
        status = {"battery": {"percentRemaining": 0.85}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle_no_nickname,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        assert sensor._attr_name == "2024 NISSAN ARIYA Battery Level"

    def test_sensor_native_value_from_dict(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test extracting native value from dictionary."""
        status = {"battery": {"percentRemaining": 0.85, "range": 250.5}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        assert sensor.native_value == 0.85

    def test_sensor_native_value_missing_data(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test native value when data is missing."""
        status = {}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        assert sensor.native_value is None

    def test_sensor_unit_conversion_metric(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor uses metric units when configured."""
        status = {"battery": {"range": 250.0}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.range",
            "range",
            "Range",
            "km",
            "mdi:battery-high",
            None,
            mock_config_entry_metric.entry_id,
        )
        
        assert sensor.native_value == 250.0
        assert sensor.native_unit_of_measurement == "km"

    def test_sensor_unit_conversion_imperial(self, mock_hass, mock_vehicle, mock_config_entry_imperial):
        """Test sensor converts to imperial units when configured."""
        status = {"battery": {"range": 250.0}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.range",
            "range",
            "Range",
            "km",
            "mdi:battery-high",
            None,
            mock_config_entry_imperial.entry_id,
        )
        
        # 250 km should convert to miles
        assert sensor.native_value == pytest.approx(155.34, rel=0.01)
        assert sensor.native_unit_of_measurement == "mi"

    def test_sensor_no_unit_conversion_for_percentage(self, mock_hass, mock_vehicle, mock_config_entry_imperial):
        """Test sensor doesn't convert percentage values."""
        status = {"battery": {"percentRemaining": 0.85}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_imperial.entry_id,
        )
        
        assert sensor.native_value == 0.85
        assert sensor.native_unit_of_measurement == "%"

    @pytest.mark.asyncio
    async def test_sensor_async_added_to_hass(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor subscribes to webhook updates."""
        status = {"battery": {"percentRemaining": 0.85}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        with patch("custom_components.nissan_na.sensor.async_dispatcher_connect") as mock_connect:
            await sensor.async_added_to_hass()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_sensor_async_will_remove_from_hass(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor unsubscribes from webhook updates."""
        status = {"battery": {"percentRemaining": 0.85}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        # Mock the unsub dispatcher
        mock_unsub = MagicMock()
        sensor._unsub_dispatcher = mock_unsub
        
        await sensor.async_will_remove_from_hass()
        mock_unsub.assert_called_once()

    def test_sensor_handle_webhook_data(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor handles webhook data updates."""
        status = {"battery": {"percentRemaining": 0.85}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            None,
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        # Mock async_write_ha_state to avoid entity_id requirement
        sensor.async_write_ha_state = MagicMock()
        
        # Update via webhook
        webhook_data = {"battery": {"percentRemaining": 0.90}}
        sensor._handle_webhook_data(webhook_data)
        
        # Status should be updated
        assert sensor._status["battery"]["percentRemaining"] == 0.90
        # Verify state update was triggered
        sensor.async_write_ha_state.assert_called_once()

    def test_sensor_properties(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor properties."""
        status = {"battery": {"percentRemaining": 0.85}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.percentRemaining",
            "percentRemaining",
            "Battery Level",
            "%",
            "mdi:battery",
            SensorDeviceClass.BATTERY,
            mock_config_entry_metric.entry_id,
        )
        
        assert sensor.icon == "mdi:battery"
        assert sensor.device_class == SensorDeviceClass.BATTERY
        assert sensor.device_info is not None
        assert (DOMAIN, mock_vehicle.vin) in sensor.device_info["identifiers"]


class TestWebhookUrlSensor:
    """Test WebhookUrlSensor class."""

    def test_webhook_sensor_initialization(self, mock_hass, mock_config_entry):
        """Test webhook sensor initialization."""
        sensor = WebhookUrlSensor(mock_hass, mock_config_entry)
        
        assert sensor._attr_name == "Webhook URL"
        assert sensor._attr_icon == "mdi:webhook"
        assert sensor._attr_unique_id == "test_entry_id_webhook_url"

    def test_webhook_sensor_native_value(self, mock_hass, mock_config_entry):
        """Test webhook sensor returns webhook URL."""
        sensor = WebhookUrlSensor(mock_hass, mock_config_entry)
        
        assert sensor.native_value == "https://example.com/webhook"

    def test_webhook_sensor_no_url_configured(self, mock_hass):
        """Test webhook sensor when no URL is configured."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {}
        
        sensor = WebhookUrlSensor(mock_hass, entry)
        
        assert sensor.native_value == "Not configured"

    @pytest.mark.asyncio
    async def test_webhook_sensor_async_update(self, mock_hass, mock_config_entry):
        """Test webhook sensor async_update does nothing."""
        sensor = WebhookUrlSensor(mock_hass, mock_config_entry)
        
        # Should not raise any exceptions
        await sensor.async_update()

    def test_webhook_sensor_device_info(self, mock_hass, mock_config_entry):
        """Test webhook sensor device info."""
        from custom_components.nissan_na.const import DOMAIN
        
        sensor = WebhookUrlSensor(mock_hass, mock_config_entry)
        
        device_info = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "webhook")}
        assert device_info["name"] == "Webhook Configuration"
        assert device_info["manufacturer"] == "Smartcar"




