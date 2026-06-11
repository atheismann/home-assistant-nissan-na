"""
Smartcar API client for Nissan vehicles.

Uses the OAuth 2.0 client-credentials grant for all API calls after the
initial Smartcar Connect flow.  No per-user refresh tokens are stored —
a short-lived application token is fetched automatically as needed.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

_LOGGER = logging.getLogger(__name__)


def _namedtuple_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a namedtuple (or any object with __dict__) to a dictionary."""
    if isinstance(obj, dict):
        return obj
    elif hasattr(obj, "_asdict"):
        result = obj._asdict()
        return {
            k: _namedtuple_to_dict(v) if hasattr(v, "_asdict") else v
            for k, v in result.items()
        }
    else:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}


class Vehicle(BaseModel):
    """Model representing a Nissan vehicle."""

    vin: str
    id: str
    model: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None


class SmartcarApiClient:
    """Client for Nissan vehicles via Smartcar API.

    Authentication uses the client-credentials grant: the user completes
    Smartcar Connect once (to associate their vehicle), we capture their
    user_id, then all subsequent API calls use short-lived app-level tokens
    that are fetched and cached automatically — no user interaction needed.
    """

    _IAM_TOKEN_URL = "https://iam.smartcar.com/oauth2/token"
    _USER_URL = "https://api.smartcar.com/v2.0/user"
    _V3_BASE = "https://vehicle.api.smartcar.com/v3"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_id: Optional[str] = None,
        test_mode: bool = False,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.test_mode = test_mode
        # Client-credentials token cache
        self._cc_token: Optional[str] = None
        self._cc_token_expires_at: float = 0.0
        # Vehicle / signal caches
        self._vehicle_model_cache: Dict[str, Any] = {}
        self._vehicle_signals_cache: Dict[str, List[str]] = {}
        self._permission_denied_signals: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Token management (client-credentials)
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Return a valid client-credentials access token, fetching one if expired."""
        if self._cc_token and time.monotonic() < self._cc_token_expires_at:
            return self._cc_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._IAM_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if resp.status_code != 200:
                raise ValueError(
                    f"Client-credentials token request failed"
                    f" ({resp.status_code}): {resp.text}"
                )
            data = resp.json()

        token: str = data["access_token"]
        self._cc_token = token
        # Expire 60 s early to avoid edge-case expiry mid-request
        self._cc_token_expires_at = time.monotonic() + data.get("expires_in", 3600) - 60
        _LOGGER.debug("Obtained new client-credentials access token")
        return token

    async def _api_headers(self) -> Dict[str, str]:
        """Return auth headers for Smartcar v3 API calls."""
        token = await self._get_access_token()
        headers: Dict[str, str] = {"Authorization": f"Bearer {token}"}
        if self.user_id:
            headers["sc-user-id"] = self.user_id
        return headers

    # ------------------------------------------------------------------
    # Generic v3 HTTP helpers
    # ------------------------------------------------------------------

    async def _v3_get(self, vehicle_id: str, path: str) -> Dict[str, Any]:
        """GET a v3 vehicle endpoint and return the attributes dict."""
        headers = await self._api_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._V3_BASE}/vehicles/{vehicle_id}/{path}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        node = data.get("data", {})
        if isinstance(node, dict):
            return node.get("attributes", data)
        return data

    async def _v3_post(
        self, vehicle_id: str, path: str, body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST to a v3 vehicle endpoint and return the full JSON response."""
        headers = await self._api_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._V3_BASE}/vehicles/{vehicle_id}/{path}",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Vehicle list (Connections API)
    # ------------------------------------------------------------------

    async def get_vehicle_list(self) -> List[Vehicle]:
        """Return all vehicles connected for this user via the Connections API."""
        if not self.user_id:
            raise ValueError("user_id is not set.")

        headers = await self._api_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._V3_BASE}/connections",
                headers=headers,
                params={"filter[user_id]": self.user_id},
            )
            if resp.status_code != 200:
                raise ValueError(
                    f"Connections API failed ({resp.status_code}): {resp.text}"
                )
            data = resp.json()

        vehicles: List[Vehicle] = []
        for conn in data.get("connections", []):
            vehicle_id = conn.get("vehicleId")
            if not vehicle_id:
                continue
            embedded: Dict[str, Any] = {}
            try:
                vehicle = await self._fetch_vehicle_attributes(
                    vehicle_id, headers, embedded
                )
                vehicles.append(vehicle)
                self._vehicle_model_cache[vehicle_id] = vehicle
            except Exception as err:
                _LOGGER.warning(
                    "Failed to get attributes for vehicle %s: %s", vehicle_id, err
                )

        return vehicles

    async def _fetch_vehicle_attributes(
        self,
        vehicle_id: str,
        headers: Optional[Dict[str, str]] = None,
        embedded: Optional[Dict[str, Any]] = None,
    ) -> Vehicle:
        """Fetch make/model/year and VIN via v3 HTTP calls.

        If `embedded` is provided (from the connections response attributes),
        only a VIN fetch is performed if the VIN is absent from the embedded data.
        """
        if headers is None:
            headers = await self._api_headers()

        # Use embedded vehicle info from connections payload if available
        if embedded:
            make = embedded.get("make")
            model = embedded.get("model")
            year_raw = embedded.get("year")
            vin = embedded.get("vin", "")

            # If VIN is missing, fetch it separately
            if not vin:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self._V3_BASE}/vehicles/{vehicle_id}/vin", headers=headers
                    )
                    vin_data = resp.json() if resp.status_code == 200 else {}
                vin = vin_data.get("data", {}).get("attributes", {}).get("vin", "")

            year = int(year_raw) if year_raw else None
            return Vehicle(id=vehicle_id, vin=vin, make=make, model=model, year=year)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._V3_BASE}/vehicles/{vehicle_id}", headers=headers
            )
            attrs_data = resp.json() if resp.status_code == 200 else {}

            resp = await client.get(
                f"{self._V3_BASE}/vehicles/{vehicle_id}/vin", headers=headers
            )
            vin_data = resp.json() if resp.status_code == 200 else {}

        attrs = attrs_data.get("data", {}).get("attributes", {})
        vin_attrs = vin_data.get("data", {}).get("attributes", {})
        year = attrs.get("year")

        return Vehicle(
            id=vehicle_id,
            vin=vin_attrs.get("vin", ""),
            make=attrs.get("make"),
            model=attrs.get("model"),
            year=int(year) if year else None,
        )

    # ------------------------------------------------------------------
    # Vehicle info
    # ------------------------------------------------------------------

    async def get_vehicle_info(self, vehicle_id: str) -> Dict[str, Any]:
        """Get vehicle information (make, model, year, VIN)."""
        if vehicle_id in self._vehicle_model_cache:
            v = self._vehicle_model_cache[vehicle_id]
            return {
                "id": vehicle_id,
                "make": v.make,
                "model": v.model,
                "year": v.year,
                "vin": v.vin,
            }
        vehicle = await self._fetch_vehicle_attributes(vehicle_id)
        self._vehicle_model_cache[vehicle_id] = vehicle
        return {
            "id": vehicle_id,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "vin": vehicle.vin,
        }

    # ------------------------------------------------------------------
    # Read methods (direct v3 HTTP)
    # ------------------------------------------------------------------

    async def get_vehicle_location(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "location")

    async def get_battery_level(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "battery")

    async def get_battery_capacity(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "battery/capacity")

    async def get_charge_status(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "charge")

    async def get_odometer(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "odometer")

    async def get_fuel_level(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "fuel")

    async def get_lock_status(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "security")

    async def get_tire_pressure(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "tires/pressure")

    async def get_engine_oil(self, vehicle_id: str) -> Dict[str, Any]:
        return await self._v3_get(vehicle_id, "engine/oil")

    async def get_permissions(self, vehicle_id: str) -> List[str]:
        data = await self._v3_get(vehicle_id, "permissions")
        return data.get("permissions", [])

    # ------------------------------------------------------------------
    # Vehicle action methods (direct v3 HTTP)
    # ------------------------------------------------------------------

    async def lock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        result = await self._v3_post(vehicle_id, "security", {"action": "LOCK"})
        _LOGGER.debug("Lock command sent for vehicle %s", vehicle_id)
        return result

    async def unlock_doors(self, vehicle_id: str) -> Dict[str, Any]:
        result = await self._v3_post(vehicle_id, "security", {"action": "UNLOCK"})
        _LOGGER.debug("Unlock command sent for vehicle %s", vehicle_id)
        return result

    async def start_charge(self, vehicle_id: str) -> Dict[str, Any]:
        result = await self._v3_post(vehicle_id, "charge", {"action": "START"})
        _LOGGER.debug("Start charge command sent for vehicle %s", vehicle_id)
        return result

    async def stop_charge(self, vehicle_id: str) -> Dict[str, Any]:
        result = await self._v3_post(vehicle_id, "charge", {"action": "STOP"})
        _LOGGER.debug("Stop charge command sent for vehicle %s", vehicle_id)
        return result

    # ------------------------------------------------------------------
    # Climate control (direct HTTP)
    # ------------------------------------------------------------------

    async def start_climate(self, vehicle_id: str) -> Dict[str, Any]:
        headers = await self._api_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._V3_BASE}/vehicles/{vehicle_id}/climate",
                headers=headers,
                json={"action": "START"},
            )
            resp.raise_for_status()
            return resp.json()

    async def stop_climate(self, vehicle_id: str) -> Dict[str, Any]:
        headers = await self._api_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._V3_BASE}/vehicles/{vehicle_id}/climate",
                headers=headers,
                json={"action": "STOP"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_climate_status(self, vehicle_id: str) -> Dict[str, Any]:
        headers = await self._api_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._V3_BASE}/vehicles/{vehicle_id}/climate",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    async def disconnect(self, vehicle_id: str) -> bool:
        headers = await self._api_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self._V3_BASE}/vehicles/{vehicle_id}", headers=headers
            )
            success = resp.status_code in (200, 204)
        if success:
            self._vehicle_model_cache.pop(vehicle_id, None)
            self._vehicle_signals_cache.pop(vehicle_id, None)
        return success

    # ------------------------------------------------------------------
    # Signals / compatibility
    # ------------------------------------------------------------------

    async def get_compatibility_signals(
        self, make: str, model: str, year: int
    ) -> List[str]:
        """Get supported signal codes from the public compatibility API.
        No auth needed.
        """
        url = "https://compatibility.api.smartcar.com/v3/compatible-vehicles"
        params = {"filter[make]": make.upper(), "filter[region]": "US"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception as err:
            _LOGGER.debug("Compatibility API error: %s", err)
            return []

        signals: List[str] = []
        for entry in data.get("data", []):
            attrs = entry.get("attributes", {})
            if attrs.get("model", "").lower() != model.lower():
                continue
            years = attrs.get("years", {})
            if not (years.get("start", 0) <= year <= years.get("end", 9999)):
                continue
            for cap in attrs.get("capabilities", []):
                if cap.get("type") == "signal":
                    code = cap.get("capability")
                    if code and code not in signals:
                        signals.append(code)
            if signals:
                _LOGGER.info(
                    "Compatibility API: %d signals for %s %s %d",
                    len(signals),
                    make,
                    model,
                    year,
                )
                return signals

        _LOGGER.debug("No compatibility match for %s %s %d", make, model, year)
        return []

    async def get_vehicle_signals(
        self, vehicle_id: str, vehicle: Any = None
    ) -> List[str]:
        """Return available signal codes for a vehicle (cached after first call)."""
        if vehicle_id in self._vehicle_signals_cache:
            return self._vehicle_signals_cache[vehicle_id]

        _LOGGER.debug("Fetching signals for vehicle %s", vehicle_id)
        headers = await self._api_headers()
        url = f"{self._V3_BASE}/vehicles/{vehicle_id}/signals"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data and isinstance(data["data"], list):
                        all_sigs = data["data"]

                        permission_codes = [
                            sig["attributes"]["code"]
                            for sig in all_sigs
                            if isinstance(sig, dict)
                            and "attributes" in sig
                            and "code" in sig.get("attributes", {})
                            and sig["attributes"]
                            .get("status", {})
                            .get("error", {})
                            .get("type")
                            == "PERMISSION"
                        ]
                        if permission_codes:
                            self._permission_denied_signals[vehicle_id] = (
                                permission_codes
                            )
                            _LOGGER.warning(
                                "Vehicle %s: %d signal(s) have PERMISSION errors: %s",
                                vehicle_id,
                                len(permission_codes),
                                permission_codes,
                            )
                        else:
                            self._permission_denied_signals.pop(vehicle_id, None)

                        signals = [
                            sig["attributes"]["code"]
                            for sig in all_sigs
                            if isinstance(sig, dict)
                            and "attributes" in sig
                            and "code" in sig["attributes"]
                            and sig["attributes"].get("status", {}).get("value")
                            == "SUCCESS"
                        ]
                        if signals:
                            _LOGGER.info(
                                "v3 signals endpoint: %d signals for vehicle %s",
                                len(signals),
                                vehicle_id,
                            )
                            self._vehicle_signals_cache[vehicle_id] = signals
                            return signals
                else:
                    _LOGGER.debug(
                        "v3 signals endpoint returned %d for vehicle %s — "
                        "falling back to compatibility API",
                        resp.status_code,
                        vehicle_id,
                    )
        except Exception as err:
            _LOGGER.debug("v3 signals endpoint error for %s: %s", vehicle_id, err)

        # Fall back to compatibility API
        v = vehicle or self._vehicle_model_cache.get(vehicle_id)
        if v and v.make and v.model and v.year:
            signals = await self.get_compatibility_signals(v.make, v.model, v.year)
            if signals:
                self._vehicle_signals_cache[vehicle_id] = signals
                return signals

        _LOGGER.warning(
            "Could not determine signals for vehicle %s — no sensors will be created",
            vehicle_id,
        )
        self._vehicle_signals_cache[vehicle_id] = []
        return []

    def get_permission_denied_signals(self, vehicle_id: str) -> List[str]:
        """Return signal codes that returned PERMISSION errors for the given vehicle."""
        return self._permission_denied_signals.get(vehicle_id, [])

    # ------------------------------------------------------------------
    # Vehicle status (bulk signals call)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_signal_body(sdk_result: dict) -> dict:
        """Extract the signal data body from a v3 SDK get_signal() result."""
        body = sdk_result.get("body", {})
        if not isinstance(body, dict):
            return {}
        data = body.get("data")
        if isinstance(data, dict):
            attrs = data.get("attributes", {})
            if isinstance(attrs, dict) and "body" in attrs:
                return attrs["body"] or {}
        attrs = body.get("attributes", {})
        if isinstance(attrs, dict) and "body" in attrs:
            return attrs["body"] or {}
        return body

    def _apply_signal_to_status(
        self, status: dict, signal_code: str, body: dict
    ) -> None:
        """Map a v3 signal response body into the shared status dict."""
        if not body:
            return

        code = signal_code.lower()
        _LOGGER.debug("Applying signal %s body: %s", code, body)

        if code == "odometer-traveleddistance":
            status.setdefault("odometer", {})["distance"] = (
                body.get("traveledDistance")
                or body.get("distance")
                or body.get("value")
            )

        elif code == "internalcombustionengine-fuellevel":
            status.setdefault("fuel", {})["percentRemaining"] = (
                body.get("fuelLevel")
                or body.get("percentRemaining")
                or body.get("value")
            )

        elif code == "internalcombustionengine-amountremaining":
            status.setdefault("fuel", {})["amountRemaining"] = body.get(
                "amountRemaining"
            ) or body.get("value")

        elif code == "internalcombustionengine-range":
            status.setdefault("fuel", {})["range"] = body.get("range") or body.get(
                "value"
            )

        elif code == "location-preciselocation":
            status["location"] = {
                "latitude": body.get("latitude"),
                "longitude": body.get("longitude"),
            }

        elif code == "wheel-tires":
            _ROW_COL_TO_POS = {
                (0, 0): "frontLeft",
                (0, 1): "frontRight",
                (1, 0): "backLeft",
                (1, 1): "backRight",
            }
            tires: dict = {}
            for entry in body.get("values", []):
                if not isinstance(entry, dict):
                    continue
                row = entry.get("row")
                col = entry.get("column")
                pressure = (
                    entry.get("tirePressure")
                    if entry.get("tirePressure") is not None
                    else entry.get("pressure")
                )
                pos = (
                    _ROW_COL_TO_POS.get((row, col))
                    if row is not None and col is not None
                    else None
                )
                if pos and pressure is not None:
                    tires[pos] = {"pressure": pressure}
            if tires:
                status["tires"] = tires

        elif code == "diagnostics-tirepressure":
            status.setdefault("diagnostics", {})["tirePressureWarning"] = body.get(
                "status"
            )

        elif code == "closure-islocked":
            status.setdefault("security", {})["isLocked"] = body.get("isLocked")

        elif code == "closure-doors":
            status.setdefault("security", {})["doors"] = body.get("doors", body)

        elif code == "closure-reartrunk":
            status.setdefault("security", {})["rearTrunk"] = body

        elif code == "closure-fronttrunk":
            status.setdefault("security", {})["frontTrunk"] = body

        elif code == "closure-enginecover":
            status.setdefault("security", {})["engineCover"] = body

        elif code == "diagnostics-mil":
            status.setdefault("diagnostics", {})["mil"] = body.get("status")

        elif code == "diagnostics-abs":
            status.setdefault("diagnostics", {})["abs"] = body.get("status")

        elif code == "diagnostics-brakefluid":
            status.setdefault("diagnostics", {})["brakeFluid"] = body.get("status")

        elif code == "diagnostics-airbag":
            status.setdefault("diagnostics", {})["airbag"] = body.get("status")

        elif code == "diagnostics-oilpressure":
            status.setdefault("diagnostics", {})["oilPressure"] = body.get("status")

        elif code == "tractionbattery-stateofcharge":
            status.setdefault("battery", {})["percentRemaining"] = body.get(
                "stateOfCharge"
            ) or body.get("percentRemaining")

        elif code == "tractionbattery-range":
            status.setdefault("battery", {})["range"] = body.get("range")

        elif code == "tractionbattery-nominalcapacity":
            status.setdefault("battery", {})["capacityKwh"] = body.get(
                "capacity"
            ) or body.get("nominalCapacity")

        elif code == "charge-ischarging":
            status.setdefault("charge", {})["isCharging"] = body.get(
                "isCharging"
            ) or body.get("value")

        elif code == "charge-ischargingcableconnected":
            status.setdefault("charge", {})["isPluggedIn"] = body.get(
                "isChargingCableConnected"
            ) or body.get("value")

        elif code == "charge-timetocomplete":
            status.setdefault("charge", {})["timeToComplete"] = body.get(
                "timeToComplete"
            ) or body.get("value")

        elif code == "charge-detailedchargingstatus":
            status.setdefault("charge", {})["state"] = (
                body.get("detailedChargingStatus")
                or body.get("status")
                or body.get("value")
            )

        elif code == "charge-chargetimers":
            status.setdefault("charge", {})["chargeTimers"] = body

        elif code == "charge-voltage":
            status.setdefault("charge", {})["voltage"] = body.get(
                "voltage"
            ) or body.get("value")

        elif code == "charge-wattage":
            status.setdefault("charge", {})["wattage"] = body.get(
                "wattage"
            ) or body.get("value")

        elif code == "hvac-cabintargettemperature":
            status.setdefault("hvac", {})["targetTemperature"] = body.get(
                "cabinTargetTemperature"
            ) or body.get("value")

        elif code == "hvac-iscabinhvacactive":
            status.setdefault("hvac", {})["isActive"] = body.get(
                "isCabinHVACActive"
            ) or body.get("value")

        else:
            _LOGGER.debug("No status mapping for signal %s — storing raw body", code)
            status[code] = body

    async def get_vehicle_status(self, vehicle_id: str) -> Dict[str, Any]:
        """Get comprehensive vehicle status via bulk call to v3 signals endpoint."""
        headers = await self._api_headers()
        url = f"{self._V3_BASE}/vehicles/{vehicle_id}/signals"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    _LOGGER.warning(
                        "Signals endpoint returned %d for vehicle %s",
                        resp.status_code,
                        vehicle_id,
                    )
                    return {}
                data = resp.json()
        except Exception as err:
            _LOGGER.error("Failed to fetch vehicle status for %s: %s", vehicle_id, err)
            return {}

        signal_list = data.get("data", [])

        success_codes = [
            sig["attributes"]["code"]
            for sig in signal_list
            if isinstance(sig, dict)
            and "attributes" in sig
            and "code" in sig.get("attributes", {})
            and sig.get("attributes", {}).get("status", {}).get("value") == "SUCCESS"
        ]
        if success_codes:
            self._vehicle_signals_cache[vehicle_id] = success_codes

        permission_codes = [
            sig["attributes"]["code"]
            for sig in signal_list
            if isinstance(sig, dict)
            and "attributes" in sig
            and "code" in sig.get("attributes", {})
            and sig.get("attributes", {}).get("status", {}).get("error", {}).get("type")
            == "PERMISSION"
        ]
        if permission_codes:
            self._permission_denied_signals[vehicle_id] = permission_codes
        else:
            self._permission_denied_signals.pop(vehicle_id, None)

        status: Dict[str, Any] = {}
        for signal in signal_list:
            attrs = signal.get("attributes", {})
            code = attrs.get("code", "")
            if not code:
                continue
            if attrs.get("status", {}).get("value") != "SUCCESS":
                continue
            body = attrs.get("body")
            if body:
                self._apply_signal_to_status(status, code, body)

        _LOGGER.debug("Vehicle status for %s: %s", vehicle_id, status)
        return status
