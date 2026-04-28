from __future__ import annotations
import re
from typing import Dict, List

"""
Model normalization helpers.

Retail vs. Platform ID:
- Retail Models (e.g. "S8G2A74MS", "S8EG2A74MSB") are specific SKUs.
- Platform IDs (e.g. "S8G2A7PE") are internal firmware identifiers.
  "PE" = Premium Edition platform (often compatible with MS hardware).
  "MS" = Mass Series platform.
  We map specific Retail SKUs to multiple Platform IDs to find all compatible firmware.

- normalize_candidates(raw): expands a retail code or device name into a set of
  likely canonical model strings ATOTO’s endpoints accept (e.g., S8G2A74MS-S01).
- build_suggestions(raw): same set, but ranked to present to users.
- series_from_model(q): returns the device "series" token (e.g., S8G2) in a few
  casings, used by JSON endpoint probing.
"""

# Retail → canonical family hints (extend as needed)
RETAIL_TO_CANONICAL: Dict[str, List[str]] = {
    # S8 Gen2, 4GB+32GB bottom-keys "MS" family
    "S8EG2A74MSB": ["S8G2A74MS", "S8G2A7PE", "S8G2A74MS-S01"],
    "S8EG2A7PE":   ["S8G2A7PE", "S8G2A74MS"],
    "ATL-S8-HU":   ["S8G2A74MS", "S8G2A7PE", "S8G2A74MS-S01"],

    # "B" side-keys "PM" family example
    "S8EG2B74PMB": ["S8G2B74PM-S01", "S8G2B74PM-S10", "S8G2B74PM"],

    # F7 Gen2 — two known hardware platforms: GDB6P (2022) and SOC5P (2023)
    # XE/WE/SE = edition suffixes common on F7 retail SKUs
    "F7G2A7XE":  ["F7G2A7XE", "F7G2A7", "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2A7WE":  ["F7G2A7WE", "F7G2A7", "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2A7SE":  ["F7G2A7SE", "F7G2A7", "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2A7":    ["F7G2A7",   "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2B7PE":  ["F7G2B7PE", "F7G2B7", "F7"],
    "F7G2B7WE":  ["F7G2B7WE", "F7G2B7", "F7"],

    # A6 Gen2 — shares UIS7862/6315 chip with S8 in some SKUs; try both PE and MS
    "A6EG2A74MSB": ["A6G2A74MS", "A6G2A7PE", "A6G2A74MS-S01", "A6G2A7"],
    "A6EG2A7PE":   ["A6G2A7PE",  "A6G2A74MS", "A6G2A7"],
    "A6G2A74MS":   ["A6G2A74MS", "A6G2A7PE",  "A6G2A7"],
    "A6G2A7PE":    ["A6G2A7PE",  "A6G2A74MS", "A6G2A7"],
    "A6G2B74PE":   ["A6G2B74PE", "A6G2B7PE",  "A6G2B7"],

    # P8 Gen2 — premium/flagship; MS and PE variants mirror S8 naming
    "P8EG2A74MSB": ["P8G2A74MS", "P8G2A7PE", "P8G2A74MS-S01", "P8G2A7"],
    "P8EG2A7PE":   ["P8G2A7PE",  "P8G2A74MS", "P8G2A7"],
    "P8G2A74MS":   ["P8G2A74MS", "P8G2A7PE",  "P8G2A7"],
    "P8G2A7PE":    ["P8G2A7PE",  "P8G2A74MS", "P8G2A7"],

    # X10 Gen2 — Qualcomm QCM6125; uses Redstone FOTA
    "X10G2A7E":    ["X10G2A7E",  "X10G2A7",   "X10G2",  "X10"],
    "X10G2A7PE":   ["X10G2A7PE", "X10G2A7",   "X10G2",  "X10"],
    "X10G2A7MS":   ["X10G2A7MS", "X10G2A7",   "X10G2",  "X10"],
    "X10EG2A7MSB": ["X10G2A7MS", "X10G2A7",   "X10G2",  "X10"],
    "X10G2A7":     ["X10G2A7",   "X10G2",     "X10"],
}

COMMON_VARIANTS = [
    "-S01","-S10","-S01W","-S10W","-S01R","-S10R",
    "S01","S10","S01W","S10W","S01R","S10R",
    "-S02F", "-S04", "-PRN", "-S02", "-S10W",
    "WE", "XE", "SE", "SD", # F7/S8 editions
    "-A", "-EU", "-NA", "-AL", # Regions (Asia/Aus?, EU, North America, Latin America?)
    "TYC", "VW", # Specific fitments (Toyota, VW)
    "-BETA", "-TEST", "_BETA", "_TEST",
    "-DEBUG", "_DEBUG",
]

def series_from_model(q: str) -> List[str]:
    """
    Extract a series token (e.g., 'S8G2') from a model-ish string.
    Returns a few casings for convenience.
    """
    q = (q or "").strip()
    m = re.match(r'([A-Za-z]+?\d+)', q)
    if m:
        s = m.group(1)
        return [s, s.lower(), s.upper()]
    if len(q) >= 2:
        s = q[:2]
        return [s, s.lower(), s.upper()]
    return [q, q.lower(), q.upper()]

def normalize_candidates(raw: str) -> List[str]:
    """
    Expand one input string into many candidates ATOTO’s API/JSON endpoints
    might accept. Order is "best guess first".
    """
    r = (raw or "").strip().upper()
    r = re.sub(r"\s+", "", r)

    mapped = RETAIL_TO_CANONICAL.get(r, [])
    out: List[str] = list(mapped)

    # If user typed the on-device "ATL-S8-HU" name, point to MS family
    if r.startswith("ATL-S8"):
        base_guess = "S8G2A74MS"
        for suf in ("-S01","-S10",""):
            v = base_guess + suf
            if v not in out:
                out.append(v)

    # Always include exactly what the user typed
    if r and r not in out:
        out.append(r)

    # Base without trailing -Sxx variant / trailing letters
    base = re.sub(r"([A-Z0-9-]*[A-Z0-9])(?!-S\d{2}[A-Z]?)?[A-Z]*$", r"\1", r)
    if base and base not in out:
        out.append(base)

    # EG2 → G2 (ATOTO uses both across docs/assets)
    eg2_to_g2 = base.replace("EG2", "G2")
    if eg2_to_g2 and eg2_to_g2 not in out:
        out.append(eg2_to_g2)

    # Also a version with trailing letters stripped
    base2 = re.sub(r"[A-Z]+$", "", eg2_to_g2)
    if base2 and base2 not in out:
        out.append(base2)

    # Try common variant suffixes with and without a dash
    for suf in COMMON_VARIANTS:
        dash   = eg2_to_g2 + (suf if suf.startswith("-") else "-" + suf)
        nodash = eg2_to_g2 + (suf if not suf.startswith("-") else suf[1:])
        for v in (dash, nodash):
            if v not in out:
                out.append(v)

    # Dedup but keep order
    seen, ordered = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            ordered.append(x)
    return ordered

def build_suggestions(raw: str) -> List[str]:
    """
    Rank normalized candidates to show in a UI list.
    """
    cands = normalize_candidates(raw)
    ranked: List[str] = []

    # 1) If we have direct retail→canonical mapping, show those first
    mapped = RETAIL_TO_CANONICAL.get(raw.upper(), [])
    ranked += mapped

    # 2) Prefer explicit S01/S10 endings
    for suf in ("-S01","-S10"):
        for c in cands:
            if c.endswith(suf) and c not in ranked:
                ranked.append(c)

    # 3) Put a clean base form near the top
    base = re.sub(r"([A-Z0-9-]*[A-Z0-9])(?:-S\d{2}[A-Z]?)?$", r"\1",
                  (cands[0] if cands else raw).upper())
    for c in cands:
        if c == base and c not in ranked:
            ranked.append(c)

    # 4) Append the rest
    for c in cands:
        if c not in ranked:
            ranked.append(c)

    return ranked[:8]
