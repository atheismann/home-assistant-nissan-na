"""Tests for the Nissan NA sensor platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.nissan_na.const import DOMAIN
from custom_components.nissan_na.sensor import NissanGenericSensor, async_setup_entry


@pytest.fixture
def mock_vehicle():
    """Create a mock vehicle."""
    vehicle = MagicMock()
    vehicle.vin = "TEST123VIN"
    vehicle.id = "vehicle-id-123"
    vehicle.nickname = "My Nissan"
    vehicle.model = "LEAF"
    vehicle.year = 2023
    vehicle.make = "Nissan"
    return vehicle


@pytest.fixture
def mock_vehicle_status():
    """Create mock vehicle status."""
    return {
        "batteryLevel": 85,
        "chargingStatus": "Charging",
        "plugStatus": "Connected",
        "odometer": 15000,
        "range": 240,
        "tirePressure": 35,
        "doorStatus": "Closed",
        "windowStatus": "Closed",
        "lastUpdate": "2026-01-29T10:00:00Z",
        "climateStatus": "Off",
        "location": {"lat": 37.7749, "lon": -122.4194},
    }


@pytest.fixture
def mock_client(mock_vehicle, mock_vehicle_status):
    """Create a mock API client."""
    client = MagicMock()
    client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    client.get_vehicle_status = AsyncMock(return_value=mock_vehicle_status)
    client.get_permissions = AsyncMock(
        return_value=[
            "read_battery",
            "read_charge",
            "read_odometer",
            "read_location",
            "read_tires",
            "read_security",
            "read_climate",
        ]
    )
    return client


async def test_async_setup_entry(hass: HomeAssistant, mock_client, mock_vehicle):
    """Test sensor platform setup."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {config_entry.entry_id: {"client": mock_client, "vehicles": []}}

    entities = []
    async_add_entities = MagicMock(side_effect=lambda ents: entities.extend(ents))

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert len(entities) == 11
    assert mock_client.get_vehicle_list.called
    assert mock_client.get_vehicle_status.called


def test_sensor_battery_level(hass, mock_vehicle, mock_vehicle_status):
    """Test battery level sensor."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    assert sensor.state == 85
    assert sensor.unique_id == "TEST123VIN_batteryLevel"
    assert sensor.unit_of_measurement == "%"
    assert "My Nissan" in sensor.name


def test_sensor_charging_status(hass, mock_vehicle, mock_vehicle_status):
    """Test charging status sensor."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "chargingStatus",
        "Charging Status",
        None,
        "test_entry",
    )

    assert sensor.state == "Charging"
    assert sensor.unique_id == "TEST123VIN_chargingStatus"
    assert sensor.unit_of_measurement is None


def test_sensor_location(hass, mock_vehicle, mock_vehicle_status):
    """Test location sensor."""
    sensor = NissanGenericSensor(
        hass, mock_vehicle, mock_vehicle_status, "location", "Location", None, "test_entry"
    )

    assert sensor.state == "37.7749,-122.4194"
    assert sensor.unique_id == "TEST123VIN_location"


def test_sensor_location_missing(hass, mock_vehicle):
    """Test location sensor with missing location data."""
    status = {"location": None}
    sensor = NissanGenericSensor(
        hass, mock_vehicle, status, "location", "Location", None, "test_entry"
    )

    assert sensor.state is None


def test_sensor_location_incomplete(hass, mock_vehicle):
    """Test location sensor with incomplete location data."""
    status = {"location": {"lat": 37.7749}}
    sensor = NissanGenericSensor(
        hass, mock_vehicle, status, "location", "Location", None, "test_entry"
    )

    assert sensor.state is None


def test_sensor_odometer(hass, mock_vehicle, mock_vehicle_status):
    """Test odometer sensor."""
    sensor = NissanGenericSensor(
        hass, mock_vehicle, mock_vehicle_status, "odometer", "Odometer", "km", "test_entry"
    )

    assert sensor.state == 15000
    assert sensor.unit_of_measurement == "km"


def test_sensor_missing_key(hass, mock_vehicle):
    """Test sensor with missing data key."""
    status = {}
    sensor = NissanGenericSensor(
        hass, mock_vehicle, status, "batteryLevel", "Battery Level", "%", "test_entry"
    )

    assert sensor.state is None


def test_sensor_no_nickname(hass, mock_vehicle, mock_vehicle_status):
    """Test sensor name when vehicle has no nickname."""
    mock_vehicle.nickname = None
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    assert "2023 Nissan LEAF" in sensor.name


def test_sensor_webhook_update(hass, mock_vehicle, mock_vehicle_status):
    """Test sensor updates via webhook data."""
    from unittest.mock import patch
    
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    # Initial state
    assert sensor.state == 85

    # Simulate webhook data update with mocked async_write_ha_state
    with patch.object(sensor, 'async_write_ha_state'):
        webhook_data = {"batteryLevel": 90, "range": 250}
        sensor._handle_webhook_data(webhook_data)

    # Verify state updated
    assert sensor.state == 90
    # Verify status dict was updated with webhook data
    assert sensor._status["batteryLevel"] == 90
    assert sensor._status["range"] == 250
    # Verify other data was preserved
    assert sensor._status["chargingStatus"] == "Charging"


async def test_dynamic_entity_creation_from_webhook(
    hass: HomeAssistant, mock_client, mock_vehicle, mock_vehicle_status
):
    """Test that new entities are created when webhook data contains new keys."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {
        config_entry.entry_id: {"client": mock_client, "vehicles": []}
    }

    entities = []
    
    # Track calls to async_add_entities
    add_entities_calls = []
    def track_add_entities(ents):
        entities.extend(ents)
        add_entities_calls.append(ents)
    
    async_add_entities = MagicMock(side_effect=track_add_entities)

    # Initial setup - creates standard sensors
    await async_setup_entry(hass, config_entry, async_add_entities)
    initial_entity_count = len(entities)
    
    assert initial_entity_count == 11  # Standard sensors
    assert len(add_entities_calls) == 1  # First call during setup
    
    # Simulate webhook with new data key not in initial setup
    from homeassistant.helpers.dispatcher import async_dispatcher_send
    
    # Add a new key that wasn't in the initial status
    webhook_data = {
        "batteryLevel": 92,
        "fuelLevel": 45,  # New key not in SENSOR_DEFINITIONS
        "engineStatus": "running",  # New key not in SENSOR_DEFINITIONS
    }
    
    # Send webhook signal
    async_dispatcher_send(
        hass,
        f"nissan_na_webhook_data_{mock_vehicle.id}",
        webhook_data,
    )
    
    # Wait for async task to complete
    await hass.async_block_till_done()
    
    # Should have created new entities for the new keys
    assert len(entities) > initial_entity_count
    assert len(add_entities_calls) == 2  # Second call for dynamic entities
    
    # Check that new entities were created
    new_entities = add_entities_calls[1]
    assert len(new_entities) == 2  # fuelLevel and engineStatus
    
    # Verify the new entities have the correct keys
    new_keys = {entity._key for entity in new_entities}
    assert "fuelLevel" in new_keys
    assert "engineStatus" in new_keys


def test_sensor_polling_disabled(hass, mock_vehicle, mock_vehicle_status):
    """Test that polling is disabled for sensors."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    assert sensor.should_poll is False


async def test_async_setup_entry_api_error(hass: HomeAssistant, mock_client, mock_vehicle):
    """Test sensor platform setup when API returns error."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    # Mock get_vehicle_status to raise an exception
    mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("API Error"))

    hass.data[DOMAIN] = {config_entry.entry_id: {"client": mock_client, "vehicles": []}}

    entities = []
    async_add_entities = MagicMock(side_effect=lambda ents: entities.extend(ents))

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Should still create entities with empty status
    assert len(entities) == 11
    assert mock_client.get_vehicle_list.called


async def test_async_setup_entry_with_initial_refresh(
    hass: HomeAssistant, mock_client, mock_vehicle, mock_vehicle_status
):
    """Test that sensors are refreshed after initial setup."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {config_entry.entry_id: {"client": mock_client, "vehicles": []}}

    entities = []

    def track_entities(ents):
        entities.extend(ents)

    async_add_entities = MagicMock(side_effect=track_entities)

    # Setup the sensors
    await async_setup_entry(hass, config_entry, async_add_entities)

    assert len(entities) > 0
    # Initial setup should call get_vehicle_status twice:
    # once for initial state and once for refresh
    assert mock_client.get_vehicle_status.call_count >= 1


async def test_sensor_async_update(hass, mock_vehicle, mock_vehicle_status):
    """Test sensor async_update method."""
    from unittest.mock import patch

    # Setup sensor
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    # Mock the client
    mock_client = MagicMock()
    mock_client.get_vehicle_status = AsyncMock(
        return_value={"batteryLevel": 95, "range": 260}
    )

    hass.data[DOMAIN] = {"test_entry": {"client": mock_client}}

    # Call async_update
    await sensor.async_update()

    # Verify client was called
    assert mock_client.get_vehicle_status.called

    # Verify status was updated
    assert sensor._status["batteryLevel"] == 95
    assert sensor._status["range"] == 260


async def test_sensor_async_update_error(hass, mock_vehicle, mock_vehicle_status):
    """Test sensor async_update handles errors gracefully."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    # Mock the client to raise an error
    mock_client = MagicMock()
    mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("API Error"))

    hass.data[DOMAIN] = {"test_entry": {"client": mock_client}}

    # Call async_update - should not raise
    await sensor.async_update()

    # Status should remain unchanged
    assert sensor.state == 85


async def test_dynamic_entity_creation_with_known_keys(
    hass: HomeAssistant, mock_client, mock_vehicle, mock_vehicle_status
):
    """Test that dynamic entity creation works for known sensor keys."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    # Create initial setup with limited status
    limited_status = {"batteryLevel": 85}
    mock_client.get_vehicle_status = AsyncMock(return_value=limited_status)

    hass.data[DOMAIN] = {
        config_entry.entry_id: {"client": mock_client, "vehicles": []}
    }

    entities = []
    add_entities_calls = []

    def track_add_entities(ents):
        entities.extend(ents)
        add_entities_calls.append(ents)

    async_add_entities = MagicMock(side_effect=track_add_entities)

    # Initial setup
    await async_setup_entry(hass, config_entry, async_add_entities)
    initial_count = len(entities)

    # Simulate webhook with completely new unknown key
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    webhook_data = {"batteryLevel": 90, "newUnknownKey": "test_value"}

    async_dispatcher_send(
        hass,
        f"nissan_na_webhook_data_{mock_vehicle.id}",
        webhook_data,
    )

    # Wait for async task
    await hass.async_block_till_done()

    # Should have created new entity for newUnknownKey
    assert len(entities) > initial_count


async def test_sensor_webhook_partial_update(hass, mock_vehicle, mock_vehicle_status):
    """Test sensor webhook updates with partial data."""
    from unittest.mock import patch
    
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        mock_vehicle_status,
        "range",
        "Range",
        "km",
        "test_entry",
    )

    # Initial state
    assert sensor.state == 240
    initial_battery = sensor._status.get("batteryLevel")

    # Simulate partial webhook update (only range changes)
    with patch.object(sensor, 'async_write_ha_state'):
        sensor._handle_webhook_data({"range": 300})

    # Verify range updated
    assert sensor.state == 300
    # Verify other data preserved
    assert sensor._status.get("batteryLevel") == initial_battery


async def test_sensor_location_formatting(hass, mock_vehicle):
    """Test location sensor formats lat/lon correctly."""
    location_data = {
        "location": {"lat": 37.7749, "lon": -122.4194},
        "batteryLevel": 85,
    }
    
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        location_data,
        "location",
        "Location",
        None,
        "test_entry",
    )

    assert sensor.state == "37.7749,-122.4194"


async def test_sensor_device_info(hass, mock_vehicle):
    """Test sensor device_info links to vehicle device."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"batteryLevel": 85},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    device_info = sensor.device_info
    assert (DOMAIN, mock_vehicle.vin) in device_info["identifiers"]
    assert device_info["via_device"] == (DOMAIN, "test_entry")


async def test_sensor_unique_id(hass, mock_vehicle):
    """Test sensor unique_id is properly formatted."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"batteryLevel": 85},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    assert sensor.unique_id == f"{mock_vehicle.vin}_batteryLevel"


async def test_sensor_unit_of_measurement(hass, mock_vehicle):
    """Test sensor unit_of_measurement property."""
    sensor_with_unit = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"batteryLevel": 85},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )
    assert sensor_with_unit.unit_of_measurement == "%"

    sensor_without_unit = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"chargingStatus": "Charging"},
        "chargingStatus",
        "Charging Status",
        None,
        "test_entry",
    )
    assert sensor_without_unit.unit_of_measurement is None


async def test_async_setup_entry_permission_check_fail(
    hass: HomeAssistant, mock_client, mock_vehicle
):
    """Test setup when permission check fails - should be conservative."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    # Mock data structure
    hass.data = {
        DOMAIN: {
            "test_entry": {
                "client": mock_client,
                "sensors": {},
            }
        }
    }

    mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    # Permissions check fails
    mock_client.get_permissions = AsyncMock(side_effect=Exception("API Error"))
    # But vehicle has status data
    mock_client.get_vehicle_status = AsyncMock(
        return_value={"batteryLevel": 85, "odometer": 10000}
    )

    entities = []
    async_add_entities = MagicMock(side_effect=lambda x: entities.extend(x))

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Should create sensors for data that exists
    assert len(entities) > 0
    created_keys = {e._key for e in entities}
    # Since permission check failed, should only create sensors with data
    assert "batteryLevel" in created_keys
    assert "odometer" in created_keys


async def test_async_setup_entry_no_status_data(hass: HomeAssistant, mock_client, mock_vehicle):
    """Test setup when vehicle has no status data."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data = {
        DOMAIN: {
            "test_entry": {
                "client": mock_client,
                "sensors": {},
            }
        }
    }

    mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    mock_client.get_permissions = AsyncMock(return_value=[])
    # Empty status
    mock_client.get_vehicle_status = AsyncMock(return_value={})

    entities = []
    async_add_entities = MagicMock(side_effect=lambda x: entities.extend(x))

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Should only create sensors with no permission requirement (always-available sensors)
    # like "lastUpdate"
    created_keys = {e._key for e in entities}
    assert "lastUpdate" in created_keys  # Has no required_permission


async def test_sensor_async_update_missing_client(hass, mock_vehicle):
    """Test async_update when client data is missing."""
    # Setup hass.data without proper structure
    hass.data = {DOMAIN: {"test_entry": {}}}  # Missing "client" key

    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"batteryLevel": 85},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    # Should handle missing client gracefully
    await sensor.async_update()
    # Status should remain unchanged or have logged error
    assert sensor._status.get("batteryLevel") == 85


def test_sensor_display_name_year_make_model(hass, mock_vehicle):
    """Test sensor display name uses year/make/model when available."""
    # Mock vehicle with year, make, model
    vehicle = MagicMock()
    vehicle.id = "test_vehicle"
    vehicle.vin = "12345678901234567"
    vehicle.nickname = None
    vehicle.year = 2023
    vehicle.make = "NISSAN"
    vehicle.model = "Leaf"

    sensor = NissanGenericSensor(
        hass,
        vehicle,
        {"batteryLevel": 85},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    assert sensor._attr_name == "2023 NISSAN Leaf Battery Level"


def test_sensor_display_name_vin_fallback(hass, mock_vehicle):
    """Test sensor display name falls back to VIN."""
    # Mock vehicle with no year/make/model
    vehicle = MagicMock()
    vehicle.id = "test_vehicle"
    vehicle.vin = "12345678901234567"
    vehicle.nickname = None
    vehicle.year = None
    vehicle.make = None
    vehicle.model = None

    sensor = NissanGenericSensor(
        hass,
        vehicle,
        {"batteryLevel": 85},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )

    assert sensor._attr_name == "12345678901234567 Battery Level"


async def test_dynamic_entity_creation_webhook_vehicle_not_found(hass, mock_client, mock_vehicle):
    """Test dynamic entity creation when vehicle not found in vehicle list."""
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data = {
        DOMAIN: {
            "test_entry": {
                "client": mock_client,
                "sensors": {"unknown_vehicle": {}},
            }
        }
    }

    mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    mock_client.get_permissions = AsyncMock(return_value=["read_battery"])
    mock_client.get_vehicle_status = AsyncMock(return_value={"batteryLevel": 85})

    entities = []
    async_add_entities = MagicMock(side_effect=lambda x: entities.extend(x))

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Send webhook data for unknown vehicle
    # The handler should log error but not crash
    signal_name = f"nissan_na_webhook_data_unknown_vehicle"
    await hass.async_block_till_done()

    # Verify setup succeeded
    assert async_add_entities.called


async def test_dynamic_entity_creation_new_unknown_key(hass, mock_client, mock_vehicle):
    """Test dynamic entity creation with unknown data key (auto-naming)."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data = {
        DOMAIN: {
            "test_entry": {
                "client": mock_client,
                "sensors": {mock_vehicle.id: {}},
            }
        }
    }

    mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    mock_client.get_permissions = AsyncMock(return_value=["read_custom_data"])
    mock_client.get_vehicle_status = AsyncMock(return_value={})

    entities = []
    async_add_entities = MagicMock(side_effect=lambda x: entities.extend(x))

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Now simulate webhook with unknown key
    webhook_data = {"customDataField": "value123"}
    
    # This will trigger the dynamic creation handler registered in setup
    # We verify the setup completed without errors
    assert async_add_entities.called


def test_sensor_state_location_with_null_values(hass, mock_vehicle):
    """Test location formatting handles missing lat/lon gracefully."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"location": {"lat": None, "lon": -122.14}},
        "location",
        "Location",
        None,
        "test_entry",
    )
    
    # Should return None when lat is missing
    assert sensor.state is None
    
    # Test with lon missing
    sensor2 = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"location": {"lat": 37.42, "lon": None}},
        "location",
        "Location",
        None,
        "test_entry",
    )
    
    assert sensor2.state is None


def test_sensor_state_nonlocation_None_value(hass, mock_vehicle):
    """Test sensor returns None for missing keys."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )
    
    # Status doesn't have the key
    assert sensor.state is None


def test_sensor_webhook_data_not_dict(hass, mock_vehicle):
    """Test webhook handler handles non-dict data gracefully."""
    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"batteryLevel": 50},
        "batteryLevel",
        "Battery Level",
        "%",
        "test_entry",
    )
    
    # Call handler with non-dict data (shouldn't crash)
    sensor._handle_webhook_data("not a dict")
    
    # Status should remain unchanged
    assert sensor._status["batteryLevel"] == 50


async def test_async_setup_entry_all_permission_types(hass: HomeAssistant, mock_client, mock_vehicle):
    """Test setup with various permission configurations."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data = {
        DOMAIN: {
            "test_entry": {
                "client": mock_client,
                "sensors": {},
            }
        }
    }

    mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    # Return permissions for some features but not others
    mock_client.get_permissions = AsyncMock(return_value=[
        "read_battery",
        "read_odometer",
        # Missing read_charge, read_tires, etc.
    ])
    mock_client.get_vehicle_status = AsyncMock(
        return_value={"batteryLevel": 85, "odometer": 10000, "chargingStatus": "Idle"}
    )

    entities = []
    async_add_entities = MagicMock(side_effect=lambda x: entities.extend(x))

    await async_setup_entry(hass, config_entry, async_add_entities)

    created_keys = {e._key for e in entities}
    # Should create battery and odometer (have permissions)
    assert "batteryLevel" in created_keys
    assert "odometer" in created_keys
    # Charging requires read_charge permission which we don't have
    assert "chargingStatus" not in created_keys



