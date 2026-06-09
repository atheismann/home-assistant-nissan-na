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
        self._vehicle_model_cache: Dict[str, Any] = {}  # vehicle_id -> Vehicle model
        self._vehicle_signals_cache: Dict[str, List[str]] = {}  # vehicle_id -> capability codes
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

        # Clear vehicle caches since tokens have changed
        self._vehicles_cache.clear()
        self._vehicle_signals_cache.clear()

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

            v = Vehicle(
                id=vehicle_id,
                vin=vin_dict.get("vin", ""),
                make=attrs_dict.get("make"),
                model=attrs_dict.get("model"),
                year=int(attrs_dict["year"]) if attrs_dict.get("year") else None,
            )
            vehicles.append(v)
            self._vehicle_model_cache[vehicle_id] = v

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

    async def get_compatibility_signals(self, make: str, model: str, year: int) -> List[str]:
        """
        Get supported signal capability codes for a vehicle model from the Smartcar
        compatibility API.  This is a public catalog endpoint — no auth token needed.

        Args:
            make: Vehicle make (e.g. 'NISSAN').
            model: Vehicle model (e.g. 'Pathfinder').
            year: Model year (e.g. 2025).

        Returns:
            List[str]: Capability codes for signals supported by this model/year,
                       e.g. ['odometer-traveleddistance', 'internalcombustionengine-fuellevel'].
        """
        url = "https://compatibility.api.smartcar.com/v3/compatible-vehicles"
        params = {"filter[make]": make.upper(), "filter[region]": "US"}
        _LOGGER.debug(
            "Fetching compatibility signals for %s %s %d", make, model, year
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        _LOGGER.debug(
                            "Compatibility API returned %d for %s", response.status, make
                        )
                        return []
                    data = await response.json()
        except Exception as err:
            _LOGGER.debug("Error calling compatibility API: %s", err)
            return []

        signals: List[str] = []
        for entry in data.get("data", []):
            attrs = entry.get("attributes", {})
            if attrs.get("model", "").lower() != model.lower():
                continue
            years = attrs.get("years", {})
            if not (years.get("start", 0) <= year <= years.get("end", 9999)):
                continue
            for cap in attrs.get("capabilities", []):
                if cap.get("type") == "signal":
                    code = cap.get("capability")
                    if code and code not in signals:
                        signals.append(code)
            if signals:
                _LOGGER.info(
                    "Compatibility API: %d signals for %s %s %d",
                    len(signals),
                    make,
                    model,
                    year,
                )
                return signals

        _LOGGER.debug("No compatibility match for %s %s %d", make, model, year)
        return []

    async def get_vehicle_signals(self, vehicle_id: str, vehicle: Any = None) -> List[str]:
        """
        Get the list of available signal capability codes for a vehicle.

        First tries the v3 per-vehicle signals endpoint.  If that returns an error
        (common outside certain regions), falls back to the public compatibility API
        using the vehicle's make/model/year.

        Results are cached on the client instance so repeated calls are free.

        Args:
            vehicle_id: Smartcar vehicle ID.
            vehicle: Optional Vehicle model object (used for compatibility API fallback).

        Returns:
            List[str]: Capability codes, e.g. ['odometer-traveleddistance', ...].
        """
        if vehicle_id in self._vehicle_signals_cache:
            return self._vehicle_signals_cache[vehicle_id]

        _LOGGER.debug("Fetching signals for vehicle %s", vehicle_id)

        # Try v3 per-vehicle signals endpoint first
        url = f"https://vehicle.api.smartcar.com/v3/vehicles/{vehicle_id}/signals"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "data" in data and isinstance(data["data"], list):
                            signals = [
                                sig["attributes"]["code"]
                                for sig in data["data"]
                                if isinstance(sig, dict)
                                and "attributes" in sig
                                and "code" in sig["attributes"]
                            ]
                            if signals:
                                _LOGGER.info(
                                    "v3 signals endpoint: %d signals for vehicle %s",
                                    len(signals),
                                    vehicle_id,
                                )
                                self._vehicle_signals_cache[vehicle_id] = signals
                                return signals
                    else:
                        _LOGGER.debug(
                            "v3 signals endpoint returned %d for vehicle %s — "
                            "falling back to compatibility API",
                            response.status,
                            vehicle_id,
                        )
        except Exception as err:
            _LOGGER.debug("v3 signals endpoint error for %s: %s", vehicle_id, err)

        # Fall back to compatibility API
        v = vehicle or self._vehicle_model_cache.get(vehicle_id)
        if v and v.make and v.model and v.year:
            signals = await self.get_compatibility_signals(v.make, v.model, v.year)
            if signals:
                self._vehicle_signals_cache[vehicle_id] = signals
                return signals

        _LOGGER.warning(
            "Could not determine signals for vehicle %s — no sensors will be created",
            vehicle_id,
        )
        self._vehicle_signals_cache[vehicle_id] = []
        return []

    @staticmethod
    def _extract_signal_body(sdk_result: dict) -> dict:
        """Extract the signal data body from a v3 SDK get_signal() result."""
        body = sdk_result.get("body", {})
        if not isinstance(body, dict):
            return {}
        # JSON:API format: {"data": {"attributes": {"body": {...}}}}
        data = body.get("data")
        if isinstance(data, dict):
            attrs = data.get("attributes", {})
            if isinstance(attrs, dict) and "body" in attrs:
                return attrs["body"] or {}
        # Flat format (some endpoints): {"attributes": {"body": {...}}}
        attrs = body.get("attributes", {})
        if isinstance(attrs, dict) and "body" in attrs:
            return attrs["body"] or {}
        return body

    def _apply_signal_to_status(self, status: dict, signal_code: str, body: dict) -> None:
        """Map a v3 signal response body into the shared status dict."""
        if not body:
            return

        code = signal_code.lower()
        _LOGGER.debug("Applying signal %s body: %s", code, body)

        if code == "odometer-traveleddistance":
            # Body: {"value": 12845.78, "unit": "km"}
            status.setdefault("odometer", {})["distance"] = (
                body.get("traveledDistance") or body.get("distance") or body.get("value")
            )

        elif code == "internalcombustionengine-fuellevel":
            # Body: {"value": 66.74, "unit": "percent"}
            status.setdefault("fuel", {})["percentRemaining"] = (
                body.get("fuelLevel") or body.get("percentRemaining") or body.get("value")
            )

        elif code == "internalcombustionengine-amountremaining":
            # Body: {"value": 46.74, "unit": "liters"}
            status.setdefault("fuel", {})["amountRemaining"] = (
                body.get("amountRemaining") or body.get("value")
            )

        elif code == "internalcombustionengine-range":
            # Body: {"value": 439.35, "unit": "km"}
            status.setdefault("fuel", {})["range"] = (
                body.get("range") or body.get("value")
            )

        elif code == "location-preciselocation":
            status["location"] = {
                "latitude": body.get("latitude"),
                "longitude": body.get("longitude"),
            }

        elif code == "wheel-tires":
            # Body: {"values": [{"row": 0, "column": 0, "tirePressure": 255.1}, ...], "unit": "kPa"}
            # row=0 → front, row=1 → back; column=0 → left, column=1 → right
            _ROW_COL_TO_POS = {
                (0, 0): "frontLeft",
                (0, 1): "frontRight",
                (1, 0): "backLeft",
                (1, 1): "backRight",
            }
            tires: dict = {}
            for entry in body.get("values", []):
                if not isinstance(entry, dict):
                    continue
                row = entry.get("row")
                col = entry.get("column")
                pressure = entry.get("tirePressure") or entry.get("pressure")
                pos = _ROW_COL_TO_POS.get((row, col)) if row is not None and col is not None else None
                if pos and pressure is not None:
                    tires[pos] = {"pressure": pressure}
            if tires:
                status["tires"] = tires

        elif code == "diagnostics-tirepressure":
            # This signal is a warning indicator ("OK" / "LOW"), not per-tire pressure values.
            # Store it as a diagnostic flag; the wheel-tires signal has the actual pressure.
            status.setdefault("diagnostics", {})["tirePressureWarning"] = body.get("status")

        elif code == "closure-islocked":
            status.setdefault("security", {})["isLocked"] = body.get("isLocked")

        elif code == "closure-doors":
            status.setdefault("security", {})["doors"] = body.get("doors", body)

        elif code == "closure-reartrunk":
            status.setdefault("security", {})["rearTrunk"] = body

        elif code == "closure-fronttrunk":
            status.setdefault("security", {})["frontTrunk"] = body

        elif code == "closure-enginecover":
            status.setdefault("security", {})["engineCover"] = body

        elif code == "diagnostics-mil":
            status.setdefault("diagnostics", {})["mil"] = (
                body.get("isActive") or body.get("mil") or body.get("value")
            )

        elif code == "diagnostics-abs":
            status.setdefault("diagnostics", {})["abs"] = (
                body.get("isActive") or body.get("abs") or body.get("value")
            )

        elif code == "diagnostics-brakefluid":
            status.setdefault("diagnostics", {})["brakeFluid"] = (
                body.get("isLow") or body.get("brakeFluid") or body.get("value")
            )

        elif code == "diagnostics-airbag":
            status.setdefault("diagnostics", {})["airbag"] = (
                body.get("isDeployed") or body.get("airbag") or body.get("value")
            )

        elif code == "diagnostics-oilpressure":
            status.setdefault("diagnostics", {})["oilPressure"] = (
                body.get("isLow") or body.get("oilPressure") or body.get("value")
            )

        elif code == "tractionbattery-stateofcharge":
            status.setdefault("battery", {})["percentRemaining"] = (
                body.get("stateOfCharge") or body.get("percentRemaining")
            )

        elif code == "tractionbattery-range":
            status.setdefault("battery", {})["range"] = body.get("range")

        elif code == "tractionbattery-nominalcapacity":
            status.setdefault("battery", {})["capacityKwh"] = (
                body.get("capacity") or body.get("nominalCapacity")
            )

        elif code == "charge-ischarging":
            status.setdefault("charge", {})["isCharging"] = (
                body.get("isCharging") or body.get("value")
            )

        elif code == "charge-ischargingcableconnected":
            status.setdefault("charge", {})["isPluggedIn"] = (
                body.get("isChargingCableConnected") or body.get("value")
            )

        elif code == "charge-timetocomplete":
            status.setdefault("charge", {})["timeToComplete"] = (
                body.get("timeToComplete") or body.get("value")
            )

        elif code == "charge-detailedchargingstatus":
            status.setdefault("charge", {})["state"] = (
                body.get("detailedChargingStatus") or body.get("status") or body.get("value")
            )

        elif code == "charge-chargetimers":
            status.setdefault("charge", {})["chargeTimers"] = body

        elif code == "charge-voltage":
            status.setdefault("charge", {})["voltage"] = (
                body.get("voltage") or body.get("value")
            )

        elif code == "charge-wattage":
            status.setdefault("charge", {})["wattage"] = (
                body.get("wattage") or body.get("value")
            )

        elif code == "hvac-cabintargettemperature":
            status.setdefault("hvac", {})["targetTemperature"] = (
                body.get("cabinTargetTemperature") or body.get("value")
            )

        elif code == "hvac-iscabinhvacactive":
            status.setdefault("hvac", {})["isActive"] = (
                body.get("isCabinHVACActive") or body.get("value")
            )

        else:
            _LOGGER.debug("No status mapping for signal %s — storing raw body", code)
            status[code] = body

    async def get_vehicle_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get comprehensive vehicle status in a single bulk call to the v3 signals endpoint.

        Fetches all signals at once, filters to SUCCESS-only, and extracts the body
        directly from the response — no per-signal SDK calls needed.

        Also refreshes the signals cache as a side effect.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Structured vehicle status keyed by domain (odometer, fuel, tires, …).
        """
        url = f"https://vehicle.api.smartcar.com/v3/vehicles/{vehicle_id}/signals"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        _LOGGER.warning(
                            "Signals endpoint returned %d for vehicle %s — status will be empty",
                            response.status,
                            vehicle_id,
                        )
                        return {}
                    data = await response.json()
        except Exception as err:
            _LOGGER.error("Failed to fetch vehicle status for %s: %s", vehicle_id, err)
            return {}

        signal_list = data.get("data", [])

        # Refresh the signals cache from this response (codes regardless of status)
        all_codes = [
            sig["attributes"]["code"]
            for sig in signal_list
            if isinstance(sig, dict)
            and "attributes" in sig
            and "code" in sig.get("attributes", {})
        ]
        if all_codes:
            self._vehicle_signals_cache[vehicle_id] = all_codes

        status: Dict[str, Any] = {}
        for signal in signal_list:
            attrs = signal.get("attributes", {})
            code = attrs.get("code", "")
            if not code:
                continue
            if attrs.get("status", {}).get("value") != "SUCCESS":
                continue
            body = attrs.get("body")
            if body:
                self._apply_signal_to_status(status, code, body)

        _LOGGER.debug("Vehicle status for %s: %s", vehicle_id, status)
        return status
