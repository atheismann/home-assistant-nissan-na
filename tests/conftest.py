"""Pytest configuration and shared fixtures.

Test Organization:
- Core: test_const.py, test_unit_conversion.py
- API: test_api.py, test_application_credentials.py, test_nissan_api.py, test_services.py
- Platforms: test_binary_sensor.py, test_climate.py, test_config_flow.py, 
             test_device_tracker.py, test_sensor.py, test_switch.py, test_webhook.py
- System: test_acceptance.py, test_diagnostics.py, test_init.py

This module provides shared fixtures used across all test files.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.nissan_na.const import DOMAIN, CONF_UNIT_SYSTEM


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.async_create_task = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock ConfigEntry."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": 9999999999,
        "webhook_id": "test_webhook_id",
        "webhook_url": "https://example.com/webhook",
    }
    config_entry.options = {}
    config_entry.unique_id = "test_unique_id"
    return config_entry


@pytest.fixture
def mock_vehicle():
    """Create a mock vehicle."""
    vehicle = MagicMock()
    vehicle.id = "vehicle_123"
    vehicle.vin = "VIN123ABC"
    vehicle.nickname = "Test Vehicle"
    vehicle.year = 2024
    vehicle.make = "NISSAN"
    vehicle.model = "LEAF"
    return vehicle


@pytest.fixture
def mock_vehicle_no_nickname():
    """Create a mock vehicle without nickname."""
    vehicle = MagicMock()
    vehicle.id = "vehicle_456"
    vehicle.vin = "VIN456DEF"
    vehicle.nickname = None
    vehicle.year = 2024
    vehicle.make = "NISSAN"
    vehicle.model = "ARIYA"
    return vehicle


@pytest.fixture
def mock_config_entry_metric(mock_hass):
    """Create a mock ConfigEntry with metric unit system."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_metric"
    config_entry.data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": 9999999999,
        "webhook_id": "test_webhook_id",
        "webhook_url": "https://example.com/webhook",
    }
    config_entry.options = {CONF_UNIT_SYSTEM: "metric"}
    config_entry.unique_id = "test_unique_metric"
    # Configure mock_hass to return this entry
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=config_entry)
    return config_entry


@pytest.fixture
def mock_config_entry_imperial(mock_hass):
    """Create a mock ConfigEntry with imperial unit system."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_imperial"
    config_entry.data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": 9999999999,
        "webhook_id": "test_webhook_id",
        "webhook_url": "https://example.com/webhook",
    }
    config_entry.options = {CONF_UNIT_SYSTEM: "imperial"}
    config_entry.unique_id = "test_unique_imperial"
    # Configure mock_hass to return this entry
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=config_entry)
    return config_entry


@pytest.fixture
def mock_client():
    """Create a mock Nissan API client."""
    client = MagicMock()
    client.get_vehicle_list = AsyncMock(return_value=[])
    client.get_vehicle_signals = AsyncMock(return_value=[])
    client.get_vehicle_status = AsyncMock(return_value={})
    client.get_permissions = AsyncMock(return_value=[])
    return client
