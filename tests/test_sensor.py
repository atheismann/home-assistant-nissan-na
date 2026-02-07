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


def test_sensor_battery_level(mock_vehicle, mock_vehicle_status):
    """Test battery level sensor."""
    sensor = NissanGenericSensor(
        mock_vehicle, mock_vehicle_status, "batteryLevel", "Battery Level", "%"
    )

    assert sensor.state == 85
    assert sensor.unique_id == "TEST123VIN_batteryLevel"
    assert sensor.unit_of_measurement == "%"
    assert "My Nissan" in sensor.name


def test_sensor_charging_status(mock_vehicle, mock_vehicle_status):
    """Test charging status sensor."""
    sensor = NissanGenericSensor(
        mock_vehicle, mock_vehicle_status, "chargingStatus", "Charging Status", None
    )

    assert sensor.state == "Charging"
    assert sensor.unique_id == "TEST123VIN_chargingStatus"
    assert sensor.unit_of_measurement is None


def test_sensor_location(mock_vehicle, mock_vehicle_status):
    """Test location sensor."""
    sensor = NissanGenericSensor(
        mock_vehicle, mock_vehicle_status, "location", "Location", None
    )

    assert sensor.state == "37.7749,-122.4194"
    assert sensor.unique_id == "TEST123VIN_location"


def test_sensor_location_missing(mock_vehicle):
    """Test location sensor with missing location data."""
    status = {"location": None}
    sensor = NissanGenericSensor(mock_vehicle, status, "location", "Location", None)

    assert sensor.state is None


def test_sensor_location_incomplete(mock_vehicle):
    """Test location sensor with incomplete location data."""
    status = {"location": {"lat": 37.7749}}
    sensor = NissanGenericSensor(mock_vehicle, status, "location", "Location", None)

    assert sensor.state is None


def test_sensor_odometer(mock_vehicle, mock_vehicle_status):
    """Test odometer sensor."""
    sensor = NissanGenericSensor(
        mock_vehicle, mock_vehicle_status, "odometer", "Odometer", "km"
    )

    assert sensor.state == 15000
    assert sensor.unit_of_measurement == "km"


def test_sensor_missing_key(mock_vehicle):
    """Test sensor with missing data key."""
    status = {}
    sensor = NissanGenericSensor(
        mock_vehicle, status, "batteryLevel", "Battery Level", "%"
    )

    assert sensor.state is None


def test_sensor_no_nickname(mock_vehicle, mock_vehicle_status):
    """Test sensor name when vehicle has no nickname."""
    mock_vehicle.nickname = None
    sensor = NissanGenericSensor(
        mock_vehicle, mock_vehicle_status, "batteryLevel", "Battery Level", "%"
    )

    assert "TEST123VIN" in sensor.name
