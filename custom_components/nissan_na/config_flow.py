"""Config flow for Nissan North America integration using Smartcar OAuth2."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_entry_oauth2_flow

from .const import CONF_MANAGEMENT_TOKEN, CONF_UNIT_SYSTEM, DOMAIN, UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC
from .nissan_api import SmartcarApiClient

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
                "reauth_info": "Update OAuth permissions when new features are added",
            },
        )

    async def async_step_unit_system(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Configure unit system (metric/imperial)."""
        if user_input is not None:
            # Update options with new unit system
            new_options = {**self.config_entry.options}
            new_options[CONF_UNIT_SYSTEM] = user_input[CONF_UNIT_SYSTEM]
            
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=new_options
            )
            
            # Reload the integration to apply new units
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            return self.async_create_entry(title="", data={})

        # Get current unit system or default to metric
        current_unit_system = self.config_entry.options.get(
            CONF_UNIT_SYSTEM, UNIT_SYSTEM_METRIC
        )

        return self.async_show_form(
            step_id="unit_system",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UNIT_SYSTEM,
                        default=current_unit_system,
                    ): vol.In({
                        UNIT_SYSTEM_METRIC: "Metric (km, L, °C, bar)",
                        UNIT_SYSTEM_IMPERIAL: "Imperial (mi, gal, °F, psi)",
                    }),
                }
            ),
            description_placeholders={
                "current_system": "Metric" if current_unit_system == UNIT_SYSTEM_METRIC else "Imperial",
            },
        )

    async def async_step_refresh_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Manually refresh all sensors for this integration."""
        try:
            # Get integration data
            data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not data:
                return self.async_abort(reason="integration_not_loaded")

            sensors = data.get("sensors", {})
            total_sensors = sum(len(vehicle_sensors) for vehicle_sensors in sensors.values())
            
            if total_sensors == 0:
                return self.async_abort(reason="no_sensors_found")

            # Refresh all sensors
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
                            sensor._attr_name if hasattr(sensor, '_attr_name') else sensor_key,
                            err,
                        )
                        failed += 1

            _LOGGER.info(
                "Manual refresh completed: %d sensors updated, %d failed",
                refreshed,
                failed,
            )

            # Show success message and return to menu
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
        # Return to main menu
        return await self.async_step_init()
    
    async def async_step_rebuild_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Rebuild sensors - remove unsupported and add new sensors."""
        try:
            # Get integration data
            data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not data:
                return self.async_abort(reason="integration_not_loaded")

            client = data.get("client")
            if not client:
                return self.async_abort(reason="client_not_found")
            
            # Get current sensor counts
            initial_sensors = data.get("sensors", {})
            initial_count = sum(len(vehicle_sensors) for vehicle_sensors in initial_sensors.values())
            
            _LOGGER.info("Starting sensor rebuild, current sensors: %d", initial_count)
            
            # Import and call sensor setup in rebuild mode
            from .sensor import async_setup_entry as sensor_setup
            
            # Track new entities
            new_entities = []
            
            async def async_add_entities(entities, update_before_add=True):
                """Callback to track and add entities."""
                new_entities.extend(entities)
                # Add to Home Assistant
                from homeassistant.helpers.entity_platform import AddEntitiesCallback
                # We need to manually add these to the platform
                platform = self.hass.data.get("entity_platform", {}).get("sensor", [])
                for p in platform:
                    if p.config_entry == self.config_entry:
                        await p.async_add_entities(entities, update_before_add)
                        break
            
            # Re-run sensor setup in rebuild mode
            await sensor_setup(self.hass, self.config_entry, async_add_entities, rebuild_mode=True)
            
            # Count sensors after rebuild
            final_sensors = data.get("sensors", {})
            final_count = sum(len(vehicle_sensors) for vehicle_sensors in final_sensors.values())
            
            added = len(new_entities)
            removed = initial_count - final_count + added
            
            _LOGGER.info(
                "Sensor rebuild completed: %d total sensors, %d added, %d removed",
                final_count,
                added,
                removed,
            )
            
            # Show completion
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
        # Return to main menu
        return await self.async_step_init()

    async def async_step_reload_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Reload entities and discover new sensors."""
        try:
            # Reload the sensor platform to discover new entities
            from .sensor import async_setup_entry as sensor_setup
            
            data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not data:
                return self.async_abort(reason="integration_not_loaded")

            # Validate available signals for all vehicles
            client = data.get("client")
            if client:
                try:
                    vehicles = await client.get_vehicle_list()
                    for vehicle in vehicles:
                        signals = await client.get_vehicle_signals(vehicle.id)
                        _LOGGER.info(
                            "Discovered %d available signals for vehicle %s",
                            len(signals),
                            vehicle.id,
                        )
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to validate vehicle signals during reload: %s",
                        err,
                    )

            # Get current sensor tracking
            current_sensors = data.get("sensors", {})
            initial_count = sum(len(v) for v in current_sensors.values())
            
            # Create entity registry lookup
            from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
            entity_registry = async_get_entity_registry(self.hass)
            
            # Track new entities
            new_entities = []
            
            async def async_add_entities(entities):
                """Callback to track added entities."""
                new_entities.extend(entities)
            
            # Re-run sensor setup to discover new entities
            await sensor_setup(self.hass, self.config_entry, async_add_entities)
            
            # Count sensors after reload
            current_sensors = data.get("sensors", {})
            final_count = sum(len(v) for v in current_sensors.values())
            
            new_count = final_count - initial_count
            
            _LOGGER.info(
                "Entity reload completed: %d new sensors discovered, %d total sensors",
                new_count,
                final_count,
            )
            
            # Show completion form and return to menu
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
        # Return to main menu
        return await self.async_step_init()

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
