# atoto_fw/core.py
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys, urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter, Retry

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn
)
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

# ────────────────────────── Globals & session ──────────────────────────
console = Console()
BASE = "https://resources.myatoto.com/atoto-product-ibook/ibMobile"
API_GET_IBOOK_LIST = f"{BASE}/getIbookList"
UA = "ATOTO-Firmware-CLI/3.1"

def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5, backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter); s.mount("https://", adapter)
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

# ────────────────────────── Retail→Canonical hints ──────────────────────────
RETAIL_TO_CANONICAL: Dict[str, List[str]] = {
    "S8EG2A74MSB": ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],
    "ATL-S8-HU":   ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],
    "S8EG2B74PMB": ["S8G2B74PM-S01", "S8G2B74PM-S10", "S8G2B74PM"],
}
COMMON_VARIANTS = [
    "-S01","-S10","-S01W","-S10W","-S01R","-S10R",
    "S01","S10","S01W","S10W","S01R","S10R"
]

# ────────────────────────── UI helpers ──────────────────────────
def clear_screen() -> None:
    console.clear()

def header_art() -> str:
    return r"""
   ___   ______ ____  ______ ____ 
  /   | /_  __// __ \_  __// __ \
 / /| |  / /  / / / / / /  / / / /
/ ___ | / /  / /_/ / / /  / /_/ / 
/_/  |_|/_/   \____/ /_/   \____/  
"""

def section(title: str, subtitle: str = "") -> None:
    clear_screen()
    msg = f"[bold magenta]{header_art()}[/]\n[bold]{title}[/]"
    if subtitle: msg += f"\n[dim]{subtitle}[/]"
    console.print(Panel.fit(msg, border_style="magenta"))

# ────────────────────────── Small utils ──────────────────────────
def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]+', "_", (name or "")).strip() or "file"

def human_size(n: Optional[int]) -> str:
    if not n or n <= 0: return "?"
    units = ["B","KB","MB","GB","TB"]
    i = int(math.floor(math.log(n, 1024)))
    return f"{n/(1024**i):.2f} {units[i]}"

def url_leaf_name(u: str) -> str:
    return urllib.parse.unquote(u.split("/")[-1]) or "download.zip"

def dig(obj: Any, *keys: str) -> Any:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict): return None
        cur = cur.get(k)
    return cur

def head_ok(url: str, timeout: int = 12) -> bool:
    try:
        r = SESSION.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code < 400: return True
        r = SESSION.get(url, timeout=timeout, stream=True)
        return r.status_code < 400
    except Exception:
        return False

# ────────────────────────── Resolution & variant helpers ──────────────────────────
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

def group_by_url(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
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
    return grouped

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

def build_suggestions(raw: str) -> List[str]:
    cands = normalize_candidates(raw)
    ranked: List[str] = []
    mapped = RETAIL_TO_CANONICAL.get(raw.upper(), [])
    ranked += mapped
    for suf in ("-S01","-S10"):
        for c in cands:
            if c.endswith(suf) and c not in ranked:
                ranked.append(c)
    base = re.sub(r"([A-Z0-9-]*[A-Z0-9])(?:-S\d{2}[A-Z]?)?$", r"\1", (cands[0] if cands else raw).upper())
    for c in cands:
        if c == base and c not in ranked:
            ranked.append(c)
    for c in cands:
        if c not in ranked:
            ranked.append(c)
    return ranked[:8]

# ────────────────────────── API discovery ──────────────────────────
def fetch_api_packages(model: str, mcu_version: str = "") -> List[Dict[str, Any]]:
    params = {"skuModel": model, "mcuVersion": mcu_version, "langType": 1, "iBookType": 2}
    try:
        r = SESSION.get(API_GET_IBOOK_LIST, params=params, timeout=20)
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

# ────────────────────────── JSON discovery ──────────────────────────
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

def fetch_json(url: str, timeout: int = 20) -> Any:
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()
    except json.JSONDecodeError:
        return json.loads(r.text)

def discover_packages_via_json(model: str) -> Tuple[List[Dict[str, Any]], str]:
    for u in candidate_endpoints_for_model(model):
        if not head_ok(u): continue
        try:
            data = fetch_json(u)
        except Exception:
            continue
        if isinstance(data, list): iterable = data
        elif isinstance(data, dict): iterable = data.get("packages") or data.get("firmware") or data.get("files") or []
        else: iterable = []

        pkgs: List[Dict[str, Any]] = []
        for idx, e in enumerate(iterable, start=1):
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
                "id":str(idx),"title":title,"version":version,"date":date,"size":size,
                "url":full,"hash":sha,"source":"JSON"
            })
        if pkgs: return pkgs, u
    return [], ""

# ────────────────────────── Known mirror plumbing ──────────────────────────
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

# ────────────────────────── Dedupe & selection ──────────────────────────
def dedupe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for r in rows:
        key = ((r.get("url") or "").strip(), (r.get("title") or "").strip())
        if key in seen: continue
        seen.add(key); out.append(r)
    return out

def select_from_rows(rows: List[Dict[str, Any]], title: str,
                     my_res: str, prefer_universal: bool,
                     want_variants: List[str]) -> Optional[Dict[str, Any]]:
    tag_rows(rows, my_res)
    grouped = list(group_by_url(rows).values())

    def row_ok(r: Dict[str,Any]) -> bool:
        if prefer_universal and not r.get("scope","").startswith("Universal"):
            return False
        if want_variants and r.get("variants") not in ("-", ""):
            row_vars = set(r["variants"].split(","))
            if not (row_vars & set(want_variants)):
                return False
        return True

    filt = [r for r in grouped if row_ok(r)]
    if not filt: filt = grouped

    section(title, "Universal = package not tied to a specific display resolution. Res-specific = explicit 1024×600 or 1280×720.")
    console.print(Panel.fit(
        "[bold]Tip[/]: Prefer Universal packages for the same device family; use Res-specific only when a package explicitly targets your screen.\n"
        f"[dim]Profile Fit targets: {my_res or '?'}; Variant prefs: {', '.join(want_variants) if want_variants else 'ANY'}; "
        f"Scope: {'Universal preferred' if prefer_universal else 'Show all'}[/]",
        border_style="cyan"
    ))

    table = Table(title="Available Packages", show_lines=False,
                  header_style="bold magenta", box=box.SIMPLE_HEAVY)
    cols = [("id","#"),("source","Src"),("title","Title"),("version","Ver"),
            ("date","Date"),("size","Size"),("res","Res"),("scope","Scope"),
            ("variants","Variants"),("fit","Fit"),("url","URL")]
    for _, hdr in cols: table.add_column(hdr, overflow="fold")
    for idx, r in enumerate(filt, 1):
        r_view = r.copy(); r_view["id"] = str(idx)
        r_view["size"] = human_size(r.get("size"))
        table.add_row(*[str(r_view.get(k, "")) for k,_ in cols])
    console.print(table)

    default_pick = "1" if filt else "0"
    raw = Prompt.ask("Select # (0 to cancel)", default=default_pick).strip()
    if raw == "0" or not raw.isdigit(): clear_screen(); return None
    i = int(raw)
    if not (1 <= i <= len(filt)): return None
    chosen = filt[i-1]
    if chosen.get("fit") == "⚠":
        console.print(f"[yellow]Heads-up:[/] package looks like [bold]{chosen.get('res','?')}[/], "
                      f"your profile is [bold]{my_res}[/].")
        if not Confirm.ask("Continue anyway?", default=False):
            return None
    clear_screen(); return chosen

# ────────────────────────── Download ──────────────────────────
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def download_with_progress(url: str, out_path: Path, expected_hash: str = "") -> None:
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    resume = tmp.stat().st_size if tmp.exists() else 0
    headers = {"Range": f"bytes={resume}-"} if resume > 0 else {}

    with SESSION.get(url, stream=True, headers=headers, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", "0"))
        if r.status_code == 206:
            try:
                full = SESSION.head(url, timeout=12, allow_redirects=True)
                total = int(full.headers.get("Content-Length", total))
            except Exception:
                pass

        mode = "ab" if resume > 0 else "wb"
        downloaded = resume
        task_desc = f"[bold]Downloading[/] {out_path.name}"
        with Progress(
            TextColumn(task_desc, justify="left"), BarColumn(),
            TransferSpeedColumn(), TextColumn("{task.completed:>10.0f}/{task.total:>10.0f} B"),
            TimeRemainingColumn(), console=console, transient=False
        ) as progress:
            task_id = progress.add_task("dl", total=total, completed=downloaded)
            with open(tmp, mode) as f:
                for chunk in r.iter_content(chunk_size=128 * 1024):
                    if not chunk: continue
                    f.write(chunk); downloaded += len(chunk)
                    progress.update(task_id, completed=downloaded)
        tmp.rename(out_path)

    if expected_hash:
        console.print("Verifying checksum...")
        algo = "sha256" if len(expected_hash) == 64 else ("sha1" if len(expected_hash) == 40 else "md5")
        if algo == "sha256":
            digest = sha256_file(out_path)
        elif algo == "sha1":
            h = hashlib.sha1()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
            digest = h.hexdigest()
        else:
            h = hashlib.md5()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
            digest = h.hexdigest()
        if digest.lower() != expected_hash.lower():
            console.print(f"[red]Checksum mismatch![/] expected {expected_hash}, got {digest}")
        else:
            console.print("[green]Checksum OK[/]")

# ────────────────────────── Orchestration ──────────────────────────
def show_candidates(title: str, tried: List[str], hits: List[str]) -> None:
    section(title, "Auto-normalized inputs and which matched the API")
    tbl = Table(show_lines=False, header_style="bold magenta", box=box.SIMPLE_HEAVY)
    tbl.add_column("Tried", overflow="fold"); tbl.add_column("Matched", overflow="fold")
    L = max(len(tried), len(hits))
    tried += [""]*(L-len(tried)); hits += [""]*(L-len(hits))
    for a, b in zip(tried, hits): tbl.add_row(a, b)
    console.print(tbl)

def known_links_block(model: str) -> List[Dict[str, Any]]:
    fam = model
    return known_links_for_model(fam)

def try_lookup(model: str, mcu: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    cands = normalize_candidates(model)
    hits: List[str] = []
    merged: List[Dict[str, Any]] = []

    for cand in cands:
        pkgs = fetch_api_packages(cand, mcu)
        if pkgs:
            for p in pkgs: p.setdefault("source", "API")
            for p in pkgs:
                q = p.copy(); q["title"] = f"[{cand}] {q['title']}"
                merged.append(q)
            hits.append(cand)

    for cand in cands:
        pkgs_json, endpoint = discover_packages_via_json(cand)
        if pkgs_json:
            for p in pkgs_json: p["title"] = f"[{cand}] {p['title']}"
            merged.extend(pkgs_json)
            break

    merged.extend(known_links_block(cands[0] if cands else model))

    merged = dedupe_rows(merged)
    for i, p in enumerate(merged, 1):
        p["id"] = str(i); p.setdefault("source","?")
    return merged, hits

# ────────────────────────── Profiles (persisted) ──────────────────────────
def config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        return base / "ATOTO_Firmware"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "atoto_fw"

def config_path() -> Path:
    d = config_dir(); d.mkdir(parents=True, exist_ok=True)
    return d / "config.json"

def load_cfg() -> Dict[str, Any]:
    p = config_path()
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: pass
    return {"profiles": {}, "last_profile": ""}

def save_cfg(cfg: Dict[str, Any]) -> None:
    config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def prompt_profile(existing: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    console.print(Panel.fit("Create / Edit Profile", border_style="cyan"))
    prof = dict(existing or {})
    prof["name"]  = Prompt.ask("Profile name", default=prof.get("name","My S8"))
    prof["model"] = Prompt.ask("Model / Device name", default=prof.get("model","S8EG2A74MSB")).upper().strip()
    prof["mcu"]   = Prompt.ask("MCU version (blank if unknown)", default=prof.get("mcu","")).strip()
    prof["res"]   = Prompt.ask("Display resolution", default=prof.get("res","1280x720")).strip()
    vdefault = prof.get("variants","ANY")
    v = Prompt.ask("Variant prefs (MS,PE,PM or ANY)", default=vdefault).upper().replace(" ","")
    if v == "" or v == "ANY": prof["variants"] = "ANY"
    else:
        keep = [t for t in v.split(",") if t in ("MS","PE","PM")]
        prof["variants"] = ",".join(sorted(set(keep))) if keep else "ANY"
    prof["prefer_universal"] = Confirm.ask("Prefer Universal packages?", default=bool(prof.get("prefer_universal", True)))
    return prof

def profile_menu(cfg: Dict[str,Any]) -> Optional[Dict[str,Any]]:
    while True:
        section("Profiles", f"Config file: {config_path()}")
        tbl = Table(show_lines=False, header_style="bold magenta", box=box.SIMPLE_HEAVY)
        tbl.add_column("#"); tbl.add_column("Name"); tbl.add_column("Model"); tbl.add_column("MCU"); tbl.add_column("Res"); tbl.add_column("Variants"); tbl.add_column("Universal?")
        names = sorted(cfg["profiles"].keys())
        for i, name in enumerate(names, 1):
            p = cfg["profiles"][name]
            tbl.add_row(str(i), name, p.get("model",""), p.get("mcu",""), p.get("res",""),
                        p.get("variants","ANY"), "Yes" if p.get("prefer_universal",True) else "No")
        console.print(tbl)
        console.print("[dim]A=Add  E=Edit  D=Delete  S=Select default  Q=Back[/]")
        ans = Prompt.ask("Action", default="S").strip().upper()
        if ans == "Q": return None
        if ans == "A":
            p = prompt_profile({})
            cfg["profiles"][p["name"]] = p
            save_cfg(cfg)
        elif ans == "E" and names:
            idx = Prompt.ask("Edit #", default="1").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(names):
                name = names[int(idx)-1]
                p = prompt_profile(cfg["profiles"][name])
                if p["name"] != name:
                    del cfg["profiles"][name]
                cfg["profiles"][p["name"]] = p
                save_cfg(cfg)
        elif ans == "D" and names:
            idx = Prompt.ask("Delete #", default="1").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(names):
                name = names[int(idx)-1]
                if Confirm.ask(f"Delete profile '{name}'?", default=False):
                    del cfg["profiles"][name]
                    if cfg.get("last_profile") == name: cfg["last_profile"] = ""
                    save_cfg(cfg)
        elif ans == "S" and names:
            idx = Prompt.ask("Select # as default", default="1").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(names):
                name = names[int(idx)-1]
                cfg["last_profile"] = name
                save_cfg(cfg)
                return cfg["profiles"][name]

# ────────────────────────── Search & download orchestration ──────────────────────────
def run_search_download_flow(profile: Dict[str,Any], out_base: Path) -> None:
    model = profile.get("model","").strip() or Prompt.ask("Model / Device", default="S8EG2A74MSB").strip()
    mcu   = profile.get("mcu","").strip()
    my_res = profile.get("res","1280x720").strip()
    variants_pref = [] if profile.get("variants","ANY") == "ANY" else profile.get("variants","ANY").split(",")
    prefer_universal = bool(profile.get("prefer_universal", True))

    pkgs, hits = try_lookup(model, mcu)
    show_candidates("Normalization Results", normalize_candidates(model), hits)

    if not pkgs:
        section("No Packages Found",
                "Could not find firmware via API/JSON/mirrors.\nUse Manual URL or adjust the model.")
        return

    chosen = select_from_rows(pkgs, "Firmware Results", my_res, prefer_universal, variants_pref)
    if not chosen:
        section("Canceled")
        return

    model_for_path = (hits[0] if hits else model)
    out_dir = out_base / safe_filename(model_for_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(f"{model_for_path}_{chosen.get('version','NAv')}_{url_leaf_name(chosen['url'])}")
    out_path = out_dir / filename

    section("Download Ready",
            f"Saving to: {out_path}\nReported size: {human_size(chosen.get('size'))}\n\nPress Ctrl+C to cancel")
    try:
        download_with_progress(chosen["url"], out_path, expected_hash=chosen.get("hash",""))
        section("Download Complete")
        console.print(f"[green]Done![/] File saved:\n[bold]{out_path}[/]")
    except KeyboardInterrupt:
        section("Interrupted"); console.print("[yellow]Interrupted by user.[/]")
    except Exception as e:
        section("Download Failed"); console.print(f"[red]Download failed:[/] {e}")

# ────────────────────────── Manual URL ──────────────────────────
def manual_url_flow(download_dir: Path) -> None:
    section("Manual URL", "Paste a direct firmware URL from ATOTO")
    url = Prompt.ask("Direct URL (or leave blank to abort)", default="").strip()
    if not url:
        section("Canceled"); return
    download_dir.mkdir(parents=True, exist_ok=True)
    out = download_dir / safe_filename(url_leaf_name(url))
    section("Download Ready", f"Saving to: {out}\n\nPress Ctrl+C to cancel")
    try:
        download_with_progress(url, out)
        section("Download Complete"); console.print(f"[green]Done![/] File saved:\n[bold]{out}[/]")
    except KeyboardInterrupt:
        section("Interrupted"); console.print("[yellow]Interrupted by user.[/]")
    except Exception as e:
        section("Download Failed"); console.print(f"[red]Download failed:[/] {e}")
