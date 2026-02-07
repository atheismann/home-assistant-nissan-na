# Nissan North America for Home Assistant (Smartcar)

![GitHub release](https://img.shields.io/github/v/release/atheismann/home-assistant-nissan-na?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/atheismann/home-assistant-nissan-na?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/atheismann/home-assistant-nissan-na?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)
![HACS badge](https://img.shields.io/badge/HACS-Custom-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)

Easily control and monitor your Nissan vehicle from Home Assistant using the **Smartcar API**! This integration provides reliable, standardized access to your vehicle's features through Smartcar's platform, supporting lock/unlock, battery monitoring, location tracking, charging control, and more.

---

This integration uses the **Smartcar API** for reliable vehicle connectivity:

- **Stable API** - Actively maintained by Smartcar
- **Secure** - OAuth 2.0 authentication
- **Standardized** - Consistent commands across vehicles
- **Well-documented** - Comprehensive API documentation

---

## What Can You Do?

- **Lock or unlock your doors** from anywhere
- **Check your battery level** (for EVs)
- **Monitor charging status** and control charging remotely
- **See your car's location** on the Home Assistant map
- **Check odometer, fuel level, and more**
- **Track vehicle information** like make, model, and year

All features depend on your vehicle model and Smartcar's support for your specific vehicle.

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

📖 **See [SETUP.md](SETUP.md) for detailed setup instructions and migration guide.**

---

## How to Install

### The Easy Way: HACS

1. In Home Assistant, go to HACS > Integrations > Custom Repositories.
2. Add the URL of this repository as a custom repository (choose "Integration").
3. Search for "Nissan North America" in HACS and install.
4. Restart Home Assistant.

### Manual Installation

1. Download or copy the `nissan_na` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

---

## How to Set Up

1. **Add Application Credentials** (one-time setup)
   - Go to **Settings > Devices & Services > Application Credentials**
   - Click **Add Application Credential**
   - Select **Nissan North America (Smartcar)**
   - Enter your **Smartcar Client ID** and **Client Secret**
   - Save the credentials

2. **Add the Integration**
   - Go to **Settings > Devices & Services > Add Integration**
   - Search for "Nissan North America" and select it
   - Click the authorization link to connect via Smartcar OAuth
   - Log in with your Nissan account and authorize access
   - Your Nissan vehicle will be automatically discovered and added!

**Note**: Application credentials are stored securely and can be reused for multiple integration instances.

---

## Configuration Options

You can adjust settings after setup:

1. Go to **Settings > Devices & Services** in Home Assistant.
2. Find the Nissan North America integration and click the three dots (⋮) > **Configure**.
3. Set your preferred **update interval** (5-60 minutes, default is 15).

---

## What Sensors and Controls Will I See?

Depending on your vehicle's capabilities:

- **Lock control**: Lock or unlock your doors
- **Location tracker**: See your car's current GPS location
- **Battery level**: Battery charge percentage (EVs)
- **Charging status**: Whether the vehicle is charging or plugged in
- **Charge control**: Start or stop charging remotely
- **Odometer**: Total mileage
- **Fuel level**: Fuel tank level (non-EVs)
- **Vehicle information**: Make, model, year, VIN

---

## Available Services

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

---

## Troubleshooting

### OAuth Authentication Issues
- Ensure **Redirect URI** in Smartcar is set to: `https://my.home-assistant.io/redirect/oauth`
- Verify your **Client ID** and **Client Secret** are correct in Application Credentials
- Check that your Home Assistant instance is accessible externally
- Try removing and re-adding the application credentials if authentication fails

### No Vehicles Found
- Verify your Nissan account has vehicles registered
- Check [Smartcar compatibility](https://smartcar.com/docs/api-reference/compatibility/)
- Ensure your vehicle supports connected services

### Token Expired Errors
- The integration automatically refreshes tokens
- If persistent, try removing and re-adding the integration

### Rate Limiting
- Smartcar has API rate limits (varies by plan)
- Increase your update interval if you see rate limit errors

---

## Support & Contributing

- **Issues**: [GitHub Issues](https://github.com/atheismann/home-assistant-nissan-na/issues)
- **Setup Guide**: See [SETUP.md](SETUP.md) for detailed instructions
- **Smartcar Docs**: [Smartcar API Documentation](https://smartcar.com/docs/)

Contributions welcome! Feel free to open issues or pull requests.

---

## Privacy & Disclaimer

This integration is not affiliated with or endorsed by Nissan or Smartcar. Your credentials are only used to authenticate with Smartcar's OAuth system and are never shared. Use at your own risk.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
