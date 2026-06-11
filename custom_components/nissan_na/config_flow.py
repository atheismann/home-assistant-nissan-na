"""Config flow for Nissan North America integration.
Uses Smartcar API Authentication (OAuth2 Client Credentials)."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    CONF_MANAGEMENT_TOKEN,
    CONF_UNIT_SYSTEM,
    CONF_USER_ID,
    DOMAIN,
    UNIT_SYSTEM_IMPERIAL,
    UNIT_SYSTEM_METRIC,
)
from .nissan_api import SmartcarApiClient

_LOGGER = logging.getLogger(__name__)


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Smartcar OAuth2 authentication."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data appended to the Smartcar Connect authorize URL."""
        scopes = [
            "required:read_vehicle_info",
            "required:read_location",
            "required:read_odometer",
            "required:control_security",
            "read_battery",
            "read_charge",
            "control_charge",
            "read_charge_locations",
            "read_charge_records",
            "read_fuel",
            "read_vin",
            "read_security",
            "read_tires",
            "read_engine_oil",
            "read_thermometer",
            "read_speedometer",
            "read_compass",
            "read_climate",
            "control_climate",
            "read_alerts",
            "read_diagnostics",
            "read_extended_vehicle_info",
            "read_service_history",
            "read_user_profile",
            "control_navigation",
            "control_trunk",
        ]
        return {
            "scope": " ".join(scopes),
            "make": "NISSAN",
            "single_select": "true",
        }

    async def async_step_creation(self, user_input: dict | None = None) -> dict:
        """Skip the OAuth code→token exchange entirely.

        Smartcar Connect redirects back with a `user_id` (new API Auth flow)
        or `userId` (migration flow) parameter directly in the redirect URL.
        HA captures these in `self.external_data`.  We read the user ID from
        there and call `async_oauth_create_entry` — never touching the token
        endpoint.
        """
        external = getattr(self, "external_data", None) or {}
        # New API Auth flow uses `user_id`; migration flow uses `userId`
        user_id = external.get("user_id") or external.get("userId")
        if not user_id:
            _LOGGER.error(
                "Smartcar Connect redirect did not include a user_id. "
                "Ensure your application is using the v3 API. Params received: %s",
                list(external.keys()),
            )
            return self.async_abort(reason="missing_user_id")

        self._smartcar_user_id: str = user_id
        _LOGGER.debug("Captured user_id from Connect redirect: %s", user_id)
        # Bypass super() to skip token exchange
        return await self.async_oauth_create_entry(
            {"auth_implementation": self.flow_impl.domain}
        )

    async def async_oauth_create_entry(self, data: dict) -> dict:
        """Create a config entry after Connect completes — no tokens stored."""
        if not self.flow_impl.client_id or not self.flow_impl.client_secret:
            _LOGGER.error("API credentials not configured.")
            return self.async_abort(reason="missing_credentials")

        user_id: str | None = getattr(self, "_smartcar_user_id", None)
        if not user_id:
            return self.async_abort(reason="missing_user_id")

        client = SmartcarApiClient(
            client_id=self.flow_impl.client_id,
            client_secret=self.flow_impl.client_secret,
            user_id=user_id,
        )
        try:
            vehicles = await client.get_vehicle_list()
            if not vehicles:
                return self.async_abort(reason="no_vehicles")
        except Exception as err:
            _LOGGER.error("Error fetching vehicles: %s", err, exc_info=True)
            return self.async_abort(reason="connection_error")

        entry_data = {
            "auth_implementation": data.get(
                "auth_implementation", self.flow_impl.domain
            ),
            CONF_USER_ID: user_id,
        }

        if self.source == config_entries.SOURCE_REAUTH:
            reauth_entry = self._get_reauth_entry()
            self.hass.config_entries.async_update_entry(reauth_entry, data=entry_data)
            await self.hass.config_entries.async_reload(reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(title="Nissan (Smartcar)", data=entry_data)

    async def async_step_reauth(self, entry_data: dict) -> dict:
        """Handle reauth upon an API authentication error."""
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
        return NissanNAOptionsFlowHandler()


class NissanNAOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Nissan NA integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> dict:
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "unit_system": "Configure Units (Metric/Imperial)",
                "refresh_sensors": "Refresh All Sensors",
                "rebuild_sensors": "Rebuild Sensors",
                "reload_entities": "Re-load Entities",
                "webhook_config": "Configure Webhooks",
                "reauth": "Re-authorize Integration",
            },
            description_placeholders={
                "unit_info": (
                    "Configure measurement units"
                    " (kilometers/miles, liters/gallons, etc.)"
                ),
                "refresh_info": "Manually fetch current vehicle data from Smartcar",
                "rebuild_info": "Validate and rebuild all sensors",
                "reload_info": "Discover and load any new entities",
                "webhook_info": "Configure real-time vehicle updates via webhooks",
                "reauth_info": "Update API credentials or re-authorize vehicle access",
            },
        )

    async def async_step_unit_system(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_UNIT_SYSTEM] = user_input[CONF_UNIT_SYSTEM]
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=new_options
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current_unit_system = self.config_entry.options.get(
            CONF_UNIT_SYSTEM, UNIT_SYSTEM_METRIC
        )
        return self.async_show_form(
            step_id="unit_system",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UNIT_SYSTEM, default=current_unit_system): vol.In(
                        {
                            UNIT_SYSTEM_METRIC: "Metric (km, L, °C, bar)",
                            UNIT_SYSTEM_IMPERIAL: "Imperial (mi, gal, °F, psi)",
                        }
                    ),
                }
            ),
            description_placeholders={
                "current_system": (
                    "Metric"
                    if current_unit_system == UNIT_SYSTEM_METRIC
                    else "Imperial"
                ),
            },
        )

    async def async_step_refresh_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        try:
            data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not data:
                return self.async_abort(reason="integration_not_loaded")

            sensors = data.get("sensors", {})
            total_sensors = sum(len(v) for v in sensors.values())
            if total_sensors == 0:
                return self.async_abort(reason="no_sensors_found")

            refreshed = 0
            failed = 0
            for vehicle_id, vehicle_sensors in sensors.items():
                for sensor_key, sensor in vehicle_sensors.items():
                    try:
                        await sensor.async_update()
                        refreshed += 1
                    except Exception as err:
                        _LOGGER.warning(
                            "Failed to refresh sensor %s: %s",
                            (
                                sensor._attr_name
                                if hasattr(sensor, "_attr_name")
                                else sensor_key
                            ),
                            err,
                        )
                        failed += 1

            _LOGGER.info(
                "Manual refresh completed: %d updated, %d failed", refreshed, failed
            )
            return self.async_show_form(
                step_id="refresh_complete",
                description_placeholders={
                    "refreshed": str(refreshed),
                    "failed": str(failed),
                    "total": str(total_sensors),
                },
            )
        except Exception as err:
            _LOGGER.error("Error refreshing sensors: %s", err, exc_info=True)
            return self.async_abort(reason="refresh_failed")

    async def async_step_refresh_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        return await self.async_step_init()

    async def async_step_rebuild_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        try:
            data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not data:
                return self.async_abort(reason="integration_not_loaded")

            client = data.get("client")
            if not client:
                return self.async_abort(reason="client_not_found")

            initial_sensors = data.get("sensors", {})
            initial_count = sum(len(v) for v in initial_sensors.values())
            _LOGGER.info("Starting sensor rebuild, current sensors: %d", initial_count)

            from .sensor import async_setup_entry as sensor_setup

            new_entities: list = []

            def async_add_entities_callback(entities, update_before_add=True):
                new_entities.extend(entities)

            await sensor_setup(
                self.hass,
                self.config_entry,
                async_add_entities_callback,
                rebuild_mode=True,
            )

            final_sensors = data.get("sensors", {})
            final_count = sum(len(v) for v in final_sensors.values())
            added = len(new_entities)
            removed = initial_count - final_count + added

            _LOGGER.info(
                "Sensor rebuild completed: %d total, %d added, %d removed",
                final_count,
                added,
                removed,
            )
            return self.async_show_form(
                step_id="rebuild_complete",
                description_placeholders={
                    "initial": str(initial_count),
                    "final": str(final_count),
                    "added": str(added),
                    "removed": str(removed),
                },
            )
        except Exception as err:
            _LOGGER.error("Error rebuilding sensors: %s", err, exc_info=True)
            return self.async_abort(reason="rebuild_failed")

    async def async_step_rebuild_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        return await self.async_step_init()

    async def async_step_reload_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        try:
            from .sensor import async_setup_entry as sensor_setup
            from homeassistant.helpers.entity_registry import (
                async_get as async_get_entity_registry,
            )

            data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not data:
                return self.async_abort(reason="integration_not_loaded")

            client = data.get("client")
            if client:
                try:
                    vehicles = await client.get_vehicle_list()
                    for vehicle in vehicles:
                        signals = await client.get_vehicle_signals(vehicle.id)
                        _LOGGER.info(
                            "Discovered %d signals for vehicle %s",
                            len(signals),
                            vehicle.id,
                        )
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to validate vehicle signals during reload: %s", err
                    )

            current_sensors = data.get("sensors", {})
            initial_count = sum(len(v) for v in current_sensors.values())
            async_get_entity_registry(self.hass)

            new_entities: list = []

            def async_add_entities(entities):
                new_entities.extend(entities)

            await sensor_setup(self.hass, self.config_entry, async_add_entities)

            current_sensors = data.get("sensors", {})
            final_count = sum(len(v) for v in current_sensors.values())

            _LOGGER.info(
                "Entity reload completed: %d new sensors, %d total",
                final_count - initial_count,
                final_count,
            )
            return self.async_show_form(
                step_id="reload_complete",
                description_placeholders={
                    "initial": str(initial_count),
                    "final": str(final_count),
                    "new": str(final_count - initial_count),
                },
            )
        except Exception as err:
            _LOGGER.error("Error reloading entities: %s", err, exc_info=True)
            return self.async_abort(reason="reload_failed")

    async def async_step_reload_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        return await self.async_step_init()

    async def async_step_webhook_config(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
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
                    "To enable real-time webhook updates from Smartcar:\n"
                    "1. Get your Application Management"
                    " Token from the Smartcar Dashboard\n"
                    "2. Enter it below\n"
                    "3. Configure this webhook URL in"
                    f" your Smartcar Dashboard: {webhook_url}"
                ),
            },
        )

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> dict:
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
