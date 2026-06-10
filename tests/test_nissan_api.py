"""Unit tests for nissan_api.py - SmartcarApiClient"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from custom_components.nissan_na.nissan_api import (
    SmartcarApiClient,
    Vehicle,
    _namedtuple_to_dict,
)
from collections import namedtuple


def _make_client(**kwargs) -> SmartcarApiClient:
    """Create a SmartcarApiClient with a pre-seeded cc token so tests skip HTTP."""
    client = SmartcarApiClient(
        client_id=kwargs.get("client_id", "test_client_id"),
        client_secret=kwargs.get("client_secret", "test_secret"),
        redirect_uri=kwargs.get("redirect_uri", "https://example.com/callback"),
        user_id=kwargs.get("user_id", "test_user_id"),
        test_mode=kwargs.get("test_mode", False),
    )
    # Pre-seed token cache so _get_access_token() never makes a network call
    client._cc_token = "mock_cc_token"
    client._cc_token_expires_at = float("inf")
    return client


class TestNamedTupleToDict:
    """Tests for _namedtuple_to_dict helper function"""

    def test_dict_input_returns_same_dict(self):
        input_dict = {"key1": "value1", "key2": "value2"}
        assert _namedtuple_to_dict(input_dict) == input_dict

    def test_namedtuple_to_dict_simple(self):
        TestTuple = namedtuple("TestTuple", ["field1", "field2"])
        obj = TestTuple(field1="value1", field2="value2")
        assert _namedtuple_to_dict(obj) == {"field1": "value1", "field2": "value2"}

    def test_namedtuple_to_dict_nested(self):
        InnerTuple = namedtuple("InnerTuple", ["inner_field"])
        OuterTuple = namedtuple("OuterTuple", ["outer_field", "nested"])
        inner = InnerTuple(inner_field="inner_value")
        outer = OuterTuple(outer_field="outer_value", nested=inner)
        result = _namedtuple_to_dict(outer)
        assert result == {"outer_field": "outer_value", "nested": {"inner_field": "inner_value"}}

    def test_object_without_asdict(self):
        class SimpleObject:
            field1 = "value1"
            field2 = "value2"

        result = _namedtuple_to_dict(SimpleObject())
        assert "field1" in result
        assert "field2" in result


class TestVehicleModel:
    """Tests for Vehicle Pydantic model"""

    def test_vehicle_model_required_fields(self):
        vehicle = Vehicle(vin="TEST123", id="vehicle_123")
        assert vehicle.vin == "TEST123"
        assert vehicle.id == "vehicle_123"
        assert vehicle.model is None
        assert vehicle.year is None
        assert vehicle.make is None

    def test_vehicle_model_all_fields(self):
        vehicle = Vehicle(vin="TEST123", id="vehicle_123", model="Leaf", year=2024, make="Nissan")
        assert vehicle.vin == "TEST123"
        assert vehicle.model == "Leaf"
        assert vehicle.year == 2024
        assert vehicle.make == "Nissan"


class TestSmartcarApiClientInit:
    """Tests for SmartcarApiClient initialization"""

    def test_client_init_minimal(self):
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
        )
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_secret"
        assert client.redirect_uri == "https://example.com/callback"
        assert client.user_id is None
        assert client.test_mode is False
        assert client._cc_token is None

    def test_client_init_with_user_id(self):
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            user_id="sc_user_abc123",
        )
        assert client.user_id == "sc_user_abc123"

    def test_client_init_test_mode(self):
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            test_mode=True,
        )
        assert client.test_mode is True

    def test_client_caches_initialized(self):
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
        )
        assert client._vehicle_model_cache == {}
        assert client._vehicle_signals_cache == {}
        assert client._permission_denied_signals == {}


class TestGetAccessToken:
    """Tests for _get_access_token (client-credentials token fetch)"""

    @pytest.mark.asyncio
    async def test_returns_cached_token(self):
        client = _make_client()
        # _cc_token is pre-seeded by _make_client; should return without HTTP
        token = await client._get_access_token()
        assert token == "mock_cc_token"

    @pytest.mark.asyncio
    async def test_fetches_new_token_when_expired(self):
        client = _make_client()
        client._cc_token = None
        client._cc_token_expires_at = 0.0

        response_data = {"access_token": "fresh_token", "expires_in": 3600}
        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_sess_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=response_data)
            mock_resp.text = AsyncMock(return_value="")

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_sess = AsyncMock()
            mock_sess.post = Mock(return_value=mock_ctx)
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=None)
            mock_sess_cls.return_value = mock_sess

            token = await client._get_access_token()

        assert token == "fresh_token"
        assert client._cc_token == "fresh_token"


class TestGetAuthUrl:
    """Tests for get_auth_url method"""

    @patch("custom_components.nissan_na.nissan_api.smartcar.AuthClient")
    def test_get_auth_url_without_state(self, mock_auth_client_class):
        mock_instance = Mock()
        mock_instance.get_auth_url.return_value = "https://smartcar.com/auth?params"
        mock_auth_client_class.return_value = mock_instance

        url = _make_client().get_auth_url()

        assert url == "https://smartcar.com/auth?params"
        mock_auth_client_class.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            mode="live",
        )

    @patch("custom_components.nissan_na.nissan_api.smartcar.AuthClient")
    def test_get_auth_url_with_state(self, mock_auth_client_class):
        mock_instance = Mock()
        mock_instance.get_auth_url.return_value = "https://smartcar.com/auth?state=test123"
        mock_auth_client_class.return_value = mock_instance

        url = _make_client().get_auth_url(state="test123")

        assert url == "https://smartcar.com/auth?state=test123"
        call_args = mock_instance.get_auth_url.call_args
        assert call_args.kwargs["options"]["state"] == "test123"

    @patch("custom_components.nissan_na.nissan_api.smartcar.AuthClient")
    def test_get_auth_url_test_mode(self, mock_auth_client_class):
        mock_instance = Mock()
        mock_instance.get_auth_url.return_value = "https://smartcar.com/test/auth"
        mock_auth_client_class.return_value = mock_instance

        _make_client(test_mode=True).get_auth_url()

        mock_auth_client_class.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
            mode="test",
        )

    @patch("custom_components.nissan_na.nissan_api.smartcar.AuthClient")
    def test_get_auth_url_includes_nissan_make_bypass(self, mock_auth_client_class):
        mock_instance = Mock()
        mock_instance.get_auth_url.return_value = "https://smartcar.com/auth"
        mock_auth_client_class.return_value = mock_instance

        _make_client().get_auth_url()

        call_args = mock_instance.get_auth_url.call_args
        assert call_args.kwargs["options"]["make_bypass"] == "NISSAN"

    @patch("custom_components.nissan_na.nissan_api.smartcar.AuthClient")
    def test_get_auth_url_includes_required_scopes(self, mock_auth_client_class):
        mock_instance = Mock()
        mock_instance.get_auth_url.return_value = "https://smartcar.com/auth"
        mock_auth_client_class.return_value = mock_instance

        _make_client().get_auth_url()

        scopes = mock_instance.get_auth_url.call_args.kwargs["scope"]
        assert "required:read_vehicle_info" in scopes
        assert "required:read_location" in scopes
        assert "required:read_odometer" in scopes
        assert "read_battery" in scopes
        assert "read_charge" in scopes
        assert "control_charge" in scopes
        assert "read_fuel" in scopes


class TestAuthenticate:
    """Tests for authenticate method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.AuthClient")
    async def test_authenticate_success(self, mock_auth_client_class, mock_to_thread):
        """authenticate() captures user_id and returns it."""
        AccessResponse = namedtuple(
            "AccessResponse",
            ["access_token", "refresh_token", "expires_in", "token_type", "expiration", "refresh_expiration"],
        )
        UserResponse = namedtuple("UserResponse", ["id"])

        tokens = AccessResponse(
            access_token="tmp_access",
            refresh_token="tmp_refresh",
            expires_in=3600,
            token_type="Bearer",
            expiration="2024-01-01T00:00:00Z",
            refresh_expiration="2024-02-01T00:00:00Z",
        )
        user = UserResponse(id="sc_user_abc123")

        mock_auth_client_class.return_value = Mock()
        call_count = {"n": 0}

        async def to_thread_side_effect(func, *args):
            call_count["n"] += 1
            return tokens if call_count["n"] == 1 else user

        mock_to_thread.side_effect = to_thread_side_effect

        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
        )
        result = await client.authenticate("test_code")

        assert result == {"user_id": "sc_user_abc123"}
        assert client.user_id == "sc_user_abc123"

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.AuthClient")
    async def test_authenticate_clears_caches(self, mock_auth_client_class, mock_to_thread):
        """authenticate() clears signal caches."""
        AccessResponse = namedtuple("AccessResponse", ["access_token", "refresh_token", "expires_in", "token_type", "expiration", "refresh_expiration"])
        UserResponse = namedtuple("UserResponse", ["id"])

        tokens = AccessResponse("tmp", "tmp_r", 3600, "Bearer", "x", "y")
        user = UserResponse(id="user_123")

        mock_auth_client_class.return_value = Mock()
        call_count = {"n": 0}

        async def side_effect(func, *args):
            call_count["n"] += 1
            return tokens if call_count["n"] == 1 else user

        mock_to_thread.side_effect = side_effect

        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
        )
        client._vehicle_signals_cache["v1"] = ["some_signal"]

        await client.authenticate("test_code")

        assert client._vehicle_signals_cache == {}


class TestSdkVehicle:
    """Tests for _sdk_vehicle helper"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_sdk_vehicle_uses_cc_token(self, mock_vehicle_class):
        mock_vehicle_class.return_value = Mock()
        client = _make_client()

        vehicle = await client._sdk_vehicle("vehicle_123")

        mock_vehicle_class.assert_called_once_with("vehicle_123", "mock_cc_token")
        assert vehicle == mock_vehicle_class.return_value


class TestV3BaseUrl:
    """Tests for v3 API base URL constant"""

    def test_v3_base_url(self):
        assert SmartcarApiClient._V3_BASE == "https://vehicle.api.smartcar.com/v3"

    def test_iam_token_url(self):
        assert "iam.smartcar.com" in SmartcarApiClient._IAM_TOKEN_URL


class TestGetVehicleList:
    """Tests for get_vehicle_list method (Connections API)"""

    @pytest.mark.asyncio
    async def test_get_vehicle_list_success(self):
        """Vehicle list fetched from connections endpoint."""
        client = _make_client()

        connections_response = {
            "data": [{"vehicleId": "vehicle_1"}, {"vehicleId": "vehicle_2"}]
        }
        attrs_response = {"data": {"attributes": {"make": "NISSAN", "model": "Pathfinder", "year": 2025}}}
        vin_response = {"data": {"attributes": {"vin": "TESTVIN123"}}}

        call_n = {"n": 0}

        def make_resp(body):
            resp = AsyncMock()
            resp.status = 200
            resp.json = AsyncMock(return_value=body)
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=resp)
            ctx.__aexit__ = AsyncMock(return_value=None)
            return ctx

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            def get_side_effect(url, **kwargs):
                call_n["n"] += 1
                if "connections" in url:
                    return make_resp(connections_response)
                elif "/vin" in url:
                    return make_resp(vin_response)
                else:
                    return make_resp(attrs_response)

            mock_session.get = Mock(side_effect=get_side_effect)
            mock_cls.return_value = mock_session

            vehicles = await client.get_vehicle_list()

        assert len(vehicles) == 2
        assert vehicles[0].vin == "TESTVIN123"
        assert vehicles[0].make == "NISSAN"
        assert vehicles[0].model == "Pathfinder"
        assert vehicles[0].year == 2025

    @pytest.mark.asyncio
    async def test_get_vehicle_list_no_user_id(self):
        """get_vehicle_list raises when user_id is not set."""
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
        )
        client._cc_token = "mock"
        client._cc_token_expires_at = float("inf")

        with pytest.raises(ValueError, match="user_id is not set"):
            await client.get_vehicle_list()


class TestGetVehicleInfo:
    """Tests for get_vehicle_info method"""

    @pytest.mark.asyncio
    async def test_get_vehicle_info_from_cache(self):
        """Returns cached vehicle info without HTTP calls."""
        client = _make_client()
        client._vehicle_model_cache["vehicle_1"] = Vehicle(
            id="vehicle_1", vin="VIN123", make="Nissan", model="Leaf", year=2024
        )

        info = await client.get_vehicle_info("vehicle_1")

        assert info["make"] == "Nissan"
        assert info["model"] == "Leaf"
        assert info["year"] == 2024
        assert info["vin"] == "VIN123"

    @pytest.mark.asyncio
    async def test_get_vehicle_info_fetches_via_http(self):
        """Fetches vehicle attributes via direct HTTP when not in cache."""
        client = _make_client()

        attrs_resp = {"data": {"attributes": {"make": "NISSAN", "model": "Pathfinder", "year": 2025}}}
        vin_resp = {"data": {"attributes": {"vin": "TESTVIN999"}}}

        def make_resp(body):
            resp = AsyncMock()
            resp.status = 200
            resp.json = AsyncMock(return_value=body)
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=resp)
            ctx.__aexit__ = AsyncMock(return_value=None)
            return ctx

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = Mock(side_effect=lambda url, **kw: make_resp(vin_resp if "/vin" in url else attrs_resp))
            mock_cls.return_value = mock_session

            info = await client.get_vehicle_info("vehicle_1")

        assert info["make"] == "NISSAN"
        assert info["vin"] == "TESTVIN999"


class TestGetVehicleLocation:
    """Tests for get_vehicle_location method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_vehicle_location_success(self, mock_vehicle_class, mock_to_thread):
        LocationResponse = namedtuple("LocationResponse", ["latitude", "longitude"])
        location = LocationResponse(latitude=37.7749, longitude=-122.4194)

        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = location

        result = await _make_client().get_vehicle_location("vehicle_1")

        assert result["latitude"] == 37.7749
        assert result["longitude"] == -122.4194


class TestGetBatteryLevel:
    """Tests for get_battery_level method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_battery_level_success(self, mock_vehicle_class, mock_to_thread):
        BatteryResponse = namedtuple("BatteryResponse", ["percentRemaining", "range"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = BatteryResponse(percentRemaining=85.0, range=280)

        result = await _make_client().get_battery_level("vehicle_1")

        assert result["percentRemaining"] == 85.0
        assert result["range"] == 280


class TestGetBatteryCapacity:
    """Tests for get_battery_capacity method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_battery_capacity_success(self, mock_vehicle_class, mock_to_thread):
        CapacityResponse = namedtuple("CapacityResponse", ["capacity"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = CapacityResponse(capacity=62.0)

        result = await _make_client().get_battery_capacity("vehicle_1")

        assert result["capacity"] == 62.0


class TestGetChargeStatus:
    """Tests for get_charge_status method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_charge_status_success(self, mock_vehicle_class, mock_to_thread):
        ChargeResponse = namedtuple("ChargeResponse", ["isPluggedIn", "state"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = ChargeResponse(isPluggedIn=True, state="CHARGING")

        result = await _make_client().get_charge_status("vehicle_1")

        assert result["isPluggedIn"] is True
        assert result["state"] == "CHARGING"


class TestGetOdometer:
    """Tests for get_odometer method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_odometer_success(self, mock_vehicle_class, mock_to_thread):
        OdometerResponse = namedtuple("OdometerResponse", ["distance"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = OdometerResponse(distance=15000)

        result = await _make_client().get_odometer("vehicle_1")

        assert result["distance"] == 15000


class TestGetFuelLevel:
    """Tests for get_fuel_level method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_fuel_level_success(self, mock_vehicle_class, mock_to_thread):
        FuelResponse = namedtuple("FuelResponse", ["percentRemaining", "range"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = FuelResponse(percentRemaining=75.0, range=400)

        result = await _make_client().get_fuel_level("vehicle_1")

        assert result["percentRemaining"] == 75.0
        assert result["range"] == 400


class TestGetLockStatus:
    """Tests for get_lock_status method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_lock_status_success(self, mock_vehicle_class, mock_to_thread):
        LockResponse = namedtuple("LockResponse", ["is_locked"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = LockResponse(is_locked=True)

        result = await _make_client().get_lock_status("vehicle_1")

        assert result["is_locked"] is True


class TestGetTirePressure:
    """Tests for get_tire_pressure method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_tire_pressure_success(self, mock_vehicle_class, mock_to_thread):
        TireResponse = namedtuple("TireResponse", ["frontLeft", "frontRight", "backLeft", "backRight"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = TireResponse(frontLeft=32.5, frontRight=32.5, backLeft=30.0, backRight=30.0)

        result = await _make_client().get_tire_pressure("vehicle_1")

        assert result["frontLeft"] == 32.5
        assert result["backLeft"] == 30.0


class TestGetEngineOil:
    """Tests for get_engine_oil method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_engine_oil_success(self, mock_vehicle_class, mock_to_thread):
        OilResponse = namedtuple("OilResponse", ["percentRemaining"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = OilResponse(percentRemaining=85.0)

        result = await _make_client().get_engine_oil("vehicle_1")

        assert result["percentRemaining"] == 85.0


class TestLockDoors:
    """Tests for lock_doors method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_lock_doors_success(self, mock_vehicle_class, mock_to_thread):
        ActionResponse = namedtuple("ActionResponse", ["status"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = ActionResponse(status="success")

        result = await _make_client().lock_doors("vehicle_1")

        assert result["status"] == "success"


class TestUnlockDoors:
    """Tests for unlock_doors method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_unlock_doors_success(self, mock_vehicle_class, mock_to_thread):
        ActionResponse = namedtuple("ActionResponse", ["status"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = ActionResponse(status="success")

        result = await _make_client().unlock_doors("vehicle_1")

        assert result["status"] == "success"


class TestStartCharge:
    """Tests for start_charge method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_start_charge_success(self, mock_vehicle_class, mock_to_thread):
        ActionResponse = namedtuple("ActionResponse", ["status"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = ActionResponse(status="success")

        result = await _make_client().start_charge("vehicle_1")

        assert result["status"] == "success"


class TestStopCharge:
    """Tests for stop_charge method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_stop_charge_success(self, mock_vehicle_class, mock_to_thread):
        ActionResponse = namedtuple("ActionResponse", ["status"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = ActionResponse(status="success")

        result = await _make_client().stop_charge("vehicle_1")

        assert result["status"] == "success"


class TestGetPermissions:
    """Tests for get_permissions method"""

    @pytest.mark.asyncio
    @patch("custom_components.nissan_na.nissan_api.asyncio.to_thread")
    @patch("custom_components.nissan_na.nissan_api.smartcar.Vehicle")
    async def test_get_permissions_success(self, mock_vehicle_class, mock_to_thread):
        PermissionsResponse = namedtuple("PermissionsResponse", ["permissions"])
        mock_vehicle_class.return_value = Mock()
        mock_to_thread.return_value = PermissionsResponse(permissions=["read_location", "control_security"])

        result = await _make_client().get_permissions("vehicle_1")

        assert len(result) == 2
        assert "read_location" in result
        assert "control_security" in result


class TestDisconnect:
    """Tests for disconnect method"""

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        client = _make_client()
        client._vehicle_model_cache["vehicle_1"] = Mock()

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_sess = AsyncMock()
            mock_sess.delete = Mock(return_value=mock_ctx)
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_sess

            result = await client.disconnect("vehicle_1")

        assert result is True
        assert "vehicle_1" not in client._vehicle_model_cache


class TestGetVehicleSignals:
    """Tests for get_vehicle_signals method"""

    @pytest.mark.asyncio
    async def test_get_vehicle_signals_success(self):
        client = _make_client()

        response_data = {
            "data": [
                {"attributes": {"code": "tractionbattery-stateofcharge", "status": {"value": "SUCCESS"}}},
                {"attributes": {"code": "location-preciselocation", "status": {"value": "SUCCESS"}}},
                {"attributes": {"code": "odometer-traveleddistance", "status": {"value": "SUCCESS"}}},
                {"attributes": {"code": "internalcombustionengine-fuellevel", "status": {"value": "ERROR"}}},
            ]
        }

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=response_data)
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_sess = AsyncMock()
            mock_sess.get = Mock(return_value=mock_ctx)
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_sess

            result = await client.get_vehicle_signals("vehicle_1")

        assert len(result) == 3
        assert "tractionbattery-stateofcharge" in result
        assert "location-preciselocation" in result
        assert "odometer-traveleddistance" in result

    @pytest.mark.asyncio
    async def test_get_vehicle_signals_api_error(self):
        client = _make_client()

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 404
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_sess = AsyncMock()
            mock_sess.get = Mock(return_value=mock_ctx)
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_sess

            result = await client.get_vehicle_signals("vehicle_1")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_vehicle_signals_exception(self):
        client = _make_client()

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession", side_effect=Exception("Connection error")):
            result = await client.get_vehicle_signals("vehicle_1")

        assert result == []


class TestGetVehicleStatus:
    """Tests for get_vehicle_status method"""

    @pytest.mark.asyncio
    async def test_get_vehicle_status_success(self):
        """Successful vehicle status retrieval from bulk signals endpoint."""
        client = _make_client()

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

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=bulk_response)
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_sess = AsyncMock()
            mock_sess.get = Mock(return_value=mock_ctx)
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_sess

            result = await client.get_vehicle_status("vehicle_1")

        assert "odometer" in result
        assert result["odometer"]["distance"] == 15000.0
        assert "fuel" in result
        assert result["fuel"]["percentRemaining"] == 0.75
        assert "location" in result
        assert result["location"]["latitude"] == 37.77

    @pytest.mark.asyncio
    async def test_get_vehicle_status_partial_failure(self):
        """ERROR signals are skipped; SUCCESS signals populate status."""
        client = _make_client()

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

        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=bulk_response)
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_sess = AsyncMock()
            mock_sess.get = Mock(return_value=mock_ctx)
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_sess

            result = await client.get_vehicle_status("vehicle_1")

        assert "odometer" in result
        assert result["odometer"]["distance"] == 15000.0
        assert "battery" not in result


class TestClimateControl:
    """Tests for climate control methods"""

    def _mock_session(self, method, response_body):
        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=response_body)
        mock_resp.raise_for_status = Mock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sess = AsyncMock()
        setattr(mock_sess, method, Mock(return_value=mock_ctx))
        mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_sess.__aexit__ = AsyncMock(return_value=None)
        return mock_sess

    @pytest.mark.asyncio
    async def test_start_climate_success(self):
        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = self._mock_session("post", {"status": "success"})
            result = await _make_client().start_climate("vehicle_1")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_stop_climate_success(self):
        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = self._mock_session("post", {"status": "success"})
            result = await _make_client().stop_climate("vehicle_1")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_climate_status_success(self):
        with patch("custom_components.nissan_na.nissan_api.aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = self._mock_session("get", {"state": "ACTIVE"})
            result = await _make_client().get_climate_status("vehicle_1")
        assert result["state"] == "ACTIVE"
