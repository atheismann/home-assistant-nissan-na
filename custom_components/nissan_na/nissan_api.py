"""
Nissan North America API client implementation using requests and pydantic.

This module provides the NissanNAApiClient class for interacting with
the Nissan North America (NNA) API. It supports authentication, vehicle
data retrieval, and remote actions such as locking/unlocking doors,
starting/stopping climate control, and more.
"""

from typing import List, Optional

import requests
from pydantic import BaseModel

NISSAN_BASE_URL = "https://nissan-na-smartphone-b2c-us.azurewebsites.net/"


class Vehicle(BaseModel):
    """Model representing a Nissan vehicle."""

    vin: str
    model: Optional[str]
    year: Optional[int]
    nickname: Optional[str]


class NissanNAApiClient:
    """
    Client for interacting with the Nissan North America API.

    Methods:
        authenticate: Authenticate and obtain an access token.
        get_vehicle_list: Retrieve all vehicles linked to the account.
        get_vehicle_status: Get status for a specific vehicle.
        lock_doors: Lock the vehicle doors.
        unlock_doors: Unlock the vehicle doors.
        start_climate: Start the vehicle's climate control.
        stop_climate: Stop the vehicle's climate control.
        find_vehicle: Activate horn/lights to locate the vehicle.
        refresh_vehicle_status: Request a fresh status update from the vehicle.
    """

    def __init__(self, username: str, password: str):
        """
        Initialize the NissanNAApiClient.

        Args:
            username (str): NissanConnect account username.
            password (str): NissanConnect account password.
        """
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.session = requests.Session()

    def authenticate(self):
        """
        Authenticate with the Nissan NA API and store the access token.

        Returns:
            str: The access token.
        """
        url = NISSAN_BASE_URL + "auth/oauth2/token"
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "scope": "openid profile vehicles offline_access",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
        }
        # NOTE: client_id and client_secret may be required, see reverse-engineered docs
        # headers["Authorization"] = "Basic <base64(client_id:client_secret)>"
        response = self.session.post(url, data=data, headers=headers)
        response.raise_for_status()
        tokens = response.json()
        self.access_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token")
        return self.access_token

    def get_vehicle_list(self) -> List[Vehicle]:
        """
        Retrieve a list of vehicles linked to the account.

        Returns:
            List[Vehicle]: List of Vehicle objects.
        """
        url = NISSAN_BASE_URL + "api/v1/vehicles"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        vehicles = response.json().get("vehicles", [])
        return [Vehicle(**v) for v in vehicles]

    def get_vehicle_status(self, vin):
        """
        Get the status for a specific vehicle.

        Args:
            vin (str): Vehicle Identification Number.

        Returns:
            dict: Vehicle status data.
        """
        url = NISSAN_BASE_URL + f"api/v1/vehicles/{vin}/status"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def lock_doors(self, vin):
        """
        Lock the vehicle doors.

        Args:
            vin (str): Vehicle Identification Number.

        Returns:
            dict: API response.
        """
        url = NISSAN_BASE_URL + f"api/v1/vehicles/{vin}/remote/lock"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.post(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def unlock_doors(self, vin):
        """
        Unlock the vehicle doors.

        Args:
            vin (str): Vehicle Identification Number.

        Returns:
            dict: API response.
        """
        url = NISSAN_BASE_URL + f"api/v1/vehicles/{vin}/remote/unlock"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.post(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def start_engine(self, vin):
        """
        Remotely start the vehicle's engine (uses climate start endpoint).

        Args:
            vin (str): Vehicle Identification Number.

        Returns:
            dict: API response.
        """
        url = NISSAN_BASE_URL + f"api/v1/vehicles/{vin}/remote/climate/start"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.post(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def stop_engine(self, vin):
        """
        Remotely stop the vehicle's engine (uses climate stop endpoint).

        Args:
            vin (str): Vehicle Identification Number.

        Returns:
            dict: API response.
        """
        url = NISSAN_BASE_URL + f"api/v1/vehicles/{vin}/remote/climate/stop"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.post(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def find_vehicle(self, vin):
        """
        Activate horn/lights to help locate the vehicle.

        Args:
            vin (str): Vehicle Identification Number.

        Returns:
            dict: API response.
        """
        url = NISSAN_BASE_URL + f"api/v1/vehicles/{vin}/remote/horn"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.post(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def refresh_vehicle_status(self, vin):
        """
        Request a fresh status update from the vehicle.

        Args:
            vin (str): Vehicle Identification Number.

        Returns:
            dict: API response.
        """
        url = NISSAN_BASE_URL + f"api/v1/vehicles/{vin}/status/refresh"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "NissanConnect/4.5.0 (Android)",
            "Accept": "application/json",
        }
        response = self.session.post(url, headers=headers)
        response.raise_for_status()
        return response.json()
