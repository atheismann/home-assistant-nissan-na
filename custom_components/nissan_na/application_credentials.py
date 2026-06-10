"""Application credentials platform for Nissan NA integration."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

# Smartcar Connect is still used once to authorize the user's vehicle and
# capture the userId from the redirect URL.  No auth-code token exchange
# occurs — the redirect params are read directly by the config flow.
AUTHORIZATION_SERVER = AuthorizationServer(
    authorize_url="https://connect.smartcar.com/oauth/authorize",
    token_url="https://iam.smartcar.com/oauth2/token",
)


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AUTHORIZATION_SERVER


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return description placeholders for the credentials dialog."""
    return {
        "setup_url": "https://dashboard.smartcar.com",
        "more_info_url": "https://github.com/atheismann/home-assistant-nissan-na",
    }
