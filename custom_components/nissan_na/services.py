#
# Nissan North America Home Assistant Integration - Service Documentation
#
# This file defines the available Home Assistant services for the Nissan NA integration.
#
# Each service requires a VIN (vehicle identification number) as input.
#
# Services:
#   lock_doors: Remotely lock the vehicle doors.
#     Example YAML:
#       service: nissan_na.lock_doors
#       data:
#         vin: "YOUR_VIN_HERE"
#
#   unlock_doors: Remotely unlock the vehicle doors.
#     Example YAML:
#       service: nissan_na.unlock_doors
#       data:
#         vin: "YOUR_VIN_HERE"
#
#   start_engine: Remotely start the vehicle's engine.
#     Example YAML:
#       service: nissan_na.start_engine
#       data:
#         vin: "YOUR_VIN_HERE"
#
#   stop_engine: Remotely stop the vehicle's engine.
#     Example YAML:
#       service: nissan_na.stop_engine
#       data:
#         vin: "YOUR_VIN_HERE"
#
#   find_vehicle: Activate horn/lights to help locate the vehicle.
#     Example YAML:
#       service: nissan_na.find_vehicle
#       data:
#         vin: "YOUR_VIN_HERE"
#
#   refresh_vehicle_status: Request a fresh status update from the vehicle.
#     Example YAML:
#       service: nissan_na.refresh_vehicle_status
#       data:
#         vin: "YOUR_VIN_HERE"
#
# Describes the services for the Nissan NA integration

SERVICE_LOCK = "lock_doors"
SERVICE_UNLOCK = "unlock_doors"
SERVICE_START_ENGINE = "start_engine"
SERVICE_STOP_ENGINE = "stop_engine"
SERVICE_FIND_VEHICLE = "find_vehicle"
SERVICE_REFRESH_STATUS = "refresh_vehicle_status"

import voluptuous as vol

SERVICE_SCHEMA = vol.Schema({
	vol.Required("vin"): str
})
