from __future__ import annotations
from typing import Any, Dict, List
from .variants import infer_resolution_from_name, scope_from_res, detect_variants_from_text

def tag_rows(rows: List[Dict[str,Any]], my_res: str) -> None:
    my_res = (my_res or "").lower().replace("×","x")
    for r in rows:
        title_url = f"{r.get('title','')} {r.get('url','')}"
        guess = infer_resolution_from_name(title_url)
        r["res"] = guess
        r["scope"] = scope_from_res(guess, title_url)
        r["variants"] = ",".join(detect_variants_from_text(title_url)) or "-"
        if guess == "?": r["fit"] = "?"
        elif my_res and guess == my_res: r["fit"] = "✓"
        else: r["fit"] = "⚠"

def group_by_url(rows: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        u = (r.get("url") or "").strip()
        if not u: continue
        g = grouped.get(u)
        if not g:
            grouped[u] = r.copy()
            continue
        # merge variants
        v1 = set(filter(None, (g.get("variants","-") or "-").split(",")))
        v2 = set(filter(None, (r.get("variants","-") or "-").split(",")))
        v = (v1 | v2) - {"-"}
        g["variants"] = ",".join(sorted(v)) if v else "-"
        # prefer concrete res/scope
        if g.get("res","?") == "?" and r.get("res","?") != "?":
            g["res"] = r["res"]; g["fit"] = r.get("fit", g.get("fit","?"))
        if r.get("scope") == "Res-specific":
            g["scope"] = "Res-specific"
    return list(grouped.values())

def dedupe_rows(rows: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    seen=set(); out=[]
    for r in rows:
        key=((r.get("url") or "").strip(), (r.get("title") or "").strip())
        if key in seen: continue
        seen.add(key); out.append(r)
    return out
