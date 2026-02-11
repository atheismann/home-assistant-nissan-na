# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

#### Comprehensive Sensor Coverage
- **31 Sensors** (expanded from 7) covering:
  - **Battery**: Percentage, Range, Capacity, Low Voltage Battery
  - **Charging**: State, Voltage, Current, Power, Time to Complete, Max Current, Plugged In Status
  - **Fuel**: Amount, Percentage, Range
  - **Tires**: Pressure for all 4 wheels (FL, FR, RL, RR)
  - **Vehicle Status**: Current Gear, Oil Life, Software Version
  - **Location**: Latitude, Longitude
  - **Connectivity**: Online, Asleep, Digital Key Paired
  - **Other**: Surveillance, Battery Heater, Charge Limit, Odometer

#### Binary Sensors (NEW)
- **25 Binary Sensors** covering:
  - **Doors**: All 4 doors (open + lock status)
  - **Windows**: All 4 windows (open status)
  - **Trunks**: Front/Rear trunks (open + lock status)
  - **Connectivity**: Online, Asleep, Digital Key Paired
  - **Charging**: Cable plugged, Fast charger connected
  - **Other**: Sunroof, Engine cover, Battery heater, Surveillance

#### Vehicle Control (NEW)
- **Charging Switch**: Start/stop charging remotely
- **Charge Limit Number**: Set target charge percentage (0-100%)

#### Intelligent Signal Validation
- **Dynamic entity creation** based on vehicle capabilities using Smartcar signals API
- **Boot behavior**: Only adds new sensors, never removes existing ones for stability
- **Rebuild Sensors option**: Manual validation and cleanup via configuration menu
  - Removes sensors no longer supported by vehicle
  - Adds newly available sensors
  - Validates all sensors against current vehicle capabilities
  - Shows summary of changes (added/removed/total)
- Entities validated at setup using signals API
- Clean sensor management without breaking existing automations

#### Enhanced Configuration
- **Entity Reload Option**: Discover and load new sensors after upgrades
- **Signal Discovery**: Automatic detection of available vehicle features
- **Diagnostics Support**: View webhook URL and integration status
- **Entity Descriptions**: Comprehensive strings.json with all entity descriptions

#### Webhook Enhancements
- Real-time state updates for all entity types
- Nested data structure parsing for complex signals
- Async dispatcher pattern for efficient updates
- Comprehensive webhook logging for troubleshooting

#### Developer Features
- Complete Home Assistant device classes and icons
- Unique ID persistence for all entities
- Device registry integration
- Backward compatibility maintained
- Zero breaking changes

### Improved

- **Sensor state management** using proper `SensorEntity` base class
- **Device tracker** now supports real-time webhook location updates
- **Automatic token refresh** - eliminates most manual re-authorization needs
- **Comprehensive debug logging** throughout webhook lifecycle
- **Error handling** with graceful fallbacks at all levels
- **OAuth permissions** expanded to 32 comprehensive permissions

### Technical

- Total entity count: **58** (from 10, +480% increase)
- Signal coverage: **31/51** Smartcar signals (61%)
- Code additions: ~1,200 lines
- New platforms: binary_sensor, switch, number
- Python requirement: 3.12+
- Home Assistant: 2024.1+
  - Added read_charge_locations, read_charge_records for EV charging history
  - Added control_navigation for sending destinations to vehicle
  - Added control_trunk for remote trunk/frunk control
  - Total of 32 permissions requested to maximize feature availability
- **Climate control platform**
  - Supports start/stop HVAC system via climate entity
  - Uses direct Smartcar REST API calls (not available in Python SDK)
  - Includes HEAT, COOL, AUTO, and OFF modes
  - Temperature control not supported (API limitation)

### Fixed

- **Sensor state unavailability** - Sensors now properly expose state through SensorEntity
  - Fixed Entity → SensorEntity inheritance
  - Proper state property naming (native_value vs state)
  - Handles nested API responses with metadata
- **Device tracker unavailability** - Device tracker now receives webhook updates
  - Subscribes to webhook signals like sensors
  - Proper state management through TrackerEntity
  - Location updates trigger through webhook data
- **Vehicle object cache** - Cache now cleared on token operations
  - Ensures vehicle objects always have fresh authentication credentials
  - Prevents authentication failures from stale cached vehicles
- **Reauth flow creates duplicate entries** - Fixed reauth flow to update existing entry instead of creating new one
- **Authentication error handling** - Integration now automatically attempts token refresh before triggering reauth
  - Catches authentication errors during setup and periodic updates
  - Attempts automatic token refresh first
  - Only prompts for re-authorization if refresh fails
- **Webhook import naming conflict** - Renamed `webhook` import to `ha_webhook` to avoid collision
- **OptionsFlow config_entry property issue** - Removed custom `__init__` that was conflicting with base class
- **Missing auth_implementation handling** - Added defensive checks for missing OAuth implementation
- **Data structure access in platforms** - Fixed all platforms (sensor, lock, climate, device_tracker) to properly access client from dict structure
- **Service handler data access** - Fixed service handlers to get client from `hass.data` on each call instead of using closure
- **Periodic update timer cleanup** - Added proper cancellation of periodic update listener in `async_unload_entry` to prevent lingering timers
- **Periodic update data access** - Fixed periodic update function to get client from `hass.data` instead of closure
- Non-blocking async operations using asyncio.to_thread() for all Smartcar SDK calls
- **Enhanced documentation**
  - Comprehensive single README with all documentation consolidated
  - Complete entity reference with descriptions and requirements
  - Detailed webhook setup guide with troubleshooting
  - OAuth permissions reference with vehicle compatibility
  - Vehicle compatibility information and limitations
  - FAQ section addressing common questions
  - Automation examples for common use cases
  - Clear notes about feature availability by vehicle year/model
  - Troubleshooting guide for missing entities and common issues

### Changed

- **BREAKING**: Migrated to OAuth2 Application Credentials flow
  - Now uses Home Assistant's built-in OAuth2 framework
  - Requires adding application credentials before integration setup
  - Eliminates manual redirect URI configuration
  - Must use `https://my.home-assistant.io/redirect/oauth` as redirect URI
- Integration `iot_class` changed from `cloud_polling` to `cloud_push` (when webhooks configured)
- Improved OAuth state management and reliability
- Enhanced reauth support for expired credentials
- Fixed blocking I/O operations that could cause event loop warnings
- Documentation now clearly explains that entity availability depends on vehicle capabilities

### Migration Guide

**For Existing Users:**

1. Note your current Smartcar Client ID and Client Secret
2. Remove existing integration instance
3. Update Smartcar app redirect URI to: `https://my.home-assistant.io/redirect/oauth`
4. Add Application Credentials in Home Assistant (Settings > Application Credentials)
5. Re-add the integration using the new OAuth2 flow
6. (Optional) Configure webhooks by adding Management Token in integration options

## [0.0.1] - 2026-01-02

### Initial Release

- Initial release of the Nissan North America Home Assistant integration.
- Support for vehicle sensors, lock, climate, and device tracker.
- Service calls for lock/unlock, engine start/stop, find vehicle, and refresh status.
- HACS support and user-friendly configuration.
- Automated versioning and changelog workflows.
- Comprehensive test coverage and documentation.
