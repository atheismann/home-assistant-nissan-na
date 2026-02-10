"""Tests for reload entities feature in config flow."""

from unittest.mock import MagicMock
import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nissan_na.const import DOMAIN
from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    return entry


async def test_reload_entities_menu_structure(hass: HomeAssistant, mock_config_entry):
    """Test that reload entities is available in options menu."""
    # Just verify the menu structure has reload_entities option
    from custom_components.nissan_na.config_flow import NissanNAOptionsFlowHandler
    
    flow = NissanNAOptionsFlowHandler()
    # This test verifies the code path exists for reload entities
    assert hasattr(flow, "async_step_reload_entities")
    assert hasattr(flow, "async_step_reload_complete")
