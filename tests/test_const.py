"""Unit tests for constants module."""
from custom_components.nissan_na.const import (
    DOMAIN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REDIRECT_URI,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_CODE,
    CONF_WEBHOOK_ID,
    CONF_MANAGEMENT_TOKEN,
    CONF_UNIT_SYSTEM,
    UNIT_SYSTEM_METRIC,
    UNIT_SYSTEM_IMPERIAL,
    PLATFORMS,
)


class TestConstants:
    """Test constants are defined correctly."""

    def test_domain(self):
        """Test DOMAIN constant."""
        assert DOMAIN == "nissan_na"
        assert isinstance(DOMAIN, str)

    def test_config_keys(self):
        """Test configuration key constants."""
        assert CONF_CLIENT_ID == "client_id"
        assert CONF_CLIENT_SECRET == "client_secret"
        assert CONF_REDIRECT_URI == "redirect_uri"
        assert CONF_ACCESS_TOKEN == "access_token"
        assert CONF_REFRESH_TOKEN == "refresh_token"
        assert CONF_CODE == "code"

    def test_webhook_keys(self):
        """Test webhook configuration constants."""
        assert CONF_WEBHOOK_ID == "webhook_id"
        assert CONF_MANAGEMENT_TOKEN == "management_token"

    def test_unit_system_keys(self):
        """Test unit system constants."""
        assert CONF_UNIT_SYSTEM == "unit_system"
        assert UNIT_SYSTEM_METRIC == "metric"
        assert UNIT_SYSTEM_IMPERIAL == "imperial"

    def test_platforms(self):
        """Test platform list."""
        assert isinstance(PLATFORMS, list)
        assert len(PLATFORMS) == 7
        assert "sensor" in PLATFORMS
        assert "binary_sensor" in PLATFORMS
        assert "switch" in PLATFORMS
        assert "number" in PLATFORMS
        assert "lock" in PLATFORMS
        assert "device_tracker" in PLATFORMS
        assert "climate" in PLATFORMS

    def test_platforms_are_strings(self):
        """Test all platforms are strings."""
        for platform in PLATFORMS:
            assert isinstance(platform, str)
            assert len(platform) > 0
