import re

def infer_resolution_from_name(s: str) -> str:
    s = (s or "").lower().replace("×","x")
    if re.search(r"1024[^0-9]*600", s): return "1024x600"
    if re.search(r"(1280[^0-9]*720|720[^0-9]*1280)", s): return "1280x720"
    return "?"

def detect_variants_from_text(s: str) -> list[str]:
    s = (s or "").upper()
    found = set()
    for token in ("MS","PE","PM"):
        import re as _re
        if _re.search(rf"\b{token}\b", s) or _re.search(rf"[-_\.]{token}[-_\.]", s):
            found.add(token)
    return sorted(found)

def scope_from_res(res: str, title_url: str) -> str:
    if res != "?": return "Res-specific"
    import re as _re
    hint = _re.search(r"(universal|all[-_]?res|all[-_]?resolution|both[-_]?res|generic)", (title_url or "").lower())
    return "Universal" if hint else "⚠ Unknown Res"
