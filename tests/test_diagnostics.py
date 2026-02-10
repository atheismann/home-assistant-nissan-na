"""Tests for diagnostics support."""

from unittest.mock import MagicMock, AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.nissan_na.const import CONF_WEBHOOK_ID, DOMAIN
from custom_components.nissan_na.diagnostics import async_get_config_entry_diagnostics


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.data = {
        CONF_WEBHOOK_ID: "webhook_abc123",
        "webhook_url": "https://example.com/api/webhook/webhook_abc123",
        "token": {
            "access_token": "secret_token_xyz",
            "refresh_token": "refresh_secret_abc",
        },
    }
    return entry


@pytest.fixture
def mock_vehicle():
    """Create a mock vehicle."""
    vehicle = MagicMock()
    vehicle.id = "vehicle_1"
    vehicle.vin = "TEST123VIN"
    vehicle.nickname = "My Nissan"
    return vehicle


async def test_diagnostics_with_webhook_configured(hass: HomeAssistant, mock_config_entry):
    """Test diagnostics output includes webhook URL."""
    diags = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diags["webhook"]["id"] == "webhook_abc123"
    assert diags["webhook"]["url"] == "https://example.com/api/webhook/webhook_abc123"
    assert diags["vehicles"] == 0
    assert diags["sensors"] == 0
    # Tokens should be redacted
    assert "secret_token_xyz" not in str(diags)


async def test_diagnostics_with_vehicles_and_sensors(
    hass: HomeAssistant, mock_config_entry, mock_vehicle
):
    """Test diagnostics shows vehicle and sensor counts."""
    # Setup hass.data with vehicles and sensors
    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "vehicles": [mock_vehicle],
            "sensors": {
                "vehicle_1": {
                    "battery_percent": MagicMock(),
                    "battery_range": MagicMock(),
                    "location_lat": MagicMock(),
                    "location_lon": MagicMock(),
                }
            },
        }
    }

    diags = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diags["vehicles"] == 1
    assert diags["sensors"] == 4


async def test_diagnostics_without_webhook_id(hass: HomeAssistant):
    """Test diagnostics handles missing webhook ID gracefully."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {}  # No webhook_id

    diags = await async_get_config_entry_diagnostics(hass, entry)

    assert diags["webhook"]["id"] == "Not configured"
    assert diags["webhook"]["url"] == "Not configured"


async def test_diagnostics_redacts_tokens(hass: HomeAssistant, mock_config_entry):
    """Test that sensitive tokens are redacted in diagnostics."""
    diags = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Check that token is not present in the output
    diags_str = str(diags)
    assert "secret_token_xyz" not in diags_str
    assert "refresh_secret_abc" not in diags_str

    # Webhook URL should still be visible
    assert "webhook_abc123" in diags_str
