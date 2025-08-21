# atoto_fw/core/config.py
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict

# ---- schema & defaults -------------------------------------------------------
SCHEMA_VERSION = 1
DEFAULT_CFG: Dict[str, Any] = {
    "schema": SCHEMA_VERSION,
    "profiles": {},        # { "<name>": {model, mcu, res, variants, prefer_universal} }
    "last_profile": "",    # default profile name
    "verbose": False,      # extra logging in UI
}

# ---- locations ---------------------------------------------------------------
# You can override location with env vars:
#   ATOTO_FW_CONFIG=<full path to config.json>
#   ATOTO_FW_DIR=<directory to place config.json>
def _windows_roaming_dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))

def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

def config_dir() -> Path:
    env_dir = os.environ.get("ATOTO_FW_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    if os.name == "nt":
        return (_windows_roaming_dir() / "ATOTO_Firmware").resolve()
    return (_xdg_config_home() / "atoto_fw").resolve()

def config_path() -> Path:
    env_path = os.environ.get("ATOTO_FW_CONFIG")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "config.json"

# ---- load / save -------------------------------------------------------------
def _merge_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    out = DEFAULT_CFG.copy()
    out.update(cfg or {})
    if "schema" not in out:
        out["schema"] = SCHEMA_VERSION
    return out

def _maybe_migrate_old_path(new_path: Path) -> None:
    """
    If you used an older location/name and the new file doesn't exist,
    copy the old file here once. (Safe no-op if none found.)
    """
    if new_path.exists():
        return
    candidates = []
    # Old Windows style (kept the same dir but just in case file name changed):
    candidates.append(_windows_roaming_dir() / "ATOTO_Firmware" / "config.json")
    # Old Linux style:
    candidates.append(_xdg_config_home() / "atoto_fw" / "config.json")
    for old in candidates:
        try:
            if old.exists() and old.is_file():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                new_path.write_bytes(old.read_bytes())
                break
        except Exception:
            pass  # best-effort only

def load_cfg() -> Dict[str, Any]:
    p = config_path()
    _maybe_migrate_old_path(p)
    if not p.exists():
        return DEFAULT_CFG.copy()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return DEFAULT_CFG.copy()
        return _merge_defaults(raw)
    except Exception:
        # If the file is corrupt, keep a .bad copy and start fresh
        try:
            p.rename(p.with_suffix(".bad.json"))
        except Exception:
            pass
        return DEFAULT_CFG.copy()

def save_cfg(cfg: Dict[str, Any]) -> None:
    p = config_path()
    tmp = p.with_suffix(".tmp")
    data = _merge_defaults(cfg)
    # Atomic-ish write
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        if p.exists():
            p.replace(p.with_suffix(".bak.json"))
    except Exception:
        pass
    tmp.replace(p)
