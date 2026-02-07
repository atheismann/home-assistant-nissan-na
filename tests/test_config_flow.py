"""Tests for the Nissan NA OAuth2 config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.nissan_na.const import DOMAIN


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
        mock_instance.get_vehicle_list = AsyncMock(
            return_value=[{"id": "vehicle_1"}]
        )
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
