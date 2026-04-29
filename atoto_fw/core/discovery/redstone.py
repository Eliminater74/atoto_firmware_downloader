"""
atoto_fw.core.discovery.redstone
Redstone FOTA protocol used by newer ATOTO models (X10 series, QCM6125 chipset).
Endpoint: https://fota.redstone.net.cn:7100/service/request

POST body confirmed by community network capture (2025-08):
  {"version":"A1.0","session":"FUMO-REQ","devid":"SN:xxxx","man":"ATOTO",
   "mod":"qcm6125_T10","swv":"<current_fw_version>",
   "carrier":{"appid":"ilppa7c9qlze3znkzaaxdqpa","channel":"myatoto"}}

The server returns firmware newer than swv.  We probe with several known old
versions so we can surface multiple historical packages in one search.
"""

import requests
import urllib3
from typing import Dict, List, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REDSTONE_URL = "https://fota.redstone.net.cn:7100/service/request"

# Maps model substring (uppercase) to the Redstone platform identifier.
# Community-captured values — add new entries as captures are shared.
PLATFORM_MAP: Dict[str, str] = {
    "X10":   "qcm6125_T10",   # X10 Gen2 (confirmed capture)
    "X10G2": "qcm6125_T10",
    "X10D":  "qcm6125_T10",   # X10 DAB variant (X10DG2B7E)
}

# Known firmware versions for qcm6125_T10, captured from real devices.
# Probing with each as swv discovers the update that follows it.
# (True = full/factory firmware, False = incremental OTA)
_PROBE_VERSIONS: List[tuple] = [
    ("20200101.000000", False),   # sentinel — triggers "give me latest"
    ("20250318.213333", False),
    ("20250430.143509", False),
    ("20250815.210712", False),
    ("20250925.150720", True),    # full firmware
    ("20251021.191955", False),
    # 20251106.174502 is the current latest — use earlier swv values to fetch it
]

# Which toversion strings are known-full (not incremental)
_KNOWN_FULL: Dict[str, bool] = {
    "20250925.150720": True,
}

_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; ATOTO Build/QP1A)",
    "Content-Type": "application/json",
}

# Extra channel strings to try when include_beta=True.
# These are speculative — add confirmed captures here as they are shared.
_BETA_CHANNELS = ["myatoto-beta", "myatoto_test", "myatoto_cn"]


def platform_for_model(model: str) -> Optional[str]:
    """Return the Redstone platform string for a model, or None if unknown."""
    mu = (model or "").upper()
    for key, plat in PLATFORM_MAP.items():
        if key in mu:
            return plat
    return None



def fetch_redstone_update(
    model: str,
    sn: str = "SN:5319f700",
    current_version: str = "",
    include_beta: bool = False,
) -> List[Dict]:
    """
    Probe the Redstone FOTA server for firmware newer than each known version.
    Returns a list of unique candidate dicts (compatible with our standard format).
    Returns [] immediately for models not in PLATFORM_MAP.
    """
    platform = platform_for_model(model)
    if not platform:
        return []

    sn_str = sn if sn.startswith("SN:") else f"SN:{sn}"
    probes = list(_PROBE_VERSIONS)
    if current_version and not any(v == current_version for v, _ in probes):
        probes.insert(0, (current_version, False))

    seen_urls: set = set()
    results: List[Dict] = []

    # Release-channel probes
    channels = ["myatoto"]
    if include_beta:
        channels += _BETA_CHANNELS

    for swv, _ in probes:
        for channel in channels:
            try:
                payload = {
                    "version": "A1.0",
                    "session": "FUMO-REQ",
                    "devid": sn_str,
                    "man": "ATOTO",
                    "mod": platform,
                    "swv": swv,
                    "carrier": {
                        "appid": "ilppa7c9qlze3znkzaaxdqpa",
                        "channel": channel,
                    },
                }
                r = requests.post(REDSTONE_URL, json=payload, headers=_HEADERS,
                                  verify=False, timeout=12)
                r.raise_for_status()
                data = r.json()
                if data.get("msg") != "success" or "fw" not in data:
                    continue
                fw = data["fw"]
                url = fw.get("objecturi", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                ver = fw.get("toversion", "")
                name = fw.get("objectName") or f"redstone_{ver}.zip"
                size = int(fw.get("objectsize") or 0)
                icv  = fw.get("icv", "")

                raw_date = (fw.get("dateline") or "")[:8]
                if len(raw_date) == 8 and raw_date.isdigit():
                    date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                else:
                    date = raw_date

                is_full = _KNOWN_FULL.get(ver, False)
                is_beta = (channel != "myatoto") or "beta" in name.lower() or "beta" in ver.lower()
                kind = (" [FULL]" if is_full else " [incremental]") + (" [beta]" if is_beta else "")

                results.append({
                    "title":   f"[Redstone] {name}{kind}",
                    "url":     url,
                    "version": ver,
                    "date":    date,
                    "size":    size,
                    "hash":    icv,
                    "source":  "Redstone",
                })
            except Exception:
                continue

    return results
