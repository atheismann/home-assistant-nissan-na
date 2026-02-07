"""Tests for webhook functionality."""

import hashlib
import hmac
import json
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nissan_na.const import DOMAIN
from custom_components.nissan_na.webhook import (
    CONF_MANAGEMENT_TOKEN,
    EVENT_TYPE_VEHICLE_ERROR,
    EVENT_TYPE_VEHICLE_STATE,
    EVENT_TYPE_VERIFY,
    SIGNAL_WEBHOOK_DATA,
    async_handle_webhook,
    async_register_webhook,
    async_unregister_webhook,
    hash_challenge,
    verify_signature,
)


def test_verify_signature_valid():
    """Test signature verification with valid signature."""
    token = "test_management_token"
    body = b'{"test": "data"}'

    # Create valid signature
    signature = hmac.new(token.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(token, signature, body) is True


def test_verify_signature_invalid():
    """Test signature verification with invalid signature."""
    token = "test_management_token"
    body = b'{"test": "data"}'
    invalid_signature = "invalid_signature_here"

    assert verify_signature(token, invalid_signature, body) is False


def test_verify_signature_no_token():
    """Test signature verification with missing token."""
    body = b'{"test": "data"}'
    signature = "some_signature"

    assert verify_signature("", signature, body) is False
    assert verify_signature(None, signature, body) is False


def test_verify_signature_no_signature():
    """Test signature verification with missing signature."""
    token = "test_management_token"
    body = b'{"test": "data"}'

    assert verify_signature(token, "", body) is False
    assert verify_signature(token, None, body) is False


def test_hash_challenge():
    """Test challenge hashing."""
    token = "test_management_token"
    challenge = "test_challenge_string"

    expected = hmac.new(token.encode(), challenge.encode(), hashlib.sha256).hexdigest()

    assert hash_challenge(token, challenge) == expected


async def test_webhook_verify_event(hass):
    """Test webhook VERIFY event handling."""
    token = "test_management_token"
    challenge = "test_challenge_123"

    # Create config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    # Create request with VERIFY event
    payload = {
        "eventType": EVENT_TYPE_VERIFY,
        "data": {"challenge": challenge},
    }
    body_bytes = json.dumps(payload).encode()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    assert response.status == HTTPStatus.OK
    response_text = response.body.decode()
    expected_hash = hash_challenge(token, challenge)
    assert expected_hash in response_text


async def test_webhook_verify_missing_challenge(hass):
    """Test webhook VERIFY event without challenge."""
    token = "test_management_token"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    payload = {
        "eventType": EVENT_TYPE_VERIFY,
        "data": {},
    }
    body_bytes = json.dumps(payload).encode()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    assert response.status == HTTPStatus.BAD_REQUEST


async def test_webhook_verify_no_management_token(hass):
    """Test webhook VERIFY event without management token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
        },
    )
    entry.add_to_hass(hass)

    payload = {
        "eventType": EVENT_TYPE_VERIFY,
        "data": {"challenge": "test_challenge"},
    }
    body_bytes = json.dumps(payload).encode()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_webhook_vehicle_state_event(hass):
    """Test webhook VEHICLE_STATE event handling."""
    token = "test_management_token"
    vehicle_id = "vehicle_123"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    payload = {
        "eventType": EVENT_TYPE_VEHICLE_STATE,
        "vehicleId": vehicle_id,
        "data": {"some": "data"},
    }
    body_bytes = json.dumps(payload).encode()
    signature = hmac.new(token.encode(), body_bytes, hashlib.sha256).hexdigest()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)
    request.headers = {"SC-Signature": signature}

    # Mock dispatcher
    with patch(
        "custom_components.nissan_na.webhook.async_dispatcher_send"
    ) as mock_dispatcher:
        response = await async_handle_webhook(hass, "test_webhook_id", request)

        assert response.status == HTTPStatus.OK
        mock_dispatcher.assert_called_once()
        call_args = mock_dispatcher.call_args[0]
        assert call_args[0] == hass
        assert SIGNAL_WEBHOOK_DATA in call_args[1]
        assert vehicle_id in call_args[1]  # Signal includes vehicle ID
        assert call_args[2] == {"some": "data"}  # Third arg is the data payload


async def test_webhook_vehicle_error_event(hass):
    """Test webhook VEHICLE_ERROR event handling."""
    token = "test_management_token"
    vehicle_id = "vehicle_123"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    payload = {
        "eventType": EVENT_TYPE_VEHICLE_ERROR,
        "vehicleId": vehicle_id,
        "error": {"type": "VEHICLE_DISCONNECTED"},
    }
    body_bytes = json.dumps(payload).encode()
    signature = hmac.new(token.encode(), body_bytes, hashlib.sha256).hexdigest()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)
    request.headers = {"SC-Signature": signature}

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    assert response.status == HTTPStatus.OK


async def test_webhook_invalid_signature(hass):
    """Test webhook with invalid signature."""
    token = "test_management_token"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    payload = {
        "eventType": EVENT_TYPE_VEHICLE_STATE,
        "vehicleId": "vehicle_123",
    }
    body_bytes = json.dumps(payload).encode()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)
    request.headers = {"SC-Signature": "invalid_signature"}

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_webhook_missing_signature(hass):
    """Test webhook without signature header."""
    token = "test_management_token"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    payload = {
        "eventType": EVENT_TYPE_VEHICLE_STATE,
        "vehicleId": "vehicle_123",
    }
    body_bytes = json.dumps(payload).encode()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)
    request.headers = {}

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_webhook_invalid_json(hass):
    """Test webhook with invalid JSON payload."""
    token = "test_management_token"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    body_bytes = b"invalid json {"

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)
    request.headers = {}

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    assert response.status == HTTPStatus.BAD_REQUEST


async def test_webhook_no_config_entry(hass):
    """Test webhook with no matching config entry."""
    payload = {"eventType": EVENT_TYPE_VERIFY}
    body_bytes = json.dumps(payload).encode()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)
    request.headers = {}

    response = await async_handle_webhook(hass, "nonexistent_webhook", request)

    assert response.status == HTTPStatus.NOT_FOUND


async def test_webhook_register(hass):
    """Test webhook registration."""
    entry_id = "test_entry_123"
    webhook_id = "test_webhook_id"

    with patch(
        "custom_components.nissan_na.webhook.webhook.async_register"
    ) as mock_register:
        async_register_webhook(hass, entry_id, webhook_id)

        # Verify registration was called
        mock_register.assert_called_once()


async def test_webhook_unregister(hass):
    """Test webhook unregistration."""
    webhook_id = "test_webhook_id"

    with patch(
        "custom_components.nissan_na.webhook.webhook.async_unregister"
    ) as mock_unregister:
        async_unregister_webhook(hass, webhook_id)

        # Verify unregistration was called
        mock_unregister.assert_called_once_with(hass, webhook_id)


async def test_webhook_unknown_event_type(hass):
    """Test webhook with unknown event type."""
    token = "test_management_token"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test_webhook_id",
            CONF_MANAGEMENT_TOKEN: token,
        },
    )
    entry.add_to_hass(hass)

    payload = {
        "eventType": "UNKNOWN_EVENT",
        "vehicleId": "vehicle_123",
    }
    body_bytes = json.dumps(payload).encode()
    signature = hmac.new(token.encode(), body_bytes, hashlib.sha256).hexdigest()

    request = MagicMock(spec=web.Request)
    request.read = AsyncMock(return_value=body_bytes)
    request.headers = {"SC-Signature": signature}

    response = await async_handle_webhook(hass, "test_webhook_id", request)

    # Should still return OK but log warning
    assert response.status == HTTPStatus.OK
