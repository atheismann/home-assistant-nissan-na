"""
Smartcar API client implementation for Nissan vehicles.

This module provides the SmartcarApiClient class for interacting with
Nissan vehicles through the Smartcar API. It supports OAuth authentication,
vehicle data retrieval, and remote actions such as locking/unlocking doors,
starting/stopping climate control, location tracking, and more.

Smartcar API documentation: https://smartcar.com/docs/
"""

import asyncio
from typing import Any, Dict, List, Optional

import smartcar
from pydantic import BaseModel


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
        lock_doors: Lock the vehicle doors.
        unlock_doors: Unlock the vehicle doors.
        start_charge: Start charging the vehicle.
        stop_charge: Stop charging the vehicle.
        disconnect: Disconnect a vehicle from Smartcar.
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

        # Get vehicle IDs - v6 returns a Vehicles NamedTuple
        response = await asyncio.to_thread(smartcar.get_vehicles, self.access_token)
        vehicle_ids = response.vehicles

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
        vehicle = self._get_vehicle(vehicle_id)
        fuel = await asyncio.to_thread(vehicle.fuel)
        return _namedtuple_to_dict(fuel)

    async def lock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Lock the vehicle doors.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.lock)
        return _namedtuple_to_dict(result)

    async def unlock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Unlock the vehicle doors.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.unlock)
        return _namedtuple_to_dict(result)

    async def start_charge(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Start charging the vehicle.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.start_charge)
        return _namedtuple_to_dict(result)

    async def stop_charge(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Stop charging the vehicle.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        result = await asyncio.to_thread(vehicle.stop_charge)
        return _namedtuple_to_dict(result)

    async def disconnect(self, vehicle_id: str) -> bool:
        """
        Disconnect a vehicle from Smartcar.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            bool: True if successful.
        """
        vehicle = self._get_vehicle(vehicle_id)
        await asyncio.to_thread(vehicle.disconnect)
        if vehicle_id in self._vehicles_cache:
            del self._vehicles_cache[vehicle_id]
        return True

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

        return status
