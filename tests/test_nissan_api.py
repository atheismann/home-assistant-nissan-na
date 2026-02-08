import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "custom_components/nissan_na")

import nissan_api  # noqa: E402

SmartcarApiClient = nissan_api.SmartcarApiClient
Vehicle = nissan_api.Vehicle

MOCK_AUTH_URL = (
    "https://connect.smartcar.com/oauth/authorize"
    "?response_type=code&client_id=test_client"
)

MOCK_TOKEN_RESPONSE = {
    "access_token": "mock_access_token",
    "refresh_token": "mock_refresh_token",
    "expires_in": 7200,
    "token_type": "Bearer",
}

MOCK_VEHICLE_IDS = {"vehicles": ["vehicle-id-123", "vehicle-id-456"]}

MOCK_VEHICLE_INFO = {
    "id": "vehicle-id-123",
    "make": "NISSAN",
    "model": "LEAF",
    "year": 2023,
    "vin": "1N4AZ1CP8JC123456",
}

MOCK_BATTERY_RESPONSE = {
    "percentRemaining": 0.8,
    "range": 161.5,
}

MOCK_CHARGE_RESPONSE = {
    "isPluggedIn": True,
    "state": "CHARGING",
}

MOCK_LOCATION_RESPONSE = {
    "latitude": 37.4292,
    "longitude": -122.1381,
}

MOCK_ODOMETER_RESPONSE = {
    "distance": 123456.78,
}

MOCK_BATTERY_CAPACITY_RESPONSE = {
    "capacity": 62.0,
}

MOCK_FUEL_RESPONSE = {
    "percentRemaining": 0.5,
    "range": 320.5,
}


class TestSmartcarApiClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    def test_init(self):
        """Test client initialization."""
        self.assertEqual(self.client.client_id, "test_client_id")
        self.assertEqual(self.client.client_secret, "test_client_secret")
        self.assertEqual(self.client.redirect_uri, "https://example.com/callback")
        self.assertIsNone(self.client.access_token)
        self.assertIsNone(self.client.refresh_token)

    @patch("smartcar.AuthClient")
    def test_get_auth_url(self, mock_auth_client):
        """Test OAuth authorization URL generation."""
        mock_client_instance = MagicMock()
        mock_client_instance.get_auth_url.return_value = MOCK_AUTH_URL
        mock_auth_client.return_value = mock_client_instance

        auth_url = self.client.get_auth_url(state="test_state")

        self.assertEqual(auth_url, MOCK_AUTH_URL)
        # Check that scope and options are passed to get_auth_url (v6 API)
        call_args = mock_client_instance.get_auth_url.call_args
        self.assertIn("scope", call_args.kwargs)
        self.assertIn("options", call_args.kwargs)
        self.assertEqual(call_args.kwargs["options"]["state"], "test_state")

    @patch("smartcar.AuthClient")
    async def test_authenticate(self, mock_auth_client):
        """Test OAuth code exchange for tokens."""
        mock_client_instance = MagicMock()
        # Mock v6 Access NamedTuple
        mock_access = MagicMock()
        mock_access.access_token = "mock_access_token"
        mock_access.refresh_token = "mock_refresh_token"
        mock_access.expires_in = 7200
        mock_access.token_type = "Bearer"
        mock_access.expiration = None
        mock_access.refresh_expiration = None
        mock_client_instance.exchange_code.return_value = mock_access
        mock_auth_client.return_value = mock_client_instance

        response = await self.client.authenticate("test_auth_code")

        self.assertEqual(response["access_token"], "mock_access_token")
        self.assertEqual(response["refresh_token"], "mock_refresh_token")
        self.assertEqual(self.client.access_token, "mock_access_token")
        self.assertEqual(self.client.refresh_token, "mock_refresh_token")

    @patch("smartcar.AuthClient")
    async def test_refresh_access_token(self, mock_auth_client):
        """Test token refresh."""
        self.client.refresh_token = "old_refresh_token"
        mock_client_instance = MagicMock()
        # Mock v6 Access NamedTuple
        mock_access = MagicMock()
        mock_access.access_token = "mock_access_token"
        mock_access.refresh_token = "mock_refresh_token"
        mock_access.expires_in = 7200
        mock_access.token_type = "Bearer"
        mock_access.expiration = None
        mock_access.refresh_expiration = None
        mock_client_instance.exchange_refresh_token.return_value = mock_access
        mock_auth_client.return_value = mock_client_instance

        response = await self.client.refresh_access_token()

        self.assertEqual(response["access_token"], "mock_access_token")
        self.assertEqual(self.client.access_token, "mock_access_token")

    @patch("smartcar.get_vehicles")
    @patch("smartcar.Vehicle")
    async def test_get_vehicle_list(self, mock_vehicle_class, mock_get_vehicles):
        """Test retrieving vehicle list."""
        self.client.access_token = "mock_access_token"
        # Mock v6 Vehicles NamedTuple
        mock_vehicles_response = MagicMock()
        mock_vehicles_response.vehicles = ["vehicle-id-123", "vehicle-id-456"]
        mock_get_vehicles.return_value = mock_vehicles_response

        mock_vehicle_instance = MagicMock()
        # Mock v6 API: attributes() and vin() instead of info()
        mock_attrs = MagicMock()
        mock_attrs._asdict.return_value = {
            "id": "vehicle-id-123",
            "make": "NISSAN",
            "model": "LEAF",
            "year": "2023",
            "meta": {},
        }
        mock_vin = MagicMock()
        mock_vin._asdict.return_value = {"vin": "1N4AZ1CP8JC123456", "meta": {}}
        mock_vehicle_instance.attributes.return_value = mock_attrs
        mock_vehicle_instance.vin.return_value = mock_vin
        mock_vehicle_class.return_value = mock_vehicle_instance

        vehicles = await self.client.get_vehicle_list()

        self.assertEqual(len(vehicles), 2)
        self.assertEqual(vehicles[0].id, "vehicle-id-123")
        self.assertEqual(vehicles[0].vin, "1N4AZ1CP8JC123456")

    @patch("smartcar.Vehicle")
    async def test_get_battery_level(self, mock_vehicle_class):
        """Test getting battery level."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.battery.return_value = MOCK_BATTERY_RESPONSE
        mock_vehicle_class.return_value = mock_vehicle

        battery = await self.client.get_battery_level("vehicle-id-123")

        self.assertEqual(battery, MOCK_BATTERY_RESPONSE)

    @patch("smartcar.Vehicle")
    async def test_get_charge_status(self, mock_vehicle_class):
        """Test getting charge status."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.charge.return_value = MOCK_CHARGE_RESPONSE
        mock_vehicle_class.return_value = mock_vehicle

        charge = await self.client.get_charge_status("vehicle-id-123")

        self.assertEqual(charge, MOCK_CHARGE_RESPONSE)

    @patch("smartcar.Vehicle")
    async def test_lock_unlock_doors(self, mock_vehicle_class):
        """Test lock and unlock operations."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.lock.return_value = {"status": "success"}
        mock_vehicle.unlock.return_value = {"status": "success"}
        mock_vehicle_class.return_value = mock_vehicle

        lock_result = await self.client.lock_doors("vehicle-id-123")
        unlock_result = await self.client.unlock_doors("vehicle-id-123")

        self.assertEqual(lock_result, {"status": "success"})
        self.assertEqual(unlock_result, {"status": "success"})

    @patch("smartcar.Vehicle")
    async def test_start_stop_charge(self, mock_vehicle_class):
        """Test charge control operations."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.start_charge.return_value = {"status": "success"}
        mock_vehicle.stop_charge.return_value = {"status": "success"}
        mock_vehicle_class.return_value = mock_vehicle

        start_result = await self.client.start_charge("vehicle-id-123")
        stop_result = await self.client.stop_charge("vehicle-id-123")

        self.assertEqual(start_result, {"status": "success"})
        self.assertEqual(stop_result, {"status": "success"})

    @patch("smartcar.Vehicle")
    async def test_get_vehicle_location(self, mock_vehicle_class):
        """Test getting vehicle location."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.location.return_value = MOCK_LOCATION_RESPONSE
        mock_vehicle_class.return_value = mock_vehicle

        location = await self.client.get_vehicle_location("vehicle-id-123")

        self.assertEqual(location, MOCK_LOCATION_RESPONSE)

    @patch("smartcar.Vehicle")
    async def test_get_odometer(self, mock_vehicle_class):
        """Test getting odometer reading."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.odometer.return_value = MOCK_ODOMETER_RESPONSE
        mock_vehicle_class.return_value = mock_vehicle

        odometer = await self.client.get_odometer("vehicle-id-123")

        self.assertEqual(odometer, MOCK_ODOMETER_RESPONSE)

    @patch("smartcar.Vehicle")
    async def test_get_battery_capacity(self, mock_vehicle_class):
        """Test getting battery capacity."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.battery_capacity.return_value = MOCK_BATTERY_CAPACITY_RESPONSE
        mock_vehicle_class.return_value = mock_vehicle

        capacity = await self.client.get_battery_capacity("vehicle-id-123")

        self.assertEqual(capacity, MOCK_BATTERY_CAPACITY_RESPONSE)

    @patch("smartcar.Vehicle")
    async def test_get_fuel_level(self, mock_vehicle_class):
        """Test getting fuel level."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_vehicle.fuel.return_value = MOCK_FUEL_RESPONSE
        mock_vehicle_class.return_value = mock_vehicle

        fuel = await self.client.get_fuel_level("vehicle-id-123")

        self.assertEqual(fuel, MOCK_FUEL_RESPONSE)

    @patch("smartcar.Vehicle")
    async def test_get_vehicle_info(self, mock_vehicle_class):
        """Test getting vehicle info."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        # Mock v6 API: attributes() and vin() instead of info()
        mock_attrs = MagicMock()
        mock_attrs._asdict.return_value = {
            "id": "vehicle-id-123",
            "make": "NISSAN",
            "model": "LEAF",
            "year": "2023",
            "meta": {},
        }
        mock_vin = MagicMock()
        mock_vin._asdict.return_value = {"vin": "1N4AZ1CP8JC123456", "meta": {}}
        mock_vehicle.attributes.return_value = mock_attrs
        mock_vehicle.vin.return_value = mock_vin
        mock_vehicle_class.return_value = mock_vehicle

        info = await self.client.get_vehicle_info("vehicle-id-123")

        self.assertEqual(info, MOCK_VEHICLE_INFO)

    @patch("smartcar.Vehicle")
    async def test_get_vehicle_status(self, mock_vehicle_class):
        """Test getting comprehensive vehicle status."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        # Mock v6 API: attributes() and vin() instead of info()
        mock_attrs = MagicMock()
        mock_attrs._asdict.return_value = {
            "id": "vehicle-id-123",
            "make": "NISSAN",
            "model": "LEAF",
            "year": "2023",
            "meta": {},
        }
        mock_vin = MagicMock()
        mock_vin._asdict.return_value = {"vin": "1N4AZ1CP8JC123456", "meta": {}}
        mock_vehicle.attributes.return_value = mock_attrs
        mock_vehicle.vin.return_value = mock_vin
        mock_vehicle.location.return_value = MOCK_LOCATION_RESPONSE
        mock_vehicle.battery.return_value = MOCK_BATTERY_RESPONSE
        mock_vehicle.charge.return_value = MOCK_CHARGE_RESPONSE
        mock_vehicle.odometer.return_value = MOCK_ODOMETER_RESPONSE
        mock_vehicle_class.return_value = mock_vehicle

        status = await self.client.get_vehicle_status("vehicle-id-123")

        self.assertIn("info", status)
        self.assertIn("location", status)
        self.assertIn("battery", status)
        self.assertIn("charge", status)
        self.assertIn("odometer", status)
        self.assertEqual(status["info"], MOCK_VEHICLE_INFO)
        self.assertEqual(status["location"], MOCK_LOCATION_RESPONSE)

    @patch("smartcar.Vehicle")
    async def test_get_permissions(self, mock_vehicle_class):
        """Test getting vehicle permissions."""
        self.client.access_token = "mock_access_token"
        mock_vehicle = MagicMock()
        mock_permissions = MagicMock()
        mock_permissions._asdict.return_value = {
            "permissions": [
                "read_vehicle_info",
                "read_location",
                "read_odometer",
                "control_security",
                "read_battery",
                "read_charge",
            ],
            "meta": {},
        }
        mock_vehicle.permissions.return_value = mock_permissions
        mock_vehicle_class.return_value = mock_vehicle

        permissions = await self.client.get_permissions("vehicle-id-123")

        self.assertIsInstance(permissions, list)
        self.assertIn("read_vehicle_info", permissions)
        self.assertIn("control_security", permissions)


if __name__ == "__main__":
    unittest.main()
