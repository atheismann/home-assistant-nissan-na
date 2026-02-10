import re

# Read the test file
with open('tests/test_sensor.py', 'r') as f:
    content = f.read()

# Pattern to find NissanGenericSensor constructors with old signature
pattern = r'NissanGenericSensor\(\s*hass,\s*((?:mock_)?vehicle),\s*((?:mock_vehicle_)?status),\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*("[^"]*"|None),\s*"test_entry",?\s*\)'

def replacer(match):
    vehicle_var = match.group(1)
    status_var = match.group(2)
    api_key = match.group(3)
    field_name = match.group(4)
    name = match.group(5)
    unit = match.group(6)
    
    # Convert api_key to signal_id format
    signal_id = f"{api_key}.{field_name}"
    
    # Determine icon and device_class
    icon = "None"
    device_class = "None"
    
    if "battery" in api_key.lower():
        device_class = '"battery"'
    elif "location" in api_key.lower():
        icon = '"mdi:map-marker"'
    elif "charge" in api_key.lower():
        icon = '"mdi:ev-station"'
    elif "odometer" in api_key.lower():
        icon = '"mdi:counter"'
    
    return f'''NissanGenericSensor(
        hass,
        {vehicle_var},
        {status_var},
        "{signal_id}",
        "{field_name}",
        "{name}",
        {unit},
        {icon},
        {device_class},
        "test_entry",
    )'''

# Count matches
matches = list(re.finditer(pattern, content))
print(f"Found {len(matches)} NissanGenericSensor constructors to fix")

# Apply replacements
new_content = re.sub(pattern, replacer, content)

# Write back
with open('tests/test_sensor.py', 'w') as f:
    f.write(new_content)

print("Fixed all NissanGenericSensor constructors")
