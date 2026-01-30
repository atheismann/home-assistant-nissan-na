"""Tests for the Nissan NA device tracker platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.device_tracker import SourceType
from homeassistant.core import HomeAssistant

from custom_components.nissan_na.const import DOMAIN
from custom_components.nissan_na.device_tracker import (
    NissanVehicleTracker,
    async_setup_entry,
)


@pytest.fixture
def mock_vehicle():
    """Create a mock vehicle."""
    vehicle = MagicMock()
    vehicle.vin = "TEST123VIN"
    vehicle.id = "vehicle-id-123"
    vehicle.nickname = "My Nissan"
    vehicle.model = "LEAF"
    return vehicle


@pytest.fixture
def mock_vehicle_status():
    """Create mock vehicle status with location."""
    return {
        "location": {"lat": 37.7749, "lon": -122.4194},
        "batteryLevel": 85,
    }


@pytest.fixture
def mock_client(mock_vehicle, mock_vehicle_status):
    """Create a mock API client."""
    client = MagicMock()
    client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    client.get_vehicle_status = AsyncMock(return_value=mock_vehicle_status)
    return client


async def test_async_setup_entry(hass: HomeAssistant, mock_client):
    """Test device tracker platform setup."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {config_entry.entry_id: mock_client}

    entities = []
    async_add_entities = MagicMock(side_effect=lambda ents: entities.extend(ents))

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert len(entities) == 1
    assert isinstance(entities[0], NissanVehicleTracker)
    assert mock_client.get_vehicle_list.called
    assert mock_client.get_vehicle_status.called


def test_tracker_init(mock_vehicle, mock_vehicle_status):
    """Test device tracker initialization."""
    tracker = NissanVehicleTracker(mock_vehicle, mock_vehicle_status)

    assert tracker._vehicle == mock_vehicle
    assert tracker._status == mock_vehicle_status
    assert "My Nissan" in tracker.name
    assert tracker.unique_id == "TEST123VIN_location"


def test_latitude_property(mock_vehicle, mock_vehicle_status):
    """Test latitude property."""
    tracker = NissanVehicleTracker(mock_vehicle, mock_vehicle_status)

    assert tracker.latitude == 37.7749


def test_longitude_property(mock_vehicle, mock_vehicle_status):
    """Test longitude property."""
    tracker = NissanVehicleTracker(mock_vehicle, mock_vehicle_status)

    assert tracker.longitude == -122.4194


def test_source_type_property(mock_vehicle, mock_vehicle_status):
    """Test source type property."""
    tracker = NissanVehicleTracker(mock_vehicle, mock_vehicle_status)

    assert tracker.source_type == SourceType.GPS


def test_latitude_missing_location(mock_vehicle):
    """Test latitude when location is missing."""
    status = {}
    tracker = NissanVehicleTracker(mock_vehicle, status)

    assert tracker.latitude is None


def test_longitude_missing_location(mock_vehicle):
    """Test longitude when location is missing."""
    status = {}
    tracker = NissanVehicleTracker(mock_vehicle, status)

    assert tracker.longitude is None


def test_latitude_incomplete_location(mock_vehicle):
    """Test latitude when location data is incomplete."""
    status = {"location": {"lon": -122.4194}}
    tracker = NissanVehicleTracker(mock_vehicle, status)

    assert tracker.latitude is None


def test_longitude_incomplete_location(mock_vehicle):
    """Test longitude when location data is incomplete."""
    status = {"location": {"lat": 37.7749}}
    tracker = NissanVehicleTracker(mock_vehicle, status)

    assert tracker.longitude is None


def test_tracker_no_nickname(mock_vehicle, mock_vehicle_status):
    """Test device tracker when vehicle has no nickname."""
    mock_vehicle.nickname = None
    tracker = NissanVehicleTracker(mock_vehicle, mock_vehicle_status)

    assert "TEST123VIN" in tracker.name
