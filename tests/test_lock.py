"""Tests for the Nissan NA lock platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.nissan_na.const import DOMAIN
from custom_components.nissan_na.lock import NissanDoorLockEntity, async_setup_entry


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
def mock_client(mock_vehicle):
    """Create a mock API client."""
    client = MagicMock()
    client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    client.lock_doors = AsyncMock(return_value={"status": "success"})
    client.unlock_doors = AsyncMock(return_value={"status": "success"})
    return client


async def test_async_setup_entry(hass: HomeAssistant, mock_client):
    """Test lock platform setup."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {config_entry.entry_id: mock_client}

    entities = []
    async_add_entities = MagicMock(side_effect=lambda ents: entities.extend(ents))

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert len(entities) == 1
    assert isinstance(entities[0], NissanDoorLockEntity)
    assert mock_client.get_vehicle_list.called


def test_lock_entity_init(mock_vehicle, mock_client):
    """Test lock entity initialization."""
    lock = NissanDoorLockEntity(mock_vehicle, mock_client)

    assert lock._vehicle == mock_vehicle
    assert lock._client == mock_client
    assert "My Nissan" in lock.name
    assert lock.unique_id == "TEST123VIN_door_lock"
    assert lock._is_locked is None


async def test_async_lock(mock_vehicle, mock_client):
    """Test locking the vehicle."""
    lock = NissanDoorLockEntity(mock_vehicle, mock_client)
    lock.async_write_ha_state = MagicMock()

    await lock.async_lock()

    mock_client.lock_doors.assert_called_once_with(mock_vehicle.vin)
    assert lock.is_locked is True
    assert lock.async_write_ha_state.called


async def test_async_unlock(mock_vehicle, mock_client):
    """Test unlocking the vehicle."""
    lock = NissanDoorLockEntity(mock_vehicle, mock_client)
    lock.async_write_ha_state = MagicMock()

    await lock.async_unlock()

    mock_client.unlock_doors.assert_called_once_with(mock_vehicle.vin)
    assert lock.is_locked is False
    assert lock.async_write_ha_state.called


def test_is_locked_property(mock_vehicle, mock_client):
    """Test is_locked property."""
    lock = NissanDoorLockEntity(mock_vehicle, mock_client)

    # Initially None
    assert lock.is_locked is None

    # Set to True
    lock._is_locked = True
    assert lock.is_locked is True

    # Set to False
    lock._is_locked = False
    assert lock.is_locked is False


def test_lock_entity_no_nickname(mock_vehicle, mock_client):
    """Test lock entity when vehicle has no nickname."""
    mock_vehicle.nickname = None
    lock = NissanDoorLockEntity(mock_vehicle, mock_client)

    assert "TEST123VIN" in lock.name
