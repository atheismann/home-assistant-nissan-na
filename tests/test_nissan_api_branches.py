import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "custom_components/nissan_na")
import nissan_api

SmartcarApiClient = nissan_api.SmartcarApiClient


class TestSmartcarApiClientErrorHandling(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
            access_token="mock_access_token",
            refresh_token="mock_refresh_token",
        )

    async def test_refresh_access_token_no_refresh_token(self):
        """Test refresh fails when no refresh token is available."""
        self.client.refresh_token = None

        with self.assertRaises(ValueError) as context:
            await self.client.refresh_access_token()

        self.assertIn("No refresh token", str(context.exception))

    async def test_get_vehicle_list_not_authenticated(self):
        """Test vehicle list fails when not authenticated."""
        self.client.access_token = None

        with self.assertRaises(ValueError) as context:
            await self.client.get_vehicle_list()

        self.assertIn("Not authenticated", str(context.exception))

    @patch("smartcar.Vehicle")
    async def test_get_vehicle_status_with_errors(self, mock_vehicle_class):
        """Test get_vehicle_status handles partial failures gracefully."""
        mock_vehicle = MagicMock()
        # Mock v6 API failures - both attributes() and vin() must fail
        mock_vehicle.attributes.side_effect = Exception("API Error")
        mock_vehicle.vin.side_effect = Exception("API Error")
        mock_vehicle.location.return_value = {
            "latitude": 37.4292,
            "longitude": -122.1381,
        }
        mock_vehicle.battery.side_effect = Exception("Battery API Error")
        mock_vehicle.charge.return_value = {"state": "CHARGING"}
        mock_vehicle.odometer.side_effect = Exception("Odometer Error")
        mock_vehicle_class.return_value = mock_vehicle

        status = await self.client.get_vehicle_status("vehicle-id-123")

        # Should have location and charge but not info, battery, or odometer
        self.assertIn("location", status)
        self.assertIn("charge", status)
        self.assertNotIn("info", status)
        self.assertNotIn("battery", status)
        self.assertNotIn("odometer", status)

    @patch("smartcar.Vehicle")
    async def test_get_vehicle_status_all_fail(self, mock_vehicle_class):
        """Test get_vehicle_status when all calls fail."""
        mock_vehicle = MagicMock()
        # Mock v6 API failures
        mock_vehicle.attributes.side_effect = Exception("Info Error")
        mock_vehicle.vin.side_effect = Exception("Info Error")
        mock_vehicle.location.side_effect = Exception("Location Error")
        mock_vehicle.battery.side_effect = Exception("Battery Error")
        mock_vehicle.charge.side_effect = Exception("Charge Error")
        mock_vehicle.odometer.side_effect = Exception("Odometer Error")
        mock_vehicle_class.return_value = mock_vehicle

        status = await self.client.get_vehicle_status("vehicle-id-123")

        # Should return empty dict when everything fails
        self.assertEqual(status, {})

    @patch("smartcar.Vehicle")
    async def test_lock_doors_failure(self, mock_vehicle_class):
        """Test lock doors handles API errors."""
        mock_vehicle = MagicMock()
        mock_vehicle.lock.side_effect = Exception("Lock failed")
        mock_vehicle_class.return_value = mock_vehicle

        with self.assertRaises(Exception) as context:
            await self.client.lock_doors("vehicle-id-123")

        self.assertIn("Lock failed", str(context.exception))

    @patch("smartcar.Vehicle")
    async def test_unlock_doors_failure(self, mock_vehicle_class):
        """Test unlock doors handles API errors."""
        mock_vehicle = MagicMock()
        mock_vehicle.unlock.side_effect = Exception("Unlock failed")
        mock_vehicle_class.return_value = mock_vehicle

        with self.assertRaises(Exception) as context:
            await self.client.unlock_doors("vehicle-id-123")

        self.assertIn("Unlock failed", str(context.exception))

    @patch("smartcar.Vehicle")
    async def test_start_charge_failure(self, mock_vehicle_class):
        """Test start charge handles API errors."""
        mock_vehicle = MagicMock()
        mock_vehicle.start_charge.side_effect = Exception("Charge start failed")
        mock_vehicle_class.return_value = mock_vehicle

        with self.assertRaises(Exception) as context:
            await self.client.start_charge("vehicle-id-123")

        self.assertIn("Charge start failed", str(context.exception))

    @patch("smartcar.Vehicle")
    async def test_stop_charge_failure(self, mock_vehicle_class):
        """Test stop charge handles API errors."""
        mock_vehicle = MagicMock()
        mock_vehicle.stop_charge.side_effect = Exception("Charge stop failed")
        mock_vehicle_class.return_value = mock_vehicle

        with self.assertRaises(Exception) as context:
            await self.client.stop_charge("vehicle-id-123")

        self.assertIn("Charge stop failed", str(context.exception))

    @patch("smartcar.Vehicle")
    async def test_disconnect_vehicle(self, mock_vehicle_class):
        """Test disconnecting a vehicle."""
        mock_vehicle = MagicMock()
        mock_vehicle.disconnect.return_value = None
        mock_vehicle_class.return_value = mock_vehicle

        # Add vehicle to cache first
        self.client._vehicles_cache["vehicle-id-123"] = mock_vehicle

        result = await self.client.disconnect("vehicle-id-123")

        self.assertTrue(result)
        self.assertNotIn("vehicle-id-123", self.client._vehicles_cache)
        mock_vehicle.disconnect.assert_called_once()

    @patch("smartcar.Vehicle")
    async def test_disconnect_vehicle_not_in_cache(self, mock_vehicle_class):
        """Test disconnecting a vehicle that is not in cache."""
        mock_vehicle = MagicMock()
        mock_vehicle.disconnect.return_value = None
        mock_vehicle_class.return_value = mock_vehicle

        # Don't add to cache, should still work
        result = await self.client.disconnect("vehicle-id-456")

        self.assertTrue(result)
        mock_vehicle_class.assert_called_once()

    @patch("smartcar.AuthClient")
    async def test_authenticate_failure(self, mock_auth_client):
        """Test authentication failure."""
        mock_client_instance = MagicMock()
        mock_client_instance.exchange_code.side_effect = Exception("Invalid code")
        mock_auth_client.return_value = mock_client_instance

        with self.assertRaises(Exception) as context:
            await self.client.authenticate("invalid_code")

        self.assertIn("Invalid code", str(context.exception))

    @patch("smartcar.get_vehicles")
    async def test_get_vehicle_list_empty(self, mock_get_vehicles):
        """Test handling empty vehicle list."""
        mock_get_vehicles.return_value = {"vehicles": []}

        vehicles = await self.client.get_vehicle_list()

        self.assertEqual(len(vehicles), 0)

    @patch("smartcar.Vehicle")
    async def test_vehicle_caching(self, mock_vehicle_class):
        """Test that vehicle instances are cached."""
        mock_vehicle = MagicMock()
        mock_vehicle_class.return_value = mock_vehicle

        # First call should create vehicle
        vehicle1 = self.client._get_vehicle("vehicle-id-123")
        # Second call should return cached vehicle
        vehicle2 = self.client._get_vehicle("vehicle-id-123")

        self.assertIs(vehicle1, vehicle2)
        # Should only be called once due to caching
        mock_vehicle_class.assert_called_once()


if __name__ == "__main__":
    unittest.main()
