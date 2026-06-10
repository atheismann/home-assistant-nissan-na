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
        )
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_secret"
        assert client.user_id is None
        assert client.test_mode is False
        assert client._cc_token is None

    def test_client_init_with_user_id(self):
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            user_id="sc_user_abc123",
        )
        assert client.user_id == "sc_user_abc123"

    def test_client_init_test_mode(self):
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
            test_mode=True,
        )
        assert client.test_mode is True

    def test_client_caches_initialized(self):
        client = SmartcarApiClient(
            client_id="test_client_id",
            client_secret="test_secret",
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
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = response_data

        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.post = AsyncMock(return_value=mock_resp)

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
            token = await client._get_access_token()

        assert token == "fresh_token"
        assert client._cc_token == "fresh_token"


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

        def make_resp(body):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = body
            return resp

        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)

        def get_side_effect(url, **kwargs):
            if "connections" in url:
                return make_resp(connections_response)
            elif "/vin" in url:
                return make_resp(vin_response)
            else:
                return make_resp(attrs_response)

        mock_httpx.get = AsyncMock(side_effect=get_side_effect)

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
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
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = body
            return r

        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.get = AsyncMock(side_effect=lambda url, **kw: make_resp(vin_resp if "/vin" in url else attrs_resp))

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
            info = await client.get_vehicle_info("vehicle_1")

        assert info["make"] == "NISSAN"
        assert info["vin"] == "TESTVIN999"


def _make_v3_get_mock(response_body: dict):
    """Return a mock httpx client that responds to any GET with response_body."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = response_body
    mock_resp.raise_for_status = MagicMock()
    mock_httpx = AsyncMock()
    mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
    mock_httpx.__aexit__ = AsyncMock(return_value=None)
    mock_httpx.get = AsyncMock(return_value=mock_resp)
    return mock_httpx


def _make_v3_post_mock(response_body: dict):
    """Return a mock httpx client that responds to any POST with response_body."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = response_body
    mock_resp.raise_for_status = MagicMock()
    mock_httpx = AsyncMock()
    mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
    mock_httpx.__aexit__ = AsyncMock(return_value=None)
    mock_httpx.post = AsyncMock(return_value=mock_resp)
    return mock_httpx


class TestGetVehicleLocation:
    """Tests for get_vehicle_location method"""

    @pytest.mark.asyncio
    async def test_get_vehicle_location_success(self):
        body = {"data": {"attributes": {"latitude": 37.7749, "longitude": -122.4194}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_vehicle_location("vehicle_1")
        assert result["latitude"] == 37.7749
        assert result["longitude"] == -122.4194


class TestGetBatteryLevel:
    """Tests for get_battery_level method"""

    @pytest.mark.asyncio
    async def test_get_battery_level_success(self):
        body = {"data": {"attributes": {"percentRemaining": 85.0, "range": 280}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_battery_level("vehicle_1")
        assert result["percentRemaining"] == 85.0
        assert result["range"] == 280


class TestGetBatteryCapacity:
    """Tests for get_battery_capacity method"""

    @pytest.mark.asyncio
    async def test_get_battery_capacity_success(self):
        body = {"data": {"attributes": {"capacity": 62.0}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_battery_capacity("vehicle_1")
        assert result["capacity"] == 62.0


class TestGetChargeStatus:
    """Tests for get_charge_status method"""

    @pytest.mark.asyncio
    async def test_get_charge_status_success(self):
        body = {"data": {"attributes": {"isPluggedIn": True, "state": "CHARGING"}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_charge_status("vehicle_1")
        assert result["isPluggedIn"] is True
        assert result["state"] == "CHARGING"


class TestGetOdometer:
    """Tests for get_odometer method"""

    @pytest.mark.asyncio
    async def test_get_odometer_success(self):
        body = {"data": {"attributes": {"distance": 15000}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_odometer("vehicle_1")
        assert result["distance"] == 15000


class TestGetFuelLevel:
    """Tests for get_fuel_level method"""

    @pytest.mark.asyncio
    async def test_get_fuel_level_success(self):
        body = {"data": {"attributes": {"percentRemaining": 75.0, "range": 400}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_fuel_level("vehicle_1")
        assert result["percentRemaining"] == 75.0
        assert result["range"] == 400


class TestGetLockStatus:
    """Tests for get_lock_status method"""

    @pytest.mark.asyncio
    async def test_get_lock_status_success(self):
        body = {"data": {"attributes": {"is_locked": True}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_lock_status("vehicle_1")
        assert result["is_locked"] is True


class TestGetTirePressure:
    """Tests for get_tire_pressure method"""

    @pytest.mark.asyncio
    async def test_get_tire_pressure_success(self):
        body = {"data": {"attributes": {"frontLeft": 32.5, "frontRight": 32.5, "backLeft": 30.0, "backRight": 30.0}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_tire_pressure("vehicle_1")
        assert result["frontLeft"] == 32.5
        assert result["backLeft"] == 30.0


class TestGetEngineOil:
    """Tests for get_engine_oil method"""

    @pytest.mark.asyncio
    async def test_get_engine_oil_success(self):
        body = {"data": {"attributes": {"percentRemaining": 85.0}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_engine_oil("vehicle_1")
        assert result["percentRemaining"] == 85.0


class TestLockDoors:
    """Tests for lock_doors method"""

    @pytest.mark.asyncio
    async def test_lock_doors_success(self):
        body = {"status": "success"}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_post_mock(body)):
            result = await _make_client().lock_doors("vehicle_1")
        assert result["status"] == "success"


class TestUnlockDoors:
    """Tests for unlock_doors method"""

    @pytest.mark.asyncio
    async def test_unlock_doors_success(self):
        body = {"status": "success"}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_post_mock(body)):
            result = await _make_client().unlock_doors("vehicle_1")

        assert result["status"] == "success"


class TestStartCharge:
    """Tests for start_charge method"""

    @pytest.mark.asyncio
    async def test_start_charge_success(self):
        body = {"status": "success"}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_post_mock(body)):
            result = await _make_client().start_charge("vehicle_1")
        assert result["status"] == "success"


class TestStopCharge:
    """Tests for stop_charge method"""

    @pytest.mark.asyncio
    async def test_stop_charge_success(self):
        body = {"status": "success"}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_post_mock(body)):
            result = await _make_client().stop_charge("vehicle_1")
        assert result["status"] == "success"


class TestGetPermissions:
    """Tests for get_permissions method"""

    @pytest.mark.asyncio
    async def test_get_permissions_success(self):
        body = {"data": {"attributes": {"permissions": ["read_location", "control_security"]}}}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
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

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.delete = AsyncMock(return_value=mock_resp)

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
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
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = response_data
        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.get = AsyncMock(return_value=mock_resp)

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.get_vehicle_signals("vehicle_1")

        assert len(result) == 3
        assert "tractionbattery-stateofcharge" in result
        assert "location-preciselocation" in result
        assert "odometer-traveleddistance" in result

    @pytest.mark.asyncio
    async def test_get_vehicle_signals_api_error(self):
        client = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.get = AsyncMock(return_value=mock_resp)

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.get_vehicle_signals("vehicle_1")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_vehicle_signals_exception(self):
        client = _make_client()

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", side_effect=Exception("Connection error")):
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

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = bulk_response
        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.get = AsyncMock(return_value=mock_resp)

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
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

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = bulk_response
        mock_httpx = AsyncMock()
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.get = AsyncMock(return_value=mock_resp)

        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.get_vehicle_status("vehicle_1")

        assert "odometer" in result
        assert result["odometer"]["distance"] == 15000.0
        assert "battery" not in result


class TestClimateControl:
    """Tests for climate control methods"""

    @pytest.mark.asyncio
    async def test_start_climate_success(self):
        body = {"status": "success"}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_post_mock(body)):
            result = await _make_client().start_climate("vehicle_1")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_stop_climate_success(self):
        body = {"status": "success"}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_post_mock(body)):
            result = await _make_client().stop_climate("vehicle_1")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_climate_status_success(self):
        body = {"state": "ACTIVE"}
        with patch("custom_components.nissan_na.nissan_api.httpx.AsyncClient", return_value=_make_v3_get_mock(body)):
            result = await _make_client().get_climate_status("vehicle_1")
        assert result["state"] == "ACTIVE"
