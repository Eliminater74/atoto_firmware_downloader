from __future__ import annotations
from typing import Any, Dict, List, Tuple

from .discovery.normalize import normalize_candidates
from .discovery.api import fetch_api_packages
from .discovery.json_probe import discover_packages_via_json
from .discovery.mirrors import known_links_for_model
from .grouping import dedupe_rows

def try_lookup(model: str, mcu: str, progress=None) -> Tuple[List[Dict[str,Any]], List[str]]:
    cands = normalize_candidates(model)
    hits: List[str] = []
    merged: List[Dict[str,Any]] = []

    total = len(cands) or 1
    for j, cand in enumerate(cands, start=1):
        if progress: progress(f"API {j}/{total} @ {cand}")
        pkgs = fetch_api_packages(cand, mcu)
        if pkgs:
            for p in pkgs:
                p.setdefault("source","API")
                q = p.copy(); q["title"] = f"[{cand}] {q['title']}"
                merged.append(q)
            hits.append(cand)

    seen_eps=set()
    for j, cand in enumerate(cands, start=1):
        pkgs_json, endpoint = discover_packages_via_json(cand, progress=progress, seen_endpoints=seen_eps)
        if pkgs_json:
            for p in pkgs_json: p["title"] = f"[{cand}] {p['title']}"
            merged.extend(pkgs_json)
            break

    if progress: progress("Adding mirrors…")
    leader = cands[0] if cands else model
    merged.extend(known_links_for_model(leader))

    merged = dedupe_rows(merged)
    for i, p in enumerate(merged, 1):
        p["id"]=str(i); p.setdefault("source","?")
    return merged, hits
