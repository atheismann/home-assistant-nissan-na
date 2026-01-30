"""Tests for the Nissan NA climate platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate.const import HVACMode
from homeassistant.core import HomeAssistant

from custom_components.nissan_na.climate import NissanClimateEntity, async_setup_entry
from custom_components.nissan_na.const import DOMAIN


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
    client.start_climate = AsyncMock(return_value={"status": "success"})
    client.stop_climate = AsyncMock(return_value={"status": "success"})
    return client


async def test_async_setup_entry(hass: HomeAssistant, mock_client):
    """Test climate platform setup."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {config_entry.entry_id: mock_client}

    entities = []
    async_add_entities = MagicMock(side_effect=lambda ents: entities.extend(ents))

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert len(entities) == 1
    assert isinstance(entities[0], NissanClimateEntity)
    assert mock_client.get_vehicle_list.called


def test_climate_entity_init(mock_vehicle, mock_client):
    """Test climate entity initialization."""
    climate = NissanClimateEntity(mock_vehicle, mock_client)

    assert climate._vehicle == mock_vehicle
    assert climate._client == mock_client
    assert "My Nissan" in climate.name
    assert climate.unique_id == "TEST123VIN_climate"
    assert climate._hvac_mode == HVACMode.OFF


def test_hvac_modes_available(mock_vehicle, mock_client):
    """Test available HVAC modes."""
    climate = NissanClimateEntity(mock_vehicle, mock_client)

    assert HVACMode.OFF in climate.hvac_modes
    assert HVACMode.HEAT in climate.hvac_modes
    assert HVACMode.COOL in climate.hvac_modes
    assert HVACMode.AUTO in climate.hvac_modes


async def test_set_hvac_mode_off(mock_vehicle, mock_client):
    """Test setting HVAC mode to OFF."""
    climate = NissanClimateEntity(mock_vehicle, mock_client)
    climate.async_write_ha_state = MagicMock()

    await climate.async_set_hvac_mode(HVACMode.OFF)

    mock_client.stop_climate.assert_called_once_with(mock_vehicle.vin)
    assert climate.hvac_mode == HVACMode.OFF
    assert climate.async_write_ha_state.called


async def test_set_hvac_mode_heat(mock_vehicle, mock_client):
    """Test setting HVAC mode to HEAT."""
    climate = NissanClimateEntity(mock_vehicle, mock_client)
    climate.async_write_ha_state = MagicMock()

    await climate.async_set_hvac_mode(HVACMode.HEAT)

    mock_client.start_climate.assert_called_once_with(mock_vehicle.vin)
    assert climate.hvac_mode == HVACMode.HEAT
    assert climate.async_write_ha_state.called


async def test_set_hvac_mode_cool(mock_vehicle, mock_client):
    """Test setting HVAC mode to COOL."""
    climate = NissanClimateEntity(mock_vehicle, mock_client)
    climate.async_write_ha_state = MagicMock()

    await climate.async_set_hvac_mode(HVACMode.COOL)

    mock_client.start_climate.assert_called_once_with(mock_vehicle.vin)
    assert climate.hvac_mode == HVACMode.COOL
    assert climate.async_write_ha_state.called


async def test_set_hvac_mode_auto(mock_vehicle, mock_client):
    """Test setting HVAC mode to AUTO."""
    climate = NissanClimateEntity(mock_vehicle, mock_client)
    climate.async_write_ha_state = MagicMock()

    await climate.async_set_hvac_mode(HVACMode.AUTO)

    mock_client.start_climate.assert_called_once_with(mock_vehicle.vin)
    assert climate.hvac_mode == HVACMode.AUTO
    assert climate.async_write_ha_state.called


def test_hvac_mode_property(mock_vehicle, mock_client):
    """Test hvac_mode property."""
    climate = NissanClimateEntity(mock_vehicle, mock_client)

    assert climate.hvac_mode == HVACMode.OFF

    climate._hvac_mode = HVACMode.HEAT
    assert climate.hvac_mode == HVACMode.HEAT


def test_climate_entity_no_nickname(mock_vehicle, mock_client):
    """Test climate entity when vehicle has no nickname."""
    mock_vehicle.nickname = None
    climate = NissanClimateEntity(mock_vehicle, mock_client)

    assert "TEST123VIN" in climate.name
