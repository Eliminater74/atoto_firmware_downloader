from __future__ import annotations
import re
from typing import Any, Dict, List
from ..http import SESSION
from ..utils import dig, url_leaf_name

BASE = "https://resources.myatoto.com/atoto-product-ibook/ibMobile"
API_GET_IBOOK_LIST = f"{BASE}/getIbookList"

def fetch_api_packages(model: str, mcu_version: str = "") -> List[Dict[str, Any]]:
    params = {"skuModel": model, "mcuVersion": mcu_version, "langType": 1, "iBookType": 2}
    try:
        r = SESSION.get(API_GET_IBOOK_LIST, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    if not isinstance(data, dict): return []
    code = data.get("code") or data.get("status")
    if code not in (None, 0, "0", 200, "200"): return []

    pkgs: List[Dict[str, Any]] = []
    soc_url = dig(data, "data","softwareVo","socVo","socUrl")
    if isinstance(soc_url, str) and soc_url.startswith("http"):
        title = url_leaf_name(soc_url)
        ver = re.findall(r'([rv]?[\d._-]+)', title.replace(" ",""))[:1] or ["N/A"]
        pkgs.append({"id":"1","title":title,"version":ver[0],"date":"","size":None,"url":soc_url,"hash":"","source":"API"})

    for arr in (
        dig(data, "data","softwareVo","fileList"),
        dig(data, "data","softwareVo","socVo","files"),
        dig(data, "data","files"),
        dig(data, "files")
    ):
        if isinstance(arr, list):
            for e in arr:
                if not isinstance(e, dict): continue
                url = e.get("url") or e.get("file") or e.get("download")
                if not url: continue
                title = e.get("title") or e.get("name") or url_leaf_name(url)
                pkgs.append({
                    "id":"0","title":title,"version":e.get("version") or "N/A",
                    "date":e.get("date") or "", "size":e.get("size") or None,
                    "url":url, "hash":e.get("sha256") or e.get("sha1") or e.get("md5") or "",
                    "source":"API"
                })
    return pkgs
