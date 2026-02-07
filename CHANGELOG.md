# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

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
