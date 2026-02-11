"""Integration tests for the Nissan NA integration."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from custom_components.nissan_na import async_setup_entry, async_unload_entry
from custom_components.nissan_na.const import DOMAIN, PLATFORMS


@pytest.mark.asyncio
class TestIntegrationSetup:
    """Test integration setup and unload."""

    async def test_async_setup_entry_success(self, mock_hass, mock_config_entry, mock_client):
        """Test successful integration setup."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[])
        
        with patch("custom_components.nissan_na.SmartcarApiClient", return_value=mock_client):
            with patch.object(mock_hass.config_entries, "async_forward_entry_setups", new=AsyncMock()) as mock_forward:
                result = await async_setup_entry(mock_hass, mock_config_entry)
                
                assert result is True
                assert DOMAIN in mock_hass.data
                assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
                mock_forward.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_async_setup_entry_stores_client(self, mock_hass, mock_config_entry, mock_client):
        """Test setup stores API client."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[])
        
        with patch("custom_components.nissan_na.SmartcarApiClient", return_value=mock_client):
            with patch.object(mock_hass.config_entries, "async_forward_entry_setups", new=AsyncMock()):
                await async_setup_entry(mock_hass, mock_config_entry)
                
                entry_data = mock_hass.data[DOMAIN][mock_config_entry.entry_id]
                assert "client" in entry_data
                assert entry_data["client"] == mock_client

    async def test_async_unload_entry_success(self, mock_hass, mock_config_entry):
        """Test successful integration unload."""
        # Setup initial data
        mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: {"client": MagicMock()}}
        
        with patch.object(mock_hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)) as mock_unload:
            result = await async_unload_entry(mock_hass, mock_config_entry)
            
            assert result is True
            assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
            mock_unload.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_async_unload_entry_failure(self, mock_hass, mock_config_entry):
        """Test integration unload handles failure."""
        mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: {"client": MagicMock()}}
        
        with patch.object(mock_hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=False)):
            result = await async_unload_entry(mock_hass, mock_config_entry)
            
            assert result is False
            # Data should still be present on failure
            assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
class TestWebhookRegistration:
    """Test webhook registration and handling."""

    async def test_webhook_registered_on_setup(self, mock_hass, mock_config_entry, mock_client):
        """Test webhook is registered during setup."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[])
        
        with patch("custom_components.nissan_na.SmartcarApiClient", return_value=mock_client):
            with patch.object(mock_hass.config_entries, "async_forward_entry_setups", new=AsyncMock()):
                with patch("custom_components.nissan_na.ha_webhook") as mock_webhook:
                    await async_setup_entry(mock_hass, mock_config_entry)
                    
                    # Verify webhook was registered
                    assert mock_webhook.async_register.called


@pytest.mark.asyncio
class TestFullIntegrationFlow:
    """Test full integration lifecycle."""

    async def test_complete_setup_and_unload_cycle(self, mock_hass, mock_config_entry, mock_client, mock_vehicle):
        """Test complete setup and unload cycle."""
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        
        # Setup
        with patch("custom_components.nissan_na.SmartcarApiClient", return_value=mock_client):
            with patch.object(mock_hass.config_entries, "async_forward_entry_setups", new=AsyncMock()):
                setup_result = await async_setup_entry(mock_hass, mock_config_entry)
                
                assert setup_result is True
                assert DOMAIN in mock_hass.data
                assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
        
        # Unload
        with patch.object(mock_hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)):
            unload_result = await async_unload_entry(mock_hass, mock_config_entry)
            
            assert unload_result is True
            assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]

    async def test_multiple_vehicles_setup(self, mock_hass, mock_config_entry, mock_client):
        """Test setup with multiple vehicles."""
        vehicle1 = MagicMock()
        vehicle1.id = "vehicle_1"
        vehicle1.vin = "VIN1234567890123"
        
        vehicle2 = MagicMock()
        vehicle2.id = "vehicle_2"
        vehicle2.vin = "VIN9876543210987"
        
        mock_client.get_vehicle_list = AsyncMock(return_value=[vehicle1, vehicle2])
        
        with patch("custom_components.nissan_na.SmartcarApiClient", return_value=mock_client):
            with patch.object(mock_hass.config_entries, "async_forward_entry_setups", new=AsyncMock()):
                result = await async_setup_entry(mock_hass, mock_config_entry)
                
                assert result is True
                # Verify both vehicles are handled
                mock_client.get_vehicle_list.assert_called_once()
