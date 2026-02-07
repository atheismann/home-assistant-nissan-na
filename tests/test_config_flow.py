"""Tests for the Nissan NA config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries

from custom_components.nissan_na.config_flow import (
    NissanNAConfigFlow,
    NissanNAOptionsFlow,
)
from custom_components.nissan_na.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_CODE,
    CONF_REDIRECT_URI,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.nissan_na.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


def test_config_flow_init():
    """Test config flow initialization."""
    flow = NissanNAConfigFlow()

    assert flow.VERSION == 2
    assert flow.CONNECTION_CLASS == config_entries.CONN_CLASS_CLOUD_POLL
    assert flow._oauth_data == {}
    assert flow.client is None


async def test_async_step_user_no_input():
    """Test user step with no input shows form."""
    flow = NissanNAConfigFlow()

    result = await flow.async_step_user(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert CONF_CLIENT_ID in result["data_schema"].schema
    assert CONF_CLIENT_SECRET in result["data_schema"].schema
    assert CONF_REDIRECT_URI in result["data_schema"].schema


async def test_async_step_user_with_valid_input():
    """Test user step with valid input generates auth URL."""
    flow = NissanNAConfigFlow()
    flow.async_external_step = MagicMock(return_value={"type": "external"})

    with patch(
        "custom_components.nissan_na.config_flow.SmartcarApiClient"
    ) as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_auth_url.return_value = "https://smartcar.com/auth"
        mock_client.return_value = mock_instance

        result = await flow.async_step_user(
            user_input={
                CONF_CLIENT_ID: "test_client_id",
                CONF_CLIENT_SECRET: "test_secret",
                CONF_REDIRECT_URI: "https://example.com/callback",
            }
        )

        assert mock_client.called
        assert mock_instance.get_auth_url.called
        assert flow.async_external_step.called


async def test_async_step_user_auth_url_error():
    """Test user step when auth URL generation fails."""
    flow = NissanNAConfigFlow()

    with patch(
        "custom_components.nissan_na.config_flow.SmartcarApiClient"
    ) as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_auth_url.side_effect = Exception("Auth error")
        mock_client.return_value = mock_instance

        result = await flow.async_step_user(
            user_input={
                CONF_CLIENT_ID: "test_client_id",
                CONF_CLIENT_SECRET: "test_secret",
                CONF_REDIRECT_URI: "https://example.com/callback",
            }
        )

        assert result["type"] == "form"
        assert result["errors"]["base"] == "auth_url_failed"


async def test_async_step_authorize_no_input():
    """Test authorize step with no input."""
    flow = NissanNAConfigFlow()
    flow.async_external_step_done = MagicMock(return_value={"type": "external_done"})

    result = await flow.async_step_authorize(user_input=None)

    assert flow.async_external_step_done.called


async def test_async_step_authorize_success():
    """Test successful OAuth authorization."""
    flow = NissanNAConfigFlow()
    flow.init_data = {
        CONF_CLIENT_ID: "test_id",
        CONF_CLIENT_SECRET: "test_secret",
        CONF_REDIRECT_URI: "https://example.com",
    }
    flow._oauth_data = {"state": "test_state"}

    mock_client = MagicMock()
    mock_client.authenticate = AsyncMock(
        return_value={
            "access_token": "test_access",
            "refresh_token": "test_refresh",
        }
    )
    mock_vehicle = MagicMock()
    mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
    flow.client = mock_client

    result = await flow.async_step_authorize(
        user_input={CONF_CODE: "test_auth_code", "state": "test_state"}
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Nissan (Smartcar)"
    assert result["data"][CONF_ACCESS_TOKEN] == "test_access"
    assert result["data"][CONF_REFRESH_TOKEN] == "test_refresh"


async def test_async_step_authorize_no_vehicles():
    """Test authorization when no vehicles are found."""
    flow = NissanNAConfigFlow()
    flow.init_data = {}
    flow._oauth_data = {"state": "test_state"}

    mock_client = MagicMock()
    mock_client.authenticate = AsyncMock(
        return_value={
            "access_token": "test_access",
            "refresh_token": "test_refresh",
        }
    )
    mock_client.get_vehicle_list = AsyncMock(return_value=[])
    flow.client = mock_client

    result = await flow.async_step_authorize(
        user_input={CONF_CODE: "test_auth_code", "state": "test_state"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "auth_failed"


async def test_async_step_authorize_auth_error():
    """Test authorization when authentication fails."""
    flow = NissanNAConfigFlow()
    flow.init_data = {}
    flow._oauth_data = {"state": "test_state"}

    mock_client = MagicMock()
    mock_client.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
    flow.client = mock_client

    result = await flow.async_step_authorize(
        user_input={CONF_CODE: "test_auth_code", "state": "test_state"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "auth_failed"


async def test_async_step_authorize_no_code():
    """Test authorization when no code is provided."""
    flow = NissanNAConfigFlow()
    flow._oauth_data = {"state": "test_state"}

    result = await flow.async_step_authorize(
        user_input={"state": "test_state"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "auth_failed"


def test_options_flow_init():
    """Test options flow initialization."""
    config_entry = MagicMock()
    flow = NissanNAOptionsFlow(config_entry)

    assert flow.config_entry == config_entry


async def test_async_step_init_no_input():
    """Test options flow init step with no input."""
    config_entry = MagicMock()
    config_entry.options = {"update_interval": 20}
    flow = NissanNAOptionsFlow(config_entry)

    result = await flow.async_step_init(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "init"


async def test_async_step_init_with_input():
    """Test options flow init step with valid input."""
    config_entry = MagicMock()
    config_entry.options = {}
    flow = NissanNAOptionsFlow(config_entry)

    result = await flow.async_step_init(user_input={"update_interval": 30})

    assert result["type"] == "create_entry"
    assert result["data"]["update_interval"] == 30


async def test_async_step_init_default_interval():
    """Test options flow with default update interval."""
    config_entry = MagicMock()
    config_entry.options = {}
    flow = NissanNAOptionsFlow(config_entry)

    result = await flow.async_step_init(user_input=None)

    assert result["type"] == "form"
    # Default interval is 15
    assert "update_interval" in str(result["data_schema"])


def test_async_get_options_flow():
    """Test getting the options flow."""
    config_entry = MagicMock()

    flow = NissanNAConfigFlow.async_get_options_flow(config_entry)

    assert isinstance(flow, NissanNAOptionsFlow)
    assert flow.config_entry == config_entry
