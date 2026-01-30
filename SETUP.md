# Setup Guide

Complete guide for setting up the Nissan North America integration with Smartcar.

---

## Table of Contents

- [Installation](#installation)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

1. **Create a Smartcar Developer Account**
   - Go to [Smartcar Dashboard](https://dashboard.smartcar.com)
   - Sign up for a free account

2. **Create a Smartcar Application**
   - In the dashboard, create a new application
   - Set **Redirect URI** to: `https://my.home-assistant.io/redirect/oauth`
     - Or use: `https://your-ha-url.com/auth/external/callback`
   - Save your **Client ID** and **Client Secret**

3. **Verify Vehicle Compatibility**
   - Check [Smartcar Compatibility](https://smartcar.com/docs/api-reference/compatibility/)

### Installation Steps

1. **Install via HACS**
   - HACS > Integrations > Custom Repositories
   - Add: `https://github.com/atheismann/home-assistant-nissan-na`
   - Search "Nissan North America" and install
   - Restart Home Assistant

2. **Configure Integration**
   - Settings > Devices & Services > Add Integration
   - Search "Nissan North America"
   - Enter your Smartcar **Client ID**, **Client Secret**, and **Redirect URI**
   - Click the authorization link
   - Log in with your Nissan account
   - Authorize access

3. **Done!**
   - Your vehicle(s) will appear as devices
   - Entities will be created automatically

---

## Troubleshooting

### OAuth Authentication Failed

**Solutions:**
- Verify Client ID and Client Secret are correct
- Ensure Redirect URI matches exactly in both Smartcar and HA
- Make sure Home Assistant is accessible via HTTPS
- Try `https://my.home-assistant.io/redirect/oauth` as redirect URI

### No Vehicles Found

**Solutions:**
- Check [vehicle compatibility](https://smartcar.com/docs/api-reference/compatibility/)
- Verify vehicle appears in Nissan mobile app
- Ensure NissanConnect subscription is active

### Token Expired Errors

**Solution:**
- Integration automatically refreshes tokens
- If persistent: remove and re-add integration

### Rate Limit Exceeded

**Solutions:**
- Increase update interval (Settings > Configure)
- Wait a few minutes before retrying
- Consider Smartcar plan limits

### Services Not Working

**Common Issue:** Using VIN instead of vehicle_id

**Solution:** 
- Get vehicle_id from entity attributes
- Update service calls to use vehicle_id

---

## Available Services

### `nissan_na.lock_doors`
```yaml
service: nissan_na.lock_doors
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.unlock_doors`
```yaml
service: nissan_na.unlock_doors
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.start_charge`
```yaml
service: nissan_na.start_charge
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.stop_charge`
```yaml
service: nissan_na.stop_charge
data:
  vehicle_id: "your-vehicle-id"
```

### `nissan_na.refresh_status`
```yaml
service: nissan_na.refresh_status
data:
  vehicle_id: "your-vehicle-id"
```

---

## FAQ

**Q: Is this free?**  
A: Smartcar offers a free developer tier. Check [pricing](https://smartcar.com/pricing/) for limits.

**Q: How often does data update?**  
A: Default is 15 minutes. Adjustable in integration options (5-60 min).


---

## Support

- **Issues**: [GitHub Issues](https://github.com/atheismann/home-assistant-nissan-na/issues)
- **Smartcar Docs**: [smartcar.com/docs](https://smartcar.com/docs/)
- **HA Forums**: [community.home-assistant.io](https://community.home-assistant.io/)

---

**Need more help?** Open a GitHub issue with:
- Home Assistant version
- Vehicle make/model/year
- Error messages from logs
- Steps to reproduce the issue
