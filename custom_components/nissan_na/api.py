"""Smartcar OAuth2 implementation for Nissan NA."""

from typing import Any

from homeassistant.helpers import config_entry_oauth2_flow


class SmartcarOAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Smartcar OAuth2 implementation."""

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to append to the authorization request."""
        scopes = [
            "required:read_vehicle_info",
            "required:read_location",
            "required:read_odometer",
            "required:control_security",
            "read_battery",
            "read_charge",
            "control_charge",
            "read_fuel",
            "read_vin",
            "read_tires",
            "read_engine_oil",
            "read_thermometer",
            "control_engine",
        ]
        return {
            "scope": " ".join(scopes),
            "make": "NISSAN",
            "single_select": "true",
        }
