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

    # F7 Gen1 — older platform, separate firmware from Gen2
    "F7G1A8XE":  ["F7G1A8XE", "F7G1A8", "F7G1", "F7"],
    "F7G1A8PE":  ["F7G1A8PE", "F7G1A8", "F7G1", "F7"],
    "F7G1A8SE":  ["F7G1A8SE", "F7G1A8", "F7G1", "F7"],
    "F7G110XE":  ["F7G110XE", "F7G1",   "F7"],

    # F7 Gen2 — two known hardware platforms: GDB6P (2022) and SOC5P (2023)
    # XE/WE/SE = edition suffixes; -A/-EU/-NA/-AL = regional variants
    "F7G2A7XE":  ["F7G2A7XE", "F7G2A7", "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2A7WE":  ["F7G2A7WE", "F7G2A7", "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2A7SE":  ["F7G2A7SE", "F7G2A7", "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2A7XED": ["F7G2A7XED","F7G2A7", "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2A7":    ["F7G2A7",   "F7-GDB6P", "F7-SOC5P", "F7"],
    "F7G2B7PE":  ["F7G2B7PE", "F7G2B7", "F7"],
    "F7G2B7WE":  ["F7G2B7WE", "F7G2B7", "F7"],
    "F7G2B7XE":  ["F7G2B7XE", "F7G2B7", "F7"],
    "F7G2B7XED": ["F7G2B7XED","F7G2B7", "F7"],

    # F7 Gen2 numeric screen-size variants (10-inch G210, 11-inch G211)
    "F7G209SE":  ["F7G209SE", "F7G209", "F7G2", "F7"],
    "F7G210XE":  ["F7G210XE", "F7G210", "F7G2", "F7"],
    "F7G210PE":  ["F7G210PE", "F7G210", "F7G2", "F7"],
    "F7G211XE":  ["F7G211XE", "F7G211", "F7G2", "F7"],
    "F7G211WE":  ["F7G211WE", "F7G211", "F7G2", "F7"],
    "F7G211SE":  ["F7G211SE", "F7G211", "F7G2", "F7"],

    # F7 Toyota / vehicle-fit — same F7G2 firmware platform
    "F7TYC7XE":  ["F7TYC7XE", "F7G2A7XE", "F7G2A7", "F7-SOC5P", "F7"],
    "F7TYC7SE":  ["F7TYC7SE", "F7G2A7SE", "F7G2A7", "F7"],

    # A6 Gen2 — shares UIS7862/6315 chip with S8 in some SKUs; try both PE and MS
    "A6EG2A74MSB": ["A6G2A74MS", "A6G2A7PE", "A6G2A74MS-S01", "A6G2A7"],
    "A6EG2A7PE":   ["A6G2A7PE",  "A6G2A74MS", "A6G2A7"],
    "A6G2A74MS":   ["A6G2A74MS", "A6G2A7PE",  "A6G2A7"],
    "A6G2A7PE":    ["A6G2A7PE",  "A6G2A74MS", "A6G2A7"],
    # PF suffix = side-label Gen2 variant (April 2024+); firmware: ATOTO_A6_PF_7_Inch_OS_240627.zip
    # NOTE: A6-H1-B is a separate incompatible hardware; do NOT cross-flash
    "A6G2A7PF":    ["A6G2A7PF",  "A6G2A7PE",  "A6G2A7"],
    "A6G2A7PF-S01":["A6G2A7PF",  "A6G2A7PE",  "A6G2A7"],
    "A6G2A7PF-S02":["A6G2A7PF",  "A6G2A7PE",  "A6G2A7"],
    "A6G2B7PF":    ["A6G2B7PF",  "A6G2B7PE",  "A6G2B7"],
    "A6G2B74PE":   ["A6G2B74PE", "A6G2B7PE",  "A6G2B7"],

    # A6 vehicle-fit variants — confirmed same firmware platform as base A6G2A7PF
    "A6TYC7PF":    ["A6G2A7PF",  "A6G2A7PE",  "A6G2A7"],   # Toyota
    "A6VW07APF":   ["A6G2A7PF",  "A6G2A7PE",  "A6G2A7"],   # VW (confirmed = A6G2A7PF bundle)
    "A6VW09PF":    ["A6G2A7PF",  "A6G2A7PE",  "A6G2A7"],   # VW 9-inch
    "A6OP07APF":   ["A6G2A7PF",  "A6G2A7PE",  "A6G2A7"],   # Opel/Vauxhall

    # A6 Y-series — different generation / OEM variant (platform IDs unconfirmed)
    "A6Y2721P":    ["A6Y2721P",  "A6Y2721",   "A6Y27",  "A6"],
    "A6Y2721PR":   ["A6Y2721PR", "A6Y2721",   "A6Y27",  "A6"],
    "A6Y2710S":    ["A6Y2710S",  "A6Y2710",   "A6Y27",  "A6"],
    "A6YTY721PR":  ["A6YTY721PR","A6Y2721PR", "A6Y27",  "A6"],   # Toyota
    "A6YVW721PRB": ["A6YVW721PRB","A6Y2721PR","A6Y27",  "A6"],   # VW

    # P8 Gen2 — premium/flagship; MS and PE variants mirror S8 naming
    "P8EG2A74MSB": ["P8G2A74MS", "P8G2A7PE", "P8G2A74MS-S01", "P8G2A7"],
    "P8EG2A7PE":   ["P8G2A7PE",  "P8G2A74MS", "P8G2A7"],
    "P8G2A74MS":   ["P8G2A74MS", "P8G2A7PE",  "P8G2A7"],
    "P8G2A7PE":    ["P8G2A7PE",  "P8G2A74MS", "P8G2A7"],

    # X10 Gen2 — Qualcomm QCM6125; uses Redstone FOTA (platform: qcm6125_T10)
    "X10G2A7E":    ["X10G2A7E",  "X10G2A7",   "X10G2",  "X10"],
    "X10G2A7PE":   ["X10G2A7PE", "X10G2A7",   "X10G2",  "X10"],
    "X10G2A7MS":   ["X10G2A7MS", "X10G2A7",   "X10G2",  "X10"],
    "X10EG2A7MSB": ["X10G2A7MS", "X10G2A7",   "X10G2",  "X10"],
    "X10G2A7":     ["X10G2A7",   "X10G2",     "X10"],
    # B-variant and DAB variant — same QCM6125 platform, same Redstone FOTA
    "X10G2B7E":    ["X10G2B7E",  "X10G2B7",   "X10G2",  "X10"],
    "X10DG2B7E":   ["X10DG2B7E", "X10G2B7E",  "X10G2",  "X10"],  # DAB radio variant

    # DS7 — newer flagship; shares UIS8581A chip family
    "DS7G2A7PE":   ["DS7G2A7PE", "DS7G2A74MS", "DS7G2A7", "DS7G2",  "DS7"],
    "DS7G2A74MS":  ["DS7G2A74MS","DS7G2A7PE",  "DS7G2A7", "DS7G2",  "DS7"],
    "DS7G2A7":     ["DS7G2A7",   "DS7G2",      "DS7"],

    # Z7 — compact flagship; follows same A7/MS/PE naming convention
    "Z7G2A7PE":    ["Z7G2A7PE",  "Z7G2A74MS",  "Z7G2A7",  "Z7G2",   "Z7"],
    "Z7G2A74MS":   ["Z7G2A74MS", "Z7G2A7PE",   "Z7G2A7",  "Z7G2",   "Z7"],
    "Z7G2A7":      ["Z7G2A7",    "Z7G2",        "Z7"],

    # F10 — 10-inch variant of F7; may share SOC5P / GDB6P platforms
    "F10G2A7PE":   ["F10G2A7PE", "F10G2A7",    "F10G2",   "F10",    "F7-SOC5P"],
    "F10G2A7":     ["F10G2A7",   "F10G2",      "F10",     "F7-SOC5P"],

    # P7 — predecessor to P8; uses MediaTek MT8168 / 6762 class chipsets
    "P7G2A7PE":    ["P7G2A7PE",  "P7G2A74MS",  "P7G2A7",  "P7G2",   "P7"],
    "P7G2A74MS":   ["P7G2A74MS", "P7G2A7PE",   "P7G2A7",  "P7G2",   "P7"],
    "P7G2A7":      ["P7G2A7",    "P7G2",        "P7"],
}

COMMON_VARIANTS = [
    "-S01","-S10","-S01W","-S10W","-S01R","-S10R",
    "S01","S10","S01W","S10W","S01R","S10R",
    "-S02F", "-S04", "-PRN", "-S02",
    "WE", "XE", "SE", "SD", "XED",           # F7/S8 editions
    "-A", "-EU", "-EU2", "-NA", "-AL",        # regional: Asia, Europe, Europe2, N.America, Latin America
    "TYC", "VW",                              # vehicle-fit: Toyota, Volkswagen
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
