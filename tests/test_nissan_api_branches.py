import unittest
from unittest.mock import patch, MagicMock
from custom_components.nissan_na.nissan_api import NissanNAApiClient, Vehicle

MOCK_TOKEN_RESPONSE = {
    "access_token": "mock_access_token",
    "refresh_token": "mock_refresh_token",
}
MOCK_VEHICLE_LIST = {
    "vehicles": [
        {"vin": "VIN123", "model": "Pathfinder", "year": 2022, "nickname": "My Nissan"}
    ]
}
MOCK_VEHICLE_STATUS = {
    "batteryLevel": 80,
    "chargingStatus": "Not Charging",
    "plugStatus": "Unplugged",
    "odometer": 12345,
    "range": 250,
    "tirePressure": 35,
    "doorStatus": "Closed",
    "windowStatus": "Closed",
    "lastUpdate": "2026-01-02T12:00:00Z",
    "climateStatus": "Off",
    "location": {"lat": 40.0, "lon": -75.0},
}


class TestNissanNAApiClientBranches(unittest.TestCase):
    def setUp(self):
        self.client = NissanNAApiClient("user", "pass")
        self.client.access_token = "mock_access_token"

    @patch("requests.Session.post")
    def test_authenticate_failure(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=401,
            raise_for_status=MagicMock(side_effect=Exception("401 Unauthorized")),
        )
        with self.assertRaises(Exception):
            self.client.authenticate()

    @patch("requests.Session.get")
    def test_get_vehicle_list_empty(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"vehicles": []}
        )
        vehicles = self.client.get_vehicle_list()
        self.assertEqual(vehicles, [])

    @patch("requests.Session.get")
    def test_get_vehicle_status_missing_fields(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {})
        status = self.client.get_vehicle_status("VIN123")
        self.assertEqual(status, {})

    @patch("requests.Session.post")
    def test_lock_doors_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=500,
            raise_for_status=MagicMock(side_effect=Exception("500 Error")),
        )
        with self.assertRaises(Exception):
            self.client.lock_doors("VIN123")

    @patch("requests.Session.post")
    def test_unlock_doors_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=500,
            raise_for_status=MagicMock(side_effect=Exception("500 Error")),
        )
        with self.assertRaises(Exception):
            self.client.unlock_doors("VIN123")

    @patch("requests.Session.post")
    def test_start_engine_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=500,
            raise_for_status=MagicMock(side_effect=Exception("500 Error")),
        )
        with self.assertRaises(Exception):
            self.client.start_engine("VIN123")

    @patch("requests.Session.post")
    def test_stop_engine_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=500,
            raise_for_status=MagicMock(side_effect=Exception("500 Error")),
        )
        with self.assertRaises(Exception):
            self.client.stop_engine("VIN123")

    @patch("requests.Session.post")
    def test_find_vehicle_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=500,
            raise_for_status=MagicMock(side_effect=Exception("500 Error")),
        )
        with self.assertRaises(Exception):
            self.client.find_vehicle("VIN123")

    @patch("requests.Session.post")
    def test_refresh_vehicle_status_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=500,
            raise_for_status=MagicMock(side_effect=Exception("500 Error")),
        )
        with self.assertRaises(Exception):
            self.client.refresh_vehicle_status("VIN123")


if __name__ == "__main__":
    unittest.main()
