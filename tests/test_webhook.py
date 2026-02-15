"""Tests for webhook module."""
import pytest
import hmac
import hashlib
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiohttp import web
from http import HTTPStatus


class TestWebhookSignatureVerification:
    """Test webhook signature verification."""

    def test_verify_signature_with_valid_signature(self):
        """Test signature verification with valid signature."""
        from custom_components.nissan_na.webhook import verify_signature
        
        management_token = "test_token_123"
        body = b'{"event": "test"}'
        
        # Create valid signature
        expected_signature = hmac.new(
            management_token.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        assert verify_signature(management_token, expected_signature, body) is True

    def test_verify_signature_with_invalid_signature(self):
        """Test signature verification with invalid signature."""
        from custom_components.nissan_na.webhook import verify_signature
        
        management_token = "test_token_123"
        body = b'{"event": "test"}'
        invalid_signature = "invalid_signature_xyz"
        
        assert verify_signature(management_token, invalid_signature, body) is False

    def test_verify_signature_with_empty_token(self):
        """Test signature verification with empty token."""
        from custom_components.nissan_na.webhook import verify_signature
        
        assert verify_signature("", "signature", b"body") is False
        assert verify_signature(None, "signature", b"body") is False

    def test_verify_signature_with_empty_signature(self):
        """Test signature verification with empty signature."""
        from custom_components.nissan_na.webhook import verify_signature
        
        assert verify_signature("token", "", b"body") is False
        assert verify_signature("token", None, b"body") is False

    def test_verify_signature_with_different_body(self):
        """Test signature verification fails with different body."""
        from custom_components.nissan_na.webhook import verify_signature
        
        management_token = "test_token_123"
        original_body = b'{"event": "test"}'
        different_body = b'{"event": "different"}'
        
        signature = hmac.new(
            management_token.encode("utf-8"),
            original_body,
            hashlib.sha256
        ).hexdigest()
        
        assert verify_signature(management_token, signature, different_body) is False


class TestWebhookConstants:
    """Test webhook constants."""

    def test_conf_management_token_constant(self):
        """Test management token constant."""
        from custom_components.nissan_na.webhook import CONF_MANAGEMENT_TOKEN
        
        assert CONF_MANAGEMENT_TOKEN == "management_token"
        assert isinstance(CONF_MANAGEMENT_TOKEN, str)

    def test_webhook_id_key_constant(self):
        """Test webhook ID key constant."""
        from custom_components.nissan_na.webhook import WEBHOOK_ID_KEY
        
        assert WEBHOOK_ID_KEY == "webhook_id"
        assert isinstance(WEBHOOK_ID_KEY, str)

    def test_event_type_verify_constant(self):
        """Test verify event type constant."""
        from custom_components.nissan_na.webhook import EVENT_TYPE_VERIFY
        
        assert EVENT_TYPE_VERIFY == "VERIFY"

    def test_event_type_vehicle_state_constant(self):
        """Test vehicle state event type constant."""
        from custom_components.nissan_na.webhook import EVENT_TYPE_VEHICLE_STATE
        
        assert EVENT_TYPE_VEHICLE_STATE == "VEHICLE_STATE"

    def test_event_type_vehicle_error_constant(self):
        """Test vehicle error event type constant."""
        from custom_components.nissan_na.webhook import EVENT_TYPE_VEHICLE_ERROR
        
        assert EVENT_TYPE_VEHICLE_ERROR == "VEHICLE_ERROR"

    def test_signal_webhook_data_constant(self):
        """Test webhook data signal constant."""
        from custom_components.nissan_na.webhook import SIGNAL_WEBHOOK_DATA
        
        assert SIGNAL_WEBHOOK_DATA == "nissan_na_webhook_data"


class TestSmartcarSignalParser:
    """Test Smartcar webhook signal format parser."""

    def test_parse_smartcar_signals_basic_boolean(self):
        """Test parsing simple boolean signal."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        signals = [
            {
                "code": "charge-ischarging",
                "name": "IsCharging",
                "body": True,
                "status": {"value": "SUCCESS"},
                "meta": {"oemUpdatedAt": 1771185093925}
            }
        ]
        
        result = _parse_smartcar_signals(signals)
        assert result == {"charge-ischarging": True}

    def test_parse_smartcar_signals_numeric_with_unit(self):
        """Test parsing numeric signal with unit."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        signals = [
            {
                "code": "internalcombustionengine-fuellevel",
                "name": "FuelLevel",
                "body": {"value": 65, "unit": "percent"},
                "status": {"value": "SUCCESS"},
                "meta": {"oemUpdatedAt": 1771185093925}
            }
        ]
        
        result = _parse_smartcar_signals(signals)
        assert result == {"internalcombustionengine-fuellevel": 65}

    def test_parse_smartcar_signals_complex_location(self):
        """Test parsing complex location signal."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        signals = [
            {
                "code": "location-preciselocation",
                "name": "PreciseLocation",
                "body": {
                    "latitude": 51.5014,
                    "longitude": -0.1419,
                    "direction": "NE",
                    "heading": 45.3,
                    "locationType": "CURRENT"
                },
                "status": {"value": "SUCCESS"},
                "meta": {"oemUpdatedAt": 1771185093925}
            }
        ]
        
        result = _parse_smartcar_signals(signals)
        # Complex objects should be stored as-is
        assert "location-preciselocation" in result
        assert result["location-preciselocation"]["latitude"] == 51.5014
        assert result["location-preciselocation"]["longitude"] == -0.1419

    def test_parse_smartcar_signals_multiple_signals(self):
        """Test parsing multiple signals."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        signals = [
            {
                "code": "charge-ischarging",
                "name": "IsCharging",
                "body": True,
                "status": {"value": "SUCCESS"},
            },
            {
                "code": "closure-islocked",
                "name": "IsLocked",
                "body": False,
                "status": {"value": "SUCCESS"},
            },
            {
                "code": "battery-percent",
                "name": "BatteryPercent",
                "body": {"value": 78, "unit": "percent"},
                "status": {"value": "SUCCESS"},
            }
        ]
        
        result = _parse_smartcar_signals(signals)
        assert len(result) == 3
        assert result["charge-ischarging"] is True
        assert result["closure-islocked"] is False
        assert result["battery-percent"] == 78

    def test_parse_smartcar_signals_skips_failed_status(self):
        """Test that signals with non-SUCCESS status are skipped."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        signals = [
            {
                "code": "charge-ischarging",
                "name": "IsCharging",
                "body": True,
                "status": {"value": "SUCCESS"},
            },
            {
                "code": "battery-level",
                "name": "BatteryLevel",
                "body": 75,
                "status": {"value": "ERROR"},  # This should be skipped
            }
        ]
        
        result = _parse_smartcar_signals(signals)
        assert len(result) == 1
        assert "charge-ischarging" in result
        assert "battery-level" not in result

    def test_parse_smartcar_signals_empty_signals_list(self):
        """Test parsing empty signals list."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        result = _parse_smartcar_signals([])
        assert result == {}

    def test_parse_smartcar_signals_invalid_input(self):
        """Test parsing with invalid input types."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        # Non-list input should return empty dict
        result = _parse_smartcar_signals("not a list")
        assert result == {}
        
        result = _parse_smartcar_signals(None)
        assert result == {}
        
        result = _parse_smartcar_signals({"dict": "instead of list"})
        assert result == {}

    def test_parse_smartcar_signals_missing_code(self):
        """Test parsing signal with missing code."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        signals = [
            {
                # Missing "code" field
                "name": "IsCharging",
                "body": True,
                "status": {"value": "SUCCESS"},
            },
            {
                "code": "charge-ischarging",
                "name": "IsCharging",
                "body": True,
                "status": {"value": "SUCCESS"},
            }
        ]
        
        result = _parse_smartcar_signals(signals)
        assert len(result) == 1
        assert "charge-ischarging" in result

    def test_parse_smartcar_signals_missing_body(self):
        """Test parsing signal with missing body."""
        from custom_components.nissan_na.webhook import _parse_smartcar_signals
        
        signals = [
            {
                "code": "charge-ischarging",
                "name": "IsCharging",
                # Missing "body" field
                "status": {"value": "SUCCESS"},
            },
            {
                "code": "battery-level",
                "name": "BatteryLevel",
                "body": 75,
                "status": {"value": "SUCCESS"},
            }
        ]
        
        result = _parse_smartcar_signals(signals)
        assert len(result) == 1
        assert "battery-level" in result
        assert "charge-ischarging" not in result



    """Test hash_challenge function."""

    def test_hash_challenge_generates_valid_hash(self):
        """Test hash_challenge generates valid HMAC-SHA256 hash."""
        from custom_components.nissan_na.webhook import hash_challenge
        
        management_token = "test_token_123"
        challenge = "test_challenge_xyz"
        
        result = hash_challenge(management_token, challenge)
        
        # Verify it matches expected HMAC-SHA256
        expected = hmac.new(
            management_token.encode("utf-8"),
            challenge.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        assert result == expected
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex is 64 chars

    def test_hash_challenge_different_challenges_different_hashes(self):
        """Test different challenges produce different hashes."""
        from custom_components.nissan_na.webhook import hash_challenge
        
        management_token = "test_token"
        challenge1 = "challenge_1"
        challenge2 = "challenge_2"
        
        hash1 = hash_challenge(management_token, challenge1)
        hash2 = hash_challenge(management_token, challenge2)
        
        assert hash1 != hash2

    def test_hash_challenge_same_challenge_same_hash(self):
        """Test same challenge with same token produces same hash."""
        from custom_components.nissan_na.webhook import hash_challenge
        
        management_token = "test_token"
        challenge = "test_challenge"
        
        hash1 = hash_challenge(management_token, challenge)
        hash2 = hash_challenge(management_token, challenge)
        
        assert hash1 == hash2


@pytest.mark.asyncio
class TestAsyncHandleWebhook:
    """Test async_handle_webhook function."""

    async def test_webhook_verify_event_success(self):
        """Test successful VERIFY event handling."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {
            "webhook_id": "test_webhook_id",
            "management_token": "test_management_token"
        }
        hass.config_entries.async_entries.return_value = [config_entry]
        
        challenge = "test_challenge_string"
        payload = {
            "eventType": "VERIFY",
            "vehicleId": "test_vehicle",
            "data": {"challenge": challenge}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {"SC-Signature": "test_sig"}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.OK
        assert isinstance(response, web.Response)

    async def test_webhook_verify_event_missing_challenge(self):
        """Test VERIFY event with missing challenge."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {
            "webhook_id": "test_webhook_id",
            "management_token": "test_token"
        }
        hass.config_entries.async_entries.return_value = [config_entry]
        
        payload = {
            "eventType": "VERIFY",
            "vehicleId": "test_vehicle",
            "data": {}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.BAD_REQUEST

    async def test_webhook_verify_event_no_management_token(self):
        """Test VERIFY event without management token."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {"webhook_id": "test_webhook_id"}
        hass.config_entries.async_entries.return_value = [config_entry]
        
        payload = {
            "eventType": "VERIFY",
            "vehicleId": "test_vehicle",
            "data": {"challenge": "test_challenge"}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR

    async def test_webhook_no_config_entry_found(self):
        """Test webhook handler when no config entry found."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        hass.config_entries.async_entries.return_value = []
        
        payload = {"eventType": "VERIFY", "vehicleId": "test"}
        body_bytes = json.dumps(payload).encode("utf-8")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {}
        
        response = await async_handle_webhook(hass, "unknown_webhook", request)
        
        assert response.status == HTTPStatus.NOT_FOUND

    async def test_webhook_invalid_json_payload(self):
        """Test webhook with invalid JSON payload."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {"webhook_id": "test_webhook_id", "management_token": "token"}
        hass.config_entries.async_entries.return_value = [config_entry]
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = b'invalid json {'
        request.headers = {}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.BAD_REQUEST

    async def test_webhook_vehicle_state_event(self):
        """Test VEHICLE_STATE event handling."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {
            "webhook_id": "test_webhook_id",
            "management_token": "test_token"
        }
        hass.config_entries.async_entries.return_value = [config_entry]
        
        vehicle_id = "vehicle_123"
        payload = {
            "eventType": "VEHICLE_STATE",
            "vehicleId": vehicle_id,
            "data": {"battery": 85, "location": {"latitude": 10.0, "longitude": 20.0}}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        # Create valid signature
        management_token = "test_token"
        signature = hmac.new(
            management_token.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {"SC-Signature": signature}
        
        with patch("custom_components.nissan_na.webhook.async_dispatcher_send") as mock_dispatch:
            response = await async_handle_webhook(hass, "test_webhook_id", request)
            
            assert response.status == HTTPStatus.OK
            mock_dispatch.assert_called_once()
            call_args = mock_dispatch.call_args
            assert vehicle_id in call_args[0][1]

    async def test_webhook_vehicle_error_event(self):
        """Test VEHICLE_ERROR event handling."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {
            "webhook_id": "test_webhook_id",
            "management_token": "test_token"
        }
        hass.config_entries.async_entries.return_value = [config_entry]
        
        vehicle_id = "vehicle_123"
        payload = {
            "eventType": "VEHICLE_ERROR",
            "vehicleId": vehicle_id,
            "data": {"error": "Unauthorized"}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        # Create valid signature
        management_token = "test_token"
        signature = hmac.new(
            management_token.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {"SC-Signature": signature}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.OK

    async def test_webhook_unknown_event_type(self):
        """Test webhook with unknown event type."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {
            "webhook_id": "test_webhook_id",
            "management_token": "test_token"
        }
        hass.config_entries.async_entries.return_value = [config_entry]
        
        payload = {
            "eventType": "UNKNOWN_EVENT",
            "vehicleId": "vehicle_123",
            "data": {}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        # Create valid signature
        management_token = "test_token"
        signature = hmac.new(
            management_token.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {"SC-Signature": signature}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.OK

    async def test_webhook_missing_signature_header(self):
        """Test webhook request missing SC-Signature header (non-VERIFY)."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {
            "webhook_id": "test_webhook_id",
            "management_token": "test_token"
        }
        hass.config_entries.async_entries.return_value = [config_entry]
        
        payload = {
            "eventType": "VEHICLE_STATE",
            "vehicleId": "vehicle_123",
            "data": {}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.UNAUTHORIZED

    async def test_webhook_invalid_signature(self):
        """Test webhook with invalid signature."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {
            "webhook_id": "test_webhook_id",
            "management_token": "test_token"
        }
        hass.config_entries.async_entries.return_value = [config_entry]
        
        payload = {
            "eventType": "VEHICLE_STATE",
            "vehicleId": "vehicle_123",
            "data": {}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {"SC-Signature": "invalid_signature"}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.UNAUTHORIZED

    async def test_webhook_no_management_token_for_signature_verification(self):
        """Test webhook without management token for signature verification."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {"webhook_id": "test_webhook_id"}
        hass.config_entries.async_entries.return_value = [config_entry]
        
        payload = {
            "eventType": "VEHICLE_STATE",
            "vehicleId": "vehicle_123",
            "data": {}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {"SC-Signature": "test_sig"}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR

    async def test_webhook_exception_handling(self):
        """Test exception handling in webhook."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        hass.config_entries.async_entries.side_effect = Exception("Test exception")
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = b'{}'
        request.headers = {}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        # Exception is caught and returns OK to prevent retries
        assert response.status == HTTPStatus.OK

    async def test_webhook_unicode_decode_error(self):
        """Test webhook with invalid UTF-8 encoding."""
        from custom_components.nissan_na.webhook import async_handle_webhook
        
        hass = Mock()
        config_entry = MagicMock()
        config_entry.data = {"webhook_id": "test_webhook_id"}
        hass.config_entries.async_entries.return_value = [config_entry]
        
        # Invalid UTF-8 sequence
        body_bytes = b'\x80\x81\x82\x83'
        
        request = AsyncMock(spec=web.Request)
        request.read.return_value = body_bytes
        request.headers = {}
        
        response = await async_handle_webhook(hass, "test_webhook_id", request)
        
        assert response.status == HTTPStatus.BAD_REQUEST


class TestAsyncRegisterWebhook:
    """Test async_register_webhook function."""

    def test_register_webhook_success(self):
        """Test successful webhook registration."""
        from custom_components.nissan_na.webhook import async_register_webhook
        
        hass = Mock()
        
        with patch("custom_components.nissan_na.webhook.webhook") as mock_webhook:
            async_register_webhook(hass, "entry_123", "webhook_123")
            
            mock_webhook.async_register.assert_called_once()
            call_args = mock_webhook.async_register.call_args[0]
            assert call_args[0] == hass
            assert call_args[3] == "webhook_123"  # webhook_id is 4th argument

    def test_register_webhook_already_exists(self):
        """Test webhook registration when already registered."""
        from custom_components.nissan_na.webhook import async_register_webhook
        
        hass = Mock()
        
        with patch("custom_components.nissan_na.webhook.webhook") as mock_webhook:
            mock_webhook.async_register.side_effect = ValueError("Already registered")
            
            # Should not raise exception
            async_register_webhook(hass, "entry_123", "webhook_123")
            
            mock_webhook.async_register.assert_called_once()


class TestAsyncUnregisterWebhook:
    """Test async_unregister_webhook function."""

    def test_unregister_webhook(self):
        """Test webhook unregistration."""
        from custom_components.nissan_na.webhook import async_unregister_webhook
        
        hass = Mock()
        
        with patch("custom_components.nissan_na.webhook.webhook") as mock_webhook:
            async_unregister_webhook(hass, "webhook_123")
            
            mock_webhook.async_unregister.assert_called_once_with(hass, "webhook_123")

    def test_unregister_webhook_multiple_calls(self):
        """Test unregistering multiple webhooks."""
        from custom_components.nissan_na.webhook import async_unregister_webhook
        
        hass = Mock()
        
        with patch("custom_components.nissan_na.webhook.webhook") as mock_webhook:
            async_unregister_webhook(hass, "webhook_1")
            async_unregister_webhook(hass, "webhook_2")
            
            assert mock_webhook.async_unregister.call_count == 2


class TestAsyncGenerateWebhookUrl:
    """Test async_generate_webhook_url function."""

    def test_generate_webhook_url(self):
        """Test webhook URL generation."""
        from custom_components.nissan_na.webhook import async_generate_webhook_url
        
        hass = Mock()
        expected_url = "https://example.com/api/webhook/test_webhook_123"
        
        with patch("custom_components.nissan_na.webhook.webhook") as mock_webhook:
            mock_webhook.async_generate_url.return_value = expected_url
            
            url = async_generate_webhook_url(hass, "test_webhook_123")
            
            assert url == expected_url
            mock_webhook.async_generate_url.assert_called_once_with(
                hass, "test_webhook_123", prefer_external=True
            )

    def test_generate_webhook_url_returns_external_preference(self):
        """Test webhook URL generation prefers external."""
        from custom_components.nissan_na.webhook import async_generate_webhook_url
        
        hass = Mock()
        
        with patch("custom_components.nissan_na.webhook.webhook") as mock_webhook:
            mock_webhook.async_generate_url.return_value = "https://external.url"
            
            async_generate_webhook_url(hass, "webhook_id")
            
            call_kwargs = mock_webhook.async_generate_url.call_args[1]
            assert call_kwargs.get("prefer_external") is True