"""Unit tests for lock.py - door lock entity tests"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.components.lock import LockEntity

from custom_components.nissan_na.lock import (
    NissanDoorLockEntity,
    async_setup_entry,
)
from custom_components.nissan_na.const import DOMAIN


class TestLockEntityInitialization:
    """Tests for NissanDoorLockEntity initialization"""

    def test_init_with_nickname(self):
        """Test lock entity initialization with vehicle nickname"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "My Tesla"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        assert entity._attr_name == "My Tesla Door Lock"
        assert entity._attr_unique_id == "TEST123_door_lock"
        assert entity._is_locked == True
        assert entity._vehicle == mock_vehicle
        assert entity._client == mock_client

    def test_init_with_year_make_model(self):
        """Test lock entity initialization with year/make/model"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = None
        mock_vehicle.year = "2024"
        mock_vehicle.make = "Nissan"
        mock_vehicle.model = "Leaf"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": False}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        assert entity._attr_name == "2024 Nissan Leaf Door Lock"
        assert entity._is_locked == False

    def test_init_with_vin_fallback(self):
        """Test lock entity initialization falling back to VIN"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TESTVIN123"
        mock_vehicle.nickname = None
        mock_vehicle.year = None
        mock_vehicle.make = None
        mock_vehicle.model = None

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        assert entity._attr_name == "TESTVIN123 Door Lock"
        assert entity._is_locked is None

    def test_init_with_empty_year_make_model(self):
        """Test lock entity initialization with partial year/make/model"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TESTVIN456"
        mock_vehicle.nickname = None
        mock_vehicle.year = "2024"
        mock_vehicle.make = ""
        mock_vehicle.model = "Leaf"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        # Should fall back to VIN since make is empty
        assert entity._attr_name == "TESTVIN456 Door Lock"

    def test_device_info(self):
        """Test device_info property"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "ABC123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        device_info = entity.device_info
        assert device_info == {"identifiers": {(DOMAIN, "ABC123")}}

    def test_is_locked_property_true(self):
        """Test is_locked property when locked"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        assert entity.is_locked == True

    def test_is_locked_property_false(self):
        """Test is_locked property when unlocked"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": False}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        assert entity.is_locked == False

    def test_is_locked_property_none(self):
        """Test is_locked property when status unknown"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        assert entity.is_locked is None


class TestLockEntityWebhookHandling:
    """Tests for webhook data handling"""

    def test_handle_webhook_data_lock(self):
        """Test webhook handling for lock event"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": False}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        webhook_data = {"lock": {"is_locked": True}}

        entity._handle_webhook_data(webhook_data)

        assert entity._is_locked == True
        entity.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_unlock(self):
        """Test webhook handling for unlock event"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        webhook_data = {"lock": {"is_locked": False}}

        entity._handle_webhook_data(webhook_data)

        assert entity._is_locked == False
        entity.async_write_ha_state.assert_called_once()

    def test_handle_webhook_data_missing_lock_key(self):
        """Test webhook handling when lock key is missing"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        webhook_data = {"some_other_data": True}

        entity._handle_webhook_data(webhook_data)

        assert entity._is_locked == True
        entity.async_write_ha_state.assert_not_called()

    def test_handle_webhook_data_missing_is_locked_key(self):
        """Test webhook handling when is_locked key is missing"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        webhook_data = {"lock": {"some_other_field": False}}

        entity._handle_webhook_data(webhook_data)

        assert entity._is_locked == True
        entity.async_write_ha_state.assert_not_called()

    def test_handle_webhook_data_non_dict_data(self):
        """Test webhook handling with non-dict data"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        entity._handle_webhook_data("invalid")

        assert entity._is_locked == True
        entity.async_write_ha_state.assert_not_called()

    def test_handle_webhook_data_non_dict_lock_value(self):
        """Test webhook handling when lock value is not a dict"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        webhook_data = {"lock": "invalid"}

        entity._handle_webhook_data(webhook_data)

        assert entity._is_locked == True
        entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
class TestLockEntityCommands:
    """Tests for lock/unlock commands"""

    async def test_async_lock(self):
        """Test locking the vehicle"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.lock_doors = AsyncMock()

        mock_hass = MagicMock()
        lock_status = {"is_locked": False}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_lock()

        mock_client.lock_doors.assert_called_once_with("vehicle_123")
        assert entity._is_locked == True
        entity.async_write_ha_state.assert_called_once()

    async def test_async_unlock(self):
        """Test unlocking the vehicle"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.unlock_doors = AsyncMock()

        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_unlock()

        mock_client.unlock_doors.assert_called_once_with("vehicle_123")
        assert entity._is_locked == False
        entity.async_write_ha_state.assert_called_once()

    async def test_async_lock_with_kwargs(self):
        """Test locking with additional keyword arguments"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.lock_doors = AsyncMock()

        mock_hass = MagicMock()
        lock_status = {"is_locked": False}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_lock(some_arg="value")

        mock_client.lock_doors.assert_called_once_with("vehicle_123")
        assert entity._is_locked == True

    async def test_async_unlock_with_kwargs(self):
        """Test unlocking with additional keyword arguments"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.unlock_doors = AsyncMock()

        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )
        entity.async_write_ha_state = MagicMock()

        await entity.async_unlock(some_arg="value")

        mock_client.unlock_doors.assert_called_once_with("vehicle_123")
        assert entity._is_locked == False


@pytest.mark.asyncio
class TestLockEntityLifecycle:
    """Tests for lock entity lifecycle"""

    async def test_async_added_to_hass(self):
        """Test subscription to webhook updates"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"
        mock_vehicle.id = "vehicle_123"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        mock_unsub = MagicMock()
        with patch(
            "custom_components.nissan_na.lock.async_dispatcher_connect",
            return_value=mock_unsub,
        ):
            await entity.async_added_to_hass()

        assert entity._subscription == mock_unsub

    async def test_async_will_remove_from_hass(self):
        """Test unsubscription from webhook updates"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        mock_unsub = MagicMock()
        entity._subscription = mock_unsub

        await entity.async_will_remove_from_hass()

        mock_unsub.assert_called_once()
        assert entity._subscription is None

    async def test_async_will_remove_from_hass_no_subscription(self):
        """Test cleanup when subscription is None"""
        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test"

        mock_client = MagicMock()
        mock_hass = MagicMock()
        lock_status = {"is_locked": True}

        entity = NissanDoorLockEntity(
            mock_vehicle, mock_client, "entry_123", mock_hass, lock_status
        )

        entity._subscription = None

        # Should not raise error
        await entity.async_will_remove_from_hass()

        assert entity._subscription is None


@pytest.mark.asyncio
class TestAsyncSetupEntry:
    """Tests for async_setup_entry function"""

    async def test_async_setup_entry_with_lock_support(self):
        """Test setup when vehicle supports lock control"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_async_add_entities = AsyncMock()

        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_permissions = AsyncMock(
            return_value=["control_security", "read_location"]
        )
        mock_client.get_vehicle_status = AsyncMock(
            return_value={"lock": {"is_locked": True}}
        )

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], NissanDoorLockEntity)

    async def test_async_setup_entry_without_lock_support(self):
        """Test setup when vehicle doesn't support lock control"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_async_add_entities = AsyncMock()

        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_permissions = AsyncMock(return_value=["read_location"])

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 0

    async def test_async_setup_entry_permission_api_failure(self):
        """Test setup when permission API fails (conservative approach)"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_async_add_entities = AsyncMock()

        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_permissions = AsyncMock(side_effect=Exception("API error"))
        mock_client.get_vehicle_status = AsyncMock(
            return_value={"lock": {"is_locked": False}}
        )

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        # Should create entity (conservative approach)
        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 1

    async def test_async_setup_entry_status_api_failure(self):
        """Test setup when vehicle status API fails"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_async_add_entities = AsyncMock()

        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_permissions = AsyncMock(return_value=["control_security"])
        mock_client.get_vehicle_status = AsyncMock(side_effect=Exception("API error"))

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        # Should create entity with empty lock status
        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert entities[0]._is_locked is None

    async def test_async_setup_entry_empty_permissions(self):
        """Test setup when vehicle has empty permission list"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_async_add_entities = AsyncMock()

        mock_vehicle = MagicMock()
        mock_vehicle.vin = "TEST123"
        mock_vehicle.nickname = "Test Car"
        mock_vehicle.id = "vehicle_123"

        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(return_value=[mock_vehicle])
        mock_client.get_permissions = AsyncMock(return_value=[])
        mock_client.get_vehicle_status = AsyncMock(
            return_value={"lock": {"is_locked": True}}
        )

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        # Empty permission list should create entity (conservative approach)
        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 1

    async def test_async_setup_entry_multiple_vehicles(self):
        """Test setup with multiple vehicles"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_async_add_entities = AsyncMock()

        mock_vehicle1 = MagicMock()
        mock_vehicle1.vin = "VIN1"
        mock_vehicle1.nickname = "Car 1"
        mock_vehicle1.id = "vehicle_1"

        mock_vehicle2 = MagicMock()
        mock_vehicle2.vin = "VIN2"
        mock_vehicle2.nickname = "Car 2"
        mock_vehicle2.id = "vehicle_2"

        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(
            return_value=[mock_vehicle1, mock_vehicle2]
        )
        mock_client.get_permissions = AsyncMock(return_value=["control_security"])
        mock_client.get_vehicle_status = AsyncMock(
            return_value={"lock": {"is_locked": True}}
        )

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 2

    async def test_async_setup_entry_mixed_permissions(self):
        """Test setup with multiple vehicles with mixed permissions"""
        mock_hass = MagicMock()
        mock_hass.async_create_task = MagicMock()

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_async_add_entities = AsyncMock()

        mock_vehicle1 = MagicMock()
        mock_vehicle1.vin = "VIN1"
        mock_vehicle1.nickname = "Car 1"
        mock_vehicle1.id = "vehicle_1"

        mock_vehicle2 = MagicMock()
        mock_vehicle2.vin = "VIN2"
        mock_vehicle2.nickname = "Car 2"
        mock_vehicle2.id = "vehicle_2"

        mock_client = AsyncMock()
        mock_client.get_vehicle_list = AsyncMock(
            return_value=[mock_vehicle1, mock_vehicle2]
        )

        # Vehicle 1 supports locks, Vehicle 2 doesn't
        async def get_permissions_side_effect(vehicle_id):
            if vehicle_id == "vehicle_1":
                return ["control_security"]
            else:
                return ["read_location"]

        mock_client.get_permissions = AsyncMock(side_effect=get_permissions_side_effect)
        mock_client.get_vehicle_status = AsyncMock(
            return_value={"lock": {"is_locked": True}}
        )

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "client": mock_client,
                }
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        mock_async_add_entities.assert_called_once()
        entities = mock_async_add_entities.call_args[0][0]
        # Only vehicle 1 should have a lock entity
        assert len(entities) == 1
