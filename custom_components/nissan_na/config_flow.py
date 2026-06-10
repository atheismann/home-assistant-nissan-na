"""Config flow for Nissan North America integration using Smartcar API Authentication."""

import logging
import urllib.parse
from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_MANAGEMENT_TOKEN,
    CONF_UNIT_SYSTEM,
    CONF_USER_ID,
    DOMAIN,
    UNIT_SYSTEM_IMPERIAL,
    UNIT_SYSTEM_METRIC,
)
from .nissan_api import SmartcarApiClient

_LOGGER = logging.getLogger(__name__)

_CONNECT_AUTHORIZE_URL = "https://connect.smartcar.com/oauth/authorize"
_CONNECT_REDIRECT_URI = "https://my.home-assistant.io/redirect/oauth"

_CONNECT_SCOPE = " ".join([
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
])


def _build_connect_url(client_id: str) -> str:
    """Return the Smartcar Connect URL for the given client_id."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": _CONNECT_REDIRECT_URI,
        "scope": _CONNECT_SCOPE,
        "make": "NISSAN",
        "single_select": "true",
    }
    return f"{_CONNECT_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


class NissanNAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Nissan NA — uses Smartcar API Authentication (no OAuth token exchange)."""

    VERSION = 1

    def __init__(self) -> None:
        self._client_id: str = ""
        self._client_secret: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Step 1: Collect and validate API credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()

            client = SmartcarApiClient(client_id=client_id, client_secret=client_secret)
            try:
                await client._get_access_token()
            except Exception as err:
                _LOGGER.error("Credential validation failed: %s", err)
                errors["base"] = "invalid_credentials"
            else:
                self._client_id = client_id
                self._client_secret = client_secret
                return await self.async_step_connect()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
            }),
            errors=errors,
            description_placeholders={
                "dashboard_url": "https://dashboard.smartcar.com",
            },
        )

    async def async_step_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Step 2: Show Connect URL, collect the user_id from the redirect."""
        errors: dict[str, str] = {}
        connect_url = _build_connect_url(self._client_id)

        if user_input is not None:
            user_id = user_input[CONF_USER_ID].strip()

            client = SmartcarApiClient(
                client_id=self._client_id,
                client_secret=self._client_secret,
                user_id=user_id,
            )
            try:
                vehicles = await client.get_vehicle_list()
                if not vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    return self.async_create_entry(
                        title="Nissan (Smartcar)",
                        data={
                            CONF_CLIENT_ID: self._client_id,
                            CONF_CLIENT_SECRET: self._client_secret,
                            CONF_USER_ID: user_id,
                        },
                    )
            except Exception as err:
                _LOGGER.error("Vehicle list fetch failed: %s", err)
                errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="connect",
            data_schema=vol.Schema({
                vol.Required(CONF_USER_ID): str,
            }),
            errors=errors,
            description_placeholders={
                "connect_url": connect_url,
                "redirect_uri": _CONNECT_REDIRECT_URI,
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> dict:
        """Handle reauthorization."""
        reauth_entry = self._get_reauth_entry()
        self._client_id = reauth_entry.data.get(CONF_CLIENT_ID, "")
        self._client_secret = reauth_entry.data.get(CONF_CLIENT_SECRET, "")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Confirm reauth and proceed to credential entry."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_reauth_user()

    async def async_step_reauth_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Re-enter credentials during reauth."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()

            client = SmartcarApiClient(client_id=client_id, client_secret=client_secret)
            try:
                await client._get_access_token()
            except Exception as err:
                _LOGGER.error("Credential validation failed during reauth: %s", err)
                errors["base"] = "invalid_credentials"
            else:
                self._client_id = client_id
                self._client_secret = client_secret
                return await self.async_step_reauth_connect()

        return self.async_show_form(
            step_id="reauth_user",
            data_schema=vol.Schema({
                vol.Required(CONF_CLIENT_ID, default=self._client_id): str,
                vol.Required(CONF_CLIENT_SECRET): str,
            }),
            errors=errors,
            description_placeholders={
                "dashboard_url": "https://dashboard.smartcar.com",
            },
        )

    async def async_step_reauth_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Re-enter user_id during reauth."""
        errors: dict[str, str] = {}
        connect_url = _build_connect_url(self._client_id)

        if user_input is not None:
            user_id = user_input[CONF_USER_ID].strip()
            client = SmartcarApiClient(
                client_id=self._client_id,
                client_secret=self._client_secret,
                user_id=user_id,
            )
            try:
                vehicles = await client.get_vehicle_list()
                if not vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    reauth_entry = self._get_reauth_entry()
                    self.hass.config_entries.async_update_entry(
                        reauth_entry,
                        data={
                            **reauth_entry.data,
                            CONF_CLIENT_ID: self._client_id,
                            CONF_CLIENT_SECRET: self._client_secret,
                            CONF_USER_ID: user_id,
                        },
                    )
                    await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
            except Exception as err:
                _LOGGER.error("Vehicle list fetch failed during reauth: %s", err)
                errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="reauth_connect",
            data_schema=vol.Schema({
                vol.Required(CONF_USER_ID): str,
            }),
            errors=errors,
            description_placeholders={
                "connect_url": connect_url,
                "redirect_uri": _CONNECT_REDIRECT_URI,
            },
        )

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
            menu_options={
                "unit_system": "Configure Units (Metric/Imperial)",
                "refresh_sensors": "Refresh All Sensors",
                "rebuild_sensors": "Rebuild Sensors",
                "reload_entities": "Re-load Entities",
                "webhook_config": "Configure Webhooks",
                "reauth": "Re-authorize Integration",
            },
            description_placeholders={
                "unit_info": "Configure measurement units (kilometers/miles, liters/gallons, etc.)",
                "refresh_info": "Manually fetch current vehicle data from Smartcar",
                "rebuild_info": "Validate and rebuild all sensors - removes unsupported sensors and adds new ones",
                "reload_info": "Discover and load any new entities not in previous version",
                "webhook_info": "Configure real-time vehicle updates via webhooks",
                "reauth_info": "Update API credentials or re-authorize vehicle access",
            },
        )

    async def async_step_unit_system(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Configure unit system (metric/imperial)."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_UNIT_SYSTEM] = user_input[CONF_UNIT_SYSTEM]
            self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current_unit_system = self.config_entry.options.get(CONF_UNIT_SYSTEM, UNIT_SYSTEM_METRIC)

        return self.async_show_form(
            step_id="unit_system",
            data_schema=vol.Schema({
                vol.Required(CONF_UNIT_SYSTEM, default=current_unit_system): vol.In({
                    UNIT_SYSTEM_METRIC: "Metric (km, L, °C, bar)",
                    UNIT_SYSTEM_IMPERIAL: "Imperial (mi, gal, °F, psi)",
                }),
            }),
            description_placeholders={
                "current_system": "Metric" if current_unit_system == UNIT_SYSTEM_METRIC else "Imperial",
            },
        )

    async def async_step_refresh_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Manually refresh all sensors for this integration."""
        try:
            data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not data:
                return self.async_abort(reason="integration_not_loaded")

            sensors = data.get("sensors", {})
            total_sensors = sum(len(vehicle_sensors) for vehicle_sensors in sensors.values())

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
                            sensor._attr_name if hasattr(sensor, "_attr_name") else sensor_key,
                            err,
                        )
                        failed += 1

            _LOGGER.info("Manual refresh completed: %d sensors updated, %d failed", refreshed, failed)

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
        """Show refresh completion and return to menu."""
        return await self.async_step_init()

    async def async_step_rebuild_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Rebuild sensors - remove unsupported and add new sensors."""
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

            await sensor_setup(self.hass, self.config_entry, async_add_entities_callback, rebuild_mode=True)

            final_sensors = data.get("sensors", {})
            final_count = sum(len(v) for v in final_sensors.values())
            added = len(new_entities)
            removed = initial_count - final_count + added

            _LOGGER.info(
                "Sensor rebuild completed: %d total sensors, %d added, %d removed",
                final_count, added, removed,
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
        """Show rebuild completion and return to menu."""
        return await self.async_step_init()

    async def async_step_reload_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Reload entities and discover new sensors."""
        try:
            from .sensor import async_setup_entry as sensor_setup
            from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

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
                            "Discovered %d available signals for vehicle %s",
                            len(signals), vehicle.id,
                        )
                except Exception as err:
                    _LOGGER.warning("Failed to validate vehicle signals during reload: %s", err)

            current_sensors = data.get("sensors", {})
            initial_count = sum(len(v) for v in current_sensors.values())

            async_get_entity_registry(self.hass)

            new_entities: list = []

            def async_add_entities(entities):
                new_entities.extend(entities)

            await sensor_setup(self.hass, self.config_entry, async_add_entities)

            current_sensors = data.get("sensors", {})
            final_count = sum(len(v) for v in current_sensors.values())
            new_count = final_count - initial_count

            _LOGGER.info(
                "Entity reload completed: %d new sensors discovered, %d total sensors",
                new_count, final_count,
            )

            return self.async_show_form(
                step_id="reload_complete",
                description_placeholders={
                    "initial": str(initial_count),
                    "final": str(final_count),
                    "new": str(new_count),
                },
            )

        except Exception as err:
            _LOGGER.error("Error reloading entities: %s", err, exc_info=True)
            return self.async_abort(reason="reload_failed")

    async def async_step_reload_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Show reload completion and return to menu."""
        return await self.async_step_init()

    async def async_step_webhook_config(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Manage the webhook configuration."""
        if user_input is not None:
            new_data = {**self.config_entry.data}
            if user_input.get(CONF_MANAGEMENT_TOKEN):
                new_data[CONF_MANAGEMENT_TOKEN] = user_input[CONF_MANAGEMENT_TOKEN]
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_token = self.config_entry.data.get(CONF_MANAGEMENT_TOKEN, "")
        webhook_url = self.config_entry.data.get("webhook_url", "Not configured")

        return self.async_show_form(
            step_id="webhook_config",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_MANAGEMENT_TOKEN,
                    description={"suggested_value": current_token},
                ): str,
            }),
            description_placeholders={
                "webhook_url": webhook_url,
                "webhook_info": (
                    "To enable real-time webhook updates from Smartcar, you need to:\n"
                    "1. Get your Application Management Token from the Smartcar Dashboard\n"
                    "2. Enter it below\n"
                    f"3. Configure this webhook URL in your Smartcar Dashboard: {webhook_url}\n\n"
                    "Your webhook URL will be automatically registered once you save."
                ),
            },
        )

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> dict:
        """Handle reauthorization request from options."""
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
