# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **Automatic token refresh** - Access tokens now automatically renew when expired
  - Tokens are refreshed and persisted to config entry
  - Eliminates most manual re-authorization needs
  - Falls back to re-auth flow only if refresh token expires
- **Re-authorization capability** - Users can now manually re-authorize the integration from the options menu
  - Menu-based configuration UI with clear options
  - "Configure Webhooks" option for webhook setup
  - "Re-authorize Integration" option to grant updated permissions
  - Webhook URL now displayed directly in the configuration UI (no need to check logs)
- **Webhook support for real-time updates**
  - Integration now supports Smartcar webhooks for instant vehicle state updates
  - Eliminates need for constant polling when webhooks are configured
  - Handles VERIFY, VEHICLE_STATE, and VEHICLE_ERROR webhook events
  - HMAC-SHA256 signature verification for webhook security
  - Configuration option to add Application Management Token
  - Automatic webhook registration and URL generation
- Support for additional vehicle sensors:
  - Tire pressure monitoring
  - Engine oil life
  - Interior/exterior temperature
- **Expanded OAuth permissions for comprehensive Nissan compatibility**
  - Added read_alerts, read_diagnostics for vehicle alerts and maintenance notifications
  - Added read_climate, control_climate for climate system monitoring and control
  - Added read_speedometer, read_compass for real-time driving data
  - Added read_extended_vehicle_info for additional vehicle configuration details
  - Added read_service_history for dealership service records
  - Added read_user_profile for connected account information
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

### Added

- Initial release of the Nissan North America Home Assistant integration.
- Support for vehicle sensors, lock, climate, and device tracker.
- Service calls for lock/unlock, engine start/stop, find vehicle, and refresh status.
- HACS support and user-friendly configuration.
- Automated versioning and changelog workflows.
- Comprehensive test coverage and documentation.
