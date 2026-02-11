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

    @pytest.mark.asyncio
    async def test_setup_with_vehicles_and_signals(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup creates sensors when signals are available."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining", "charge.state"])
        mock_client.get_vehicle_status = AsyncMock(return_value={"battery": {"percentRemaining": 0.85}})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create sensors for available signals plus webhook sensor
        assert len(entities) > 0
        assert any(isinstance(e, WebhookUrlSensor) for e in entities)

    @pytest.mark.asyncio
    async def test_setup_without_signals_skips_vehicle(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup skips vehicle when signals API fails."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=Exception("API error"))
        mock_client.get_vehicle_status = AsyncMock(return_value={"battery": {"percentRemaining": 0.85}})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should only have webhook sensor (no vehicle sensors since signals API failed)
        assert any(isinstance(e, WebhookUrlSensor) for e in entities)

    @pytest.mark.asyncio
    async def test_setup_with_failed_status_fetch(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup continues when status fetch fails."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining"])
        mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("Status fetch failed"))
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should still create entities with empty status
        assert len(entities) > 0

    @pytest.mark.asyncio
    async def test_setup_filters_sensors_by_available_signals(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup only creates sensors for available signals."""
        # Only battery and charge signals available, not others
        available_signals = [
            "battery.percentRemaining",
            "battery.range",
            "charge.state",
        ]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={"battery": {"percentRemaining": 0.85, "range": 250}})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Count non-webhook sensors
        sensor_entities = [e for e in entities if not isinstance(e, WebhookUrlSensor)]
        
        # Should create sensors only for the 3 available signals
        assert len(sensor_entities) == 3
        
        # All created sensors should be for available signals
        for sensor in sensor_entities:
            assert sensor._signal_id in available_signals
    
    @pytest.mark.asyncio
    async def test_setup_only_adds_new_sensors(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test that boot only adds new sensors, doesn't remove existing ones."""
        available_signals = [
            "battery.percentRemaining",
            "battery.range",
            "charge.state",
        ]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        # Simulate existing sensors in data (one that's available, one that's not)
        existing_sensor = MagicMock()
        existing_sensor._signal_id = "battery.percentRemaining"
        unavailable_sensor = MagicMock()
        unavailable_sensor._signal_id = "fuel.percentRemaining"  # Not in available_signals
        
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "client": mock_client,
                    "sensors": {
                        mock_vehicle.id: {
                            "battery.percentRemaining": existing_sensor,
                            "fuel.percentRemaining": unavailable_sensor,  # Not available but should NOT be removed
                        }
                    }
                }
            }
        }
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should only add 2 NEW sensors (battery.range and charge.state), not battery.percentRemaining (already exists)
        sensor_entities = [e for e in entities if not isinstance(e, WebhookUrlSensor)]
        assert len(sensor_entities) == 2
        
        # Existing unavailable sensor should still be in tracking (not removed at boot)
        assert "fuel.percentRemaining" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
    
    @pytest.mark.asyncio
    async def test_rebuild_mode_removes_unavailable_sensors(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test that rebuild mode removes sensors that are no longer available."""
        from homeassistant.helpers import entity_registry
        
        available_signals = [
            "battery.percentRemaining",
            "battery.range",
        ]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        # Mock entity registry
        mock_registry = MagicMock(spec=entity_registry.EntityRegistry)
        mock_registry.async_get = MagicMock(return_value=MagicMock())
        mock_registry.async_remove = MagicMock()
        
        # Mock the entity registry retrieval
        with patch.object(entity_registry, 'async_get', return_value=mock_registry):
            # Simulate existing sensors (one available, one not)
            existing_sensor = MagicMock()
            existing_sensor._signal_id = "battery.percentRemaining"
            existing_sensor.entity_id = "sensor.test_battery"
            
            unavailable_sensor = MagicMock()
            unavailable_sensor._signal_id = "fuel.percentRemaining"
            unavailable_sensor.entity_id = "sensor.test_fuel"
            
            mock_hass.data = {
                DOMAIN: {
                    mock_config_entry.entry_id: {
                        "client": mock_client,
                        "sensors": {
                            mock_vehicle.id: {
                                "battery.percentRemaining": existing_sensor,
                                "fuel.percentRemaining": unavailable_sensor,
                            }
                        }
                    }
                }
            }
            
            entities = []
            def async_add_entities(new_entities):
                """Sync callback for adding entities."""
                entities.extend(new_entities)
            
            # Call with rebuild_mode=True
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities, rebuild_mode=True)
            
            # Should remove unavailable sensor
            assert "fuel.percentRemaining" not in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            
            # Should keep available sensor
            assert "battery.percentRemaining" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            
            # Should add the new sensor (battery.range)
            sensor_entities = [e for e in entities if not isinstance(e, WebhookUrlSensor)]
            assert any(s._signal_id == "battery.range" for s in sensor_entities)
    
    @pytest.mark.asyncio
    async def test_rebuild_mode_with_no_removals_needed(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test rebuild mode when all existing sensors are still available."""
        available_signals = [
            "battery.percentRemaining",
            "battery.range",
            "charge.state",
        ]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        from homeassistant.helpers import entity_registry
        mock_registry = MagicMock(spec=entity_registry.EntityRegistry)
        mock_registry.async_get = MagicMock(return_value=MagicMock())
        mock_registry.async_remove = MagicMock()
        
        with patch.object(entity_registry, 'async_get', return_value=mock_registry):
            # Simulate existing sensors that are all still available
            existing_sensor1 = MagicMock()
            existing_sensor1._signal_id = "battery.percentRemaining"
            existing_sensor1.entity_id = "sensor.test_battery"
            
            existing_sensor2 = MagicMock()
            existing_sensor2._signal_id = "battery.range"
            existing_sensor2.entity_id = "sensor.test_range"
            
            mock_hass.data = {
                DOMAIN: {
                    mock_config_entry.entry_id: {
                        "client": mock_client,
                        "sensors": {
                            mock_vehicle.id: {
                                "battery.percentRemaining": existing_sensor1,
                                "battery.range": existing_sensor2,
                            }
                        }
                    }
                }
            }
            
            entities = []
            def async_add_entities(new_entities):
                """Sync callback for adding entities."""
                entities.extend(new_entities)
            
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities, rebuild_mode=True)
            
            # Should not remove any sensors
            assert "battery.percentRemaining" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            assert "battery.range" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            
            # Should add the new sensor (charge.state)
            sensor_entities = [e for e in entities if not isinstance(e, WebhookUrlSensor)]
            assert any(s._signal_id == "charge.state" for s in sensor_entities)
            
            # Verify no removals were attempted
            mock_registry.async_remove.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rebuild_mode_with_multiple_vehicles(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test rebuild mode handles multiple vehicles correctly."""
        from homeassistant.helpers import entity_registry
        
        # Create second vehicle
        mock_vehicle2 = MagicMock()
        mock_vehicle2.id = "vehicle_456"
        mock_vehicle2.make = "NISSAN"
        mock_vehicle2.model = "ARIYA"
        mock_vehicle2.year = 2024
        
        # Different available signals per vehicle
        available_signals_v1 = ["battery.percentRemaining", "battery.range"]
        available_signals_v2 = ["battery.percentRemaining", "charge.state"]
        
        async def get_signals(vehicle_id):
            if vehicle_id == mock_vehicle.id:
                return available_signals_v1
            return available_signals_v2
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle, mock_vehicle2])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=get_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        mock_registry = MagicMock(spec=entity_registry.EntityRegistry)
        mock_registry.async_get = MagicMock(return_value=MagicMock())
        mock_registry.async_remove = MagicMock()
        
        with patch.object(entity_registry, 'async_get', return_value=mock_registry):
            # Existing sensors for both vehicles
            sensor_v1_battery = MagicMock()
            sensor_v1_battery._signal_id = "battery.percentRemaining"
            sensor_v1_battery.entity_id = "sensor.leaf_battery"
            
            sensor_v1_fuel = MagicMock()
            sensor_v1_fuel._signal_id = "fuel.percentRemaining"  # Not available
            sensor_v1_fuel.entity_id = "sensor.leaf_fuel"
            
            sensor_v2_battery = MagicMock()
            sensor_v2_battery._signal_id = "battery.percentRemaining"
            sensor_v2_battery.entity_id = "sensor.ariya_battery"
            
            sensor_v2_range = MagicMock()
            sensor_v2_range._signal_id = "battery.range"  # Not available for v2
            sensor_v2_range.entity_id = "sensor.ariya_range"
            
            mock_hass.data = {
                DOMAIN: {
                    mock_config_entry.entry_id: {
                        "client": mock_client,
                        "sensors": {
                            mock_vehicle.id: {
                                "battery.percentRemaining": sensor_v1_battery,
                                "fuel.percentRemaining": sensor_v1_fuel,
                            },
                            mock_vehicle2.id: {
                                "battery.percentRemaining": sensor_v2_battery,
                                "battery.range": sensor_v2_range,
                            }
                        }
                    }
                }
            }
            
            entities = []
            def async_add_entities(new_entities):
                """Sync callback for adding entities."""
                entities.extend(new_entities)
            
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities, rebuild_mode=True)
            
            # Vehicle 1: should remove fuel, keep battery, add range
            assert "fuel.percentRemaining" not in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            assert "battery.percentRemaining" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            
            # Vehicle 2: should remove range, keep battery, add charge.state
            assert "battery.range" not in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle2.id]
            assert "battery.percentRemaining" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle2.id]
            
            # Verify correct number of removals
            assert mock_registry.async_remove.call_count == 2
    
    @pytest.mark.asyncio
    async def test_rebuild_mode_handles_sensor_without_entity_id(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test rebuild mode handles sensors that don't have entity_id yet."""
        from homeassistant.helpers import entity_registry
        
        available_signals = ["battery.percentRemaining"]
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        mock_registry = MagicMock(spec=entity_registry.EntityRegistry)
        mock_registry.async_get = MagicMock(return_value=MagicMock())
        mock_registry.async_remove = MagicMock()
        
        with patch.object(entity_registry, 'async_get', return_value=mock_registry):
            # Sensor without entity_id (not yet registered)
            unavailable_sensor = MagicMock()
            unavailable_sensor._signal_id = "fuel.percentRemaining"
            unavailable_sensor.entity_id = None
            
            mock_hass.data = {
                DOMAIN: {
                    mock_config_entry.entry_id: {
                        "client": mock_client,
                        "sensors": {
                            mock_vehicle.id: {
                                "fuel.percentRemaining": unavailable_sensor,
                            }
                        }
                    }
                }
            }
            
            entities = []
            def async_add_entities(new_entities):
                """Sync callback for adding entities."""
                entities.extend(new_entities)
            
            # Should not crash when sensor has no entity_id
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities, rebuild_mode=True)
            
            # Should still remove from tracking even without entity_id
            assert "fuel.percentRemaining" not in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            
            # Should not attempt to remove from registry
            mock_registry.async_remove.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_boot_preserves_all_existing_sensors(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test that normal boot preserves all existing sensors regardless of availability."""
        available_signals = ["battery.percentRemaining"]
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        # Many existing sensors, only one available
        existing_sensors = {}
        for signal in ["battery.percentRemaining", "fuel.percentRemaining", "charge.state", "odometer.distance"]:
            sensor = MagicMock()
            sensor._signal_id = signal
            sensor.entity_id = f"sensor.test_{signal.replace('.', '_')}"
            existing_sensors[signal] = sensor
        
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "client": mock_client,
                    "sensors": {
                        mock_vehicle.id: existing_sensors
                    }
                }
            }
        }
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        # Normal boot (rebuild_mode=False, the default)
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # All existing sensors should still be in tracking
        assert len(mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]) == 4
        assert "fuel.percentRemaining" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
        assert "charge.state" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
        assert "odometer.distance" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
        
        # Should not add new entities for already existing sensors
        sensor_entities = [e for e in entities if not isinstance(e, WebhookUrlSensor)]
        assert len(sensor_entities) == 0


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




