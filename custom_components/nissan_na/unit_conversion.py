"""Unit conversion utilities for Nissan NA integration."""

from .const import UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC


def km_to_miles(km: float) -> float:
    """Convert kilometers to miles."""
    return km * 0.621371


def liters_to_gallons(liters: float) -> float:
    """Convert liters to US gallons."""
    return liters * 0.264172


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9/5) + 32


def kpa_to_psi(kpa: float) -> float:
    """Convert kilopascals to PSI."""
    return kpa * 0.145038


def bar_to_psi(bar: float) -> float:
    """Convert bar to PSI."""
    return bar * 14.5038


def convert_value(value: float, from_unit: str, unit_system: str) -> float:
    """
    Convert a value based on the target unit system.
    
    Args:
        value: The value to convert
        from_unit: The original unit (metric)
        unit_system: Target unit system (metric or imperial)
        
    Returns:
        Converted value
    """
    if unit_system == UNIT_SYSTEM_METRIC or value is None:
        return value
    
    # Conversion map for imperial units
    conversions = {
        "km": km_to_miles,
        "L": liters_to_gallons,
        "°C": celsius_to_fahrenheit,
        "bar": bar_to_psi,
        "kPa": kpa_to_psi,
    }
    
    converter = conversions.get(from_unit)
    if converter:
        return round(converter(value), 2)
    
    return value


def get_display_unit(metric_unit: str, unit_system: str) -> str:
    """
    Get the display unit based on the unit system.
    
    Args:
        metric_unit: The metric unit
        unit_system: Target unit system (metric or imperial)
        
    Returns:
        Display unit for the target system
    """
    if unit_system == UNIT_SYSTEM_METRIC:
        return metric_unit
    
    # Unit conversion map
    unit_map = {
        "km": "mi",
        "L": "gal",
        "°C": "°F",
        "bar": "psi",
        "kPa": "psi",
        "km/h": "mph",
    }
    
    return unit_map.get(metric_unit, metric_unit)
