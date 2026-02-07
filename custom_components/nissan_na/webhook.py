"""Webhook support for Smartcar integration."""

import hashlib
import hmac
import logging
from http import HTTPStatus

from aiohttp import web
from homeassistant.components import webhook
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

_LOGGER = logging.getLogger(__name__)

CONF_MANAGEMENT_TOKEN = "management_token"
WEBHOOK_ID_KEY = "webhook_id"

# Smartcar webhook event types
EVENT_TYPE_VERIFY = "VERIFY"
EVENT_TYPE_VEHICLE_STATE = "VEHICLE_STATE"
EVENT_TYPE_VEHICLE_ERROR = "VEHICLE_ERROR"

# Signal for webhook data updates
SIGNAL_WEBHOOK_DATA = "nissan_na_webhook_data"


def verify_signature(management_token: str, signature: str, body_bytes: bytes) -> bool:
    """Verify the webhook signature from Smartcar.

    Args:
        management_token: The Smartcar Application Management Token
        signature: The SC-Signature header value from the webhook request
        body_bytes: The raw request body bytes

    Returns:
        True if signature is valid, False otherwise
    """
    if not management_token or not signature:
        return False

    # Create HMAC-SHA256 hash of the body using management token as secret
    expected_signature = hmac.new(
        management_token.encode("utf-8"), body_bytes, hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


def hash_challenge(management_token: str, challenge: str) -> str:
    """Hash the challenge string for webhook verification.

    Args:
        management_token: The Smartcar Application Management Token
        challenge: The challenge string from the VERIFY event

    Returns:
        HMAC-SHA256 hash of the challenge
    """
    return hmac.new(
        management_token.encode("utf-8"), challenge.encode("utf-8"), hashlib.sha256
    ).hexdigest()


async def async_handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request: web.Request,
) -> web.Response:
    """Handle incoming webhook from Smartcar.

    Handles three event types:
    1. VERIFY - Initial webhook URL verification challenge
    2. VEHICLE_STATE - Vehicle data updates when triggers fire
    3. VEHICLE_ERROR - Error notifications from Smartcar
    """
    try:
        # Get management token from config
        # The integration that registered this webhook should store it
        from .const import DOMAIN

        entry = None
        for config_entry in hass.config_entries.async_entries(DOMAIN):
            if config_entry.data.get(CONF_WEBHOOK_ID) == webhook_id:
                entry = config_entry
                break

        if not entry:
            _LOGGER.error("No config entry found for webhook %s", webhook_id)
            return web.Response(status=HTTPStatus.NOT_FOUND)

        management_token = entry.data.get(CONF_MANAGEMENT_TOKEN)

        # Read raw body for signature verification
        body_bytes = await request.read()

        # Parse JSON payload
        try:
            import json

            payload = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            _LOGGER.error("Invalid JSON payload: %s", err)
            return web.Response(status=HTTPStatus.BAD_REQUEST)

        event_type = payload.get("eventType")

        # Handle VERIFY event (no signature verification needed for initial setup)
        if event_type == EVENT_TYPE_VERIFY:
            if not management_token:
                _LOGGER.error(
                    "Management token not configured for webhook verification"
                )
                return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

            challenge = payload.get("data", {}).get("challenge")
            if not challenge:
                _LOGGER.error("No challenge in VERIFY webhook payload")
                return web.Response(status=HTTPStatus.BAD_REQUEST)

            # Hash the challenge and return it
            challenge_hash = hash_challenge(management_token, challenge)
            _LOGGER.debug("Webhook VERIFY challenge received and hashed")

            return web.json_response({"challenge": challenge_hash})

        # For all other events, verify the signature
        signature = request.headers.get("SC-Signature")
        if not signature:
            _LOGGER.warning("Missing SC-Signature header in webhook request")
            return web.Response(status=HTTPStatus.UNAUTHORIZED)

        if not management_token:
            _LOGGER.error(
                "Management token not configured, cannot verify webhook signature"
            )
            return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

        if not verify_signature(management_token, signature, body_bytes):
            _LOGGER.warning("Invalid webhook signature")
            return web.Response(status=HTTPStatus.UNAUTHORIZED)

        # Process the webhook event
        _LOGGER.debug("Received %s webhook event", event_type)

        if event_type == EVENT_TYPE_VEHICLE_STATE:
            # Extract vehicle data and dispatch to coordinators
            vehicle_id = payload.get("vehicleId")
            data = payload.get("data", {})

            _LOGGER.debug("Vehicle state update for %s: %s", vehicle_id, data)

            # Send signal to update coordinators
            async_dispatcher_send(hass, f"{SIGNAL_WEBHOOK_DATA}_{vehicle_id}", data)

        elif event_type == EVENT_TYPE_VEHICLE_ERROR:
            # Log errors from Smartcar
            vehicle_id = payload.get("vehicleId")
            error_data = payload.get("data", {})

            _LOGGER.warning("Vehicle error for %s: %s", vehicle_id, error_data)

        else:
            _LOGGER.debug("Unknown event type: %s", event_type)

        # Always return 200 to acknowledge receipt
        return web.Response(status=HTTPStatus.OK)

    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Error processing Smartcar webhook")
        # Still return 200 to prevent retries on our errors
        return web.Response(status=HTTPStatus.OK)


def async_register_webhook(
    hass: HomeAssistant,
    entry_id: str,
    webhook_id: str,
) -> None:
    """Register the webhook for this integration entry.

    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID (for webhook name)
        webhook_id: Unique webhook ID
    """
    from .const import DOMAIN

    webhook.async_register(
        hass,
        DOMAIN,
        "Nissan NA Smartcar",
        webhook_id,
        async_handle_webhook,
    )

    _LOGGER.debug("Registered Smartcar webhook: %s", webhook_id)


def async_unregister_webhook(
    hass: HomeAssistant,
    webhook_id: str,
) -> None:
    """Unregister the webhook.

    Args:
        hass: Home Assistant instance
        webhook_id: Webhook ID to unregister
    """
    webhook.async_unregister(hass, webhook_id)
    _LOGGER.debug("Unregistered Smartcar webhook: %s", webhook_id)


def async_generate_webhook_url(hass: HomeAssistant, webhook_id: str) -> str:
    """Generate the full webhook URL.

    Args:
        hass: Home Assistant instance
        webhook_id: Webhook ID

    Returns:
        Full HTTPS URL for the webhook
    """
    return webhook.async_generate_url(hass, webhook_id, prefer_external=True)
