from __future__ import annotations
import json, os, re, math, hashlib, urllib.parse
from typing import Any, Dict, List, Optional, Tuple, Callable
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

# ────────────────────────── HTTP session ──────────────────────────
BASE = "https://resources.myatoto.com/atoto-product-ibook/ibMobile"
API_GET_IBOOK_LIST = f"{BASE}/getIbookList"
UA = "ATOTO-Firmware-CLI/3.2"

def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=4, connect=3, read=3, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    a = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s.mount("http://", a); s.mount("https://", a)
    s.headers.update({"User-Agent": UA})
    return s

SESSION = make_session()

# ────────────────────────── Known mirrors (curated) ──────────────────────────
KNOWN_LINKS: List[Dict[str, str]] = [
    {
        "match": r"^(S8G2|S8EG2|ATL-S8).*$",
        "title": "S8 Gen2 (UIS7862 6315) — 2025-04-01 / 05-14",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2025/FILE_UPLOAD_URL_2/85129692/6315-SYSTEM20250401-APP20250514.zip",
    },
    {
        "match": r"^(S8G2|S8EG2|ATL-S8).*$",
        "title": "S8 Gen2 (UIS7862 6315, 1024×600) — 2023-11-10 / 20",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1024x600_system231110_app_231120.zip",
    },
    {
        "match": r"^(S8G2|S8EG2|ATL-S8).*$",
        "title": "S8 Gen2 (UIS7862 6315, 1280×720) — 2023-11-10 / 20",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1280x720_system231110_app_231120.zip",
    },
]

# ────────────────────────── Retail→Canonical ──────────────────────────
RETAIL_TO_CANONICAL = {
    "S8EG2A74MSB": ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],
    "ATL-S8-HU":   ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],
    "S8EG2B74PMB": ["S8G2B74PM-S01", "S8G2B74PM-S10", "S8G2B74PM"],
}
COMMON_VARIANTS = ["-S01","-S10","-S01W","-S10W","-S01R","-S10R","S01","S10","S01W","S10W","S01R","S10R"]

# ────────────────────────── Tiny utils ──────────────────────────
def url_leaf_name(u: str) -> str:
    return urllib.parse.unquote(u.split("/")[-1]) or "download.zip"

def dig(obj: Any, *keys: str) -> Any:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict): return None
        cur = cur.get(k)
    return cur

def human_size(n: Optional[int]) -> str:
    if not n or n <= 0: return "?"
    units = ["B","KB","MB","GB","TB"]
    i = int(math.floor(math.log(n, 1024)))
    return f"{n/(1024**i):.2f} {units[i]}"

def head_ok(url: str, timeout: int = 5) -> bool:
    # shorter probe timeout so failures don’t look like a “freeze”
    try:
        r = SESSION.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code < 400: return True
        r = SESSION.get(url, timeout=timeout, stream=True)
        return r.status_code < 400
    except Exception:
        return False

# ────────────────────────── Resolution/variant tagging ──────────────────────────
def infer_resolution_from_name(s: str) -> str:
    s = (s or "").lower().replace("×", "x")
    if re.search(r"1024[^0-9]*600", s): return "1024x600"
    if re.search(r"(1280[^0-9]*720|720[^0-9]*1280)", s): return "1280x720"
    return "?"

def detect_variants_from_text(s: str) -> List[str]:
    s = (s or "").upper()
    found = set()
    for token in ("MS","PE","PM"):
        if re.search(rf"\b{token}\b", s) or re.search(rf"[-_\.]{token}[-_\.]", s):
            found.add(token)
    return sorted(found)

def scope_from_res(res: str, title_url: str) -> str:
    if res != "?": return "Res-specific"
    hint = re.search(r"(universal|all[-_]?res|all[-_]?resolution|both[-_]?res|generic)", (title_url or "").lower())
    return "Universal" if hint else "Universal?"

def tag_rows(rows: list, my_res: str) -> None:
    my_res = (my_res or "").lower().replace("×", "x")
    for r in rows:
        title_url = f"{r.get('title','')} {r.get('url','')}"
        guess = infer_resolution_from_name(title_url)
        r["res"] = guess
        r["scope"] = scope_from_res(guess, title_url)
        r["variants"] = ",".join(detect_variants_from_text(title_url)) or "-"
        if guess == "?":    r["fit"] = "?"
        elif my_res and guess == my_res: r["fit"] = "✓"
        else:               r["fit"] = "⚠"

def group_by_url(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        u = (r.get("url") or "").strip()
        g = grouped.get(u)
        if not g:
            grouped[u] = r.copy()
        else:
            v = set((g.get("variants","-") or "-").split(",")) | set((r.get("variants","-") or "-").split(","))
            v.discard("-")
            g["variants"] = ",".join(sorted(v)) if v else "-"
            if g.get("res","?") == "?" and r.get("res","?") != "?": g["res"] = r["res"]
            if g.get("fit","?") == "?" and r.get("fit","?") in ("✓","⚠"): g["fit"] = r["fit"]
            if r.get("scope") == "Res-specific": g["scope"] = "Res-specific"
    return list(grouped.values())

def dedupe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for r in rows:
        key = ((r.get("url") or "").strip(), (r.get("title") or "").strip())
        if key in seen: continue
        seen.add(key); out.append(r)
    return out

# ────────────────────────── Model normalization ──────────────────────────
def normalize_candidates(raw: str) -> List[str]:
    r = (raw or "").strip().upper()
    r = re.sub(r"\s+", "", r)

    mapped = RETAIL_TO_CANONICAL.get(r, [])
    out: List[str] = list(mapped)

    if r.startswith("ATL-S8"):
        base_guess = "S8G2A74MS"
        for suf in ("-S01","-S10",""):
            v = base_guess + suf
            if v not in out: out.append(v)

    if r not in out: out.append(r)
    base = re.sub(r"([A-Z0-9-]*[A-Z0-9])(?!-S\d{2}[A-Z]?)?[A-Z]*$", r"\1", r)
    if base and base not in out: out.append(base)

    eg2_to_g2 = base.replace("EG2","G2")
    if eg2_to_g2 not in out: out.append(eg2_to_g2)

    base2 = re.sub(r"[A-Z]+$", "", eg2_to_g2)
    if base2 and base2 not in out: out.append(base2)

    for suf in COMMON_VARIANTS:
        dash = eg2_to_g2 + (suf if suf.startswith("-") else "-" + suf)
        nodash = eg2_to_g2 + (suf if not suf.startswith("-") else suf[1:])
        for v in (dash, nodash):
            if v not in out: out.append(v)

    seen, ordered = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x); ordered.append(x)
    return ordered

# ────────────────────────── Sources (API, JSON, Mirrors) ──────────────────────────
def fetch_api_packages(model: str, mcu_version: str = "", timeout: int = 15) -> List[Dict[str, Any]]:
    params = {"skuModel": model, "mcuVersion": mcu_version, "langType": 1, "iBookType": 2}
    try:
        r = SESSION.get(API_GET_IBOOK_LIST, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    if not isinstance(data, dict): return []
    code = data.get("code") or data.get("status")
    if code not in (None, 0, "0", 200, "200"): return []

    pkgs: List[Dict[str, Any]] = []

    soc_url = dig(data, "data", "softwareVo", "socVo", "socUrl")
    if isinstance(soc_url, str) and soc_url.startswith("http"):
        title = url_leaf_name(soc_url)
        ver = re.findall(r'([rv]?[\d._-]+)', title.replace(" ", ""))[:1] or ["N/A"]
        pkgs.append({"id":"1","title":title,"version":ver[0],"date":"","size":None,"url":soc_url,"hash":"","source":"API"})

    for arr in (
        dig(data, "data", "softwareVo", "fileList"),
        dig(data, "data", "softwareVo", "socVo", "files"),
        dig(data, "data", "files"),
        dig(data, "files"),
    ):
        if isinstance(arr, list):
            for e in arr:
                if not isinstance(e, dict): continue
                url = e.get("url") or e.get("file") or e.get("download")
                if not url: continue
                title = e.get("title") or e.get("name") or url_leaf_name(url)
                pkgs.append({
                    "id":"0", "title":title, "version":e.get("version") or "N/A",
                    "date":e.get("date") or "", "size":e.get("size") or None,
                    "url":url, "hash":e.get("sha256") or e.get("sha1") or e.get("md5") or "", "source":"API"
                })
    return pkgs

def series_from_model(q: str) -> List[str]:
    m = re.match(r'([A-Za-z]+?\d+)', q)
    if m: s = m.group(1); return [s, s.lower(), s.upper()]
    if len(q) >= 2: s = q[:2]; return [s, s.lower(), s.upper()]
    return [q, q.lower(), q.upper()]

def candidate_endpoints_for_model(model: str) -> List[str]:
    m, ml, mu = model, model.lower(), model.upper()
    series = series_from_model(model)
    cand = [
        f"{BASE}/{m}.json", f"{BASE}/{ml}.json", f"{BASE}/{mu}.json",
        f"{BASE}/{m}/index.json", f"{BASE}/{ml}/index.json", f"{BASE}/{mu}/index.json",
        f"{BASE}/{m}/{m}.json", f"{BASE}/{ml}/{ml}.json", f"{BASE}/{mu}/{mu}.json",
    ]
    for s in series:
        cand += [
            f"{BASE}/{s}/{m}.json", f"{BASE}/{s}/{ml}.json",
            f"{BASE}/{s}/firmware/{m}.json", f"{BASE}/{s}/firmware/{ml}.json",
            f"{BASE}/{s}/{m}/index.json",
        ]
    seen, out = set(), []
    for u in cand:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

def fetch_json(url: str, timeout: int = 12) -> Any:
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()
    except json.JSONDecodeError:
        return json.loads(r.text)

def discover_packages_via_json(model: str, progress: Callable[[str], None] | None = None) -> Tuple[List[Dict[str, Any]], str]:
    for idx, u in enumerate(candidate_endpoints_for_model(model), start=1):
        if progress: progress(f"JSON probe {idx}")
        if not head_ok(u): continue
        try:
            data = fetch_json(u)
        except Exception:
            continue

        if isinstance(data, list): iterable = data
        elif isinstance(data, dict): iterable = data.get("packages") or data.get("firmware") or data.get("files") or []
        else: iterable = []

        pkgs: List[Dict[str, Any]] = []
        for j, e in enumerate(iterable, start=1):
            if not isinstance(e, dict): continue
            url = e.get("url") or e.get("file") or e.get("download") or e.get("href")
            if not url: continue
            title = e.get("title") or e.get("name") or url_leaf_name(url)
            version = e.get("version") or re.findall(r'([rv]?[\d._-]+)', (title or "").replace(" ", ""))[:1]
            version = version[0] if isinstance(version, list) and version else (version or "N/A")
            size = e.get("size") or None
            date = e.get("date") or e.get("time") or e.get("released") or ""
            sha  = e.get("sha256") or e.get("sha1") or e.get("md5") or ""
            full = url if url.startswith("http") else f"{BASE.rstrip('/')}/{url.lstrip('/')}"
            pkgs.append({
                "id":str(j),"title":title,"version":version,"date":date,"size":size,
                "url":full,"hash":sha,"source":"JSON"
            })
        if pkgs: return pkgs, u
    return [], ""

def known_links_for_model(model: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for entry in KNOWN_LINKS:
        if re.search(entry["match"], model):
            url = entry["url"]
            if head_ok(url):
                title = entry.get("title") or url_leaf_name(url)
                ver = re.findall(r'([rv]?[\d._-]+)', url_leaf_name(url).replace(" ", ""))[:1] or ["N/A"]
                out.append({
                    "id":"0","title":f"[mirror] {title}","version":ver[0],
                    "date":"","size":None,"url":url,"hash":"","source":"MIRROR"
                })
    for i, p in enumerate(out, 1): p["id"] = str(i)
    return out

# ────────────────────────── Orchestration ──────────────────────────
def try_lookup(model: str, mcu: str, progress: Callable[[str], None] | None = None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Returns (rows, hits). Calls progress(<message>) occasionally so the UI can
    update a spinner/status while work happens.
    """
    cands = normalize_candidates(model)
    hits: List[str] = []
    merged: List[Dict[str, Any]] = []

    # Offer mirrors immediately so a user sees *something* fast
    merged.extend(known_links_for_model(cands[0] if cands else model))

    # API across candidates
    for i, cand in enumerate(cands, start=1):
        if progress: progress(f"API cand {i}/{len(cands)}")
        pkgs = fetch_api_packages(cand, mcu)
        if pkgs:
            for p in pkgs:
                q = p.copy(); q.setdefault("source","API")
                q["title"] = f"[{cand}] {q['title']}"
                merged.append(q)
            hits.append(cand)

    # JSON probe (first successful endpoint per normalized list)
    for i, cand in enumerate(cands, start=1):
        if progress: progress(f"JSON list {i}/{len(cands)}")
        pkgs_json, endpoint = discover_packages_via_json(cand, progress=lambda s: progress and progress(s))
        if pkgs_json:
            for p in pkgs_json: p["title"] = f"[{cand}] {p['title']}"
            merged.extend(pkgs_json)
            break

    merged = dedupe_rows(merged)
    for i, p in enumerate(merged, 1):
        p["id"] = str(i); p.setdefault("source","?")
    return merged, hits

# ────────────────────────── File hashing (used after download) ──────────────────────────
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()
