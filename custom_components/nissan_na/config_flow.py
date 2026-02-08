"""Config flow for Nissan North America integration using Smartcar OAuth2."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_entry_oauth2_flow

from .const import CONF_MANAGEMENT_TOKEN, DOMAIN

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
        scopes = [
            # Required permissions
            "required:read_vehicle_info",
            "required:read_location",
            "required:read_odometer",
            "required:control_security",
            # EV/Battery permissions
            "read_battery",
            "read_charge",
            "control_charge",
            "read_charge_locations",
            "read_charge_records",
            # General vehicle data
            "read_fuel",
            "read_vin",
            "read_security",
            "read_tires",
            "read_engine_oil",
            "read_thermometer",
            "read_speedometer",
            "read_compass",
            # Climate control
            "read_climate",
            "control_climate",
            # Advanced features
            "read_alerts",
            "read_diagnostics",
            "read_extended_vehicle_info",
            "read_service_history",
            "read_user_profile",
            # Additional control
            "control_navigation",
            "control_trunk",
        ]
        return {
            "scope": " ".join(scopes),
            "make": "NISSAN",
            "single_select": "true",
        }

    async def async_oauth_create_entry(self, data: dict) -> dict:
        """Create an entry for Nissan NA after OAuth is complete."""
        # Test connection by getting vehicle list
        from .nissan_api import SmartcarApiClient

        # Validate OAuth implementation has credentials
        if not self.flow_impl.client_id or not self.flow_impl.client_secret:
            _LOGGER.error(
                "OAuth credentials not configured. "
                "Please set up Application Credentials first."
            )
            return self.async_abort(reason="missing_credentials")

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

        # Check if this is a reauth flow
        if self.source == config_entries.SOURCE_REAUTH:
            # Update existing entry with new tokens
            reauth_entry = self._get_reauth_entry()
            self.hass.config_entries.async_update_entry(reauth_entry, data=data)
            await self.hass.config_entries.async_reload(reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        # Create new config entry
        return self.async_create_entry(
            title="Nissan (Smartcar)",
            data=data,
        )

    async def async_step_reauth(self, entry_data: dict) -> dict:
        """Perform reauth upon an API authentication error."""
        # Store the entry being reauthenticated
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry and entry.unique_id:
            await self.async_set_unique_id(entry.unique_id)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return NissanNAOptionsFlowHandler()


class NissanNAOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Nissan NA integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> dict:
        """Show menu for configuration options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["webhook_config", "reauth"],
            description_placeholders={
                "webhook_info": "Configure real-time vehicle updates via webhooks",
                "reauth_info": "Update OAuth permissions when new features are added",
            },
        )

    async def async_step_webhook_config(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Manage the webhook configuration."""
        if user_input is not None:
            # Update the config entry data with management token
            new_data = {**self.config_entry.data}
            if user_input.get(CONF_MANAGEMENT_TOKEN):
                new_data[CONF_MANAGEMENT_TOKEN] = user_input[CONF_MANAGEMENT_TOKEN]

            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )

            return self.async_create_entry(title="", data={})

        current_token = self.config_entry.data.get(CONF_MANAGEMENT_TOKEN, "")
        webhook_url = self.config_entry.data.get("webhook_url", "Not configured")

        return self.async_show_form(
            step_id="webhook_config",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MANAGEMENT_TOKEN,
                        description={"suggested_value": current_token},
                    ): str,
                }
            ),
            description_placeholders={
                "webhook_url": webhook_url,
                "webhook_info": (
                    "To enable real-time webhook updates from "
                    "Smartcar, you need to:\n"
                    "1. Get your Application Management Token from "
                    "the Smartcar Dashboard\n"
                    "2. Enter it below\n"
                    "3. Configure this webhook URL in your Smartcar "
                    f"Dashboard: {webhook_url}\n\n"
                    "Your webhook URL will be automatically registered "
                    "once you save."
                ),
            },
        )

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> dict:
        """Handle reauthorization request from options."""
        # Trigger reauth flow by initiating a new config flow with reauth context
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": self.config_entry.entry_id,
                },
                data=self.config_entry.data,
            )
        )
        return self.async_abort(reason="reauth_triggered")
