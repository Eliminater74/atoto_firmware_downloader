from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Package:
    id: str = "0"
    title: str = ""
    version: str = "N/A"
    date: str = ""
    size: Optional[int] = None
    url: str = ""
    hash: str = ""
    source: str = ""
    # Tags populated by grouping/tagging:
    res: str = "?"
    scope: str = ""
    variants: str = "-"
    fit: str = "?"
