from homeassistant.config_entries import ConfigFlow
import voluptuous as vol

from . import DOMAIN


class NissanNAConfigFlow(ConfigFlow, domain=DOMAIN):
    """
    Config flow handler for Nissan North America integration.
    Handles the UI-based configuration and authentication.
    """

    VERSION = 1

    def __init__(self):
        self.init_data = {}

    async def async_step_user(self, user_input=None):
        """
        Handle the initial step where the user enters credentials and update interval.
        """
        errors = {}
        if user_input is not None:
            # Placeholder for authentication logic
            self.init_data = user_input
            return self.async_create_entry(
                title="Nissan NA",
                data=user_input,
                options={"update_interval": user_input.get("update_interval", 15)},
            )

        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Optional("update_interval", default=15): int,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_options(self, user_input=None):
        """
        Allow the user to change the update interval after setup.
        """
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Options", data=user_input)

        current = self.options if hasattr(self, "options") else self.init_data
        data_schema = vol.Schema(
            {
                vol.Optional(
                    "update_interval", default=current.get("update_interval", 15)
                ): int,
            }
        )
        return self.async_show_form(
            step_id="options", data_schema=data_schema, errors=errors
        )
