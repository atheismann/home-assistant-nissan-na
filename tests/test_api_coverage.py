"""Tests for API and application credentials."""

from custom_components.nissan_na.api import SmartcarOAuth2Implementation
from custom_components.nissan_na.application_credentials import (
    async_get_authorization_server,
    async_get_description_placeholders,
)


async def test_oauth2_implementation_extra_data(hass):
    """Test OAuth2 implementation extra authorize data."""
    impl = SmartcarOAuth2Implementation(
        hass,
        "nissan_na",
        "client_id",
        "client_secret",
        "https://connect.smartcar.com/oauth/authorize",
        "https://connect.smartcar.com/oauth/token",
    )

    extra_data = impl.extra_authorize_data

    assert "scope" in extra_data
    assert "make" in extra_data
    assert extra_data["make"] == "NISSAN"
    assert "single_select" in extra_data
    assert "required:read_vehicle_info" in extra_data["scope"]


async def test_get_authorization_server(hass):
    """Test getting authorization server details."""
    server = await async_get_authorization_server(hass)

    assert server.authorize_url == "https://connect.smartcar.com/oauth/authorize"
    assert server.token_url == "https://connect.smartcar.com/oauth/token"


async def test_get_description_placeholders(hass):
    """Test getting description placeholders."""
    placeholders = await async_get_description_placeholders(hass)

    assert "setup_url" in placeholders
    assert placeholders["setup_url"] == "https://dashboard.smartcar.com"
