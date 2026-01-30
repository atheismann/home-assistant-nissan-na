"""
Smartcar API client implementation for Nissan vehicles.

This module provides the SmartcarApiClient class for interacting with
Nissan vehicles through the Smartcar API. It supports OAuth authentication,
vehicle data retrieval, and remote actions such as locking/unlocking doors,
starting/stopping climate control, location tracking, and more.

Smartcar API documentation: https://smartcar.com/docs/
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

import smartcar
from pydantic import BaseModel


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
    ):
        """
        Initialize the SmartcarApiClient.

        Args:
            client_id: Smartcar application client ID.
            client_secret: Smartcar application client secret.
            redirect_uri: OAuth redirect URI configured in Smartcar dashboard.
            access_token: Existing access token (if available).
            refresh_token: Existing refresh token for token renewal.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
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
            scope=[
                "required:read_vehicle_info",
                "required:read_location",
                "required:read_odometer",
                "required:control_security",
                "read_battery",
                "read_charge",
                "control_charge",
                "read_fuel",
            ],
            test_mode=False,
        )
        return client.get_auth_url(state=state)

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
        response = client.exchange_code(code)
        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]

        return response

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

        response = client.exchange_refresh_token(self.refresh_token)
        self.access_token = response["access_token"]
        self.refresh_token = response.get("refresh_token", self.refresh_token)

        return response

    async def get_vehicle_list(self) -> List[Vehicle]:
        """
        Retrieve a list of vehicles linked to the Smartcar account.

        Returns:
            List[Vehicle]: List of Vehicle objects.
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")

        # Get vehicle IDs
        response = smartcar.get_vehicles(self.access_token)
        vehicle_ids = response.vehicles

        vehicles = []
        for vehicle_id in vehicle_ids:
            vehicle = smartcar.Vehicle(vehicle_id, self.access_token)
            self._vehicles_cache[vehicle_id] = vehicle

            # Get vehicle info
            info = vehicle.info()
            vehicles.append(
                Vehicle(
                    id=vehicle_id,
                    vin=info.get("vin", ""),
                    make=info.get("make"),
                    model=info.get("model"),
                    year=info.get("year"),
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
        return vehicle.info()

    async def get_vehicle_location(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get vehicle location coordinates.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Location data with latitude and longitude.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.location()

    async def get_battery_level(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get battery charge level (for electric vehicles).

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Battery level percentage.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.battery()

    async def get_battery_capacity(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get battery capacity information.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Battery capacity in kWh.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.battery_capacity()

    async def get_charge_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get charging status (plugged in, charging, etc).

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Charging status information.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.charge()

    async def get_odometer(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get odometer reading.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Odometer distance.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.odometer()

    async def get_fuel_level(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get fuel level (for non-electric vehicles).

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: Fuel level information.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.fuel()

    async def lock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Lock the vehicle doors.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.lock()

    async def unlock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Unlock the vehicle doors.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.unlock()

    async def start_charge(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Start charging the vehicle.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.start_charge()

    async def stop_charge(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Stop charging the vehicle.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            dict: API response with action status.
        """
        vehicle = self._get_vehicle(vehicle_id)
        return vehicle.stop_charge()

    async def disconnect(self, vehicle_id: str) -> bool:
        """
        Disconnect a vehicle from Smartcar.

        Args:
            vehicle_id: Smartcar vehicle ID.

        Returns:
            bool: True if successful.
        """
        vehicle = self._get_vehicle(vehicle_id)
        vehicle.disconnect()
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
