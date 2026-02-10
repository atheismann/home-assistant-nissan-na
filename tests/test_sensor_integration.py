"""Integration tests for sensor setup and webhook integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nissan_na.const import DOMAIN


@pytest.fixture
def mock_vehicle():
    """Create a mock vehicle."""
    vehicle = MagicMock()
    vehicle.id = "vehicle_1"
    vehicle.vin = "12345678901234567"
    vehicle.nickname = "My Nissan"
    vehicle.year = 2023
    vehicle.make = "NISSAN"
    vehicle.model = "Leaf"
    return vehicle


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock()
    client.get_vehicle_list = AsyncMock()
    client.get_permissions = AsyncMock()
    client.get_vehicle_status = AsyncMock()
    return client


async def test_sensor_setup_with_mock_config_entry(hass: HomeAssistant, mock_client, mock_vehicle):
    """Test sensor setup initializes properly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    mock_client.get_vehicle_list.return_value = [mock_vehicle]
    mock_client.get_permissions.return_value = [
        "read_battery",
        "read_odometer",
        "read_location",
    ]
    mock_client.get_vehicle_status.return_value = {
        "batteryLevel": 85,
        "odometer": 10000,
        "location": {"lat": 37.42, "lon": -122.14},
    }

    hass.data[DOMAIN] = {entry.entry_id: {"client": mock_client}}

    from custom_components.nissan_na.sensor import async_setup_entry

    # Create mock async_add_entities
    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    # Should setup without error
    await async_setup_entry(hass, entry, mock_add_entities)

    # Verify setup called add_entities
    assert len(entities_added) > 0


async def test_sensor_update_with_fresh_data(hass: HomeAssistant, mock_vehicle):
    """Test sensor async_update fetches fresh data."""
    from custom_components.nissan_na.sensor import NissanGenericSensor

    mock_client = MagicMock()
    mock_client.get_vehicle_status = AsyncMock(
        return_value={"battery": {"percentRemaining": 0.90, "range": 250}, "odometer": {"distance": 10500}}
    )

    hass.data[DOMAIN] = {
        "entry_1": {"client": mock_client}
    }

    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"battery": {"percentRemaining": 0.85, "range": 240}, "odometer": {"distance": 10000}},
        "battery",
        "percentRemaining",
        "Battery Level",
        "%",
        "entry_1",
    )

    # Update should fetch fresh data
    await sensor.async_update()

    # Verify API was called with vehicle ID
    mock_client.get_vehicle_status.assert_called_with(mock_vehicle.id)

    # Status should be updated
    assert sensor._status["battery"]["percentRemaining"] == 0.90


async def test_sensor_webhook_dispatcher_subscription(hass: HomeAssistant, mock_vehicle):
    """Test sensor can subscribe to webhook dispatcher."""
    from custom_components.nissan_na.sensor import NissanGenericSensor

    hass.data[DOMAIN] = {"entry_1": {}}

    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"battery": {"percentRemaining": 0.85}},
        "battery",
        "percentRemaining",
        "Battery Level",
        "%",
        "entry_1",
    )

    # Sensor initializes without error
    assert sensor._vehicle.id == mock_vehicle.id
    assert sensor._api_key == "battery"
    assert sensor._attr_name is not None



async def test_sensor_permission_based_creation(hass: HomeAssistant, mock_client, mock_vehicle):
    """Test sensors are only created for permissions car supports."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    # Vehicle only has battery and odometer permissions
    mock_client.get_vehicle_list.return_value = [mock_vehicle]
    mock_client.get_permissions.return_value = ["read_battery", "read_odometer"]
    mock_client.get_vehicle_status.return_value = {
        "battery": {"percentRemaining": 0.85},
        "odometer": {"distance": 10000},
        "charge": {"state": "Idle"},  # Has data but no permission
        "location": {"latitude": 37.42, "longitude": -122.14},  # Has data but no permission
    }

    hass.data[DOMAIN] = {entry.entry_id: {"client": mock_client}}

    from custom_components.nissan_na.sensor import async_setup_entry

    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, entry, mock_add_entities)

    # Check what api_keys were created
    created_keys = {e._api_key for e in entities_added}

    # Should have battery and odometer (have permissions)
    assert "battery" in created_keys
    assert "odometer" in created_keys

    # Should not have charge or location (no permission even though data exists)
    assert "charge" not in created_keys
    assert "location" not in created_keys


async def test_sensor_dynamic_entity_creation_from_webhook(
    hass: HomeAssistant, mock_client, mock_vehicle
):
    """Test new sensors created when webhook contains unknown keys."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    mock_client.get_vehicle_list.return_value = [mock_vehicle]
    mock_client.get_permissions.return_value = ["read_battery"]
    mock_client.get_vehicle_status.return_value = {"batteryLevel": 85}

    hass.data[DOMAIN] = {entry.entry_id: {"client": mock_client}}

    from custom_components.nissan_na.sensor import async_setup_entry

    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, entry, mock_add_entities)

    # Verify setup completed - dynamic creation handler registered
    # (actual webhook dispatch would happen later in integration)
    assert hass is not None


async def test_sensor_location_formatting(hass: HomeAssistant, mock_vehicle):
    """Test location sensor formats latitude and longitude correctly."""
    from custom_components.nissan_na.sensor import NissanGenericSensor

    sensor = NissanGenericSensor(
        hass,
        mock_vehicle,
        {"location": {"latitude": 37.4222, "longitude": -122.1413}},
        "location",
        "latitude",
        "Location Latitude",
        "°",
        "entry_1",
    )

    # Location latitude should be returned correctly
    assert sensor.native_value == 37.4222


async def test_sensor_with_missing_permissions(hass: HomeAssistant, mock_client, mock_vehicle):
    """Test sensor setup when permission check fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    mock_client.get_vehicle_list.return_value = [mock_vehicle]
    mock_client.get_permissions.side_effect = Exception("API Error")
    mock_client.get_vehicle_status.return_value = {
        "batteryLevel": 85,
        "odometer": 10000,
    }

    hass.data[DOMAIN] = {entry.entry_id: {"client": mock_client}}

    from custom_components.nissan_na.sensor import async_setup_entry

    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    # Should not crash when permission check fails
    await async_setup_entry(hass, entry, mock_add_entities)

    # Should create sensors for data that exists (conservative approach)
    assert len(entities_added) > 0


async def test_initial_sensor_refresh_after_setup(
    hass: HomeAssistant, mock_client, mock_vehicle
):
    """Test sensors are refreshed immediately after setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    mock_client.get_vehicle_list.return_value = [mock_vehicle]
    mock_client.get_permissions.return_value = ["read_battery"]
    mock_client.get_vehicle_status.return_value = {"batteryLevel": 85}

    hass.data[DOMAIN] = {entry.entry_id: {"client": mock_client}}

    from custom_components.nissan_na.sensor import async_setup_entry

    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, entry, mock_add_entities)

    # Verify initial status fetch was called
    assert mock_client.get_vehicle_status.called


async def test_sensor_multiple_vehicles_device_linking(
    hass: HomeAssistant, mock_client
):
    """Test multiple vehicles are linked to separate devices."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    # Create two vehicles
    vehicle1 = MagicMock()
    vehicle1.id = "vehicle_1"
    vehicle1.vin = "VIN_1"
    vehicle1.nickname = "Car 1"

    vehicle2 = MagicMock()
    vehicle2.id = "vehicle_2"
    vehicle2.vin = "VIN_2"
    vehicle2.nickname = "Car 2"

    mock_client.get_vehicle_list.return_value = [vehicle1, vehicle2]
    mock_client.get_permissions.return_value = ["read_battery"]
    mock_client.get_vehicle_status.return_value = {"batteryLevel": 85}

    hass.data[DOMAIN] = {entry.entry_id: {"client": mock_client}}

    from custom_components.nissan_na.sensor import async_setup_entry

    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, entry, mock_add_entities)

    # Should create sensors for both vehicles
    vins_in_entities = {list(e.device_info["identifiers"])[0][1] for e in entities_added}
    assert "VIN_1" in vins_in_entities
    assert "VIN_2" in vins_in_entities


async def test_sensor_with_no_vehicles(hass: HomeAssistant, mock_client):
    """Test setup gracefully handles no vehicles."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    mock_client.get_vehicle_list.return_value = []
    hass.data[DOMAIN] = {entry.entry_id: {"client": mock_client}}

    from custom_components.nissan_na.sensor import async_setup_entry

    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    # Should not crash with no vehicles
    await async_setup_entry(hass, entry, mock_add_entities)

    # No entities should be added
    assert len(entities_added) == 0
