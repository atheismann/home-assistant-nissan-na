"""Tests for the Nissan NA services module."""

import pytest
import voluptuous as vol

from custom_components.nissan_na import services


def test_service_constants_defined():
    """Test that all service constants are defined."""
    assert services.SERVICE_LOCK == "lock_doors"
    assert services.SERVICE_UNLOCK == "unlock_doors"
    assert services.SERVICE_START_ENGINE == "start_engine"
    assert services.SERVICE_STOP_ENGINE == "stop_engine"
    assert services.SERVICE_FIND_VEHICLE == "find_vehicle"
    assert services.SERVICE_REFRESH_STATUS == "refresh_vehicle_status"


def test_service_schema():
    """Test service schema validation."""
    # Valid data
    valid_data = {"vin": "TEST123VIN"}
    assert services.SERVICE_SCHEMA(valid_data) == valid_data

    # Invalid data - missing vin
    with pytest.raises(vol.MultipleInvalid):
        services.SERVICE_SCHEMA({})

    # Invalid data - wrong type
    with pytest.raises(vol.MultipleInvalid):
        services.SERVICE_SCHEMA({"vin": 123})


def test_service_schema_validates_vin_required():
    """Test that VIN is required in service schema."""
    with pytest.raises(vol.MultipleInvalid) as exc_info:
        services.SERVICE_SCHEMA({})

    assert "required key not provided" in str(exc_info.value)


def test_service_schema_accepts_string_vin():
    """Test that service schema accepts string VIN."""
    result = services.SERVICE_SCHEMA({"vin": "1N4AZ1CP8JC123456"})
    assert result["vin"] == "1N4AZ1CP8JC123456"
