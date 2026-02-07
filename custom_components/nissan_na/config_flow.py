"""Config flow for Nissan North America integration using Smartcar OAuth2."""

import logging
from typing import Any

from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Smartcar OAuth2 authentication."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        return {
            "make": "NISSAN",
            "single_select": "true",
        }

    async def async_oauth_create_entry(self, data: dict) -> dict:
        """Create an entry for Nissan NA after OAuth is complete."""
        # Test connection by getting vehicle list
        from .nissan_api import SmartcarApiClient

        # Extract token data
        token = data["token"]
        client = SmartcarApiClient(
            client_id=self.flow_impl.client_id,
            client_secret=self.flow_impl.client_secret,
            redirect_uri=self.flow_impl.redirect_uri,
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
        )

        try:
            vehicles = await client.get_vehicle_list()
            if not vehicles:
                return self.async_abort(reason="no_vehicles")
        except Exception as err:
            _LOGGER.error("Error fetching vehicles: %s", err, exc_info=True)
            return self.async_abort(reason="connection_error")

        # Create config entry
        return self.async_create_entry(
            title="Nissan (Smartcar)",
            data=data,
        )

    async def async_step_reauth(self, entry_data: dict) -> dict:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()
