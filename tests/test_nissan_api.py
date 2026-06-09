"""Unit tests for nissan_api.py - SmartcarApiClient"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from custom_components.nissan_na.nissan_api import (
    SmartcarApiClient,
    Vehicle,
    _namedtuple_to_dict,
)
from collections import namedtuple


class TestNamedTupleToDict:
    """Tests for _namedtuple_to_dict helper function"""
    
    def test_dict_input_returns_same_dict(self):
        """Test that dict input returns the same dict"""
        input_dict = {"key1": "value1", "key2": "value2"}
        result = _namedtuple_to_dict(input_dict)
        assert result == input_dict
    
    def test_namedtuple_to_dict_simple(self):
        """Test converting a simple namedtuple"""
        TestTuple = namedtuple("TestTuple", ["field1", "field2"])
        obj = TestTuple(field1="value1", field2="value2")
        result = _namedtuple_to_dict(obj)
        assert result == {"field1": "value1", "field2": "value2"}
    
    def test_namedtuple_to_dict_nested(self):
        """Test converting nested namedtuples"""
        InnerTuple = namedtuple("InnerTuple", ["inner_field"])
        OuterTuple = namedtuple("OuterTuple", ["outer_field", "nested"])
        
        inner = InnerTuple(inner_field="inner_value")
        outer = OuterTuple(outer_field="outer_value", nested=inner)
        
        result = _namedtuple_to_dict(outer)
        assert result == {
            "outer_field": "outer_value",
            "nested": {"inner_field": "inner_value"}
        }
    
    def test_object_without_asdict(self):
        """Test converting object without _asdict method"""
        # Create a simple object with attributes (not a Mock)
        class SimpleObject:
            field1 = "value1"
            field2 = "value2"
        
        obj = SimpleObject()
        result = _namedtuple_to_dict(obj)
        assert "field1" in result
        assert "field2" in result


class TestVehicleModel:
    """Tests for Vehicle Pydantic model"""
    
    def test_vehicle_model_required_fields(self):
        """Test Vehicle model with required fields only"""
        vehicle = Vehicle(vin="TEST123", id="vehicle_123")
        assert vehicle.vin == "TEST123"
        assert vehicle.id == "vehicle_123"
        assert vehicle.model is None
        assert vehicle.year is None
        assert vehicle.make is None
    
    def test_vehicle_model_all_fields(self):
        """Test Vehicle model with all fields"""
        vehicle = Vehicle(
            vin="TEST123",
            id="vehicle_123",
            model="Leaf",
            year=2024,
            make="Nissan"
        )
        assert vehicle.vin == "TEST123"
        assert vehicle.id == "vehicle_123"
        assert vehicle.model == "Leaf"
        assert vehicle.year == 2024
        assert vehicle.make == "Nissan"


class TestSmartcarApiClientInit:
    """Tests for SmartcarApiClient initialization"""
    
    def test_client_init_minimal(self):
        """Test client initialization with minimal parameters"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_secret"
        assert client.redirect_uri == "https://example.com/callback"
        assert client.access_token is None
        assert client.refresh_token is None
        assert client.test_mode is False
    
    def test_client_init_with_tokens(self):
        """Test client initialization with tokens"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_access_token",
            refresh_token="test_refresh_token"
        )
        assert client.access_token == "test_access_token"
        assert client.refresh_token == "test_refresh_token"
    
    def test_client_init_test_mode(self):
        """Test client initialization in test mode"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            test_mode=True
        )
        assert client.test_mode is True
    
    def test_client_vehicles_cache_initialized(self):
        """Test that vehicles cache is initialized as empty dict"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        assert client._vehicles_cache == {}


class TestGetAuthUrl:
    """Tests for get_auth_url method"""
    
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    def test_get_auth_url_without_state(self, mock_auth_client_class):
        """Test generating auth URL without state parameter"""
        mock_client_instance = Mock()
        mock_client_instance.get_auth_url.return_value = "https://smartcar.com/auth?params"
        mock_auth_client_class.return_value = mock_client_instance
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        url = client.get_auth_url()
        
        assert url == "https://smartcar.com/auth?params"
        mock_auth_client_class.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            mode="live"
        )
    
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    def test_get_auth_url_with_state(self, mock_auth_client_class):
        """Test generating auth URL with state parameter"""
        mock_client_instance = Mock()
        mock_client_instance.get_auth_url.return_value = "https://smartcar.com/auth?state=test123"
        mock_auth_client_class.return_value = mock_client_instance
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        url = client.get_auth_url(state="test123")
        
        assert url == "https://smartcar.com/auth?state=test123"
        # Check that get_auth_url was called with options including state
        call_args = mock_client_instance.get_auth_url.call_args
        assert "options" in call_args.kwargs
        assert "state" in call_args.kwargs["options"]
        assert call_args.kwargs["options"]["state"] == "test123"
    
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    def test_get_auth_url_test_mode(self, mock_auth_client_class):
        """Test generating auth URL in test mode"""
        mock_client_instance = Mock()
        mock_client_instance.get_auth_url.return_value = "https://smartcar.com/test/auth"
        mock_auth_client_class.return_value = mock_client_instance
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            test_mode=True
        )
        
        url = client.get_auth_url()
        
        mock_auth_client_class.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            mode="test"
        )
    
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    def test_get_auth_url_includes_nissan_make_bypass(self, mock_auth_client_class):
        """Test that auth URL includes NISSAN make_bypass option"""
        mock_client_instance = Mock()
        mock_client_instance.get_auth_url.return_value = "https://smartcar.com/auth"
        mock_auth_client_class.return_value = mock_client_instance
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        client.get_auth_url()
        
        call_args = mock_client_instance.get_auth_url.call_args
        assert "options" in call_args.kwargs
        assert "make_bypass" in call_args.kwargs["options"]
        assert call_args.kwargs["options"]["make_bypass"] == "NISSAN"
    
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    def test_get_auth_url_includes_required_scopes(self, mock_auth_client_class):
        """Test that auth URL includes all required scopes"""
        mock_client_instance = Mock()
        mock_client_instance.get_auth_url.return_value = "https://smartcar.com/auth"
        mock_auth_client_class.return_value = mock_client_instance
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        client.get_auth_url()
        
        call_args = mock_client_instance.get_auth_url.call_args
        assert "scope" in call_args.kwargs
        scopes = call_args.kwargs["scope"]
        
        # Check required scopes
        assert "required:read_vehicle_info" in scopes
        assert "required:read_location" in scopes
        assert "required:read_odometer" in scopes
        assert "required:control_security" in scopes
        assert "read_battery" in scopes
        assert "read_charge" in scopes
        assert "control_charge" in scopes
        assert "read_fuel" in scopes


class TestAuthenticate:
    """Tests for authenticate method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    async def test_authenticate_success(self, mock_auth_client_class, mock_to_thread):
        """Test successful authentication"""
        # Create mock response with namedtuple-like structure
        AccessResponse = namedtuple(
            "AccessResponse",
            ["access_token", "refresh_token", "expires_in", "token_type", "expiration", "refresh_expiration"]
        )
        mock_response = AccessResponse(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            expires_in=3600,
            token_type="Bearer",
            expiration="2024-01-01T00:00:00Z",
            refresh_expiration="2024-02-01T00:00:00Z"
        )
        
        mock_client_instance = Mock()
        mock_auth_client_class.return_value = mock_client_instance
        mock_to_thread.return_value = mock_response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        result = await client.authenticate("test_code")
        
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["expires_in"] == 3600
        assert client.access_token == "new_access_token"
        assert client.refresh_token == "new_refresh_token"
        
        # Check that vehicle cache was cleared
        assert client._vehicles_cache == {}
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    async def test_authenticate_clears_cache(self, mock_auth_client_class, mock_to_thread):
        """Test that authenticate clears vehicle cache"""
        AccessResponse = namedtuple(
            "AccessResponse",
            ["access_token", "refresh_token", "expires_in", "token_type", "expiration", "refresh_expiration"]
        )
        mock_response = AccessResponse(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            expires_in=3600,
            token_type="Bearer",
            expiration="2024-01-01T00:00:00Z",
            refresh_expiration="2024-02-01T00:00:00Z"
        )
        
        mock_client_instance = Mock()
        mock_auth_client_class.return_value = mock_client_instance
        mock_to_thread.return_value = mock_response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        # Add something to cache
        client._vehicles_cache["vehicle1"] = Mock()
        assert len(client._vehicles_cache) == 1
        
        await client.authenticate("test_code")
        
        # Cache should be cleared
        assert len(client._vehicles_cache) == 0


class TestGetVehicle:
    """Tests for _get_vehicle internal method"""
    
    def test_get_vehicle_from_cache(self):
        """Test retrieving vehicle from cache"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        # Add mock vehicle to cache
        mock_vehicle = Mock()
        client._vehicles_cache["vehicle_123"] = mock_vehicle
        
        with patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle') as mock_vehicle_class:
            result = client._get_vehicle("vehicle_123")
            
            # Should return cached vehicle without creating new one
            assert result == mock_vehicle
            mock_vehicle_class.assert_not_called()
    
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    def test_get_vehicle_creates_new(self, mock_vehicle_class):
        """Test creating new vehicle instance when not in cache"""
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = client._get_vehicle("vehicle_456")
        
        # Should create new vehicle and add to cache
        mock_vehicle_class.assert_called_once_with("vehicle_456", "test_token")
        assert result == mock_vehicle_instance
        assert client._vehicles_cache["vehicle_456"] == mock_vehicle_instance


class TestAPIBaseUrl:
    """Tests for API base URL"""
    
    def test_api_base_url_live_mode(self):
        """Test API base URL in live mode"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            test_mode=False
        )
        assert client._api_base_url == "https://api.smartcar.com/v2.0"
    
    def test_api_base_url_test_mode(self):
        """Test API base URL in test mode"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            test_mode=True
        )
        # Note: Current implementation uses same URL for both modes
        assert client._api_base_url == "https://api.smartcar.com/v2.0"


class TestRefreshAccessToken:
    """Tests for refresh_access_token method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.AuthClient')
    async def test_refresh_access_token_success(self, mock_auth_client_class, mock_to_thread):
        """Test successful token refresh"""
        AccessResponse = namedtuple(
            "AccessResponse",
            ["access_token", "refresh_token", "expires_in", "token_type", "expiration", "refresh_expiration"]
        )
        mock_response = AccessResponse(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            expires_in=3600,
            token_type="Bearer",
            expiration="2024-01-01T00:00:00Z",
            refresh_expiration="2024-02-01T00:00:00Z"
        )
        
        mock_client_instance = Mock()
        mock_auth_client_class.return_value = mock_client_instance
        mock_to_thread.return_value = mock_response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            refresh_token="old_refresh_token"
        )
        
        result = await client.refresh_access_token()
        
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert client.access_token == "new_access_token"
        assert client.refresh_token == "new_refresh_token"
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_no_refresh_token(self):
        """Test refresh token fails when no refresh token available"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        with pytest.raises(ValueError, match="No refresh token available"):
            await client.refresh_access_token()


class TestGetVehicleList:
    """Tests for get_vehicle_list method"""
    
    @pytest.mark.asyncio
    async def test_get_vehicle_list_success(self):
        """Test successful vehicle list retrieval"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        # Mock smartcar API responses
        VehiclesResponse = namedtuple("VehiclesResponse", ["vehicles"])
        vehicles_response = VehiclesResponse(vehicles=["vehicle_1", "vehicle_2"])
        
        AttributesResponse = namedtuple("AttributesResponse", ["make", "model", "year"])
        attributes = AttributesResponse(make="Nissan", model="Leaf", year="2024")
        
        VinResponse = namedtuple("VinResponse", ["vin"])
        vin = VinResponse(vin="TESTVIN123")
        
        with patch('custom_components.nissan_na.nissan_api.smartcar.get_vehicles') as mock_get_vehicles:
            with patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle') as mock_vehicle_class:
                with patch('custom_components.nissan_na.nissan_api.asyncio.to_thread') as mock_to_thread:
                    mock_get_vehicles.return_value = vehicles_response
                    
                    # Create a mock vehicle instance
                    mock_vehicle_instance = Mock()
                    mock_vehicle_class.return_value = mock_vehicle_instance
                    
                    # Create attributes and vin methods that return coroutines
                    async def mock_attributes():
                        return attributes
                    
                    async def mock_vin():
                        return vin
                    
                    mock_vehicle_instance.attributes = mock_attributes
                    mock_vehicle_instance.vin = mock_vin
                    
                    # Setup to_thread side effects for different calls
                    call_count = [0]
                    
                    async def to_thread_side_effect(func, *args):
                        call_count[0] += 1
                        if call_count[0] == 1:
                            # First call: smartcar.get_vehicles
                            return vehicles_response
                        else:
                            # Subsequent calls: either attributes or vin
                            result = func(*args) if args else func()
                            if hasattr(result, '__await__'):
                                return await result
                            return result
                    
                    mock_to_thread.side_effect = to_thread_side_effect
                    
                    vehicles = await client.get_vehicle_list()
                    
                    assert len(vehicles) == 2
                    assert vehicles[0].vin == "TESTVIN123"
                    assert vehicles[0].make == "Nissan"
                    assert vehicles[0].model == "Leaf"
    
    @pytest.mark.asyncio
    async def test_get_vehicle_list_not_authenticated(self):
        """Test get_vehicle_list fails when not authenticated"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback"
        )
        
        with pytest.raises(ValueError, match="Not authenticated"):
            await client.get_vehicle_list()


class TestGetVehicleInfo:
    """Tests for get_vehicle_info method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_vehicle_info_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful vehicle info retrieval"""
        AttributesResponse = namedtuple("AttributesResponse", ["id", "make", "model", "year"])
        attributes = AttributesResponse(id="vehicle_1", make="Nissan", model="Leaf", year="2024")
        
        VinResponse = namedtuple("VinResponse", ["vin"])
        vin = VinResponse(vin="TESTVIN123")
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        
        def to_thread_side_effect(func):
            if hasattr(func, '__self__') and func.__self__ == mock_vehicle_instance:
                if 'attributes' in str(func):
                    return attributes
                elif 'vin' in str(func):
                    return vin
            return None
        
        mock_to_thread.side_effect = lambda func, *args: attributes if 'attributes' in str(func) else vin
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        info = await client.get_vehicle_info("vehicle_1")
        
        assert info["make"] == "Nissan"
        assert info["model"] == "Leaf"
        assert info["year"] == 2024
        assert info["vin"] == "TESTVIN123"


class TestGetVehicleLocation:
    """Tests for get_vehicle_location method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_vehicle_location_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful location retrieval"""
        LocationResponse = namedtuple("LocationResponse", ["latitude", "longitude"])
        location = LocationResponse(latitude=37.7749, longitude=-122.4194)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = location
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_vehicle_location("vehicle_1")
        
        assert result["latitude"] == 37.7749
        assert result["longitude"] == -122.4194


class TestGetBatteryLevel:
    """Tests for get_battery_level method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_battery_level_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful battery level retrieval"""
        BatteryResponse = namedtuple("BatteryResponse", ["percentRemaining", "range"])
        battery = BatteryResponse(percentRemaining=85.0, range=280)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = battery
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_battery_level("vehicle_1")
        
        assert result["percentRemaining"] == 85.0
        assert result["range"] == 280


class TestGetBatteryCapacity:
    """Tests for get_battery_capacity method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_battery_capacity_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful battery capacity retrieval"""
        CapacityResponse = namedtuple("CapacityResponse", ["capacity"])
        capacity = CapacityResponse(capacity=62.0)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = capacity
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_battery_capacity("vehicle_1")
        
        assert result["capacity"] == 62.0


class TestGetChargeStatus:
    """Tests for get_charge_status method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_charge_status_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful charge status retrieval"""
        ChargeResponse = namedtuple("ChargeResponse", ["isPluggedIn", "state"])
        charge = ChargeResponse(isPluggedIn=True, state="CHARGING")
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = charge
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_charge_status("vehicle_1")
        
        assert result["isPluggedIn"] is True
        assert result["state"] == "CHARGING"


class TestGetOdometer:
    """Tests for get_odometer method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_odometer_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful odometer retrieval"""
        OdometerResponse = namedtuple("OdometerResponse", ["distance"])
        odometer = OdometerResponse(distance=15000)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = odometer
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_odometer("vehicle_1")
        
        assert result["distance"] == 15000


class TestGetFuelLevel:
    """Tests for get_fuel_level method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_fuel_level_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful fuel level retrieval"""
        FuelResponse = namedtuple("FuelResponse", ["percentRemaining", "range"])
        fuel = FuelResponse(percentRemaining=75.0, range=400)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = fuel
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_fuel_level("vehicle_1")
        
        assert result["percentRemaining"] == 75.0
        assert result["range"] == 400


class TestGetLockStatus:
    """Tests for get_lock_status method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_lock_status_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful lock status retrieval"""
        LockResponse = namedtuple("LockResponse", ["is_locked"])
        lock = LockResponse(is_locked=True)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = lock
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_lock_status("vehicle_1")
        
        assert result["is_locked"] is True


class TestGetTirePressure:
    """Tests for get_tire_pressure method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_tire_pressure_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful tire pressure retrieval"""
        TireResponse = namedtuple("TireResponse", ["frontLeft", "frontRight", "backLeft", "backRight"])
        tires = TireResponse(frontLeft=32.5, frontRight=32.5, backLeft=30.0, backRight=30.0)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = tires
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_tire_pressure("vehicle_1")
        
        assert result["frontLeft"] == 32.5
        assert result["backLeft"] == 30.0


class TestGetEngineOil:
    """Tests for get_engine_oil method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_engine_oil_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful engine oil retrieval"""
        OilResponse = namedtuple("OilResponse", ["percentRemaining"])
        oil = OilResponse(percentRemaining=85.0)
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = oil
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_engine_oil("vehicle_1")
        
        assert result["percentRemaining"] == 85.0


class TestLockDoors:
    """Tests for lock_doors method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_lock_doors_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful lock doors action"""
        ActionResponse = namedtuple("ActionResponse", ["status"])
        response = ActionResponse(status="success")
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.lock_doors("vehicle_1")
        
        assert result["status"] == "success"


class TestUnlockDoors:
    """Tests for unlock_doors method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_unlock_doors_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful unlock doors action"""
        ActionResponse = namedtuple("ActionResponse", ["status"])
        response = ActionResponse(status="success")
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.unlock_doors("vehicle_1")
        
        assert result["status"] == "success"


class TestStartCharge:
    """Tests for start_charge method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_start_charge_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful start charge action"""
        ActionResponse = namedtuple("ActionResponse", ["status"])
        response = ActionResponse(status="success")
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.start_charge("vehicle_1")
        
        assert result["status"] == "success"


class TestStopCharge:
    """Tests for stop_charge method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_stop_charge_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful stop charge action"""
        ActionResponse = namedtuple("ActionResponse", ["status"])
        response = ActionResponse(status="success")
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.stop_charge("vehicle_1")
        
        assert result["status"] == "success"


class TestGetPermissions:
    """Tests for get_permissions method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_get_permissions_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful permissions retrieval"""
        PermissionsResponse = namedtuple("PermissionsResponse", ["permissions"])
        response = PermissionsResponse(permissions=["read_location", "control_security"])
        
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = response
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        result = await client.get_permissions("vehicle_1")
        
        assert len(result) == 2
        assert "read_location" in result
        assert "control_security" in result


class TestDisconnect:
    """Tests for disconnect method"""
    
    @pytest.mark.asyncio
    @patch('custom_components.nissan_na.nissan_api.asyncio.to_thread')
    @patch('custom_components.nissan_na.nissan_api.smartcar.Vehicle')
    async def test_disconnect_success(self, mock_vehicle_class, mock_to_thread):
        """Test successful vehicle disconnect"""
        mock_vehicle_instance = Mock()
        mock_vehicle_class.return_value = mock_vehicle_instance
        mock_to_thread.return_value = None
        
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        # Add to cache
        client._vehicles_cache["vehicle_1"] = mock_vehicle_instance
        
        result = await client.disconnect("vehicle_1")
        
        assert result is True
        assert "vehicle_1" not in client._vehicles_cache


class TestGetVehicleSignals:
    """Tests for get_vehicle_signals method"""
    
    @pytest.mark.asyncio
    async def test_get_vehicle_signals_success(self):
        """Test successful vehicle signals retrieval"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        # Mock the response data (v3 API format — only SUCCESS signals are returned)
        response_data = {
            "data": [
                {"attributes": {"code": "tractionbattery-stateofcharge", "status": {"value": "SUCCESS"}}},
                {"attributes": {"code": "location-preciselocation", "status": {"value": "SUCCESS"}}},
                {"attributes": {"code": "odometer-traveleddistance", "status": {"value": "SUCCESS"}}},
                {"attributes": {"code": "internalcombustionengine-fuellevel", "status": {"value": "ERROR"}}},
            ]
        }
        
        with patch('custom_components.nissan_na.nissan_api.aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=response_data)
            
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            
            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_class.return_value = mock_session
            
            result = await client.get_vehicle_signals("vehicle_1")

            assert len(result) == 3
            assert "tractionbattery-stateofcharge" in result
            assert "location-preciselocation" in result
            assert "odometer-traveleddistance" in result
    
    @pytest.mark.asyncio
    async def test_get_vehicle_signals_api_error(self):
        """Test vehicle signals retrieval with API error"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        with patch('custom_components.nissan_na.nissan_api.aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 404
            
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            
            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_class.return_value = mock_session
            
            result = await client.get_vehicle_signals("vehicle_1")
            
            # Should return empty list on error
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_vehicle_signals_exception(self):
        """Test vehicle signals retrieval with exception"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        with patch('custom_components.nissan_na.nissan_api.aiohttp.ClientSession', side_effect=Exception("Connection error")):
            result = await client.get_vehicle_signals("vehicle_1")
            
            # Should return empty list on exception
            assert result == []


class TestGetVehicleStatus:
    """Tests for get_vehicle_status method"""
    
    @pytest.mark.asyncio
    async def test_get_vehicle_status_success(self):
        """Test successful vehicle status retrieval from bulk signals endpoint."""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token",
        )

        bulk_response = {
            "data": [
                {
                    "attributes": {
                        "code": "odometer-traveleddistance",
                        "status": {"value": "SUCCESS"},
                        "body": {"value": 15000.0, "unit": "km"},
                    }
                },
                {
                    "attributes": {
                        "code": "internalcombustionengine-fuellevel",
                        "status": {"value": "SUCCESS"},
                        "body": {"value": 0.75, "unit": "percent"},
                    }
                },
                {
                    "attributes": {
                        "code": "location-preciselocation",
                        "status": {"value": "SUCCESS"},
                        "body": {"latitude": 37.77, "longitude": -122.42},
                    }
                },
            ]
        }

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=bulk_response)

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_ctx)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            result = await client.get_vehicle_status("vehicle_1")

        assert "odometer" in result
        assert result["odometer"]["distance"] == 15000.0
        assert "fuel" in result
        assert result["fuel"]["percentRemaining"] == 0.75
        assert "location" in result
        assert result["location"]["latitude"] == 37.77

    @pytest.mark.asyncio
    async def test_get_vehicle_status_partial_failure(self):
        """Test that ERROR signals are skipped and SUCCESS signals populate status."""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token",
        )

        bulk_response = {
            "data": [
                {
                    "attributes": {
                        "code": "odometer-traveleddistance",
                        "status": {"value": "SUCCESS"},
                        "body": {"value": 15000.0, "unit": "km"},
                    }
                },
                {
                    "attributes": {
                        "code": "tractionbattery-stateofcharge",
                        "status": {
                            "value": "ERROR",
                            "error": {"type": "COMPATIBILITY", "code": "VEHICLE_NOT_CAPABLE"},
                        },
                    }
                },
            ]
        }

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=bulk_response)

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_ctx)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            result = await client.get_vehicle_status("vehicle_1")

        # SUCCESS signal should populate status
        assert "odometer" in result
        assert result["odometer"]["distance"] == 15000.0
        # ERROR signal should be silently skipped
        assert "battery" not in result


class TestClimateControl:
    """Tests for climate control methods"""
    
    @pytest.mark.asyncio
    async def test_start_climate_success(self):
        """Test successful start climate"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        with patch('custom_components.nissan_na.nissan_api.aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={"status": "success"})
            mock_response.raise_for_status = Mock()
            
            mock_response_context = AsyncMock()
            mock_response_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response_context.__aexit__ = AsyncMock(return_value=None)
            
            mock_session = AsyncMock()
            mock_session.post = Mock(return_value=mock_response_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_class.return_value = mock_session
            
            result = await client.start_climate("vehicle_1")
            
            assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_stop_climate_success(self):
        """Test successful stop climate"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        with patch('custom_components.nissan_na.nissan_api.aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={"status": "success"})
            mock_response.raise_for_status = Mock()
            
            mock_response_context = AsyncMock()
            mock_response_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response_context.__aexit__ = AsyncMock(return_value=None)
            
            mock_session = AsyncMock()
            mock_session.post = Mock(return_value=mock_response_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_class.return_value = mock_session
            
            result = await client.stop_climate("vehicle_1")
            
            assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_get_climate_status_success(self):
        """Test successful get climate status"""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            access_token="test_token"
        )
        
        with patch('custom_components.nissan_na.nissan_api.aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={"state": "ACTIVE"})
            mock_response.raise_for_status = Mock()
            
            mock_response_context = AsyncMock()
            mock_response_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response_context.__aexit__ = AsyncMock(return_value=None)
            
            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_response_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_class.return_value = mock_session
            
            result = await client.get_climate_status("vehicle_1")
            
            assert result["state"] == "ACTIVE"
