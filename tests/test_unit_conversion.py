"""Unit tests for unit conversion module."""
import pytest
from custom_components.nissan_na.unit_conversion import (
    km_to_miles,
    liters_to_gallons,
    celsius_to_fahrenheit,
    kpa_to_psi,
    bar_to_psi,
    convert_value,
    get_display_unit,
)
from custom_components.nissan_na.const import UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC


class TestConversionFunctions:
    """Test individual conversion functions."""

    def test_km_to_miles(self):
        """Test kilometers to miles conversion."""
        assert km_to_miles(100) == pytest.approx(62.1371, rel=0.01)
        assert km_to_miles(0) == 0
        assert km_to_miles(1) == pytest.approx(0.621371, rel=0.01)
        assert km_to_miles(160.934) == pytest.approx(100, rel=0.01)

    def test_liters_to_gallons(self):
        """Test liters to gallons conversion."""
        assert liters_to_gallons(10) == pytest.approx(2.64172, rel=0.01)
        assert liters_to_gallons(0) == 0
        assert liters_to_gallons(1) == pytest.approx(0.264172, rel=0.01)
        assert liters_to_gallons(3.78541) == pytest.approx(1, rel=0.01)

    def test_celsius_to_fahrenheit(self):
        """Test Celsius to Fahrenheit conversion."""
        assert celsius_to_fahrenheit(0) == 32
        assert celsius_to_fahrenheit(100) == 212
        assert celsius_to_fahrenheit(-40) == -40
        assert celsius_to_fahrenheit(37) == pytest.approx(98.6, rel=0.01)

    def test_kpa_to_psi(self):
        """Test kilopascals to PSI conversion."""
        assert kpa_to_psi(100) == pytest.approx(14.5038, rel=0.01)
        assert kpa_to_psi(0) == 0
        assert kpa_to_psi(206.843) == pytest.approx(30, rel=0.01)

    def test_bar_to_psi(self):
        """Test bar to PSI conversion."""
        assert bar_to_psi(1) == pytest.approx(14.5038, rel=0.01)
        assert bar_to_psi(0) == 0
        assert bar_to_psi(2) == pytest.approx(29.0076, rel=0.01)


class TestConvertValue:
    """Test the generic convert_value function."""

    def test_metric_system_no_conversion(self):
        """Test that metric system returns values unchanged."""
        assert convert_value(100, "km", UNIT_SYSTEM_METRIC) == 100
        assert convert_value(50, "L", UNIT_SYSTEM_METRIC) == 50
        assert convert_value(25, "°C", UNIT_SYSTEM_METRIC) == 25

    def test_none_value_returns_none(self):
        """Test that None values return None."""
        assert convert_value(None, "km", UNIT_SYSTEM_IMPERIAL) is None
        assert convert_value(None, "L", UNIT_SYSTEM_IMPERIAL) is None

    def test_imperial_km_conversion(self):
        """Test kilometer to miles conversion in imperial system."""
        result = convert_value(100, "km", UNIT_SYSTEM_IMPERIAL)
        assert result == 62.14

    def test_imperial_liter_conversion(self):
        """Test liter to gallon conversion in imperial system."""
        result = convert_value(10, "L", UNIT_SYSTEM_IMPERIAL)
        assert result == 2.64

    def test_imperial_celsius_conversion(self):
        """Test Celsius to Fahrenheit conversion in imperial system."""
        result = convert_value(0, "°C", UNIT_SYSTEM_IMPERIAL)
        assert result == 32.0
        
        result = convert_value(100, "°C", UNIT_SYSTEM_IMPERIAL)
        assert result == 212.0

    def test_imperial_bar_conversion(self):
        """Test bar to PSI conversion in imperial system."""
        result = convert_value(2, "bar", UNIT_SYSTEM_IMPERIAL)
        assert result == pytest.approx(29.01, rel=0.01)

    def test_imperial_kpa_conversion(self):
        """Test kPa to PSI conversion in imperial system."""
        result = convert_value(100, "kPa", UNIT_SYSTEM_IMPERIAL)
        assert result == pytest.approx(14.50, rel=0.01)

    def test_unsupported_unit_returns_original(self):
        """Test that unsupported units return original value."""
        result = convert_value(100, "%", UNIT_SYSTEM_IMPERIAL)
        assert result == 100
        
        result = convert_value(50, "kW", UNIT_SYSTEM_IMPERIAL)
        assert result == 50

    def test_rounding_to_two_decimals(self):
        """Test that conversions are rounded to 2 decimal places."""
        result = convert_value(123.456, "km", UNIT_SYSTEM_IMPERIAL)
        # 123.456 * 0.621371 = 76.721... should round to 76.71
        assert result == 76.71


class TestGetDisplayUnit:
    """Test the get_display_unit function."""

    def test_metric_system_returns_metric_units(self):
        """Test that metric system returns metric units."""
        assert get_display_unit("km", UNIT_SYSTEM_METRIC) == "km"
        assert get_display_unit("L", UNIT_SYSTEM_METRIC) == "L"
        assert get_display_unit("°C", UNIT_SYSTEM_METRIC) == "°C"
        assert get_display_unit("bar", UNIT_SYSTEM_METRIC) == "bar"

    def test_imperial_system_returns_imperial_units(self):
        """Test that imperial system returns imperial units."""
        assert get_display_unit("km", UNIT_SYSTEM_IMPERIAL) == "mi"
        assert get_display_unit("L", UNIT_SYSTEM_IMPERIAL) == "gal"
        assert get_display_unit("°C", UNIT_SYSTEM_IMPERIAL) == "°F"
        assert get_display_unit("bar", UNIT_SYSTEM_IMPERIAL) == "psi"
        assert get_display_unit("kPa", UNIT_SYSTEM_IMPERIAL) == "psi"

    def test_speed_unit_conversion(self):
        """Test speed unit conversion."""
        assert get_display_unit("km/h", UNIT_SYSTEM_IMPERIAL) == "mph"
        assert get_display_unit("km/h", UNIT_SYSTEM_METRIC) == "km/h"

    def test_unmapped_units_return_original(self):
        """Test that unmapped units return original."""
        assert get_display_unit("%", UNIT_SYSTEM_IMPERIAL) == "%"
        assert get_display_unit("kW", UNIT_SYSTEM_IMPERIAL) == "kW"
        assert get_display_unit("V", UNIT_SYSTEM_IMPERIAL) == "V"
        assert get_display_unit("A", UNIT_SYSTEM_IMPERIAL) == "A"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_negative_values(self):
        """Test conversion of negative values."""
        result = convert_value(-10, "°C", UNIT_SYSTEM_IMPERIAL)
        assert result == 14.0
        
        # Negative distance shouldn't happen but should still convert
        result = convert_value(-100, "km", UNIT_SYSTEM_IMPERIAL)
        assert result < 0

    def test_zero_values(self):
        """Test conversion of zero values."""
        assert convert_value(0, "km", UNIT_SYSTEM_IMPERIAL) == 0.0
        assert convert_value(0, "L", UNIT_SYSTEM_IMPERIAL) == 0.0
        assert convert_value(0, "°C", UNIT_SYSTEM_IMPERIAL) == 32.0

    def test_very_large_values(self):
        """Test conversion of very large values."""
        result = convert_value(1000000, "km", UNIT_SYSTEM_IMPERIAL)
        assert result == pytest.approx(621371.0, rel=0.01)

    def test_very_small_values(self):
        """Test conversion of very small values."""
        result = convert_value(0.001, "km", UNIT_SYSTEM_IMPERIAL)
        assert result == 0.0  # Rounds to 0.00
