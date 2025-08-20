from __future__ import annotations
from typing import Callable, Dict, List, Tuple

# super simple registry (callables take `console` and kwargs)
_REGISTRY: List[Tuple[str, Callable]] = []

def register(name: str, func: Callable):
    _REGISTRY.append((name, func))

def available() -> List[Tuple[str, Callable]]:
    return list(_REGISTRY)

# import built-ins to self-register
try:
    from . import extract_ota  # noqa: F401
except Exception:
    pass
