"""Tests for services.py to reach 100% coverage"""
import voluptuous as vol


class TestServiceConstants:
    """Tests for service constant definitions"""
    
    def test_service_lock_constant(self):
        """Test SERVICE_LOCK constant is defined correctly"""
        from custom_components.nissan_na.services import SERVICE_LOCK
        
        assert SERVICE_LOCK == "lock_doors"
    
    def test_service_unlock_constant(self):
        """Test SERVICE_UNLOCK constant is defined correctly"""
        from custom_components.nissan_na.services import SERVICE_UNLOCK
        
        assert SERVICE_UNLOCK == "unlock_doors"
    
    def test_service_start_engine_constant(self):
        """Test SERVICE_START_ENGINE constant is defined correctly"""
        from custom_components.nissan_na.services import SERVICE_START_ENGINE
        
        assert SERVICE_START_ENGINE == "start_engine"
    
    def test_service_stop_engine_constant(self):
        """Test SERVICE_STOP_ENGINE constant is defined correctly"""
        from custom_components.nissan_na.services import SERVICE_STOP_ENGINE
        
        assert SERVICE_STOP_ENGINE == "stop_engine"
    
    def test_service_find_vehicle_constant(self):
        """Test SERVICE_FIND_VEHICLE constant is defined correctly"""
        from custom_components.nissan_na.services import SERVICE_FIND_VEHICLE
        
        assert SERVICE_FIND_VEHICLE == "find_vehicle"
    
    def test_service_refresh_status_constant(self):
        """Test SERVICE_REFRESH_STATUS constant is defined correctly"""
        from custom_components.nissan_na.services import SERVICE_REFRESH_STATUS
        
        assert SERVICE_REFRESH_STATUS == "refresh_vehicle_status"


class TestServiceSchema:
    """Tests for SERVICE_SCHEMA validation"""
    
    def test_service_schema_accepts_valid_vin(self):
        """Test SERVICE_SCHEMA accepts valid VIN"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        valid_data = {"vin": "1N4AL3AP8HC123456"}
        
        # Should not raise
        validated = SERVICE_SCHEMA(valid_data)
        assert validated["vin"] == "1N4AL3AP8HC123456"
    
    def test_service_schema_accepts_any_string_vin(self):
        """Test SERVICE_SCHEMA accepts any string as VIN"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        valid_data = {"vin": "TEST_VIN_123"}
        
        validated = SERVICE_SCHEMA(valid_data)
        assert validated["vin"] == "TEST_VIN_123"
    
    def test_service_schema_requires_vin_field(self):
        """Test SERVICE_SCHEMA requires vin field"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        invalid_data = {}
        
        # Should raise error for missing required field
        try:
            SERVICE_SCHEMA(invalid_data)
            assert False, "Expected voluptuous.error.MultipleInvalid"
        except vol.error.MultipleInvalid:
            pass  # Expected
    
    def test_service_schema_rejects_non_string_vin(self):
        """Test SERVICE_SCHEMA rejects non-string VIN values"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        invalid_data = {"vin": 12345}
        
        # Should raise error for wrong type
        try:
            SERVICE_SCHEMA(invalid_data)
            assert False, "Expected voluptuous.error.MultipleInvalid"
        except vol.error.MultipleInvalid:
            pass  # Expected
    
    def test_service_schema_rejects_none_vin(self):
        """Test SERVICE_SCHEMA rejects None as VIN value"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        invalid_data = {"vin": None}
        
        # Should raise error for None
        try:
            SERVICE_SCHEMA(invalid_data)
            assert False, "Expected voluptuous.error.MultipleInvalid"
        except vol.error.MultipleInvalid:
            pass  # Expected
    
    def test_service_schema_is_voluptuous_schema(self):
        """Test SERVICE_SCHEMA is a voluptuous Schema instance"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        assert isinstance(SERVICE_SCHEMA, vol.Schema)
    
    def test_service_schema_accepts_empty_string_vin(self):
        """Test SERVICE_SCHEMA accepts empty string VIN"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        # Empty string is still a string, so it should be accepted
        valid_data = {"vin": ""}
        
        validated = SERVICE_SCHEMA(valid_data)
        assert validated["vin"] == ""
    
    def test_service_schema_rejects_extra_fields(self):
        """Test SERVICE_SCHEMA rejects extra fields"""
        from custom_components.nissan_na.services import SERVICE_SCHEMA
        
        data_with_extra = {"vin": "TEST_VIN", "extra_field": "value"}
        
        # Should raise error for extra fields
        try:
            SERVICE_SCHEMA(data_with_extra)
            assert False, "Expected voluptuous.error.MultipleInvalid"
        except vol.error.MultipleInvalid:
            pass  # Expected
    
    def test_all_service_constants_are_strings(self):
        """Test all service constants are strings"""
        from custom_components.nissan_na import services
        
        assert isinstance(services.SERVICE_LOCK, str)
        assert isinstance(services.SERVICE_UNLOCK, str)
        assert isinstance(services.SERVICE_START_ENGINE, str)
        assert isinstance(services.SERVICE_STOP_ENGINE, str)
        assert isinstance(services.SERVICE_FIND_VEHICLE, str)
        assert isinstance(services.SERVICE_REFRESH_STATUS, str)
    
    def test_service_constants_are_unique(self):
        """Test all service constants have unique values"""
        from custom_components.nissan_na import services
        
        service_values = [
            services.SERVICE_LOCK,
            services.SERVICE_UNLOCK,
            services.SERVICE_START_ENGINE,
            services.SERVICE_STOP_ENGINE,
            services.SERVICE_FIND_VEHICLE,
            services.SERVICE_REFRESH_STATUS,
        ]
        
        # All values should be unique
        assert len(service_values) == len(set(service_values))
