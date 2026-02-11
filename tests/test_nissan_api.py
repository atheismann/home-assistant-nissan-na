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
