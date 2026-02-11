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
        async def async_add_entities(new_entities):
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
        async def async_add_entities(new_entities):
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
        async def async_add_entities(new_entities):
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
        
        assert number._attr_name == "My Nissan Charge Limit"
        assert number.unique_id == "TEST1234567890123_charge_limit"
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
        
        # Initial value
        assert number._value == 80
        
        # Update via webhook
        webhook_data = {"charge": {"limit": 90}}
        number._handle_webhook_data(webhook_data)
        
        assert number._value == 90.0

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
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            await number.async_set_value(85.0)
        
        assert number._value == 85

    @pytest.mark.asyncio
    async def test_async_set_value_clamps_to_range(self, mock_hass, mock_vehicle, mock_client):
        """Test setting charge limit clamps to valid range."""
        number = NissanChargeLimitNumber(
            mock_hass,
            mock_vehicle,
            mock_client,
            "test_entry",
        )
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
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
        
        mock_response = MagicMock()
        mock_response.status = 500
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
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
        
        with patch("aiohttp.ClientSession", side_effect=Exception("Connection error")):
            await number.async_set_value(90.0)
        
        assert number._available is False
