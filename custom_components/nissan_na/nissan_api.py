"""
Smartcar API client implementation for Nissan vehicles.

This module provides the SmartcarApiClient class for interacting with
Nissan vehicles through the Smartcar API. It supports OAuth authentication,
vehicle data retrieval, and remote actions such as locking/unlocking doors,
starting/stopping climate control, location tracking, and more.

Smartcar API documentation: https://smartcar.com/docs/
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
import smartcar
from pydantic import BaseModel

_LOGGER = logging.getLogger(__name__)


def _namedtuple_to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert a namedtuple (or any object with __dict__) to a dictionary.

    This helper handles smartcar v6 API responses which return namedtuples.

    Args:
        obj: Object to convert (namedtuple, dict, or other).

    Returns:
        dict: Dictionary representation of the object.
    """
    if isinstance(obj, dict):
        return obj
    elif hasattr(obj, "_asdict"):
        # It's a namedtuple
        result = obj._asdict()
        # Recursively convert nested namedtuples
        return {
            k: _namedtuple_to_dict(v) if hasattr(v, "_asdict") else v
            for k, v in result.items()
        }
    else:
        # Try to access as attributes
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}


class Vehicle(BaseModel):
    """Model representing a Nissan vehicle."""

    vin: str
    id: str  # Smartcar vehicle ID
    model: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None


class SmartcarApiClient:
    """
    Client for interacting with Nissan vehicles via Smartcar API.

    The Smartcar API provides a standardized interface for vehicle connectivity
    across multiple brands including Nissan. This client handles OAuth
    authentication and provides methods for vehicle control and monitoring.

    Methods:
        authenticate: Exchange authorization code for access token.
        get_vehicle_list: Retrieve all vehicles linked to the account.
        get_vehicle_info: Get vehicle make, model, year information.
        get_vehicle_location: Get current vehicle location.
        get_battery_level: Get battery charge level (for EVs).
        get_battery_capacity: Get battery capacity information.
        get_charge_status: Get charging status.
        get_odometer: Get odometer reading.
        get_fuel_level: Get fuel level (for non-EVs).
        get_lock_status: Get lock status of doors and windows.
        get_tire_pressure: Get tire pressure for all tires.
        get_engine_oil: Get engine oil life information.
        lock_doors: Lock the vehicle doors.
        unlock_doors: Unlock the vehicle doors.
        start_charge: Start charging the vehicle.
        stop_charge: Stop charging the vehicle.
        start_climate: Start climate control (direct API call).
        stop_climate: Stop climate control (direct API call).
        get_climate_status: Get climate status (direct API call).
        disconnect: Disconnect a vehicle from Smartcar.

    Note:
        Climate control methods use direct HTTP requests to Smartcar API
        since they are not exposed in the Python SDK.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        test_mode: bool = False,
    ):
        """
        Initialize the SmartcarApiClient.

        Args:
            client_id: Smartcar application client ID.
            client_secret: Smartcar application client secret.
            redirect_uri: OAuth redirect URI configured in Smartcar dashboard.
            access_token: Existing access token (if available).
            refresh_token: Existing refresh token for token renewal.
            test_mode: Use Smartcar test mode (for development/testing).
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.test_mode = test_mode
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._vehicles_cache: Dict[str, smartcar.Vehicle] = {}
        self._api_base_url = "https://api.smartcar.com/v2.0"

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate Smartcar OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection.

        Returns:
            str: Authorization URL for user to grant access.
        """
        client = smartcar.AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            mode="test" if self.test_mode else "live",
        )
        # Build scope list for get_auth_url
        scope = [
            "required:read_vehicle_info",
            "required:read_location",
            "required:read_odometer",
            "required:control_security",
            "read_battery",
            "read_charge",
            "control_charge",
            "read_fuel",
        ]
        # In v6, state goes in options dict
        options = {
            "make_bypass": "NISSAN",  # Skip make selection, go directly to Nissan
        }
        if state:
            options["state"] = state
        return client.get_auth_url(scope=scope, options=options)

    async def authenticate(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback.

        Returns:
            dict: Token information including access_token and refresh_token.
        """
        _LOGGER.debug("Authenticating with Smartcar API")
        client = smartcar.AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )

        # Exchange code for tokens
        # v6 returns an Access NamedTuple
        response = await asyncio.to_thread(client.exchange_code, code)
        self.access_token = response.access_token
        self.refresh_token = response.refresh_token
        _LOGGER.debug("Successfully authenticated with Smartcar API")
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)

        # Clear vehicle cache to ensure fresh tokens are used
        self._vehicles_cache.clear()

        # Return as dict for compatibility
        return {
            "access_token": response.access_token,
            "refresh_token": response.refresh_token,
            "expires_in": response.expires_in,
            "token_type": response.token_type,
            "expiration": response.expiration,
            "refresh_expiration": response.refresh_expiration,
        }

    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using the refresh token.

        Returns:
            dict: New token information.
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        _LOGGER.debug("Refreshing access token with Smartcar API")
        client = smartcar.AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )

        # v6 returns an Access NamedTuple
        response = await asyncio.to_thread(
            client.exchange_refresh_token, self.refresh_token
        )
        self.access_token = response.access_token
        self.refresh_token = response.refresh_token
        _LOGGER.debug("Successfully refreshed access token")
        _LOGGER.debug("New access token: %s", self.access_token)
        _LOGGER.debug("New refresh token: %s", self.refresh_token)

        # Clear vehicle cache since tokens have changed
        # Cached vehicles will use the old token otherwise
        self._vehicles_cache.clear()

        # Return as dict for compatibility
        return {
            "access_token": response.access_token,
            "refresh_token": response.refresh_token,
            "expires_in": response.expires_in,
            "token_type": response.token_type,
            "expiration": response.expiration,
            "refresh_expiration": response.refresh_expiration,
        }

    async def get_vehicle_list(self) -> List[Vehicle]:
        """
        Retrieve a list of vehicles linked to the Smartcar account.

        Returns:
            List[Vehicle]: List of Vehicle objects.
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")

        _LOGGER.debug("API Call: get_vehicle_list")
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: smartcar.get_vehicles")
        # Get vehicle IDs - v6 returns a Vehicles NamedTuple
        response = await asyncio.to_thread(smartcar.get_vehicles, self.access_token)
        vehicle_ids = response.vehicles
        _LOGGER.debug("Retrieved %d vehicles from Smartcar API", len(vehicle_ids))

        vehicles = []
        for vehicle_id in vehicle_ids:
            vehicle = smartcar.Vehicle(vehicle_id, self.access_token)
            self._vehicles_cache[vehicle_id] = vehicle

            # Get vehicle attributes and VIN (v6 API)
            attrs = await asyncio.to_thread(vehicle.attributes)
            vin_response = await asyncio.to_thread(vehicle.vin)

            # Convert namedtuple responses to dict
            attrs_dict = _namedtuple_to_dict(attrs)
            vin_dict = _namedtuple_to_dict(vin_response)

            vehicles.append(
                Vehicle(
                    id=vehicle_id,
                    vin=vin_dict.get("vin", ""),
                    make=attrs_dict.get("make"),
                    model=attrs_dict.get("model"),
                    year=int(attrs_dict["year"]) if attrs_dict.get("year") else None,
                )
            )

        return vehicles

    def _get_vehicle(self, vehicle_id: str) -> smartcar.Vehicle:
        """
        Get or create a Smartcar Vehicle instance.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            smartcar.Vehicle: Vehicle instance.
        """
        if vehicle_id not in self._vehicles_cache:
            self._vehicles_cache[vehicle_id] = smartcar.Vehicle(
                vehicle_id, self.access_token
            )
        return self._vehicles_cache[vehicle_id]

    async def get_vehicle_info(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get vehicle information (make, model, year).

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Vehicle information.
        """
        _LOGGER.debug("API Call: get_vehicle_info | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Methods: vehicle.attributes, vehicle.vin")
        vehicle = self._get_vehicle(vehicle_id)
        attrs = await asyncio.to_thread(vehicle.attributes)
        vin_response = await asyncio.to_thread(vehicle.vin)

        # Convert namedtuple responses to dict for v6
        attrs_dict = _namedtuple_to_dict(attrs)
        vin_dict = _namedtuple_to_dict(vin_response)

        # Convert year to int if it's a string
        year = attrs_dict.get("year")
        if year and isinstance(year, str):
            year = int(year)

        return {
            "id": attrs_dict.get("id"),
            "make": attrs_dict.get("make"),
            "model": attrs_dict.get("model"),
            "year": year,
            "vin": vin_dict.get("vin"),
        }

    async def get_vehicle_location(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get vehicle location coordinates.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Location data with latitude and longitude.
        """
        _LOGGER.debug("API Call: get_vehicle_location | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.location")
        vehicle = self._get_vehicle(vehicle_id)
        location = await asyncio.to_thread(vehicle.location)
        return _namedtuple_to_dict(location)

    async def get_battery_level(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get battery charge level (for electric vehicles).

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Battery level percentage.
        """
        _LOGGER.debug("API Call: get_battery_level | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.battery")
        vehicle = self._get_vehicle(vehicle_id)
        battery = await asyncio.to_thread(vehicle.battery)
        return _namedtuple_to_dict(battery)

    async def get_battery_capacity(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get battery capacity information.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Battery capacity in kWh.
        """
        _LOGGER.debug("API Call: get_battery_capacity | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.battery_capacity")
        vehicle = self._get_vehicle(vehicle_id)
        capacity = await asyncio.to_thread(vehicle.battery_capacity)
        return _namedtuple_to_dict(capacity)

    async def get_charge_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get charging status (plugged in, charging, etc).

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Charging status information.
        """
        _LOGGER.debug("API Call: get_charge_status | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.charge")
        vehicle = self._get_vehicle(vehicle_id)
        charge = await asyncio.to_thread(vehicle.charge)
        return _namedtuple_to_dict(charge)

    async def get_odometer(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get odometer reading.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Odometer distance.
        """
        _LOGGER.debug("API Call: get_odometer | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.odometer")
        vehicle = self._get_vehicle(vehicle_id)
        odometer = await asyncio.to_thread(vehicle.odometer)
        return _namedtuple_to_dict(odometer)

    async def get_fuel_level(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get fuel level (for non-electric vehicles).

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Fuel level information.
        """
        _LOGGER.debug("API Call: get_fuel_level | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.fuel")
        vehicle = self._get_vehicle(vehicle_id)
        fuel = await asyncio.to_thread(vehicle.fuel)
        return _namedtuple_to_dict(fuel)

    async def get_lock_status(self, vehicle_id: str) -> Dict[str, Any]:
        """Get lock status of doors and windows.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Lock status information for doors, windows, etc.
        """
        _LOGGER.debug("API Call: get_lock_status | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.lock_status")
        vehicle = self._get_vehicle(vehicle_id)
        security = await asyncio.to_thread(vehicle.lock_status)
        return _namedtuple_to_dict(security)

    async def get_tire_pressure(self, vehicle_id: str) -> Dict[str, Any]:
        """Get tire pressure for all tires.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Tire pressure information for all tires.
        """
        _LOGGER.debug("API Call: get_tire_pressure | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.tires")
        vehicle = self._get_vehicle(vehicle_id)
        tires = await asyncio.to_thread(vehicle.tires)
        return _namedtuple_to_dict(tires)

    async def get_engine_oil(self, vehicle_id: str) -> Dict[str, Any]:
        """Get engine oil life information.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Engine oil life percentage and status.
        """
        _LOGGER.debug("API Call: get_engine_oil | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.engine_oil")
        vehicle = self._get_vehicle(vehicle_id)
        oil = await asyncio.to_thread(vehicle.engine_oil)
        return _namedtuple_to_dict(oil)

    async def lock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Lock the vehicle doors.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        _LOGGER.debug("API Call: lock_doors | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.lock")
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.lock)
        _LOGGER.debug("Lock doors command sent for vehicle %s", vehicle_id)
        return _namedtuple_to_dict(result)

    async def unlock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Unlock the vehicle doors.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        _LOGGER.debug("API Call: unlock_doors | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.unlock")
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.unlock)
        _LOGGER.debug("Unlock doors command sent for vehicle %s", vehicle_id)
        return _namedtuple_to_dict(result)

    async def start_charge(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Start charging the vehicle.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        _LOGGER.debug("API Call: start_charge | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.start_charge")
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.start_charge)
        _LOGGER.debug("Start charge command sent for vehicle %s", vehicle_id)
        return _namedtuple_to_dict(result)

    async def stop_charge(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Stop charging the vehicle.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        _LOGGER.debug("API Call: stop_charge | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.stop_charge")
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.stop_charge)
        _LOGGER.debug("Stop charge command sent for vehicle %s", vehicle_id)
        return _namedtuple_to_dict(result)

    async def start_climate(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Start the vehicle's climate control system.

        Uses direct API call since Python SDK doesn't expose this endpoint.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        _LOGGER.debug("API Call: start_climate | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        url = f"{self._api_base_url}/vehicles/{vehicle_id}/climate"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.debug("HTTP Method: POST | URL: %s", url)
        _LOGGER.debug("Request Headers: %s", headers)
        data = {"action": "START"}
        _LOGGER.debug("Request Body: %s", data)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()
                _LOGGER.debug("HTTP Response Status: %d", response.status)
                result = await response.json()
                _LOGGER.debug("Response Body: %s", result)
                _LOGGER.debug("Start climate command sent for vehicle %s", vehicle_id)
                return result

    async def stop_climate(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Stop the vehicle's climate control system.

        Uses direct API call since Python SDK doesn't expose this endpoint.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        _LOGGER.debug("API Call: stop_climate | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        url = f"{self._api_base_url}/vehicles/{vehicle_id}/climate"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.debug("HTTP Method: POST | URL: %s", url)
        _LOGGER.debug("Request Headers: %s", headers)
        data = {"action": "STOP"}
        _LOGGER.debug("Request Body: %s", data)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()
                _LOGGER.debug("HTTP Response Status: %d", response.status)
                result = await response.json()
                _LOGGER.debug("Response Body: %s", result)
                _LOGGER.debug("Stop climate command sent for vehicle %s", vehicle_id)
                return result

    async def get_climate_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get the vehicle's climate control status.

        Uses direct API call since Python SDK doesn't expose this endpoint.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Climate status information.
        """
        _LOGGER.debug("API Call: get_climate_status | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        url = f"{self._api_base_url}/vehicles/{vehicle_id}/climate"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.debug("HTTP Method: GET | URL: %s", url)
        _LOGGER.debug("Request Headers: %s", headers)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                _LOGGER.debug("HTTP Response Status: %d", response.status)
                result = await response.json()
                _LOGGER.debug("Response Body: %s", result)
                return result

    async def disconnect(self, vehicle_id: str) -> bool:
        """
        Disconnect a vehicle from Smartcar.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            bool: True if successful.
        """
        _LOGGER.debug("API Call: disconnect | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.disconnect")
        vehicle = self._get_vehicle(vehicle_id)
        await asyncio.to_thread(vehicle.disconnect)
        if vehicle_id in self._vehicles_cache:
            del self._vehicles_cache[vehicle_id]
        _LOGGER.debug("Successfully disconnected vehicle %s", vehicle_id)
        return True

    async def get_permissions(self, vehicle_id: str) -> List[str]:
        """
        Get the list of permissions granted for a vehicle.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            List[str]: List of permission strings
                (e.g., 'read_battery', 'control_security').
        """
        _LOGGER.debug("API Call: get_permissions | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        _LOGGER.debug("SDK Method: vehicle.permissions")
        vehicle = self._get_vehicle(vehicle_id)
        response = await asyncio.to_thread(vehicle.permissions)
        permissions_dict = _namedtuple_to_dict(response)
        permissions = permissions_dict.get("permissions", [])
        _LOGGER.debug("Permissions for vehicle %s: %s", vehicle_id, permissions)
        return permissions

    async def get_vehicle_signals(self, vehicle_id: str) -> List[str]:
        """
        Get the list of available signals for a vehicle.

        This queries the Smartcar API to determine which signals/sensors
        are actually supported by the vehicle, enabling dynamic entity creation
        based on actual vehicle capabilities.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            List[str]: List of available signal names (e.g., 'battery.percentRemaining').
        """
        _LOGGER.debug("API Call: get_vehicle_signals | Vehicle ID: %s", vehicle_id)
        _LOGGER.debug("Access token: %s", self.access_token)
        _LOGGER.debug("Refresh token: %s", self.refresh_token)
        # Use v3 API endpoint with vehicle.api.smartcar.com subdomain
        url = "https://vehicle.api.smartcar.com/v3/vehicles/{}/signals".format(vehicle_id)
        headers = {"Authorization": f"Bearer {self.access_token}"}
        _LOGGER.debug("HTTP Method: GET | URL: %s", url)
        _LOGGER.debug("Request Headers: %s", headers)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        _LOGGER.debug("HTTP Response Status: %d", response.status)
                        data = await response.json()
                        _LOGGER.debug("Response Body: %s", data)
                        # v3 API returns signals in format:
                        # {"data": [{"attributes": {"code": "battery-voltage"}, ...}, ...]}
                        if "data" in data and isinstance(data["data"], list):
                            signals = []
                            for signal in data["data"]:
                                if isinstance(signal, dict) and "attributes" in signal:
                                    code = signal["attributes"].get("code")
                                    if code:
                                        signals.append(code)
                            _LOGGER.debug("Available signals for vehicle %s: %s", vehicle_id, signals)
                            return signals
                        return []
                    else:
                        # If signal API not available, return empty (will fall back to permission-based)
                        _LOGGER.debug("HTTP Response Status: %d (Signal API not available)", response.status)
                        try:
                            error_body = await response.text()
                            _LOGGER.debug("Response Error Body: %s", error_body)
                        except Exception:
                            pass
                        _LOGGER.warning(
                            "Unable to get available signals for vehicle %s (Status: %d). "
                            "Will use permission-based signal detection instead. "
                            "This may be expected if signals API is not available in your region.",
                            vehicle_id,
                            response.status
                        )
                        return []
        except Exception as err:
            # If API call fails, return empty list (will fall back to permission-based)
            _LOGGER.debug("Error fetching signals for vehicle %s: %s", vehicle_id, err)
            _LOGGER.warning(
                "Error fetching available signals for vehicle %s. Will use permission-based detection instead.",
                vehicle_id
            )
            return []

    async def get_vehicle_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get comprehensive vehicle status.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Combined vehicle status data.
        """
        status = {}

        try:
            status["info"] = await self.get_vehicle_info(vehicle_id)
        except Exception:
            pass

        try:
            status["location"] = await self.get_vehicle_location(vehicle_id)
        except Exception:
            pass

        try:
            status["battery"] = await self.get_battery_level(vehicle_id)
        except Exception:
            pass

        try:
            status["charge"] = await self.get_charge_status(vehicle_id)
        except Exception:
            pass

        try:
            status["odometer"] = await self.get_odometer(vehicle_id)
        except Exception:
            pass

        try:
            status["lock"] = await self.get_lock_status(vehicle_id)
        except Exception:
            pass

        try:
            status["fuel"] = await self.get_fuel_level(vehicle_id)
        except Exception:
            pass

        try:
            status["tires"] = await self.get_tire_pressure(vehicle_id)
        except Exception:
            pass

        try:
            status["oil"] = await self.get_engine_oil(vehicle_id)
        except Exception:
            pass

        return status
