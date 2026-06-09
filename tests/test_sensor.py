"""Unit tests for sensor platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from homeassistant.components.sensor import SensorDeviceClass
from custom_components.nissan_na.sensor import NissanGenericSensor, async_setup_entry
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
        
        # Should create sensors for available signals
        assert len(entities) > 0

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
        
        # Should have no sensors when signals API fails
        assert len(entities) == 0

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
        """Test setup creates sensors from both signals API and permission fallback."""
        # Only battery and charge signals available from API
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
        
        # Should create sensors from both signals API and permission fallback
        # More than 3 total since permission-based sensors are also created
        assert len(entities) > 3
        
        # Signals API sensors must be present
        signal_ids = [sensor._signal_id for sensor in entities]
        assert "battery.percentRemaining" in signal_ids
        assert "battery.range" in signal_ids
        assert "charge.state" in signal_ids
        
        # Permission-based sensors should also be created  
        assert "battery.capacityKwh" in signal_ids
    
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
        
        # Should add all available sensors (signals API + permission-based), minus the one that already exists
        assert len(entities) == 22
        
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
            assert any(s._signal_id == "battery.range" for s in entities)
    
    @pytest.mark.asyncio
    async def test_rebuild_mode_with_no_removals_needed(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test rebuild mode does a clean slate — removes all tracked sensors and recreates them."""
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

            # Rebuild removes ALL tracked sensors (including still-available ones) and recreates
            # them fresh — this clears disabled/stale state and handles duplicate unique_id issues.
            mock_registry.async_remove.assert_any_call("sensor.test_battery")
            mock_registry.async_remove.assert_any_call("sensor.test_range")

            # All 3 available signals should be freshly created
            assert len(entities) == 3
            signal_ids = {s._signal_id for s in entities}
            assert "battery.percentRemaining" in signal_ids
            assert "battery.range" in signal_ids
            assert "charge.state" in signal_ids
    
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
        
        async def get_signals(vehicle_id, vehicle=None):
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
            
            # Rebuild does a clean slate — all previously tracked sensors are removed
            # from the registry (both supported and unsupported), then recreated fresh.
            # Vehicle 1: had 2 sensors (battery + fuel) → both removed → 2 recreated (battery + range)
            # Vehicle 2: had 2 sensors (battery + range) → both removed → 2 recreated (battery + charge.state)
            assert mock_registry.async_remove.call_count == 4

            # After rebuild, both vehicles should have fresh sensors for their available signals
            sensors_v1 = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]
            sensors_v2 = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle2.id]

            assert "fuel.percentRemaining" not in sensors_v1
            assert "battery.percentRemaining" in sensors_v1
            assert "battery.range" in sensors_v1

            assert "battery.range" not in sensors_v2
            assert "battery.percentRemaining" in sensors_v2
            assert "charge.state" in sensors_v2
    
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

        # Pre-populate with sensors, including some that aren't in available_signals
        existing_sensors = {}
        for signal in ["battery.percentRemaining", "fuel.percentRemaining", "charge.state", "odometer.distance"]:
            sensor = MagicMock()
            sensor._signal_id = signal
            sensor.entity_id = f"sensor.test_{signal.replace('.', '_')}"
            existing_sensors[signal] = sensor
        original_sensor_objects = dict(existing_sensors)

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

        sensors_dict = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]

        # All 4 pre-existing sensors must still be in the tracking dict
        for signal, original in original_sensor_objects.items():
            assert signal in sensors_dict, f"{signal} was removed during normal boot"
            assert sensors_dict[signal] is original, f"{signal} sensor object was replaced"

        # New sensors (via permission fallback) should have been added
        assert len(sensors_dict) > 4


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


class TestFetchStatusBackgroundTask:
    """Test initial status population during setup."""

    @pytest.mark.asyncio
    async def test_fetch_status_updates_sensors(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test initial status is populated from the API during setup."""
        fresh_status = {"battery": {"percentRemaining": 0.95, "range": 300}}
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining", "battery.range"])
        mock_client.get_vehicle_status = AsyncMock(return_value=fresh_status)

        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}

        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)

        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        # All sensors should share the status dict populated inline during setup
        sensor_entities = [e for e in entities if isinstance(e, NissanGenericSensor)]
        assert len(sensor_entities) > 0
        for sensor in sensor_entities:
            assert sensor._status == fresh_status

    @pytest.mark.asyncio
    async def test_fetch_status_handles_api_error(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup continues with empty status when API status fetch fails."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining"])
        mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("API error"))

        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}

        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)

        # Should not raise even if API status fetch fails
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        # Sensors should still be created with empty status
        assert len(entities) > 0


class TestSensorCreationLogic:
    """Test sensor creation and filtering logic."""

    @pytest.mark.asyncio
    async def test_sensor_creation_filters_by_permissions(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test that sensors are only created for permitted signals."""
        available_signals = [
            "battery.percentRemaining",  # Has permission
            "charge.state",  # Also has permission
        ]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        mock_client.get_permissions = AsyncMock(return_value=available_signals)
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        
        # Track created tasks but don't await them
        mock_hass.async_create_task = MagicMock()
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create sensors for available signals
        sensor_entities = [e for e in entities if isinstance(e, NissanGenericSensor)]
        signal_ids = [s._signal_id for s in sensor_entities]
        
        assert "battery.percentRemaining" in signal_ids
        assert "charge.state" in signal_ids

    @pytest.mark.asyncio
    async def test_sensor_creation_avoids_duplicates(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test that duplicate sensors are not created."""
        available_signals = ["battery.percentRemaining", "battery.range"]
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        # Pre-populate with existing sensor
        existing_sensor = MagicMock(spec=NissanGenericSensor)
        existing_sensor._signal_id = "battery.percentRemaining"
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {
            "client": mock_client,
            "sensors": {
                mock_vehicle.id: {
                    "battery.percentRemaining": existing_sensor
                }
            }
        }}}
        
        mock_hass.async_create_task = MagicMock()
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create new sensors for available signals + permission-based
        sensor_entities = [e for e in entities if isinstance(e, NissanGenericSensor)]
        assert len(sensor_entities) == 23  # 2 signals API (one already exists) + 22 permission-based
        
        # Should not have duplicate battery.percentRemaining
        signal_ids = [s._signal_id for s in sensor_entities]
        assert "battery.percentRemaining" not in signal_ids  # Already exists
        assert "battery.range" in signal_ids

    @pytest.mark.asyncio
    async def test_sensor_creation_with_multiple_vehicles(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test sensor creation for multiple vehicles."""
        mock_vehicle2 = MagicMock()
        mock_vehicle2.id = "vehicle_456"
        mock_vehicle2.vin = "VIN456DEF"
        mock_vehicle2.nickname = "Second Vehicle"
        
        available_signals = ["battery.percentRemaining"]
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle, mock_vehicle2])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        mock_hass.async_create_task = MagicMock()
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create sensors for both vehicles
        sensor_entities = [e for e in entities if isinstance(e, NissanGenericSensor)]
        vehicles_covered = {s._vehicle.id for s in sensor_entities}
        
        assert mock_vehicle.id in vehicles_covered
        assert mock_vehicle2.id in vehicles_covered


class TestWebhookSignalSubscription:
    """Test webhook signal subscription and handling."""

    @pytest.mark.asyncio
    async def test_webhook_signal_subscription_setup(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test that webhook signal subscription is set up."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining"])
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        mock_hass.async_create_task = MagicMock()
        
        # Track dispatcher connections
        dispatcher_calls = []
        def mock_dispatcher_connect(hass, signal, callback):
            dispatcher_calls.append((signal, callback))
            return MagicMock()
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        with patch("custom_components.nissan_na.sensor.async_dispatcher_connect", side_effect=mock_dispatcher_connect):
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should subscribe to webhook signal for the vehicle
        from custom_components.nissan_na.sensor import SIGNAL_WEBHOOK_DATA
        webhook_signals = [call[0] for call in dispatcher_calls if SIGNAL_WEBHOOK_DATA in call[0]]
        
        assert len(webhook_signals) > 0

    @pytest.mark.asyncio
    async def test_sensor_webhook_data_merge(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor merges webhook data correctly."""
        status = {
            "battery": {"percentRemaining": 0.85, "range": 250},
            "location": {"latitude": 40.0}
        }
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "battery.range",
            "range",
            "Range",
            "km",
            None,
            None,
            mock_config_entry_metric.entry_id,
        )
        
        sensor.async_write_ha_state = MagicMock()
        
        # Webhook brings partial update
        webhook_data = {
            "battery": {"percentRemaining": 0.95},  # Updated
            "location": {"longitude": -74.0}  # New field
        }
        
        sensor._handle_webhook_data(webhook_data)
        
        # Status should be merged
        assert sensor._status["battery"]["percentRemaining"] == 0.95
        assert sensor._status["battery"]["range"] == 250  # Preserved
        assert sensor._status["location"]["latitude"] == 40.0  # Preserved
        assert sensor._status["location"]["longitude"] == -74.0  # Added
        
        # State update should be triggered
        sensor.async_write_ha_state.assert_called()

    @pytest.mark.asyncio
    async def test_sensor_webhook_invalid_data_type(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor handles invalid webhook data type gracefully."""
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
        
        sensor.async_write_ha_state = MagicMock()
        
        # Pass invalid data type (list instead of dict)
        sensor._handle_webhook_data([1, 2, 3])
        
        # Status should not change
        assert sensor._status == {"battery": {"percentRemaining": 0.85}}
        
        # State update should not be called for invalid data
        sensor.async_write_ha_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_sensor_async_update(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor async_update fetches fresh data."""
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
        
        fresh_status = {"battery": {"percentRemaining": 0.95}}
        mock_client = MagicMock()
        mock_client.get_vehicle_status = AsyncMock(return_value=fresh_status)
        
        mock_hass.data[DOMAIN][mock_config_entry_metric.entry_id] = {"client": mock_client}
        
        await sensor.async_update()
        
        # Status should be updated with fresh data
        assert sensor._status["battery"]["percentRemaining"] == 0.95

    @pytest.mark.asyncio
    async def test_sensor_async_update_api_error(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test sensor async_update handles API errors."""
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
        
        mock_client = MagicMock()
        mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("API error"))
        
        mock_hass.data[DOMAIN][mock_config_entry_metric.entry_id] = {"client": mock_client}
        
        # Should not raise
        await sensor.async_update()
        
        # Status should not change
        assert sensor._status["battery"]["percentRemaining"] == 0.85


class TestSensorDefinitionBranches:
    """Test sensor creation branches for different definition types."""

    @pytest.mark.asyncio
    async def test_sensor_with_permission_requirement(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test sensor creation when permission is required."""
        # Manually create signals with different permission requirements
        available_signals = ["battery.percentRemaining"]
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        mock_client.get_permissions = AsyncMock(return_value=available_signals)
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        mock_hass.async_create_task = MagicMock()
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create at least one sensor entity
        assert len(entities) > 0

    @pytest.mark.asyncio
    async def test_rebuild_mode_logs_removals(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test rebuild mode logs summary after removals."""
        from homeassistant.helpers import entity_registry
        
        available_signals = ["battery.percentRemaining"]
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=available_signals)
        mock_client.get_vehicle_status = AsyncMock(return_value={})
        
        mock_registry = MagicMock(spec=entity_registry.EntityRegistry)
        mock_registry.async_get = MagicMock(return_value=MagicMock())
        mock_registry.async_remove = MagicMock()
        
        with patch.object(entity_registry, 'async_get', return_value=mock_registry):
            # Setup with existing sensors
            sensor1 = MagicMock()
            sensor1._signal_id = "battery.percentRemaining"
            sensor1.entity_id = "sensor.battery_1"
            
            sensor2 = MagicMock()
            sensor2._signal_id = "fuel.percentRemaining"  # Not available
            sensor2.entity_id = "sensor.fuel_1"
            
            sensor3 = MagicMock()
            sensor3._signal_id = "charge.state"  # Not available
            sensor3.entity_id = "sensor.charge_1"
            
            mock_hass.data = {
                DOMAIN: {
                    mock_config_entry.entry_id: {
                        "client": mock_client,
                        "sensors": {
                            mock_vehicle.id: {
                                "battery.percentRemaining": sensor1,
                                "fuel.percentRemaining": sensor2,
                                "charge.state": sensor3,
                            }
                        }
                    }
                }
            }
            
            mock_hass.async_create_task = MagicMock()
            
            entities = []
            def async_add_entities(new_entities):
                """Sync callback for adding entities."""
                entities.extend(new_entities)
            
            # Run in rebuild mode
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities, rebuild_mode=True)
            
            sensors = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["sensors"][mock_vehicle.id]

            # Clean-slate rebuild removes all 3 tracked sensors then recreates supported ones.
            # Unavailable sensors are not recreated.
            assert "fuel.percentRemaining" not in sensors
            assert "charge.state" not in sensors

            # battery.percentRemaining is still available — recreated fresh.
            assert "battery.percentRemaining" in sensors

            # All 3 original entities were removed from the registry (clean slate).
            assert mock_registry.async_remove.call_count == 3

    @pytest.mark.asyncio
    async def test_sensor_entity_value_extraction_from_object(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test extracting value from object with getattr."""
        # Create a simple object (not dict) to hold status
        class StatusObject:
            def __init__(self):
                self.percentRemaining = 0.85
        
        status = {"battery": StatusObject()}
        
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
        
        # Should extract via getattr
        assert sensor.native_value == 0.85

    @pytest.mark.asyncio
    async def test_sensor_value_with_unit_conversion(self, mock_hass, mock_vehicle, mock_config_entry_imperial):
        """Test sensor value conversion to imperial units."""
        status = {"odometer": {"distance": 100.0}}
        
        sensor = NissanGenericSensor(
            mock_hass,
            mock_vehicle,
            status,
            "odometer.distance",
            "distance",
            "Odometer",
            "km",
            None,
            None,
            mock_config_entry_imperial.entry_id,
        )
        
        # 100 km should convert to miles
        assert sensor.native_value == pytest.approx(62.137, rel=0.01)

    @pytest.mark.asyncio
    async def test_sensor_should_poll(self, mock_hass, mock_vehicle, mock_config_entry_metric):
        """Test that sensor disables polling."""
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
        
        assert sensor.should_poll is False

    @pytest.mark.asyncio
    async def test_initial_refresh_creates_sensors(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test that initial setup creates sensor entities."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining"])
        mock_client.get_vehicle_status = AsyncMock(return_value={"battery": {"percentRemaining": 0.85}})
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client}}}
        mock_hass.async_create_task = MagicMock()
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should have created at least one sensor entity
        assert len(entities) > 0




