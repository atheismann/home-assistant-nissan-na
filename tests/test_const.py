import sys
import unittest

sys.path.insert(0, "custom_components/nissan_na")

import const  # noqa: E402


class TestConstants(unittest.TestCase):
    """Test that all constants are defined correctly."""

    def test_domain_defined(self):
        """Test DOMAIN constant is defined."""
        self.assertEqual(const.DOMAIN, "nissan_na")

    def test_config_keys_defined(self):
        """Test OAuth configuration keys are defined."""
        self.assertEqual(const.CONF_CLIENT_ID, "client_id")
        self.assertEqual(const.CONF_CLIENT_SECRET, "client_secret")
        self.assertEqual(const.CONF_REDIRECT_URI, "redirect_uri")
        self.assertEqual(const.CONF_ACCESS_TOKEN, "access_token")
        self.assertEqual(const.CONF_REFRESH_TOKEN, "refresh_token")
        self.assertEqual(const.CONF_CODE, "code")

    def test_platforms_defined(self):
        """Test PLATFORMS list is defined."""
        self.assertIsInstance(const.PLATFORMS, list)
        self.assertEqual(len(const.PLATFORMS), 4)
        self.assertIn("sensor", const.PLATFORMS)
        self.assertIn("lock", const.PLATFORMS)
        self.assertIn("device_tracker", const.PLATFORMS)
        self.assertIn("climate", const.PLATFORMS)
        self.assertIn("climate", const.PLATFORMS)
        self.assertIn("device_tracker", const.PLATFORMS)


if __name__ == "__main__":
    unittest.main()
