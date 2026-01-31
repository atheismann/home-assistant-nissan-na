"""Config flow for Nissan North America integration using Smartcar OAuth."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_CODE,
    CONF_REDIRECT_URI,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from .nissan_api import SmartcarApiClient

_LOGGER = logging.getLogger(__name__)


class NissanNAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Config flow handler for Nissan North America integration using Smartcar OAuth.

    This flow guides users through:
    1. Setting up Smartcar application credentials
    2. Authorizing access via OAuth
    3. Completing the integration setup
    """

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._oauth_data: Dict[str, Any] = {}
        self.client: Optional[SmartcarApiClient] = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """
        Handle the initial step where the user enters Smartcar credentials.

        Users must first create a Smartcar application at:
        https://dashboard.smartcar.com
        """
        errors = {}

        if user_input is not None:
            # Store credentials in instance variable
            self._oauth_data.update(user_input)

            # Initialize Smartcar client
            self.client = SmartcarApiClient(
                client_id=user_input[CONF_CLIENT_ID],
                client_secret=user_input[CONF_CLIENT_SECRET],
                redirect_uri=user_input[CONF_REDIRECT_URI],
            )

            # Generate authorization URL
            try:
                auth_url = self.client.get_auth_url(state="ha_nissan_setup")

                # Show external step for OAuth authorization
                return self.async_external_step(
                    step_id="authorize",
                    url=auth_url,
                )
            except Exception as err:
                _LOGGER.error("Error generating auth URL: %s", err)
                errors["base"] = "auth_url_failed"

        # Show form for Smartcar credentials
        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
                vol.Required(
                    CONF_REDIRECT_URI,
                    default="https://my.home-assistant.io/redirect/oauth",
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"setup_url": "https://dashboard.smartcar.com"},
        )

    async def async_step_authorize(self, user_input: Optional[Dict[str, Any]] = None):
        """
        Handle the OAuth authorization callback.

        This step is called after the user authorizes the app in their browser.
        """
        if user_input is None:
            return self.async_external_step_done(next_step_id="authorize")

        errors = {}

        # Extract authorization code from callback
        code = user_input.get(CONF_CODE)

        if code:
            try:
                # Exchange code for tokens
                token_response = await self.client.authenticate(code)

                # Store tokens in config data
                self._oauth_data[CONF_ACCESS_TOKEN] = token_response["access_token"]
                self._oauth_data[CONF_REFRESH_TOKEN] = token_response["refresh_token"]

                # Test the connection by getting vehicle list
                vehicles = await self.client.get_vehicle_list()

                if not vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    # Success! Create the config entry
                    return self.async_create_entry(
                        title="Nissan (Smartcar)",
                        data=self._oauth_data,
                        options={"update_interval": 15},
                    )

            except Exception as err:
                _LOGGER.error("Error during OAuth authentication: %s", err)
                errors["base"] = "auth_failed"
        else:
            errors["base"] = "no_code"

        # If we got here, something went wrong
        return self.async_abort(reason="auth_failed")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NissanNAOptionsFlow(config_entry)


class NissanNAOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Nissan NA integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """
        Manage the options for update interval.
        """
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get("update_interval", 15)

        data_schema = vol.Schema(
            {
                vol.Optional("update_interval", default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=60)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
