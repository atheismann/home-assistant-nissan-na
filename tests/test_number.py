"""Unit tests for number platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.components.number import NumberEntity
from custom_components.nissan_na.number import (
    NissanChargeLimitNumber,
    async_setup_entry,
)
from custom_components.nissan_na.const import DOMAIN


@pytest.mark.asyncio
class TestAsyncSetupEntry:
    """Test async_setup_entry function for number platform."""

    async def test_setup_with_charge_control_permission(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup creates charge limit number with permission."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.limit"])
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        assert len(entities) == 1
        assert isinstance(entities[0], NissanChargeLimitNumber)

    async def test_setup_without_permission(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup skips charge limit without permission."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.limit"])
        mock_client.get_permissions = AsyncMock(return_value=["read_battery"])  # No control_charge
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        assert len(entities) == 0

    async def test_setup_without_signal(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup skips charge limit without signal."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["battery.percentRemaining"])  # No charge.limit
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        assert len(entities) == 0


class TestNissanChargeLimitNumber:
    """Test NissanChargeLimitNumber class."""

    def test_number_initialization_with_nickname(self, mock_hass, mock_vehicle, mock_client):
        """Test number initialization with vehicle nickname."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        assert number._attr_name == "Test Vehicle Charge Limit"
        assert number._attr_unique_id == "VIN123ABC_charge_limit"
        assert number._value == 80  # Default value

    def test_number_initialization_without_nickname(self, mock_hass, mock_vehicle_no_nickname, mock_client):
        """Test number initialization with year/make/model."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle_no_nickname,
            mock_client,
            "test_entry",
        )
        
        assert number._attr_name == "2024 NISSAN ARIYA Charge Limit"

    def test_number_properties(self, mock_hass, mock_vehicle, mock_client):
        """Test number entity properties."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        assert number.native_value == 80
        assert number.native_min_value == 0
        assert number.native_max_value == 100
        assert number.native_step == 1
        assert number.native_unit_of_measurement == "%"
        assert number.icon == "mdi:battery-charging-100"
        assert number.available is True

    def test_number_device_info(self, mock_hass, mock_vehicle, mock_client):
        """Test number entity device info."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        device_info = number.device_info
        assert (DOMAIN, mock_vehicle.vin) in device_info["identifiers"]

    @pytest.mark.asyncio
    async def test_async_added_to_hass(self, mock_hass, mock_vehicle, mock_client):
        """Test number subscribes to webhook updates."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        with patch("custom_components.nissan_na.number.async_dispatcher_connect") as mock_connect:
            await number.async_added_to_hass()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_will_remove_from_hass(self, mock_hass, mock_vehicle, mock_client):
        """Test number unsubscribes from webhook updates."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        mock_unsub = MagicMock()
        number._unsub_dispatcher = mock_unsub
        
        await number.async_will_remove_from_hass()
        mock_unsub.assert_called_once()

    def test_handle_webhook_data(self, mock_hass, mock_vehicle, mock_client):
        """Test handling webhook data updates."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        # Mock async_write_ha_state to avoid entity_id validation
        number.async_write_ha_state = MagicMock()
        
        # Initial value
        assert number._value == 80
        
        # Update via webhook
        webhook_data = {"charge": {"limit": 90}}
        number._handle_webhook_data(webhook_data)
        
        assert number._value == 90.0
        # Verify state update was called
        number.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_invalid(self, mock_hass, mock_vehicle, mock_client):
        """Test handling invalid webhook data."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        initial_value = number._value
        
        # Invalid data types
        number._handle_webhook_data(None)
        assert number._value == initial_value
        
        number._handle_webhook_data("invalid")
        assert number._value == initial_value
        
        number._handle_webhook_data({"charge": "invalid"})
        assert number._value == initial_value

    @pytest.mark.asyncio
    async def test_async_set_value_success(self, mock_hass, mock_vehicle, mock_client):
        """Test setting charge limit successfully."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        # Mock async_write_ha_state
        number.async_write_ha_state = MagicMock()
        # Mock the access token
        mock_client.access_token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            await number.async_set_value(85.0)
        
        assert number._value == 85
        number.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_value_clamps_to_range(self, mock_hass, mock_vehicle, mock_client):
        """Test setting charge limit clamps to valid range."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        # Mock async_write_ha_state
        number.async_write_ha_state = MagicMock()
        # Mock the access token
        mock_client.access_token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Test upper bound
            await number.async_set_value(150.0)
            assert number._value == 100
            
            # Test lower bound
            await number.async_set_value(-10.0)
            assert number._value == 0

    @pytest.mark.asyncio
    async def test_async_set_value_failure(self, mock_hass, mock_vehicle, mock_client):
        """Test setting charge limit handles failure."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        # Mock async_write_ha_state
        number.async_write_ha_state = MagicMock()
        # Mock the access token
        mock_client.access_token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            await number.async_set_value(90.0)
        
        assert number._available is False

    @pytest.mark.asyncio
    async def test_async_set_value_exception(self, mock_hass, mock_vehicle, mock_client):
        """Test setting charge limit handles exceptions."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        # Mock async_write_ha_state
        number.async_write_ha_state = MagicMock()
        
        with patch("aiohttp.ClientSession", side_effect=Exception("Connection error")):
            await number.async_set_value(90.0)
        
        assert number._available is False


class TestAsyncSetupEntryErrorHandling:
    """Test error handling in async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_handles_signal_fetch_error(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup handles error when fetching vehicle signals."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(side_effect=Exception("API error"))
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        # Should not raise and should create number (with empty available_signals)
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Empty signals means condition passes: (not available_signals) and permission granted
        assert len(entities) == 1
        assert isinstance(entities[0], NissanChargeLimitNumber)

    @pytest.mark.asyncio
    async def test_setup_handles_permission_fetch_error(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup handles error when fetching permissions."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.limit"])
        mock_client.get_permissions = AsyncMock(side_effect=Exception("API error"))
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        # Should handle gracefully and skip number (permissions empty = no control_charge)
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # No permission, so no entity created
        assert len(entities) == 0

    @pytest.mark.asyncio
    async def test_setup_with_multiple_vehicles(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup with multiple vehicles."""
        mock_vehicle2 = MagicMock()
        mock_vehicle2.id = "vehicle_456"
        mock_vehicle2.nickname = "Second Vehicle"
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle, mock_vehicle2])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.limit"])
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create one number for each vehicle
        assert len(entities) == 2
        assert all(isinstance(e, NissanChargeLimitNumber) for e in entities)
        vehicle_ids = {e._vehicle.id for e in entities}
        assert mock_vehicle.id in vehicle_ids
        assert mock_vehicle2.id in vehicle_ids

    @pytest.mark.asyncio
    async def test_setup_webhook_subscription(self, mock_hass, mock_config_entry, mock_vehicle, mock_client):
        """Test setup subscribes to webhook signals."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_vehicle_signals = AsyncMock(return_value=["charge.limit"])
        mock_client.get_permissions = AsyncMock(return_value=["control_charge"])
        
        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {"client": mock_client, "numbers": {}}}}
        mock_hass.async_create_task = MagicMock()
        
        dispatcher_calls = []
        def mock_dispatcher_connect(hass, signal, callback):
            dispatcher_calls.append((signal, callback))
            return MagicMock()
        
        entities = []
        def async_add_entities(new_entities):
            """Sync callback for adding entities."""
            entities.extend(new_entities)
        
        with patch("custom_components.nissan_na.number.async_dispatcher_connect", side_effect=mock_dispatcher_connect):
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should subscribe to webhook signal
        webhook_signals = [call[0] for call in dispatcher_calls if "nissan_na_webhook_data" in call[0]]
        assert len(webhook_signals) > 0


class TestNumberWebhookHandling:
    """Test webhook handling in number entities."""

    def test_handle_webhook_data_with_partial_charge_info(self, mock_hass, mock_vehicle, mock_client):
        """Test webhook data with charge but no limit field."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        number.async_write_ha_state = MagicMock()
        initial_value = number._value
        
        # Charge data without limit
        webhook_data = {"charge": {"state": "CHARGING"}}
        number._handle_webhook_data(webhook_data)
        
        # Value should not change
        assert number._value == initial_value
        # State update should not be called
        number.async_write_ha_state.assert_not_called()

    def test_handle_webhook_data_same_value(self, mock_hass, mock_vehicle, mock_client):
        """Test webhook data with same charge limit value."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        number.async_write_ha_state = MagicMock()
        number._value = 80
        
        # Update with same value
        webhook_data = {"charge": {"limit": 80}}
        number._handle_webhook_data(webhook_data)
        
        # State update should not be called when value unchanged
        number.async_write_ha_state.assert_not_called()

    def test_handle_webhook_data_empty_dict(self, mock_hass, mock_vehicle, mock_client):
        """Test webhook data with empty dict."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        number.async_write_ha_state = MagicMock()
        initial_value = number._value
        
        # Empty webhook data
        webhook_data = {}
        number._handle_webhook_data(webhook_data)
        
        # Value should not change
        assert number._value == initial_value
        number.async_write_ha_state.assert_not_called()


class TestNumberPropertiesAndAttributes:
    """Test number entity properties and attributes."""

    def test_native_min_max_step_values(self, mock_hass, mock_vehicle, mock_client):
        """Test min/max/step property values."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        assert number.native_min_value == 0
        assert number.native_max_value == 100
        assert number.native_step == 1
        assert number.native_unit_of_measurement == "%"

    def test_icon_attribute(self, mock_hass, mock_vehicle, mock_client):
        """Test icon attribute."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        assert number.icon == "mdi:battery-charging-100"

    def test_unique_id_format(self, mock_hass, mock_vehicle, mock_client):
        """Test unique ID is correctly formatted."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        expected_id = f"{mock_vehicle.vin}_charge_limit"
        assert number.unique_id == expected_id

    def test_name_format_with_nickname(self, mock_hass, mock_vehicle, mock_client):
        """Test name is correctly formatted with nickname."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        assert number.name == f"{mock_vehicle.nickname} Charge Limit"

    def test_available_property_changes(self, mock_hass, mock_vehicle, mock_client):
        """Test available property can be changed."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        assert number.available is True
        
        number._available = False
        assert number.available is False

    @pytest.mark.asyncio
    async def test_async_set_value_with_204_response(self, mock_hass, mock_vehicle, mock_client):
        """Test async_set_value handles 204 (No Content) response."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        number.async_write_ha_state = MagicMock()
        mock_client.access_token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            await number.async_set_value(75.0)
        
        assert number._value == 75
        assert number._available is True
        number.async_write_ha_state.assert_called()
