"""Smartcar OAuth2 implementation for Nissan NA."""

from typing import Any

from homeassistant.helpers import config_entry_oauth2_flow


class SmartcarOAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Smartcar OAuth2 implementation."""

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to append to the authorization request."""
        return {
            "make": "NISSAN",
            "single_select": "true",
        }
