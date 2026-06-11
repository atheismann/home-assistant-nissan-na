"""Tests for api.py to reach 90%+ coverage"""

import pytest
from unittest.mock import Mock

from custom_components.nissan_na.api import SmartcarOAuth2Implementation


class TestSmartcarOAuth2Implementation:
    """Tests for SmartcarOAuth2Implementation class"""

    def test_extra_authorize_data_returns_dict(self):
        """Test extra_authorize_data returns a dictionary"""
        # Create instance with minimal required params
        impl = SmartcarOAuth2Implementation(
            Mock(),  # hass
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token",
        )

        extra_data = impl.extra_authorize_data

        assert isinstance(extra_data, dict)
        assert "make" in extra_data
        assert "single_select" in extra_data

    def test_extra_authorize_data_make_is_nissan(self):
        """Test extra_authorize_data sets make to NISSAN"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token",
        )

        extra_data = impl.extra_authorize_data

        assert extra_data["make"] == "NISSAN"

    def test_extra_authorize_data_single_select_is_true(self):
        """Test extra_authorize_data sets single_select to true"""
        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token",
        )

        extra_data = impl.extra_authorize_data

        assert extra_data["single_select"] == "true"

    def test_inherits_from_local_oauth2_implementation(self):
        """Test SmartcarOAuth2Implementation inherits from LocalOAuth2Implementation"""
        from homeassistant.helpers import config_entry_oauth2_flow

        impl = SmartcarOAuth2Implementation(
            Mock(),
            "domain",
            "client_id_123",
            "client_secret_456",
            "https://example.com/authorize",
            "https://example.com/token",
        )

        assert isinstance(impl, config_entry_oauth2_flow.LocalOAuth2Implementation)
