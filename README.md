# Nissan North America for Home Assistant

![GitHub release](https://img.shields.io/github/v/release/atheismann/home-assistant-nissan-na?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/atheismann/home-assistant-nissan-na?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/atheismann/home-assistant-nissan-na?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)
![HACS badge](https://img.shields.io/badge/HACS-Custom-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)

Easily control and monitor your Nissan vehicle from Home Assistant! This integration lets you lock/unlock your doors, start or stop your engine, check your car’s status, and see its location—all from your smart home dashboard.

---

## What Can You Do?

- **Lock or unlock your doors** from anywhere
- **Start or stop your engine** remotely (great for warming up or cooling down your car)
- **See your car’s location** on the Home Assistant map
- **Check your battery level, tire pressure, odometer, and more**
- **Find your car** by making it honk or flash its lights

All features depend on your vehicle model and your NissanConnect subscription.

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

1. In Home Assistant, go to **Settings > Devices & Services > Add Integration**.
2. Search for "Nissan North America" and select it.
3. Enter your NissanConnect username and password.
4. Choose how often you want Home Assistant to refresh your car’s data (default is every 15 minutes).
5. That’s it! Your Nissan will show up with sensors, lock controls, engine start/stop, and a map tracker.

---

## Changing How Often Data Updates

You can change how often Home Assistant refreshes your car’s data at any time:

1. Go to **Settings > Devices & Services** in Home Assistant.
2. Find the Nissan North America integration and click the three dots (⋮) > **Configure**.
3. Set your preferred update interval (in minutes) and save.

---

---

## What Sensors and Controls Will I See?

Depending on your vehicle, you may see:

- **Lock control**: Lock or unlock your doors
- **Engine control**: Start or stop your engine remotely
- **Location tracker**: See your car’s last known position
- **Battery level**: (for EVs/hybrids) See your battery charge
- **Charging status**: Know if your car is charging or plugged in
- **Odometer**: See your total mileage
- **Range**: Estimated driving range
- **Tire pressure**: For each tire (if supported)
- **Door/window status**: See if anything is open
- **Last update time**: When your car last sent data
- **Climate status**: If your car supports it

---

## Using Remote Actions

You can trigger actions from the Home Assistant UI, automations, or scripts:

- **Lock/Unlock**: Lock or unlock your car
- **Start/Stop Engine**: Remotely start or stop your engine
- **Find Vehicle**: Make your car honk or flash its lights
- **Refresh Status**: Get the latest info from your car

All actions require your car’s VIN (automatically detected for each vehicle on your account).

---

## Need Help?

- Make sure your NissanConnect credentials are correct and your subscription is active
- Some features may not be available for all models or in all regions
- If something isn’t working, try restarting Home Assistant after setup

---

## Privacy & Disclaimer

This integration is not affiliated with or endorsed by Nissan. Your login is only used to connect to Nissan’s servers and is never shared. Use at your own risk.

---

## Want to Help Improve This?

Feedback, bug reports, and suggestions are welcome! Open an issue or pull request on GitHub.
