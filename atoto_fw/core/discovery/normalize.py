from __future__ import annotations
import re
from typing import Dict, List

"""
Model normalization helpers.

- normalize_candidates(raw): expands a retail code or device name into a set of
  likely canonical model strings ATOTO’s endpoints accept (e.g., S8G2A74MS-S01).
- build_suggestions(raw): same set, but ranked to present to users.
- series_from_model(q): returns the device “series” token (e.g., S8G2) in a few
  casings, used by JSON endpoint probing.
"""

# Retail → canonical family hints (extend as needed)
RETAIL_TO_CANONICAL: Dict[str, List[str]] = {
    # S8 Gen2, 4GB+32GB bottom-keys “MS” family
    "S8EG2A74MSB": ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],
    "ATL-S8-HU":   ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],

    # “B” side-keys “PM” family example
    "S8EG2B74PMB": ["S8G2B74PM-S01", "S8G2B74PM-S10", "S8G2B74PM"],
}

# Common “variant” suffixes that appear in ATOTO model strings
COMMON_VARIANTS = [
    "-S01","-S10","-S01W","-S10W","-S01R","-S10R",
    "S01","S10","S01W","S10W","S01R","S10R",
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
    might accept. Order is “best guess first”.
    """
    r = (raw or "").strip().upper()
    r = re.sub(r"\s+", "", r)

    mapped = RETAIL_TO_CANONICAL.get(r, [])
    out: List[str] = list(mapped)

    # If user typed the on-device “ATL-S8-HU” name, point to MS family
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
