from __future__ import annotations
import hashlib, json, math, urllib.parse
from pathlib import Path
from typing import Any, Optional
from .http import SESSION

def human_size(n: Optional[int]) -> str:
    if not n or n <= 0: return "?"
    units = ["B","KB","MB","GB","TB"]
    i = int(math.floor(math.log(n, 1024)))
    return f"{n/(1024**i):.2f} {units[i]}"

def url_leaf_name(u: str) -> str:
    return urllib.parse.unquote((u or "").split("/")[-1]) or "download.zip"

def dig(obj: Any, *keys: str) -> Any:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict): return None
        cur = cur.get(k)
    return cur

def head_ok(url: str, timeout: int = 10) -> bool:
    try:
        r = SESSION.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code < 400: return True
        r = SESSION.get(url, timeout=timeout, stream=True)
        return r.status_code < 400
    except Exception:
        return False

def head_info(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Returns {ok, size, date} from HEAD request."""
    default = {"ok": False, "size": None, "date": ""}
    try:
        r = SESSION.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code >= 400:
            # Try GET stream if HEAD fails (sometimes servers block HEAD)
            r = SESSION.get(url, timeout=timeout, stream=True)
            r.close() # just reading headers
        
        if r.status_code < 400:
            sz = r.headers.get("Content-Length")
            return {
                "ok": True,
                "size": int(sz) if sz and sz.isdigit() else None,
                "date": r.headers.get("Last-Modified",""),
            }
    except Exception:
        pass
    return default

def fetch_json(url: str, timeout: int = 15) -> Any:
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        import json as _json
        return _json.loads(r.text)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def check_github_update(current_ver: str) -> Optional[Tuple[str, str]]:
    """
    Checks GitHub for a newer release.
    Returns (new_version_tag, url) or None.
    """
    try:
        url = "https://api.github.com/repos/Eliminater74/atoto_firmware_downloader/releases/latest"
        r = SESSION.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            tag = data.get("tag_name", "").strip().lstrip("v")
            cur = current_ver.strip().lstrip("v")
            
            # Simple lexicographical check (or semver if needed)
            if tag and tag != cur:
                # Basic check: is remote '2.0.1' > local '2.0.0'?
                # For robust comparison, we'd need 'packaging.version', but let's do a simple string compare
                # if main digits differ. Ideally assume tags increase.
                if tag > cur: 
                    return (tag, data.get("html_url", ""))
    except Exception:
        pass
    return None
