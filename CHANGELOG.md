# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed

- **BREAKING**: Migrated to OAuth2 Application Credentials flow
  - Now uses Home Assistant's built-in OAuth2 framework
  - Requires adding application credentials before integration setup
  - Eliminates manual redirect URI configuration
  - Must use `https://my.home-assistant.io/redirect/oauth` as redirect URI
- Improved OAuth state management and reliability
- Enhanced reauth support for expired credentials

### Migration Guide

**For Existing Users:**
1. Note your current Smartcar Client ID and Client Secret
2. Remove existing integration instance
3. Update Smartcar app redirect URI to: `https://my.home-assistant.io/redirect/oauth`
4. Add Application Credentials in Home Assistant (Settings > Application Credentials)
5. Re-add the integration using the new OAuth2 flow

## [0.0.1] - 2026-01-02

### Added

- Initial release of the Nissan North America Home Assistant integration.
- Support for vehicle sensors, lock, climate, and device tracker.
- Service calls for lock/unlock, engine start/stop, find vehicle, and refresh status.
- HACS support and user-friendly configuration.
- Automated versioning and changelog workflows.
- Comprehensive test coverage and documentation.
