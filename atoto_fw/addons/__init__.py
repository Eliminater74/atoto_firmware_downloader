# atoto_fw/addons/__init__.py
from __future__ import annotations

from importlib import import_module
from typing import Callable, List, Tuple

# ───────────────── Registry ─────────────────
# UI reads available() and shows a menu of (name, func)
_REGISTRY: List[Tuple[str, Callable]] = []


def register(name: str, func: Callable) -> None:
    """Register an add-on entry.
    Expected callable signature: func()  (no args) or func(**kwargs).
    """
    _REGISTRY.append((name, func))


def available() -> List[Tuple[str, Callable]]:
    """Return a copy so callers can't mutate the registry."""
    return list(_REGISTRY)


__all__ = ["register", "available"]

# ─────────────── Auto-import built-ins ───────────────
# Import modules that self-register via register(...).
# Order matters only for how they appear in the menu.
_MODULE_CANDIDATES = (
    "firmware_workflow",  # new step-by-step firmware tools
    "ota_extract",        # your modular OTA extractor
    "extract_ota",        # legacy/alt name (if present)
    "extrator_ota",       # typo variant kept for compatibility
)

for mod in _MODULE_CANDIDATES:
    try:
        import_module(f"{__name__}.{mod}")
    except Exception:
        # Quietly skip missing/broken add-ons; UI will just not list them.
        pass
