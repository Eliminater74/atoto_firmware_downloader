from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from ..utils import head_ok, fetch_json
from ..utils import url_leaf_name
import re

BASE = "https://resources.myatoto.com/atoto-product-ibook/ibMobile"

def series_from_model(q: str) -> List[str]:
    m = re.match(r'([A-Za-z]+?\d+)', q or "")
    if m: s = m.group(1); return [s, s.lower(), s.upper()]
    if q and len(q) >= 2: s = q[:2]; return [s, s.lower(), s.upper()]
    return [q, (q or "").lower(), (q or "").upper()]

def candidate_endpoints_for_model(model: str) -> List[str]:
    m, ml, mu = model, model.lower(), model.upper()
    series = series_from_model(model)
    cand = [
        f"{BASE}/{m}.json", f"{BASE}/{ml}.json", f"{BASE}/{mu}.json",
        f"{BASE}/{m}/index.json", f"{BASE}/{ml}/index.json", f"{BASE}/{mu}/index.json",
        f"{BASE}/{m}/{m}.json", f"{BASE}/{ml}/{ml}.json", f"{BASE}/{mu}/{mu}.json",
    ]
    for s in series:
        cand += [
            f"{BASE}/{s}/{m}.json", f"{BASE}/{s}/{ml}.json",
            f"{BASE}/{s}/firmware/{m}.json", f"{BASE}/{s}/firmware/{ml}.json",
            f"{BASE}/{s}/{m}/index.json",
        ]
    seen, out = set(), []
    for u in cand:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

def _parse_endpoint(data: Any, base_url: str) -> List[Dict[str, Any]]:
    """Extract package dicts from a parsed JSON endpoint response."""
    if isinstance(data, list):
        iterable = data
    elif isinstance(data, dict):
        iterable = data.get("packages") or data.get("firmware") or data.get("files") or []
    else:
        return []

    pkgs = []
    for idx, e in enumerate(iterable, start=1):
        if not isinstance(e, dict): continue
        url = e.get("url") or e.get("file") or e.get("download") or e.get("href")
        if not url: continue
        title   = e.get("title") or e.get("name") or url_leaf_name(url)
        version = e.get("version") or re.findall(r'([rv]?[\d._-]+)', (title or "").replace(" ", ""))[:1]
        version = version[0] if isinstance(version, list) and version else (version or "N/A")
        size    = e.get("size") or None
        date    = e.get("date") or e.get("time") or e.get("released") or ""
        sha     = e.get("sha256") or e.get("sha1") or e.get("md5") or ""
        full    = url if url.startswith("http") else f"{BASE.rstrip('/')}/{url.lstrip('/')}"
        pkgs.append({"id": str(idx), "title": title, "version": version, "date": date,
                     "size": size, "url": full, "hash": sha, "source": "JSON"})
    return pkgs

def discover_packages_via_json(model: str, progress=None, seen_endpoints: Optional[set] = None) -> Tuple[List[Dict[str, Any]], str]:
    """
    Probe all candidate JSON endpoints for model and return every package found
    across all of them (not just the first hit). seen_endpoints prevents re-probing
    the same URL across multiple model candidates.
    """
    eps = candidate_endpoints_for_model(model)
    if seen_endpoints is None: seen_endpoints = set()
    eps = [u for u in eps if u not in seen_endpoints]
    total = len(eps) or 1

    all_pkgs: List[Dict[str, Any]] = []
    first_hit = ""

    for i, u in enumerate(eps, start=1):
        seen_endpoints.add(u)
        if progress: progress(f"JSON probe {i}/{total} @ {model}")
        if not head_ok(u): continue
        try:
            data = fetch_json(u)
        except Exception:
            continue

        pkgs = _parse_endpoint(data, u)
        if pkgs:
            if not first_hit:
                first_hit = u
            all_pkgs.extend(pkgs)

    return all_pkgs, first_hit
