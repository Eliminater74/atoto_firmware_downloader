from __future__ import annotations
from typing import Any, Dict, List, Tuple

from .discovery.normalize import normalize_candidates
from .discovery.api import fetch_api_packages
from .discovery.json_probe import discover_packages_via_json
from .discovery.mirrors import known_links_for_model
from .grouping import dedupe_rows, sort_rows

def try_lookup(model: str, mcu: str, progress=None, deep_scan: bool = False) -> Tuple[List[Dict[str,Any]], List[str]]:
    cands = normalize_candidates(model)
    hits: List[str] = []
    merged: List[Dict[str,Any]] = []

    if deep_scan:
        if "S8" in model or "6315" in model:
            cands.append("6315")
            cands.append("S8 Gen2")
        if "X10" in model:
            for _c in ("X10G2A7", "X10G2", "X10"):
                if _c not in cands: cands.append(_c)
        if "A6" in model:
            for _c in ("A6G2A7PE", "A6G2A74MS", "A6G2A7", "A6"):
                if _c not in cands: cands.append(_c)
        if "F7" in model:
            for _c in ("F7G2A7", "F7G2B7", "F7-GDB6P", "F7-SOC5P", "F7", "U10", "DS7P"):
                if _c not in cands: cands.append(_c)
        if "P8" in model:
            for _c in ("P8G2A7PE", "P8G2A74MS", "P8G2A7", "P8"):
                if _c not in cands: cands.append(_c)

    # ── API probe (all candidates) ────────────────────────────────────────────
    total = len(cands) or 1
    for j, cand in enumerate(cands, start=1):
        if progress: progress(f"API {j}/{total} @ {cand}")
        pkgs = fetch_api_packages(cand, mcu)
        if pkgs:
            for p in pkgs:
                p.setdefault("source", "API")
                q = p.copy(); q["title"] = f"[{cand}] {q['title']}"
                merged.append(q)
            hits.append(cand)

    # ── MCU retry: if nothing found and MCU was set, retry without it ─────────
    if not merged and mcu:
        if progress: progress("No results with MCU filter — retrying without MCU…")
        for j, cand in enumerate(cands, start=1):
            pkgs = fetch_api_packages(cand, "")
            if pkgs:
                for p in pkgs:
                    p.setdefault("source", "API")
                    q = p.copy(); q["title"] = f"[{cand}] {q['title']}"
                    merged.append(q)
                hits.append(cand)

    # ── JSON probe (all candidates, all endpoints — seen_eps avoids repeats) ──
    seen_eps: set = set()
    for j, cand in enumerate(cands, start=1):
        pkgs_json, endpoint = discover_packages_via_json(cand, progress=progress, seen_endpoints=seen_eps)
        if pkgs_json:
            for p in pkgs_json: p["title"] = f"[{cand}] {p['title']}"
            merged.extend(pkgs_json)

    if progress: progress("Adding mirrors…")
    leader = cands[0] if cands else model

    # ── Redstone FOTA (X10 Series / newer) ───────────────────────────────────
    if "X10" in model.upper() or deep_scan:
        from .discovery.redstone import fetch_redstone_update
        if progress: progress("Checking Redstone FOTA...")
        try:
            rs_updates = fetch_redstone_update(model)
            if rs_updates:
                merged.extend(rs_updates)
                hits.append("Redstone")
        except Exception: pass

    # ── Mirror links ──────────────────────────────────────────────────────────
    # Check mirrors against leader; also try the raw model in case the
    # leader was remapped to a canonical form that doesn't match the regex.
    mirror_hits = known_links_for_model(leader)
    if not mirror_hits and leader.upper() != model.upper():
        mirror_hits = known_links_for_model(model)
    merged.extend(mirror_hits)

    merged = dedupe_rows(merged)
    merged = sort_rows(merged)          # newest-first
    for i, p in enumerate(merged, 1):
        p["id"] = str(i); p.setdefault("source", "?")
    return merged, hits
