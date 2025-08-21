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
