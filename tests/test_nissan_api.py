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


class TestNissanNAApiClient(unittest.TestCase):
    def setUp(self):
        self.client = NissanNAApiClient("user", "pass")

    @patch("requests.Session.post")
    def test_authenticate(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: MOCK_TOKEN_RESPONSE
        )
        token = self.client.authenticate()
        self.assertEqual(token, "mock_access_token")
        self.assertEqual(self.client.refresh_token, "mock_refresh_token")

    @patch("requests.Session.get")
    def test_get_vehicle_list(self, mock_get):
        self.client.access_token = "mock_access_token"
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: MOCK_VEHICLE_LIST
        )
        vehicles = self.client.get_vehicle_list()
        self.assertEqual(len(vehicles), 1)
        self.assertIsInstance(vehicles[0], Vehicle)
        self.assertEqual(vehicles[0].vin, "VIN123")

    @patch("requests.Session.get")
    def test_get_vehicle_status(self, mock_get):
        self.client.access_token = "mock_access_token"
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: MOCK_VEHICLE_STATUS
        )
        status = self.client.get_vehicle_status("VIN123")
        self.assertEqual(status["batteryLevel"], 80)
        self.assertEqual(status["location"]["lat"], 40.0)

    @patch("requests.Session.post")
    def test_lock_unlock_engine_find_refresh(self, mock_post):
        self.client.access_token = "mock_access_token"
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"result": "ok"}
        )
        self.assertEqual(self.client.lock_doors("VIN123")["result"], "ok")
        self.assertEqual(self.client.unlock_doors("VIN123")["result"], "ok")
        self.assertEqual(self.client.start_engine("VIN123")["result"], "ok")
        self.assertEqual(self.client.stop_engine("VIN123")["result"], "ok")
        self.assertEqual(self.client.find_vehicle("VIN123")["result"], "ok")
        self.assertEqual(self.client.refresh_vehicle_status("VIN123")["result"], "ok")


if __name__ == "__main__":
    unittest.main()
