
"""
atoto_fw.core.discovery.redstone
Implementation of the Redstone FOTA protocol used by newer ATOTO models (e.g. X10 series).
Endpoint: https://fota.redstone.net.cn:7100/service/request
"""

import requests
import json
import urllib3
from datetime import datetime
from typing import List, Dict, Optional

# Disable SSL warnings for this specific endpoint as it often has cert issues or requires specific trust
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REDSTONE_URL = "https://fota.redstone.net.cn:7100/service/request"

# Maps model substring (uppercase) → Redstone platform identifier.
# Add entries here as new captures are shared by the community.
PLATFORM_MAP: Dict[str, str] = {
    "X10":  "qcm6125_T10",   # X10 Gen2 — confirmed capture
    "X10G2": "qcm6125_T10",
}

# Default payload template based on capture from X10 user
DEFAULT_PAYLOAD = {
    "version": "A1.0",
    "session": "FUMO-REQ",
    "devid": "SN:5319f700",
    "man": "ATOTO",
    "mod": "qcm6125_T10",
    "swv": "20200101.000000",  # intentionally old to force update response
    "carrier": {
        "appid": "ilppa7c9qlze3znkzaaxdqpa",
        "channel": "myatoto"
    }
}

def platform_for_model(model: str) -> Optional[str]:
    """Return the Redstone platform string for a model, or None if unknown."""
    mu = model.upper()
    for key, plat in PLATFORM_MAP.items():
        if key in mu:
            return plat
    return None

def fetch_redstone_update(
    model: str,
    sn: str = "SN:5319f700",
    current_version: str = "20250101.000000"
) -> List[Dict]:
    """
    Check for updates via Redstone FOTA.
    Returns a list of candidate dictionaries (compatible with our standard format).
    Skips silently if the model's platform is not yet mapped.
    """
    platform = platform_for_model(model)
    if not platform:
        return []  # unknown platform — skip rather than send wrong data

    payload = {**DEFAULT_PAYLOAD}
    payload["devid"] = sn if sn.startswith("SN:") else f"SN:{sn}"
    payload["mod"]   = platform
    payload["swv"]   = current_version
    
    # User-Agent mimicking actual device
    headers = {
        "User-Agent": f"Dalvik/2.1.0 (Linux; U; Android 10; {model} Build/QUokka)",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(REDSTONE_URL, json=payload, headers=headers, verify=False, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        # Check success
        if data.get("msg") == "success" and "fw" in data:
            fw = data["fw"]
            url = fw.get("objecturi")
            ver = fw.get("toversion", "Unknown")
            name = fw.get("objectName", f"Update_{ver}.zip")
            size = int(fw.get("objectsize", 0))
            
            # Convert to our internal candidate format
            return [{
                "title": f"[Redstone] {name}",
                "url": url,
                "version": ver,
                "date": fw.get("dateline", "").split('T')[0], # 20251118T... -> 20251118
                "size": size,
                "mirror": False,
                "desc": f"Source: Redstone FOTA\nMD5: {fw.get('icv','')}\nPlatform: {platform}"
            }]
            
    except Exception:
        pass

    return []
