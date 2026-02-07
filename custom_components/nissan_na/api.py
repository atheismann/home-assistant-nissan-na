"""Smartcar OAuth2 implementation for Nissan NA."""

from typing import Any

from homeassistant.helpers import config_entry_oauth2_flow


class SmartcarOAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Smartcar OAuth2 implementation."""

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to append to the authorization request."""
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
