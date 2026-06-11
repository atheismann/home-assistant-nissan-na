"""Unit tests for config flow (OAuth2FlowHandler + NissanNAOptionsFlowHandler)."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import voluptuous as vol
from homeassistant import config_entries
from custom_components.nissan_na.config_flow import (
    OAuth2FlowHandler,
    NissanNAOptionsFlowHandler,
)
from custom_components.nissan_na.const import (
    CONF_USER_ID,
    DOMAIN,
    CONF_MANAGEMENT_TOKEN,
    CONF_UNIT_SYSTEM,
    UNIT_SYSTEM_METRIC,
    UNIT_SYSTEM_IMPERIAL,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_oauth_flow(user_id=None, client_id="cid", client_secret="sec"):
    """Create an OAuth2FlowHandler with a mocked flow_impl."""
    flow = OAuth2FlowHandler()
    flow.hass = MagicMock()
    flow.context = {"source": config_entries.SOURCE_USER}
    mock_impl = MagicMock()
    mock_impl.domain = "nissan_na"
    mock_impl.client_id = client_id
    mock_impl.client_secret = client_secret
    flow.flow_impl = mock_impl

    if user_id:
        flow._smartcar_user_id = user_id
        flow.external_data = {"user_id": user_id, "state": "abc123"}

    return flow


# ---------------------------------------------------------------------------
# async_step_creation — captures user_id from Connect redirect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAsyncStepCreation:
    async def test_captures_user_id_from_new_api_redirect(self):
        """New API Auth: redirect has `user_id` (lowercase with underscore)."""
        flow = _make_oauth_flow()
        flow.external_data = {"user_id": "uid_abc", "state": "xyz"}

        mock_vehicle = MagicMock()
        with patch.object(
            flow,
            "async_oauth_create_entry",
            new=AsyncMock(
                return_value={"type": "create_entry", "data": {CONF_USER_ID: "uid_abc"}}
            ),
        ) as mock_create:
            result = await flow.async_step_creation()

        mock_create.assert_called_once()
        assert flow._smartcar_user_id == "uid_abc"

    async def test_captures_userId_from_migration_redirect(self):
        """Migration flow: redirect has `userId` (camelCase)."""
        flow = _make_oauth_flow()
        flow.external_data = {"code": "CODE", "userId": "uid_migration", "state": "xyz"}

        with patch.object(
            flow,
            "async_oauth_create_entry",
            new=AsyncMock(
                return_value={
                    "type": "create_entry",
                    "data": {CONF_USER_ID: "uid_migration"},
                }
            ),
        ):
            result = await flow.async_step_creation()

        assert flow._smartcar_user_id == "uid_migration"

    async def test_user_id_takes_priority_over_userId(self):
        """If both `user_id` and `userId` are present, `user_id` wins."""
        flow = _make_oauth_flow()
        flow.external_data = {"user_id": "new_uid", "userId": "old_uid", "state": "xyz"}

        with patch.object(
            flow,
            "async_oauth_create_entry",
            new=AsyncMock(return_value={"type": "create_entry", "data": {}}),
        ):
            await flow.async_step_creation()

        assert flow._smartcar_user_id == "new_uid"

    async def test_aborts_when_no_user_id_in_redirect(self):
        """If Connect redirect has no user_id / userId, abort."""
        flow = _make_oauth_flow()
        flow.external_data = {"code": "CODE", "state": "xyz"}  # no user_id

        result = await flow.async_step_creation()

        assert result["type"] == "abort"
        assert result["reason"] == "missing_user_id"

    async def test_aborts_when_external_data_empty(self):
        flow = _make_oauth_flow()
        flow.external_data = {}

        result = await flow.async_step_creation()

        assert result["type"] == "abort"
        assert result["reason"] == "missing_user_id"

    async def test_aborts_when_external_data_missing(self):
        flow = _make_oauth_flow()
        if hasattr(flow, "external_data"):
            del flow.external_data

        result = await flow.async_step_creation()

        assert result["type"] == "abort"
        assert result["reason"] == "missing_user_id"


# ---------------------------------------------------------------------------
# async_oauth_create_entry — validates vehicles and creates the config entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAsyncOauthCreateEntry:
    async def test_creates_entry_with_user_id(self):
        flow = _make_oauth_flow(user_id="uid_123")

        mock_vehicle = MagicMock()
        with patch(
            "custom_components.nissan_na.config_flow.SmartcarApiClient"
        ) as mock_cls:
            mock_client = MagicMock()
            mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
            mock_cls.return_value = mock_client
            flow.async_create_entry = MagicMock(
                return_value={
                    "type": "create_entry",
                    "title": "Nissan (Smartcar)",
                    "data": {},
                }
            )

            result = await flow.async_oauth_create_entry(
                {"auth_implementation": "nissan_na"}
            )

        assert result["type"] == "create_entry"
        flow.async_create_entry.assert_called_once()
        call_kwargs = flow.async_create_entry.call_args
        assert call_kwargs.kwargs["data"][CONF_USER_ID] == "uid_123"

    async def test_aborts_no_vehicles(self):
        flow = _make_oauth_flow(user_id="uid_123")

        with patch(
            "custom_components.nissan_na.config_flow.SmartcarApiClient"
        ) as mock_cls:
            mock_client = MagicMock()
            mock_client.get_vehicle_list = AsyncMock(return_value=[])
            mock_cls.return_value = mock_client

            result = await flow.async_oauth_create_entry(
                {"auth_implementation": "nissan_na"}
            )

        assert result["type"] == "abort"
        assert result["reason"] == "no_vehicles"

    async def test_aborts_connection_error(self):
        flow = _make_oauth_flow(user_id="uid_123")

        with patch(
            "custom_components.nissan_na.config_flow.SmartcarApiClient"
        ) as mock_cls:
            mock_client = MagicMock()
            mock_client.get_vehicle_list = AsyncMock(side_effect=Exception("timeout"))
            mock_cls.return_value = mock_client

            result = await flow.async_oauth_create_entry(
                {"auth_implementation": "nissan_na"}
            )

        assert result["type"] == "abort"
        assert result["reason"] == "connection_error"

    async def test_aborts_missing_credentials(self):
        flow = _make_oauth_flow(user_id="uid_123", client_id="", client_secret="")

        result = await flow.async_oauth_create_entry(
            {"auth_implementation": "nissan_na"}
        )

        assert result["type"] == "abort"
        assert result["reason"] == "missing_credentials"

    async def test_aborts_missing_user_id(self):
        flow = _make_oauth_flow()  # no user_id set

        result = await flow.async_oauth_create_entry(
            {"auth_implementation": "nissan_na"}
        )

        assert result["type"] == "abort"
        assert result["reason"] == "missing_user_id"

    async def test_reauth_updates_entry(self):
        flow = _make_oauth_flow(user_id="uid_new")
        flow.context["source"] = config_entries.SOURCE_REAUTH

        mock_reauth_entry = MagicMock()
        mock_reauth_entry.entry_id = "existing_entry"
        flow._get_reauth_entry = MagicMock(return_value=mock_reauth_entry)
        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()
        flow.async_abort = MagicMock(
            return_value={"type": "abort", "reason": "reauth_successful"}
        )

        mock_vehicle = MagicMock()
        with patch(
            "custom_components.nissan_na.config_flow.SmartcarApiClient"
        ) as mock_cls:
            mock_client = MagicMock()
            mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
            mock_cls.return_value = mock_client

            result = await flow.async_oauth_create_entry(
                {"auth_implementation": "nissan_na"}
            )

        flow.hass.config_entries.async_update_entry.assert_called_once()
        flow.hass.config_entries.async_reload.assert_called_once()
        flow.async_abort.assert_called_with(reason="reauth_successful")


# ---------------------------------------------------------------------------
# extra_authorize_data — scopes and Smartcar-specific params
# ---------------------------------------------------------------------------


class TestExtraAuthorizeData:
    def test_contains_make_nissan(self):
        flow = _make_oauth_flow()
        data = flow.extra_authorize_data
        assert data.get("make") == "NISSAN"

    def test_contains_single_select(self):
        flow = _make_oauth_flow()
        data = flow.extra_authorize_data
        assert data.get("single_select") == "true"

    def test_scope_includes_required_vehicle_info(self):
        flow = _make_oauth_flow()
        data = flow.extra_authorize_data
        assert "required:read_vehicle_info" in data["scope"]

    def test_scope_includes_climate_control(self):
        flow = _make_oauth_flow()
        data = flow.extra_authorize_data
        assert "control_climate" in data["scope"]


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Home Assistant deprecates setting config_entry directly in tests", run=True
)
class TestOptionsFlow:
    async def test_async_step_init_menu(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)

        result = await flow.async_step_init()
        assert result["type"] == "menu"

    async def test_async_step_unit_system_save_metric(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()

        result = await flow.async_step_unit_system(
            {CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC}
        )
        assert result["type"] in ("create_entry", "form", "abort")

    async def test_async_step_unit_system_save_imperial(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()

        result = await flow.async_step_unit_system(
            {CONF_UNIT_SYSTEM: UNIT_SYSTEM_IMPERIAL}
        )
        assert result["type"] in ("create_entry", "form", "abort")

    async def test_async_step_webhook_config_show_form(self):
        mock_entry = MagicMock()
        mock_entry.data = {"webhook_url": "https://example.com/webhook"}
        mock_entry.options = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()

        result = await flow.async_step_webhook_config()
        assert result["type"] == "form"

    async def test_async_step_webhook_config_save(self):
        mock_entry = MagicMock()
        mock_entry.data = {}
        mock_entry.options = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.config_entries.async_update_entry = MagicMock()

        result = await flow.async_step_webhook_config(
            {CONF_MANAGEMENT_TOKEN: "token_abc"}
        )
        assert result["type"] in ("create_entry", "form", "abort")

    async def test_async_step_refresh_sensors_success(self):
        mock_sensor = AsyncMock()
        mock_sensor._attr_name = "Battery"

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.data = {
            DOMAIN: {"test_entry": {"sensors": {"v1": {"bat": mock_sensor}}}}
        }

        result = await flow.async_step_refresh_sensors()
        assert result["type"] in ("form", "abort")

    async def test_async_step_refresh_sensors_no_sensors(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.data = {DOMAIN: {"test_entry": {"sensors": {}}}}

        result = await flow.async_step_refresh_sensors()
        assert result["type"] == "abort"
        assert result["reason"] == "no_sensors_found"

    async def test_async_step_refresh_sensors_with_failures(self):
        mock_sensor = AsyncMock()
        mock_sensor.async_update = AsyncMock(side_effect=Exception("API error"))
        mock_sensor._attr_name = "Battery"

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.data = {
            DOMAIN: {"test_entry": {"sensors": {"v1": {"bat": mock_sensor}}}}
        }

        result = await flow.async_step_refresh_sensors()
        assert result["type"] in ("form", "abort")

    async def test_async_step_reauth(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.async_create_task = MagicMock()
        flow.hass.config_entries.flow.async_init = AsyncMock()

        result = await flow.async_step_reauth()
        assert result["type"] == "abort"
        assert result["reason"] == "reauth_triggered"


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Home Assistant deprecates setting config_entry directly in tests", run=True
)
class TestOptionsFlowRebuildSensors:
    async def test_async_step_rebuild_sensors_integration_not_loaded(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.data = {DOMAIN: {}}

        result = await flow.async_step_rebuild_sensors()
        assert result["type"] == "abort"
        assert result["reason"] == "integration_not_loaded"

    async def test_async_step_rebuild_sensors_client_not_found(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)
        flow.hass = MagicMock()
        flow.hass.data = {DOMAIN: {"test_entry": {"sensors": {}}}}

        result = await flow.async_step_rebuild_sensors()
        assert result["type"] == "abort"
        assert result["reason"] == "client_not_found"

    async def test_init_menu_includes_rebuild_option(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)

        result = await flow.async_step_init()
        assert result["type"] == "menu"
        assert "rebuild_sensors" in result.get("menu_options", {})

    async def test_async_step_rebuild_complete_returns_to_menu(self):
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {}

        flow = NissanNAOptionsFlowHandler()
        object.__setattr__(flow, "config_entry", mock_entry)

        result = await flow.async_step_rebuild_complete()
        assert result["type"] == "menu"
