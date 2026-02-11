"""Tests for webhook module."""
import pytest
import hmac
import hashlib


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
