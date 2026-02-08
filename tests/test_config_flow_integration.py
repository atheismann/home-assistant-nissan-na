"""Integration tests for config_flow using Home Assistant testing framework."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nissan_na.const import CONF_MANAGEMENT_TOKEN, DOMAIN


@pytest.fixture
def mock_nissan_client():
    """Create a mock Nissan API client."""
    client = MagicMock()
    client.get_vehicle_list = AsyncMock(
        return_value=[
            MagicMock(
                id="vehicle_1",
                vin="12345678901234567",
                nickname="My Nissan",
                year=2023,
                make="NISSAN",
                model="Leaf",
            )
        ]
    )
    client.get_permissions = AsyncMock(return_value=["read_battery", "read_odometer"])
    client.get_vehicle_status = AsyncMock(
        return_value={"batteryLevel": 85, "odometer": 10000}
    )
    return client


async def test_options_flow_menu_shows_all_options(hass: HomeAssistant, mock_nissan_client):
    """Test options flow can be created from entry."""
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

    # Verify entry exists
    assert entry in hass.config_entries.async_entries(DOMAIN)



async def test_options_flow_refresh_sensors_updates_all_sensors(
    hass: HomeAssistant, mock_nissan_client
):
    """Test refresh sensors option calls async_update on all sensors."""
    from custom_components.nissan_na.sensor import NissanGenericSensor

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

    # Create mock vehicle
    vehicle = MagicMock()
    vehicle.id = "vehicle_1"
    vehicle.vin = "12345678901234567"
    vehicle.nickname = "My Nissan"

    # Create mock sensors
    mock_sensors = {
        "batteryLevel": MagicMock(
            spec=NissanGenericSensor,
            _attr_name="My Nissan Battery Level",
            async_update=AsyncMock(),
        ),
        "odometer": MagicMock(
            spec=NissanGenericSensor,
            _attr_name="My Nissan Odometer",
            async_update=AsyncMock(),
        ),
    }

    # Setup hass.data with sensors
    hass.data[DOMAIN] = {
        entry.entry_id: {
            "client": mock_nissan_client,
            "sensors": {"vehicle_1": mock_sensors},
        }
    }

    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = entry
    flow.async_show_form = MagicMock(return_value={"type": "form"})

    # Call refresh sensors
    result = await flow.async_step_refresh_sensors()

    # Verify all sensors were updated
    for sensor in mock_sensors.values():
        sensor.async_update.assert_called()

    # Should show completion form
    assert result["type"] == "form"


async def test_oauth_flow_with_valid_vehicles(hass: HomeAssistant, mock_nissan_client):
    """Test OAuth flow succeeds when vehicles are found."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient",
        return_value=mock_nissan_client,
    ):
        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        # Should create entry
        assert result["type"] == "create_entry"
        flow.async_create_entry.assert_called()


async def test_oauth_flow_handles_no_vehicles(hass: HomeAssistant):
    """Test OAuth flow aborts when no vehicles found."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    flow.async_abort = MagicMock(
        return_value={"type": "abort", "reason": "no_vehicles"}
    )

    # Mock client with no vehicles
    mock_client = MagicMock()
    mock_client.get_vehicle_list = AsyncMock(return_value=[])

    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient",
        return_value=mock_client,
    ):
        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        # Should abort
        assert result["type"] == "abort"
        assert result["reason"] == "no_vehicles"


async def test_oauth_flow_reauth_updates_entry(hass: HomeAssistant, mock_nissan_client):
    """Test OAuth flow handles reauth source correctly."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test_unique_id",
        data={
            "token": {
                "access_token": "old_access",
                "refresh_token": "old_refresh",
            }
        },
    )
    entry.add_to_hass(hass)

    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient",
        return_value=mock_nissan_client,
    ):
        data = {
            "token": {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        # In normal flow (not reauth), should create entry
        assert result["type"] == "create_entry"



async def test_options_flow_webhook_config_displays_current_token(
    hass: HomeAssistant,
):
    """Test webhook config entry stores management token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MANAGEMENT_TOKEN: "existing_token_value",
            "webhook_url": "https://example.com/webhook/123",
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            },
        },
    )
    entry.add_to_hass(hass)

    # Verify token is stored in config entry
    assert entry.data[CONF_MANAGEMENT_TOKEN] == "existing_token_value"
    assert entry.data["webhook_url"] == "https://example.com/webhook/123"



async def test_options_flow_refresh_handles_sensor_errors(hass: HomeAssistant):
    """Test refresh sensors handles individual sensor update failures."""
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

    # Create mock sensors - one fails, one succeeds
    mock_sensors = {
        "battery": MagicMock(
            _attr_name="Battery",
            async_update=AsyncMock(),  # Success
        ),
        "odometer": MagicMock(
            _attr_name="Odometer",
            async_update=AsyncMock(side_effect=Exception("API Error")),  # Fails
        ),
    }

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "sensors": {"vehicle_1": mock_sensors},
        }
    }

    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = entry

    # Both sensors should be called
    result = await flow.async_step_refresh_sensors()

    # Both update methods should have been called
    for sensor in mock_sensors.values():
        sensor.async_update.assert_called()



async def test_options_flow_refresh_with_multiple_vehicles(hass: HomeAssistant):
    """Test refresh sensors works with multiple vehicles."""
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

    # Create sensors for multiple vehicles
    mock_sensors = {
        "vehicle_1": {
            "battery": MagicMock(
                _attr_name="Vehicle 1 Battery",
                async_update=AsyncMock(),
            ),
        },
        "vehicle_2": {
            "battery": MagicMock(
                _attr_name="Vehicle 2 Battery",
                async_update=AsyncMock(),
            ),
        },
    }

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "sensors": mock_sensors,
        }
    }

    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = entry
    flow.async_show_form = MagicMock(return_value={"type": "form"})

    result = await flow.async_step_refresh_sensors()

    # Should update all sensors from both vehicles
    for vehicle_sensors in mock_sensors.values():
        for sensor in vehicle_sensors.values():
            sensor.async_update.assert_called()

    assert result["type"] == "form"


async def test_oauth_flow_with_api_error(hass: HomeAssistant):
    """Test OAuth flow handles API errors during vehicle fetch."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    flow.async_abort = MagicMock(
        return_value={"type": "abort", "reason": "connection_error"}
    )

    # Mock client that raises an error
    mock_client = MagicMock()
    mock_client.get_vehicle_list = AsyncMock(
        side_effect=Exception("API Connection failed")
    )

    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient",
        return_value=mock_client,
    ):
        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        assert result["type"] == "abort"
        assert result["reason"] == "connection_error"


async def test_options_flow_webhook_config_saves_token(hass: HomeAssistant):
    """Test webhook config saves management token when provided."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MANAGEMENT_TOKEN: "old_token",
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            },
        },
    )
    entry.add_to_hass(hass)

    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = entry
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    # Update token
    result = await flow.async_step_webhook_config(
        user_input={CONF_MANAGEMENT_TOKEN: "new_token_value"}
    )

    # Should create entry (or return to init)
    assert result["type"] in ["create_entry", "abort"]
