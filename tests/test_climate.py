"""Unit tests for climate.py - climate control entity"""
import pytest
from unittest.mock import Mock, AsyncMock

from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature
from custom_components.nissan_na.climate import NissanClimateEntity
from custom_components.nissan_na.const import DOMAIN


class TestNissanClimateEntityInit:
    """Tests for NissanClimateEntity initialization"""
    
    def test_climate_init_with_nickname(self):
        """Test climate initialization with vehicle nickname"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert climate._vehicle == mock_vehicle
        assert climate._client == mock_client
        assert climate._entry_id == "test_entry_id"
        assert climate._hvac_mode == HVACMode.OFF
        assert climate._attr_name == "My Nissan Climate"
        assert climate._attr_unique_id == "TEST123VIN_climate"
    
    def test_climate_init_with_year_make_model(self):
        """Test climate initialization with year/make/model"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = None
        mock_vehicle.year = 2024
        mock_vehicle.make = "Nissan"
        mock_vehicle.model = "Leaf"
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert climate._attr_name == "2024 Nissan Leaf Climate"
    
    def test_climate_init_with_vin_fallback(self):
        """Test climate initialization falling back to VIN"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = None
        mock_vehicle.year = ""
        mock_vehicle.make = ""
        mock_vehicle.model = ""
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert climate._attr_name == "TEST123VIN Climate"
    
    def test_climate_default_hvac_mode_off(self):
        """Test that default HVAC mode is OFF"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert climate._hvac_mode == HVACMode.OFF


class TestNissanClimateEntityProperties:
    """Tests for NissanClimateEntity properties"""
    
    def test_hvac_modes_property(self):
        """Test that HVAC modes are defined"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert HVACMode.OFF in climate._attr_hvac_modes
        assert HVACMode.HEAT in climate._attr_hvac_modes
        assert HVACMode.COOL in climate._attr_hvac_modes
        assert HVACMode.AUTO in climate._attr_hvac_modes
    
    def test_temperature_unit_property(self):
        """Test that temperature unit is Celsius"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert climate._attr_temperature_unit == UnitOfTemperature.CELSIUS
    
    def test_hvac_mode_property(self):
        """Test hvac_mode property"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        assert climate.hvac_mode == HVACMode.OFF
        
        climate._hvac_mode = HVACMode.HEAT
        assert climate.hvac_mode == HVACMode.HEAT
    
    def test_device_info_property(self):
        """Test device_info property"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        device_info = climate.device_info
        assert "identifiers" in device_info
        assert (DOMAIN, "TEST123VIN") in device_info["identifiers"]


class TestNissanClimateEntityActions:
    """Tests for HVAC mode actions"""
    
    @pytest.mark.asyncio
    async def test_set_hvac_mode_off(self):
        """Test setting HVAC mode to OFF"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        mock_client.stop_climate = AsyncMock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        climate.async_write_ha_state = Mock()
        
        await climate.async_set_hvac_mode(HVACMode.OFF)
        
        mock_client.stop_climate.assert_called_once_with("vehicle_123")
        assert climate._hvac_mode == HVACMode.OFF
        climate.async_write_ha_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_hvac_mode_heat(self):
        """Test setting HVAC mode to HEAT"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        mock_client.start_climate = AsyncMock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        climate.async_write_ha_state = Mock()
        
        await climate.async_set_hvac_mode(HVACMode.HEAT)
        
        mock_client.start_climate.assert_called_once_with("vehicle_123")
        assert climate._hvac_mode == HVACMode.HEAT
        climate.async_write_ha_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_hvac_mode_cool(self):
        """Test setting HVAC mode to COOL"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        mock_client.start_climate = AsyncMock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        climate.async_write_ha_state = Mock()
        
        await climate.async_set_hvac_mode(HVACMode.COOL)
        
        mock_client.start_climate.assert_called_once_with("vehicle_123")
        assert climate._hvac_mode == HVACMode.COOL
        climate.async_write_ha_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_hvac_mode_auto(self):
        """Test setting HVAC mode to AUTO"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        mock_client.start_climate = AsyncMock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        climate.async_write_ha_state = Mock()
        
        await climate.async_set_hvac_mode(HVACMode.AUTO)
        
        mock_client.start_climate.assert_called_once_with("vehicle_123")
        assert climate._hvac_mode == HVACMode.AUTO
        climate.async_write_ha_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_hvac_mode_sequence(self):
        """Test sequence of HVAC mode changes"""
        mock_vehicle = Mock()
        mock_vehicle.vin = "TEST123VIN"
        mock_vehicle.id = "vehicle_123"
        mock_vehicle.nickname = "My Nissan"
        
        mock_client = Mock()
        mock_client.start_climate = AsyncMock()
        mock_client.stop_climate = AsyncMock()
        
        climate = NissanClimateEntity(
            mock_vehicle,
            mock_client,
            "test_entry_id"
        )
        
        climate.async_write_ha_state = Mock()
        
        # Start with OFF
        assert climate._hvac_mode == HVACMode.OFF
        
        # Turn on HEAT
        await climate.async_set_hvac_mode(HVACMode.HEAT)
        assert climate._hvac_mode == HVACMode.HEAT
        assert mock_client.start_climate.call_count == 1
        
        # Switch to COOL (should call start_climate again)
        await climate.async_set_hvac_mode(HVACMode.COOL)
        assert climate._hvac_mode == HVACMode.COOL
        assert mock_client.start_climate.call_count == 2
        
        # Turn off
        await climate.async_set_hvac_mode(HVACMode.OFF)
        assert climate._hvac_mode == HVACMode.OFF
        assert mock_client.stop_climate.call_count == 1


class TestNissanClimateEntityMultipleVehicles:
    """Tests for handling multiple vehicle scenarios"""
    
    def test_unique_id_different_for_different_vehicles(self):
        """Test that unique IDs are different for different vehicles"""
        mock_client = Mock()
        
        mock_vehicle1 = Mock()
        mock_vehicle1.vin = "VIN123"
        mock_vehicle1.id = "vehicle_1"
        mock_vehicle1.nickname = "Car 1"
        
        mock_vehicle2 = Mock()
        mock_vehicle2.vin = "VIN456"
        mock_vehicle2.id = "vehicle_2"
        mock_vehicle2.nickname = "Car 2"
        
        climate1 = NissanClimateEntity(mock_vehicle1, mock_client, "entry1")
        climate2 = NissanClimateEntity(mock_vehicle2, mock_client, "entry2")
        
        assert climate1._attr_unique_id != climate2._attr_unique_id
        assert climate1._attr_unique_id == "VIN123_climate"
        assert climate2._attr_unique_id == "VIN456_climate"
    
    def test_independent_modes_for_different_vehicles(self):
        """Test that different vehicles maintain independent HVAC modes"""
        mock_client = Mock()
        
        mock_vehicle1 = Mock()
        mock_vehicle1.vin = "VIN123"
        mock_vehicle1.id = "vehicle_1"
        mock_vehicle1.nickname = "Car 1"
        
        mock_vehicle2 = Mock()
        mock_vehicle2.vin = "VIN456"
        mock_vehicle2.id = "vehicle_2"
        mock_vehicle2.nickname = "Car 2"
        
        climate1 = NissanClimateEntity(mock_vehicle1, mock_client, "entry1")
        climate2 = NissanClimateEntity(mock_vehicle2, mock_client, "entry2")
        
        # Set different modes
        climate1._hvac_mode = HVACMode.HEAT
        climate2._hvac_mode = HVACMode.COOL
        
        assert climate1.hvac_mode == HVACMode.HEAT
        assert climate2.hvac_mode == HVACMode.COOL
