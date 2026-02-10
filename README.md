# Nissan North America for Home Assistant (Smartcar)

![GitHub release](https://img.shields.io/github/v/release/atheismann/home-assistant-nissan-na?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/atheismann/home-assistant-nissan-na?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/atheismann/home-assistant-nissan-na?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)
![HACS badge](https://img.shields.io/badge/HACS-Custom-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)

Easily control and monitor your Nissan vehicle from Home Assistant using the **Smartcar API**! This integration provides reliable, standardized access to your vehicle's features through Smartcar's platform, supporting lock/unlock, battery monitoring, location tracking, charging control, and more.

---

## Table of Contents

- [Features](#features)
- [Recent Updates & Improvements](#recent-updates--improvements)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Setup](#setup)
- [Configuration Options](#configuration-options)
- [Webhook Support (Real-time Updates)](#webhook-support-real-time-updates)
- [OAuth Permissions](#oauth-permissions)
- [Available Entities](#available-entities)
- [Services](#services)
- [Vehicle Compatibility](#vehicle-compatibility)
- [Troubleshooting](#troubleshooting)
- [Debugging & Logging](#debugging--logging)
- [FAQ](#faq)
- [Automation Examples](#automation-examples)
- [Support & Contributing](#support--contributing)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Automation Examples](#automation-examples)
- [Support & Contributing](#support--contributing)

---

## Features

This integration uses the **Smartcar API** for reliable vehicle connectivity:

- **Stable API** - Actively maintained by Smartcar
- **Secure** - OAuth 2.0 authentication with comprehensive permissions
- **Standardized** - Consistent commands across vehicles
- **Real-time updates** - Optional webhook support for instant notifications
- **Well-documented** - Comprehensive API documentation

### What Can You Do?

- **Lock or unlock your doors** from anywhere
- **Check your battery level** (for EVs)
- **Monitor charging status** and control charging remotely
- **See your car's location** on the Home Assistant map
- **Check odometer, fuel level, tire pressure**
- **Monitor engine oil life and temperatures**
- **Track vehicle information** like make, model, and year
- **View vehicle alerts and diagnostics** for maintenance notifications
- **Monitor climate control status** and control remotely (if supported)
- **Check compass heading and speed** while driving
- **View charging location history and records** (for EVs)
- **Access service history** from your dealership
- **Control trunk/frunk** remotely (if supported by vehicle)

All features depend on your vehicle model and Smartcar's support for your specific vehicle. The integration requests 32 comprehensive permissions to maximize compatibility across all Nissan models.

> **Note:** Remote engine start/stop is not currently available through the Smartcar API. This functionality will be added to the integration when Smartcar adds support for engine control commands.

---

## What's New

### 🚀 Comprehensive Entity Coverage

**58 Total Entities** (up from 10) with intelligent signal validation:

- **31 Sensors**: Battery, charging, fuel, tires, vehicle status, location, and more
- **25 Binary Sensors**: Doors, windows, trunks, connectivity status
- **1 Switch**: Charging control (start/stop)
- **1 Number**: Charge limit setting (0-100%)
- Plus existing: Lock, Device Tracker, Climate

### 🎯 Smart Entity Discovery

- **Dynamic entity creation** - Only shows entities your vehicle actually supports
- **Three-level validation** - Uses Smartcar signals API, OAuth permissions, and data checks
- **No unavailable entities** - Respects your vehicle's specific capabilities
- **Automatic detection** - Discovers available features at setup and reload

### 🔄 Enhanced Features

- **Unit System Configuration** - Switch between metric and imperial units (NEW!)
- **Entity Reload Option** - Discover new sensors after upgrades
- **Diagnostics Support** - View webhook URL and integration status
- **Real-time Webhooks** - Instant updates for all entity types
- **Comprehensive Logging** - Detailed debug information for troubleshooting

### ⚡ What You Can Monitor & Control

**Battery & Charging** (EVs):
- Battery percentage, range, and capacity
- Charging state, voltage, current, and power
- Time to full charge and max current
- Charge limit control (set target %)
- Charging switch (start/stop)

**Doors & Security**:
- All 4 doors (open status + lock status)
- All 4 windows (open status)
- Front and rear trunks (open + lock)
- Engine cover and sunroof

**Vehicle Status**:
- Tire pressure (all 4 wheels)
- Current gear, oil life, software version
- GPS location (latitude/longitude)
- Odometer and fuel level

**Connectivity**:
- Vehicle online/offline status
- Sleep mode status
- Digital key pairing
- Surveillance system

See the [CHANGELOG](CHANGELOG.md) for complete details.

---

## Prerequisites

Before installing, you need to:

1. **Create a Smartcar Developer Account**
   - Go to [Smartcar Dashboard](https://dashboard.smartcar.com)
   - Sign up for a free account (no credit card required for testing)

2. **Create a Smartcar Application**
   - In the dashboard, create a new application
   - Set the **Redirect URI** to: `https://my.home-assistant.io/redirect/oauth`
   - **Important**: Must use the My Home Assistant redirect service
   - Note your **Client ID** and **Client Secret** (you'll enter these in Home Assistant)

3. **Connect Your Nissan Vehicle**
   - Your vehicle must be compatible with Smartcar
   - Check compatibility at [Smartcar's website](https://smartcar.com/docs/api-reference/compatibility/)
   - You'll need your Nissan account credentials during OAuth authorization

---

## Installation

### Method 1: HACS (Recommended)

1. In Home Assistant, go to **HACS > Integrations > Custom Repositories**
2. Add the URL of this repository as a custom repository (choose "Integration")
3. Search for "Nissan North America" in HACS and install
4. Restart Home Assistant

### Method 2: Manual Installation

1. Download or copy the `nissan_na` folder into your Home Assistant `custom_components` directory
2. Restart Home Assistant

---

## Setup

### Step 1: Add Application Credentials (One-time Setup)

1. Go to **Settings > Devices & Services > Application Credentials**
2. Click **Add Application Credential**
3. Select **Nissan North America (Smartcar)**
4. Enter your **Smartcar Client ID** and **Client Secret**
5. Save the credentials

### Step 2: Add the Integration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "Nissan North America" and select it
3. Click the authorization link to connect via Smartcar OAuth
4. Log in with your Nissan account and authorize access
5. Your Nissan vehicle will be automatically discovered and added!

**Note**: Application credentials are stored securely and can be reused for multiple integration instances.

---

## Configuration Options

You can adjust settings after setup:

1. Go to **Settings > Devices & Services** in Home Assistant
2. Find the Nissan North America integration and click **Configure**
3. A menu will appear with these options:

### Menu Options

#### Configure Units (Metric/Imperial)

- **NEW!** Switch between metric and imperial units of measurement
- **Metric**: kilometers (km), liters (L), Celsius (°C), bar
- **Imperial**: miles (mi), gallons (gal), Fahrenheit (°F), PSI
- Automatically converts and displays all applicable sensors
- Integration reloads automatically to apply the change
- Affects: Range, fuel/battery capacity, tire pressure, odometer, temperature sensors

#### Refresh All Sensors

- Manually fetch the latest vehicle data from the Smartcar API
- Updates all sensors with fresh data immediately
- Useful when you want current values without waiting for webhooks
- Shows count of successfully refreshed sensors

#### Re-load Entities

- Discover and load any new sensors not available in the previous integration version
- Perfect when upgrading the integration or when your vehicle gains new capabilities
- Shows initial sensor count, final count, and newly discovered sensors
- Re-scans vehicle status and available data from Smartcar API

#### Configure Webhooks

- Set up webhook support for real-time vehicle updates
- Enter your **Application Management Token** from Smartcar Dashboard
- View your webhook URL for registering in Smartcar Dashboard
- Optional but recommended for instant updates and reduced API usage

#### Re-authorize Integration

- Manually refresh OAuth tokens when needed
- Update permissions when new features are added
- Typically not needed as tokens refresh automatically
- Only use when automatic token refresh fails or new permissions are required

### Viewing Integration Diagnostics

To view your webhook URL and integration status:

1. Go to **Settings > Devices & Services**
2. Click on the Nissan (Smartcar) integration
3. Click the three dots menu (⋮) and select **Download diagnostics** or **View diagnostics**
4. You'll see:
   - **Webhook ID** - Unique identifier for your webhook
   - **Webhook URL** - Full URL to provide to Smartcar Dashboard
   - **Vehicle Count** - Number of connected vehicles
   - **Sensor Count** - Number of active sensors

---

## Webhook Support (Real-time Updates)

The integration supports Smartcar webhooks for real-time vehicle updates instead of polling! This provides instant notifications when your vehicle's state changes.

### Benefits

- ⚡ **Real-time updates** - Receive vehicle state changes instantly
- 🔋 **Reduced API calls** - Lower costs and better rate limits (typically 10-20 calls/day vs 96 with polling)
- 📊 **More responsive** - Instant automation triggers
- 🌐 **Efficient** - Updates only when vehicle state actually changes

### Prerequisites for Webhooks

1. **Public HTTPS access to your Home Assistant instance**
   - Use Nabu Casa Cloud (recommended) OR
   - Configure a reverse proxy with valid SSL certificate
   - Webhook URL must be accessible from the internet

2. **Smartcar Application Management Token**
   - Available in your Smartcar Dashboard
   - Required for webhook signature verification


### Setup Steps

#### 1. Get Your Management Token

1. Log in to [Smartcar Dashboard](https://dashboard.smartcar.com)
2. Navigate to your application settings
3. Find and copy your **Application Management Token**
   - This is different from your Client ID and Client Secret
   - It's used to verify webhook signatures

#### 2. Configure Home Assistant

1. Go to **Settings > Devices & Services**
2. Find **Nissan North America** integration
3. Click **Configure**
4. Select **Configure Webhooks** from the menu
5. Enter your **Application Management Token**
6. Note the **Webhook URL** displayed (it will look like):

   ```text
   https://your-ha-url/api/webhook/XXXXXXXX
   ```

7. Save the configuration

#### 3. Register Webhook in Smartcar Dashboard

1. In the Smartcar Dashboard, navigate to **Webhooks**
2. Click **Create Webhook** (or **Add Webhook**)
3. Enter your webhook configuration:

   **Webhook URL**: `https://your-ha-url/api/webhook/XXXXXXXX`
   - Copy this exactly from your Home Assistant logs

   **Select Event Types**:
   - `vehicle.state` - For state changes
   - `vehicle.error` - For error notifications

   **Configure Signals** (choose what you want to monitor):
   - `battery.percentRemaining` - Battery level changes
   - `location` - Vehicle location updates
   - `charge.state` - Charging status changes
   - `odometer` - Mileage updates
   - `fuel.percentRemaining` - Fuel level changes
   - `tires.pressure` - Tire pressure changes
   - `engineOil.lifeRemaining` - Oil life changes
   - And more...

   **Set Triggers** (optional):
   - Battery changes by X%
   - Location changes by X meters
   - Time-based intervals

4. Click **Create** or **Save**

#### 4. Verify Webhook

After creating the webhook in the Smartcar Dashboard:

1. Smartcar will send a `VERIFY` event to your webhook URL
2. The integration automatically handles this verification
3. Check your Home Assistant logs for successful verification
4. Once verified, Smartcar will begin sending real-time updates

### How It Works

The integration handles three types of webhook events:

1. **VERIFY** - Initial webhook URL verification
   - Sent when you first create the webhook
   - Automatically handled by the integration
   - Uses HMAC-SHA256 challenge-response

2. **VEHICLE_STATE** - Vehicle data updates
   - Sent when monitored signals change
   - Contains latest vehicle data
   - Triggers entity updates in Home Assistant

3. **VEHICLE_ERROR** - Error notifications
   - Sent when Smartcar encounters errors
   - Logged for debugging
   - Doesn't affect integration functionality

### Security

All webhook payloads are verified using HMAC-SHA256 signatures:

- Smartcar signs each webhook with your Application Management Token
- The integration verifies signatures before processing
- Invalid signatures are rejected (HTTP 401)
- This ensures webhooks actually come from Smartcar

### Webhook Troubleshooting

#### Webhook Not Receiving Data

- Verify your HA instance is accessible from the internet
- Check HTTPS is working with a valid SSL certificate
- Ensure the webhook URL matches exactly (including the webhook ID)
- Test with: `curl -k https://your-ha-url/api/webhook/XXXXXXXX` (should return HTTP 200)
- Check logs: Look for "Webhook request received" to confirm webhook is being called

#### Invalid Signature Errors

- Check Management Token is correctly entered in HA configuration
- Verify Management Token hasn't been regenerated in Smartcar Dashboard
- Re-enter your Management Token in Integration > Configure
- Check logs: Look for "Invalid webhook signature" to confirm signature validation failed

#### Webhook Not Verified

- Check Home Assistant logs during webhook creation
- Ensure VERIFY event was received and processed
- Look for "Webhook VERIFY challenge verified successfully" in logs
- Delete and re-create webhook in Smartcar Dashboard if still failing

#### No Real-time Updates

- Verify webhook signals are properly configured in Smartcar Dashboard
- Check triggers are set appropriately
- Make a change to your vehicle (lock/unlock) to test

> **Note:** Without webhooks, the integration will continue to work using polling at your configured update interval.

### Automatic Token Refresh

The integration **automatically renews OAuth tokens** when they expire, eliminating the need for manual re-authorization in most cases. Here's how it works:

1. **Access tokens** expire after a short period (typically 2 hours)
2. The integration automatically refreshes them using the refresh token
3. New tokens are saved to the config entry for persistence across restarts
4. If a refresh fails, the integration attempts one more time
5. Only if all refresh attempts fail will you be prompted to re-authorize

### Manual Re-authorization

Manual re-authorization is rarely needed but may be required when:

- **New features are added** that require additional OAuth permissions
- **The refresh token expires** (typically after 60 days of inactivity)
- **Smartcar API changes** require updated credentials
- **Automatic token refresh fails** repeatedly

**To manually re-authorize:**

1. Go to **Settings > Devices & Services**
2. Find **Nissan North America** integration and click **Configure**
3. Select **Re-authorize Integration** from the configuration menu
4. Click **Submit** to start the OAuth flow
5. Log in to your Nissan account and grant permissions
6. You'll be redirected back to Home Assistant

**Note:** The integration will attempt automatic token refresh before showing any re-authorization prompts. You'll only see a notification if automatic refresh is not possible.

---

## OAuth Permissions

The integration requests **32 comprehensive Smartcar permissions** to ensure compatibility across all Nissan models, years, and trims. Not all permissions will be available for every vehicle - availability depends on your vehicle model, year, trim level, and regional support.

When a permission is not supported by your vehicle, the corresponding entities simply won't appear in Home Assistant.

### Required Permissions

These permissions are mandatory for basic integration functionality:

| Permission                       | Purpose                              | Entities Created         |
| -------------------------------- | ------------------------------------ | ------------------------ |
| `required:read_vehicle_info` | Vehicle identification and details | Device info, VIN sensor |
| `required:read_location` | GPS location tracking | Device tracker |
| `required:read_odometer` | Mileage tracking | Odometer sensor |
| `required:control_security` | Door lock/unlock | Lock entity |

### Electric Vehicle / Battery Permissions

Enhanced permissions for electric and hybrid vehicles:

| Permission              | Purpose                        |
| ----------------------- | ------------------------------ |
| `read_battery`          | Battery level monitoring       |
| `read_charge` | Charging status |
| `control_charge` | Start/stop charging |
| `read_charge_locations` | Charging location history |
| `read_charge_records` | Charging session billing info |

### General Vehicle Data Permissions

Standard vehicle monitoring capabilities:

| Permission              | Purpose                        |
| ----------------------- | ------------------------------ |
| `read_fuel` | Fuel level for gas vehicles |
| `read_vin` | Vehicle identification number |
| `read_security` | Door lock status |
| `read_tires` | Tire pressure monitoring |
| `read_engine_oil` | Oil life monitoring |
| `read_thermometer` | Temperature sensors |
| `read_speedometer` | Current vehicle speed |
| `read_compass` | Compass heading |

### Climate Control Permissions

HVAC system monitoring and control:

| Permission        | Purpose                   |
| ----------------- | ------------------------- |
| `read_climate` | Climate system status |
| `control_climate` | Remote climate control |

### Advanced Diagnostic Permissions

Maintenance and health monitoring:

| Permission                      | Purpose                            |
| ------------------------------- | ---------------------------------- |
| `read_alerts` | Vehicle warnings and alerts |
| `read_diagnostics` | System diagnostics and DTCs |
| `read_extended_vehicle_info` | Additional vehicle configuration |
| `read_service_history` | Dealership service records |
| `read_user_profile` | Connected account information |

### Additional Control Permissions

Advanced remote control capabilities:

| Permission           | Purpose                          |
| -------------------- | -------------------------------- |
| `control_navigation` | Send destinations to vehicle |
| `control_trunk` | Remote trunk/frunk control |

### Why Request All Permissions?

**Maximize Compatibility**: By requesting comprehensive permissions upfront:

- ✅ Users with newer vehicles get all available features automatically
- ✅ No need to reconfigure when vehicle capabilities are updated
- ✅ Ensures compatibility across different Nissan models
- ✅ Future-proofs the integration as Smartcar adds support for more features

**User Privacy**:

- Permissions that aren't supported by your vehicle are never granted
- Even if granted, the integration only uses permissions to retrieve/control vehicle features
- No data is shared with third parties beyond Smartcar's API

---

## Available Entities

The integration creates up to **58 entities** for your vehicle. **Entity availability depends on your vehicle's capabilities.** The integration uses Smartcar's signals API to intelligently detect which features your specific vehicle supports - only relevant entities will appear.

### Lock Entity

| Entity | Description | Requirements |
|--------|-------------|--------------|
| **Door Lock** | Lock/unlock vehicle doors | `control_security` |

### Device Tracker

| Entity | Description | Requirements |
|--------|-------------|--------------|
| **Vehicle Location** | GPS location on Home Assistant map | `read_location` |

### Climate Entity

| Entity | Description | Requirements |
|--------|-------------|--------------|
| **Climate Control** | Start/stop climate system (HVAC) | `control_climate` |

**Note**: Climate control availability varies by model. HVAC modes (HEAT/COOL/AUTO) all start the climate system; only OFF stops it.

### Sensors (31 Total)

#### Battery Sensors (EVs)

| Sensor | Description | Unit | Signal ID |
|--------|-------------|------|-----------|
| **Battery Percentage** | Current charge level | % | `battery.percentRemaining` |
| **Battery Range** | Estimated driving range | km/mi | `battery.range` |
| **Battery Capacity** | Total battery capacity | kWh | `battery.capacityKwh` |
| **Low Voltage Battery** | 12V auxiliary battery | % | `battery.lowBatteryPercentRemaining` |

#### Charging Sensors (EVs)

| Sensor | Description | Unit | Signal ID |
|--------|-------------|------|-----------|
| **Charging Status** | Current charging state | - | `charge.state` |
| **Charge Voltage** | Charging voltage | V | `charge.voltage` |
| **Charge Current** | Charging amperage | A | `charge.amperage` |
| **Charge Power** | Charging wattage | W | `charge.wattage` |
| **Time to Full** | Estimated charge time | min | `charge.timeToComplete` |
| **Max Current** | Maximum charge current | A | `charge.amperageMax` |
| **Charge Limit** | Target charge percentage | % | `charge.limit` |

#### Fuel Sensors (Gas Vehicles)

| Sensor | Description | Unit | Signal ID |
|--------|-------------|------|-----------|
| **Fuel Amount** | Fuel remaining | L | `fuel.amountRemaining` |
| **Fuel Percentage** | Fuel tank level | % | `fuel.percentRemaining` |
| **Fuel Range** | Estimated range | km/mi | `fuel.range` |

#### Tire Sensors

| Sensor | Description | Unit | Signal ID |
|--------|-------------|------|-----------|
| **Front Left Tire** | Tire pressure | PSI/kPa | `tires.frontLeft.pressure` |
| **Front Right Tire** | Tire pressure | PSI/kPa | `tires.frontRight.pressure` |
| **Rear Left Tire** | Tire pressure | PSI/kPa | `tires.backLeft.pressure` |
| **Rear Right Tire** | Tire pressure | PSI/kPa | `tires.backRight.pressure` |

#### Vehicle Status Sensors

| Sensor | Description | Unit | Signal ID |
|--------|-------------|------|-----------|
| **Current Gear** | Transmission gear | - | `drivetrain.currentGear` |
| **Oil Life** | Remaining oil life | % | `engine.oilLifeRemaining` |
| **Software Version** | Vehicle firmware | - | `vehicle.softwareVersion` |
| **Odometer** | Total distance | km/mi | `odometer.value` |

#### Location Sensors

| Sensor | Description | Unit | Signal ID |
|--------|-------------|------|-----------|
| **Latitude** | GPS latitude | ° | `location.latitude` |
| **Longitude** | GPS longitude | ° | `location.longitude` |

#### Connectivity Sensors

| Sensor | Description | Signal ID |
|--------|-------------|-----------|
| **Vehicle Online** | Connection status | `connectivity.isOnline` |
| **Vehicle Asleep** | Sleep mode status | `connectivity.isAsleep` |
| **Digital Key Paired** | Digital key status | `connectivity.isDigitalKeyPaired` |

#### Other Sensors

| Sensor | Description | Signal ID |
|--------|-------------|-----------|
| **Surveillance Enabled** | Surveillance system | `surveillance.isEnabled` |
| **Battery Heater Active** | Battery heater status | `batteryHeater.isHeaterActive` |

### Binary Sensors (25 Total)

#### Door Sensors

| Sensor | Description | Signal ID |
|--------|-------------|-----------|
| **Front Left Door** | Door open status | `doors.frontLeft.isOpen` |
| **Front Left Door Lock** | Door lock status | `doors.frontLeft.isLocked` |
| **Front Right Door** | Door open status | `doors.frontRight.isOpen` |
| **Front Right Door Lock** | Door lock status | `doors.frontRight.isLocked` |
| **Rear Left Door** | Door open status | `doors.rearLeft.isOpen` |
| **Rear Left Door Lock** | Door lock status | `doors.rearLeft.isLocked` |
| **Rear Right Door** | Door open status | `doors.rearRight.isOpen` |
| **Rear Right Door Lock** | Door lock status | `doors.rearRight.isLocked` |

#### Window Sensors

| Sensor | Description | Signal ID |
|--------|-------------|-----------|
| **Front Left Window** | Window open status | `windows.frontLeft.isOpen` |
| **Front Right Window** | Window open status | `windows.frontRight.isOpen` |
| **Rear Left Window** | Window open status | `windows.rearLeft.isOpen` |
| **Rear Right Window** | Window open status | `windows.rearRight.isOpen` |

#### Trunk Sensors

| Sensor | Description | Signal ID |
|--------|-------------|-----------|
| **Front Trunk** | Front trunk/hood open | `trunks.front.isOpen` |
| **Front Trunk Lock** | Front trunk lock | `trunks.front.isLocked` |
| **Rear Trunk** | Rear trunk open | `trunks.rear.isOpen` |
| **Rear Trunk Lock** | Rear trunk lock | `trunks.rear.isLocked` |

#### Other Binary Sensors

| Sensor | Description | Signal ID |
|--------|-------------|-----------|
| **Engine Cover** | Engine cover open | `engineCover.isOpen` |
| **Sunroof** | Sunroof open status | `sunroof.isOpen` |
| **Charging Cable** | Cable plugged in | `chargingCable.isPluggedIn` |
| **Fast Charger** | DC fast charger | `fastCharger.isConnected` |
| **Battery Heater** | Heater active | `batteryHeater.isHeaterActive` |
| **Online Status** | Vehicle online | `connectivity.isOnline` |
| **Sleep Status** | Vehicle asleep | `connectivity.isAsleep` |
| **Digital Key** | Digital key paired | `connectivity.isDigitalKeyPaired` |
| **Surveillance** | Surveillance enabled | `surveillance.isEnabled` |

### Control Entities

#### Switch

| Entity | Description | Requirements |
|--------|-------------|--------------|
| **Charging** | Start/stop charging | `control_charge` |

#### Number

| Entity | Description | Range | Requirements |
|--------|-------------|-------|--------------|
| **Charge Limit** | Set target charge % | 0-100% | `control_charge` |

### Important Notes

⚠️ **Smart Entity Discovery**: The integration automatically detects which entities your vehicle supports using Smartcar's signals API. Only compatible entities will appear - you won't see unavailable entities for features your vehicle doesn't have.

🔍 **Missing Expected Entities?**
- Check [Smartcar's compatibility page](https://smartcar.com/docs/api-reference/compatibility/) for your vehicle
- EV-specific sensors only appear on electric vehicles
- Door/window sensors require your vehicle to support those signals
- Some features may require specific trim levels or model years

📊 **Checking Compatibility**: Visit the [Smartcar Compatibility Dashboard](https://smartcar.com/docs/api-reference/compatibility/) and search for your vehicle to see which features are supported.

---

## Services

Call these services from automations or the Developer Tools:

### `nissan_na.lock_doors`

Lock the vehicle doors.

```yaml
service: nissan_na.lock_doors
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.unlock_doors`

Unlock the vehicle doors.

```yaml
service: nissan_na.unlock_doors
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.start_charge`

Start charging the vehicle (EVs only).

```yaml
service: nissan_na.start_charge
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.stop_charge`

Stop charging the vehicle (EVs only).

```yaml
service: nissan_na.stop_charge
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.refresh_status`

Force a refresh of vehicle status.

```yaml
service: nissan_na.refresh_status
data:
  vehicle_id: "your-vehicle-id"
```

**Note**: Get the `vehicle_id` from entity attributes, not the VIN.

---

## Vehicle Compatibility

The integration requests comprehensive permissions to maximize compatibility, but actual feature availability varies by vehicle.

### Nissan Leaf (Electric)

✅ **Highly Compatible** - All EV-related permissions supported

- Full battery monitoring and control
- Charging status and control
- Climate control (pre-conditioning)
- All standard vehicle data
- Tire pressure monitoring
- Service alerts

### Nissan Ariya (Electric)

✅ **Highly Compatible** - Latest EV technology

- Enhanced battery management
- Bidirectional charging information
- Advanced climate controls
- Full diagnostic support
- Service history integration

### Nissan Altima / Maxima / Sentra (Gas)

⚠️ **Partial Compatibility** - Connected services required

- Basic vehicle location
- Door lock/unlock
- Odometer reading
- Fuel level (if equipped with connected services)
- Tire pressure (TPMS required)
- Limited climate control on newer models

### Nissan Rogue / Pathfinder / Murano (Gas/Hybrid)

⚠️ **Variable Compatibility** - Depends on year and trim

- Connected services required
- Hybrid models may support battery monitoring
- Advanced trims have more features
- Service history on newer models

### Checking Your Vehicle's Compatibility

**Method 1: Smartcar Compatibility API**  
Visit https://smartcar.com/docs/api-reference/compatibility/ to check specific features for your VIN.

**Method 2: Try the Integration**  
The safest approach is to install and configure the integration:

1. During OAuth authorization, Smartcar will only request permissions your vehicle supports
2. After setup, only compatible entities will appear in Home Assistant
3. Missing entities indicate unsupported features

**Method 3: Smartcar Dashboard**  
Log in to your Smartcar Dashboard at https://dashboard.smartcar.com to see which permissions were granted for your vehicle.

---

## Troubleshooting

### OAuth Authentication Issues

- Ensure **Redirect URI** in Smartcar is set to: `https://my.home-assistant.io/redirect/oauth`
- Verify your **Client ID** and **Client Secret** are correct in Application Credentials
- Check that your Home Assistant instance is accessible externally
- Try removing and re-adding the application credentials if authentication fails

### Application Credentials Not Found

- Go to **Settings > Devices & Services > Application Credentials**
- Add credentials for **Nissan North America (Smartcar)**
- You must add credentials before adding the integration

### No Vehicles Found

- Verify your Nissan account has vehicles registered
- Check [Smartcar compatibility](https://smartcar.com/docs/api-reference/compatibility/)
- Ensure your vehicle supports connected services
- Verify NissanConnect subscription is active

### Token Expired Errors

- The integration automatically refreshes tokens
- If persistent, try removing and re-adding the integration

### Rate Limiting

- Smartcar has API rate limits (varies by plan)
- Increase your update interval if you see rate limit errors
- Consider using webhooks to reduce API calls

### Services Not Working

- **Common Issue**: Using VIN instead of vehicle_id
- **Solution**: Get vehicle_id from entity attributes and use it in service calls

---

## Debugging & Logging

### Enable Debug Logging

To troubleshoot issues, enable debug logging for the integration:

#### Option 1: Via Home Assistant UI

1. Go to **Settings > Devices & Services**
2. Find **Nissan North America** and click **Enable Debug Logging**
3. Check logs in **Settings > System > Logs** to see detailed output

#### Option 2: Via configuration.yaml

```yaml
logger:
  logs:
    custom_components.nissan_na: debug
    custom_components.nissan_na.webhook: debug
    custom_components.nissan_na.nissan_api: debug
```

### What to Look For in Logs

#### Webhook Setup and Verification
```
INFO - Webhook registered at: http://10.1.0.96:8123/api/webhook/...
INFO - Configure this URL in your Smartcar Dashboard to receive real-time updates
INFO - Webhook VERIFY challenge verified successfully
```

#### Successful Webhook Data Reception
```
INFO - Webhook signature verified for vehicle af1ff81d-...
INFO - Vehicle state update received for af1ff81d-... with 3 data fields
DEBUG - Vehicle state data: {'odometer': {...}, 'location': {...}, 'battery': {...}}
DEBUG - Dispatching signal: nissan_na_webhook_data_af1ff81d-...
INFO - Sensor 2025 NISSAN PATHFINDER Odometer updated via webhook: 6218.5 -> 6225.3
```

#### Common Errors to Debug

**"No config entry found for webhook"**
- Webhook ID doesn't match configured webhook
- Webhook not properly registered during integration setup

**"Invalid webhook signature"**
- Management token is incorrect
- Management token was regenerated in Smartcar Dashboard
- Solution: Re-enter Management Token in integration configuration

**"Missing SC-Signature header"**
- Webhook not being sent from Smartcar
- Smartcar Dashboard webhook configuration issue
- Solution: Delete and recreate webhook in Smartcar Dashboard

**"Webhook data received but sensors not updating"**
- Sensors not subscribed to webhook signal (should see DEBUG logs)
- State not being written to Home Assistant
- Check for errors in Home Assistant logs

### API Data Structure

The Smartcar API returns nested responses with metadata. The integration automatically extracts the numeric values:

```json
{
  "odometer": {"distance": 6218.5, "meta": {...}},
  "location": {"latitude": 37.7749, "longitude": -122.4194, ...},
  "battery": {"level": 85, "meta": {...}}
}
```

The integration extracts and properly handles:
- Simple values: `{"level": 85}` → `85`
- Nested with metadata: `{"distance": 6218.5, "meta": {...}}` → `6218.5`
- Location objects: `{"lat": 37.7749, "lon": -122.4194}` → `"37.7749,-122.4194"`

---

## FAQ

### Why don't I see all the sensors listed in the documentation?

Not all Nissan vehicles support all features. The sensors that appear depend on:

- Your vehicle's year, make, and model
- Your vehicle's trim level and optional packages
- Whether your vehicle is electric or gas-powered
- What data Smartcar supports for your specific vehicle

Check [Smartcar's compatibility page](https://smartcar.com/docs/api-reference/compatibility/) to see which features are available for your vehicle.

### My vehicle isn't connecting or shows errors

Try these troubleshooting steps:

1. Verify your vehicle is compatible with Smartcar
2. Check that your Nissan account credentials are correct
3. Ensure your vehicle's telematics service is active and paid up
4. Try removing and re-adding the integration
5. Check Home Assistant logs for specific error messages

### Can I start my engine remotely?

No. Remote engine start/stop is not currently available through the Smartcar API. The integration includes climate control which may start the engine on some vehicles, but there's no direct engine start command. This will be added if Smartcar adds support in the future.

### Why is the battery/charging information missing? I have an electric Nissan Leaf/Ariya

Make sure:

1. Your vehicle is actually connected to Smartcar (check the Smartcar dashboard)
2. The `read_battery` and `read_charge` permissions were granted during OAuth
3. Your vehicle's year/model supports these features in Smartcar
4. Try refreshing the integration or restarting Home Assistant

Some older Leaf models may have limited data available through Smartcar.

### How often does the integration update vehicle data?

By default, the integration polls every 15 minutes. You can adjust this in the integration options (5-60 minutes). With webhooks configured, updates happen in real-time when vehicle state changes. Be aware of Smartcar's API rate limits when setting shorter intervals.

### Can I control multiple vehicles?

Yes! Each vehicle connected to your Nissan/Smartcar account will automatically appear as a separate device in Home Assistant with its own set of entities.

### Does this work with Infiniti vehicles?

This integration is specifically for Nissan vehicles in North America. However, since Infiniti is Nissan's luxury brand and shares technology, it may work with some Infiniti models. You would need to:

1. Try connecting your Infiniti through Smartcar
2. Select "Nissan" or "Infiniti" (if available) during OAuth
3. Check Smartcar's compatibility list for your specific Infiniti model

### What's the difference between this and the official Nissan integration?

This integration uses Smartcar's API instead of Nissan's direct API:

- **Smartcar**: Actively maintained, standardized API, broad vehicle support, requires paid Smartcar account for heavy usage
- **Official Nissan**: Direct Nissan API access, may have different features, depends on Nissan's API availability

Choose based on your needs and which API works better for your vehicle.

### Why does the integration show my car is X km/miles away from home?

The GPS location sensor shows your vehicle's last reported location. If the location seems incorrect:

- The vehicle may have moved since the last update
- GPS accuracy varies (typically 10-50 meters)
- The vehicle may be in a garage or area with poor GPS signal
- Try forcing a status refresh to get the latest location

### Is my data secure?

Yes. This integration uses OAuth2 for authentication, meaning your Nissan credentials are never stored in Home Assistant. Authentication happens directly with Smartcar. Communication is encrypted via HTTPS. For webhooks, all payloads are verified using HMAC-SHA256 signatures.

### Is this free?

Smartcar offers a free developer tier. Check [Smartcar pricing](https://smartcar.com/pricing/) for usage limits. The integration itself is free and open source.

---

## Automation Examples

### Lock doors when leaving home

```yaml
automation:
  - alias: "Lock Nissan when leaving"
    trigger:
      - platform: zone
        entity_id: person.your_name
        zone: zone.home
        event: leave
    action:
      - service: nissan_na.lock_doors
        data:
          vehicle_id: "your-vehicle-id"
```

### Notify when charging complete

```yaml
automation:
  - alias: "Nissan charging complete"
    trigger:
      - platform: state
        entity_id: sensor.nissan_leaf_charging_status
        to: "fully_charged"
    action:
      - service: notify.mobile_app
        data:
          message: "Your Leaf is fully charged!"
```

### Start climate before departure

```yaml
automation:
  - alias: "Pre-condition Nissan"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday_sensor
        state: "on"
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.nissan_leaf_climate
        data:
          hvac_mode: "heat"
```

### Alert on low battery

```yaml
automation:
  - alias: "Low battery alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nissan_leaf_battery_level
        below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Your Leaf battery is below 20%!"
```

---

## Support & Contributing

- **Issues**: [GitHub Issues](https://github.com/atheismann/home-assistant-nissan-na/issues)
- **Smartcar Docs**: [Smartcar API Documentation](https://smartcar.com/docs/)
- **Smartcar Webhooks**: [Webhooks Documentation](https://smartcar.com/docs/integrations/webhooks/overview/)
- **Home Assistant Forums**: [community.home-assistant.io](https://community.home-assistant.io/)

**Need help?** Open a GitHub issue with:

- Home Assistant version
- Vehicle make/model/year
- Error messages from logs
- Steps to reproduce the issue

Contributions welcome! Feel free to open issues or pull requests.

---

## Privacy & Disclaimer

This integration is not affiliated with or endorsed by Nissan or Smartcar. Your credentials are only used to authenticate with Smartcar's OAuth system and are never shared. Use at your own risk.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
