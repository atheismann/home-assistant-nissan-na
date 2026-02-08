"""Tests for the Nissan NA OAuth2 config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries

from custom_components.nissan_na.const import CONF_MANAGEMENT_TOKEN, DOMAIN


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.nissan_na.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


async def test_oauth2_flow():
    """Test the OAuth2 flow is properly configured."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    assert OAuth2FlowHandler.DOMAIN == DOMAIN


async def test_extra_authorize_data():
    """Test extra authorize data includes Nissan-specific parameters."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()

    extra_data = flow.extra_authorize_data
    assert extra_data["make"] == "NISSAN"
    assert extra_data["single_select"] == "true"


async def test_oauth_create_entry_success():
    """Test creating entry after successful OAuth."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = MagicMock()
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    # Mock the API client
    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient"
    ) as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_vehicle_list = AsyncMock(return_value=[{"id": "vehicle_1"}])
        mock_client.return_value = mock_instance

        # Mock async_create_entry
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        flow.async_abort = MagicMock(return_value={"type": "abort"})

        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        assert result["type"] == "create_entry"
        assert mock_client.called


async def test_oauth_create_entry_no_vehicles():
    """Test OAuth flow when no vehicles found."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = MagicMock()
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    # Mock the API client with no vehicles
    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient"
    ) as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_vehicle_list = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        flow.async_abort = MagicMock(
            return_value={"type": "abort", "reason": "no_vehicles"}
        )

        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        assert result["type"] == "abort"
        assert result["reason"] == "no_vehicles"


async def test_oauth_create_entry_connection_error():
    """Test OAuth flow when connection fails."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = MagicMock()
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    # Mock the API client to raise exception
    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient"
    ) as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_vehicle_list = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        mock_client.return_value = mock_instance

        flow.async_abort = MagicMock(
            return_value={"type": "abort", "reason": "connection_error"}
        )

        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        assert result["type"] == "abort"
        assert result["reason"] == "connection_error"


async def test_options_flow_init(hass):
    """Test the options flow init step shows menu."""
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    flow = NissanNAOptionsFlowHandler()
    result = await flow.async_step_init()

    assert result["type"] == "menu"
    assert result["step_id"] == "init"
    assert "refresh_sensors" in result["menu_options"]
    assert "webhook_config" in result["menu_options"]
    assert "reauth" in result["menu_options"]


async def test_options_flow_webhook_config_display(hass):
    """Test webhook config step displays current configuration."""
    from homeassistant.config_entries import ConfigEntry
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.data = {
        "management_token": "test_token",
        "webhook_url": "https://example.com/webhook",
    }

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    # Use internal attribute to avoid deprecation warning in tests
    flow._config_entry = config_entry

    result = await flow.async_step_webhook_config()

    assert result["type"] == "form"
    assert result["step_id"] == "webhook_config"
    assert "webhook_url" in result["description_placeholders"]


async def test_options_flow_refresh_sensors_no_data(hass):
    """Test refresh sensors when integration data not found."""
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    # Don't populate hass.data
    hass.data[DOMAIN] = {}

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = config_entry

    result = await flow.async_step_refresh_sensors()

    assert result["type"] == "abort"
    assert result["reason"] == "integration_not_loaded"


async def test_options_flow_refresh_sensors_no_sensors(hass):
    """Test refresh sensors when no sensors exist."""
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    # Setup hass data with empty sensors
    hass.data[DOMAIN] = {"test_entry": {"sensors": {}}}

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = config_entry

    result = await flow.async_step_refresh_sensors()

    assert result["type"] == "abort"
    assert result["reason"] == "no_sensors_found"


async def test_options_flow_refresh_sensors_success(hass):
    """Test successful sensor refresh."""
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    # Create mock sensors
    mock_sensor = MagicMock()
    mock_sensor.async_update = AsyncMock()
    mock_sensor._attr_name = "Test Sensor"

    # Setup hass data with sensors
    hass.data[DOMAIN] = {
        "test_entry": {"sensors": {"vehicle_1": {"battery": mock_sensor}}}
    }

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = config_entry

    result = await flow.async_step_refresh_sensors()

    # Verify sensor was updated
    assert mock_sensor.async_update.called
    # Verify result
    assert result["type"] == "form"
    assert result["step_id"] == "refresh_complete"
    assert "1" in result["description_placeholders"]["refreshed"]


async def test_options_flow_refresh_complete(hass):
    """Test refresh complete step returns to init."""
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    flow = NissanNAOptionsFlowHandler()
    result = await flow.async_step_refresh_complete()

    assert result["type"] == "menu"
    assert result["step_id"] == "init"


async def test_options_flow_webhook_config_no_input(hass):
    """Test webhook configuration form displays without input."""
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.data = {
        "management_token": "test_token",
        "webhook_url": "https://example.com/webhook",
    }

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = config_entry

    # Call without user input to show form
    result = await flow.async_step_webhook_config(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "webhook_config"


async def test_options_flow_reauth_triggers_flow(hass):
    """Test reauth step initiates OAuth flow."""
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.data = {}

    flow = NissanNAOptionsFlowHandler()
    flow.hass = hass
    flow._config_entry = config_entry
    flow.hass.async_create_task = MagicMock()

    result = await flow.async_step_reauth()

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_triggered"
    # Verify async task was created for flow init
    assert flow.hass.async_create_task.called




async def test_oauth_create_entry_missing_credentials():
    """Test OAuth flow fails when credentials not configured."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = MagicMock()
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = None  # Missing client_id
    flow.flow_impl.client_secret = None  # Missing client_secret
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    flow.async_abort = MagicMock(
        return_value={"type": "abort", "reason": "missing_credentials"}
    )

    data = {
        "token": {
            "access_token": "test_access",
            "refresh_token": "test_refresh",
        }
    }

    result = await flow.async_oauth_create_entry(data)

    assert result["type"] == "abort"
    assert result["reason"] == "missing_credentials"
    flow.async_abort.assert_called_with(reason="missing_credentials")


async def test_oauth_create_entry_connection_error():
    """Test OAuth flow handles API connection errors."""
    from custom_components.nissan_na.config_flow import OAuth2FlowHandler

    flow = OAuth2FlowHandler()
    flow.hass = MagicMock()
    flow.flow_impl = MagicMock()
    flow.flow_impl.client_id = "test_client"
    flow.flow_impl.client_secret = "test_secret"
    flow.flow_impl.redirect_uri = "https://my.home-assistant.io/redirect/oauth"

    # Mock the API client to raise an error
    with patch(
        "custom_components.nissan_na.nissan_api.SmartcarApiClient"
    ) as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_vehicle_list = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        mock_client.return_value = mock_instance

        flow.async_abort = MagicMock(
            return_value={"type": "abort", "reason": "connection_error"}
        )

        data = {
            "token": {
                "access_token": "test_access",
                "refresh_token": "test_refresh",
            }
        }

        result = await flow.async_oauth_create_entry(data)

        assert result["type"] == "abort"
        assert result["reason"] == "connection_error"
        flow.async_abort.assert_called_with(reason="connection_error")

