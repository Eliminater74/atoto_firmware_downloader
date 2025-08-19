#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATOTO Firmware Downloader — multi-source
- Clean-screen UI (rich; no blended output)
- Retail/DeviceName → Canonical mapping (e.g., S8EG2A74MSB / ATL-S8-HU → S8G2A74MS-S01)
- Smart normalization (ATL→S8G2…, EG2→G2, common -S01/-S10/-W variants)
- Source order shown together: API + JSON + Known mirrors (Aliyun / atoto-usa bucket)
- "Did you mean...?" suggestions with 1-click retry
- Manual URL mode for direct links
- Resumable downloads + optional checksum verify

Install:
  pip install requests rich
"""

from __future__ import annotations
import json, math, re, hashlib, urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import requests
from requests.adapters import HTTPAdapter, Retry

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
)

console = Console()

# ────────────────────────── Constants ──────────────────────────
BASE = "https://resources.myatoto.com/atoto-product-ibook/ibMobile"
API_GET_IBOOK_LIST = f"{BASE}/getIbookList"
UA = "ATOTO-Firmware-CLI/2.8 (+https://github.com/Eliminater74)"

# Retail / DeviceName → canonical firmware model(s). Extend as needed.
RETAIL_TO_CANONICAL: Dict[str, List[str]] = {
    "S8EG2A74MSB": ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],
    "ATL-S8-HU":   ["S8G2A74MS-S01", "S8G2A74MS-S10", "S8G2A74MS"],

    "S8EG2C74MSB": ["S8G2C74MS-S01", "S8G2C74MS-S10", "S8G2C74MS"],
    "S8EG2B74PMB": ["S8G2B74PM-S01", "S8G2B74PM-S10", "S8G2B74PM"],
}

COMMON_VARIANTS = ["-S01", "-S10", "-S01W", "-S10W", "-S01R", "-S10R", "S01", "S10", "S01W", "S10W", "S01R", "S10R"]

# Curated public links that have worked for S8 Gen2 (UIS7862 “6315”)
# Shown regardless of API results. We HEAD-check each before listing.
# Regex now matches ALL S8G2 variants (A7/B7 and PE/PM/MS).
KNOWN_LINKS: List[Dict[str, str]] = [
    {
        "match": r"^(S8G2A7|S8G2B7|S8G2A74|S8G2B74).*$",
        "title": "S8 Gen2 (UIS7862 6315) — 2025-04-01/05-14",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2025/FILE_UPLOAD_URL_2/85129692/6315-SYSTEM20250401-APP20250514.zip",
    },
    {
        "match": r"^(S8G2A7|S8G2B7|S8G2A74|S8G2B74).*$",
        "title": "S8 Gen2 (UIS7862 6315, 1024×600) — 2023-11-10/20",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1024x600_system231110_app_231120.zip",
    },
    {
        "match": r"^(S8G2A7|S8G2B7|S8G2A74|S8G2B74).*$",
        "title": "S8 Gen2 (UIS7862 6315, 1280×720) — 2023-11-10/20",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1280x720_system231110_app_231120.zip",
    },
    # Add more mirrors here as you discover them…
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
    txt = f"[bold magenta]{header_art()}[/]\n[bold]{title}[/]"
    if subtitle:
        txt += f"\n[dim]{subtitle}[/]"
    console.print(Panel.fit(txt, border_style="magenta"))

def splash() -> None:
    section("ATOTO Firmware Downloader")

# ────────────────────────── Session ──────────────────────────
def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": UA})
    return s

SESSION = make_session()

# ────────────────────────── Utils ──────────────────────────
def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]+', "_", (name or "")).strip() or "file"

def human_size(n: Optional[int]) -> str:
    if not n or n <= 0:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(n, 1024)))
    return f"{n / (1024 ** i):.2f} {units[i]}"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def head_ok(url: str, timeout: int = 12) -> bool:
    try:
        r = SESSION.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code < 400:
            return True
        r = SESSION.get(url, timeout=timeout, stream=True)
        return r.status_code < 400
    except Exception:
        return False

def dig(obj: Any, *keys: str) -> Any:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur

def url_leaf_name(u: str) -> str:
    return urllib.parse.unquote(u.split("/")[-1]) or "download.zip"

# ────────────────────────── Model normalization & suggestions ──────────────────────────
def normalize_candidates(raw: str) -> List[str]:
    """
    Turn retail/device inputs like 'S8EG2A74MSB' or 'ATL-S8-HU' into
    a prioritized list of canonical firmware keys.
    Order: explicit mapping → special ATL guess → raw → EG2→G2 → suffix variants.
    """
    r = (raw or "").strip().upper()
    r = re.sub(r"\s+", "", r)

    mapped = RETAIL_TO_CANONICAL.get(r, [])
    cands: List[str] = list(mapped)

    if r.startswith("ATL-S8"):  # device name seen on About screen
        base_guess = "S8G2A74MS"
        for suf in ["-S01", "-S10", ""]:
            v = base_guess + suf
            if v not in cands:
                cands.append(v)

    if r not in cands:
        cands.append(r)

    base = re.sub(r"([A-Z0-9-]*[A-Z0-9])(?!-S\d{2}[A-Z]?)?[A-Z]*$", r"\1", r)
    if base and base not in cands:
        cands.append(base)

    eg2_to_g2 = base.replace("EG2", "G2")
    if eg2_to_g2 not in cands:
        cands.append(eg2_to_g2)

    base2 = re.sub(r"[A-Z]+$", "", eg2_to_g2)
    if base2 and base2 not in cands:
        cands.append(base2)

    for suf in COMMON_VARIANTS:
        dash_form = eg2_to_g2 + (suf if suf.startswith("-") else "-" + suf)
        nodash_form = eg2_to_g2 + (suf if not suf.startswith("-") else suf[1:])
        for v in (dash_form, nodash_form):
            if v not in cands:
                cands.append(v)

    seen, out = set(), []
    for x in cands:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out

def build_suggestions(raw: str) -> List[str]:
    """
    Build a short, user-friendly suggestion list from normalization,
    ranked: mapped → -S01/-S10 → base without suffix.
    """
    cands = normalize_candidates(raw)
    ranked: List[str] = []
    mapped = RETAIL_TO_CANONICAL.get(raw.upper(), [])
    ranked += mapped
    for suf in ("-S01", "-S10"):
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

# ────────────────────────── Discovery: API & JSON ──────────────────────────
def fetch_api_packages(model: str, mcu_version: str = "") -> List[Dict[str, Any]]:
    params = {"skuModel": model, "mcuVersion": mcu_version, "langType": 1, "iBookType": 2}
    try:
        r = SESSION.get(API_GET_IBOOK_LIST, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    code = data.get("code") or data.get("status")
    if code not in (None, 0, "0", 200, "200"):
        return []

    pkgs: List[Dict[str, Any]] = []

    soc_url = dig(data, "data", "softwareVo", "socVo", "socUrl")
    if isinstance(soc_url, str) and soc_url.startswith("http"):
        title = url_leaf_name(soc_url)
        ver = re.findall(r'([rv]?[\d._-]+)', title.replace(" ", ""))[:1] or ["N/A"]
        pkgs.append({
            "id": "1", "title": title, "version": ver[0], "date": "",
            "size": None, "url": soc_url, "hash": "", "source": "API"
        })

    candidate_arrays = [
        dig(data, "data", "softwareVo", "fileList"),
        dig(data, "data", "softwareVo", "socVo", "files"),
        dig(data, "data", "files"),
        dig(data, "files"),
    ]
    for arr in candidate_arrays:
        if isinstance(arr, list):
            for e in arr:
                if not isinstance(e, dict): continue
                url = e.get("url") or e.get("file") or e.get("download")
                if not url: continue
                title = e.get("title") or e.get("name") or url_leaf_name(url)
                pkgs.append({
                    "id": "0",
                    "title": title,
                    "version": e.get("version") or "N/A",
                    "date": e.get("date") or "",
                    "size": e.get("size") or None,
                    "url": url,
                    "hash": e.get("sha256") or e.get("sha1") or e.get("md5") or "",
                    "source": "API"
                })

    return pkgs

def series_from_model(q: str) -> List[str]:
    m = re.match(r'([A-Za-z]+?\d+)', q)
    if m:
        s = m.group(1)
        return [s, s.lower(), s.upper()]
    if len(q) >= 2:
        s = q[:2]
        return [s, s.lower(), s.upper()]
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
        if not head_ok(u):
            continue
        try:
            data = fetch_json(u)
        except Exception:
            continue

        if isinstance(data, list):
            iterable = data
        elif isinstance(data, dict):
            iterable = data.get("packages") or data.get("firmware") or data.get("files") or []
        else:
            iterable = []

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
            sha = e.get("sha256") or e.get("sha1") or e.get("md5") or ""
            full_url = url if url.startswith("http") else f"{BASE.rstrip('/')}/{url.lstrip('/')}"
            pkgs.append({
                "id": str(idx), "title": title, "version": version, "date": date,
                "size": size, "url": full_url, "hash": sha, "source": "JSON"
            })
        if pkgs:
            return pkgs, u
    return [], ""

# ────────────────────────── Discovery: Known mirrors (Aliyun, etc.) ──────────────────────────
def known_links_for_model(model: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for entry in KNOWN_LINKS:
        if re.search(entry["match"], model):
            url = entry["url"]
            if head_ok(url):
                title = entry.get("title") or url_leaf_name(url)
                ver = re.findall(r'([rv]?[\d._-]+)', url_leaf_name(url).replace(" ", ""))[:1] or ["N/A"]
                out.append({
                    "id": "0",
                    "title": f"[mirror] {title}",
                    "version": ver[0],
                    "date": "",
                    "size": None,
                    "url": url,
                    "hash": "",
                    "source": "MIRROR",
                })
    # number them
    for i, p in enumerate(out, 1):
        p["id"] = str(i)
    return out

# ────────────────────────── De-dupe ──────────────────────────
def dedupe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for r in rows:
        key = ((r.get("url") or "").strip(), (r.get("title") or "").strip())
        if key in seen:
            continue
        seen.add(key); out.append(r)
    return out

# ────────────────────────── Download ──────────────────────────
def download_with_progress(url: str, out_path: Path, expected_hash: str = "") -> None:
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    resume = tmp_path.stat().st_size if tmp_path.exists() else 0
    headers = {"Range": f"bytes={resume}-"} if resume > 0 else {}

    with SESSION.get(url, stream=True, headers=headers, timeout=30) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("Content-Length", "0"))
        if r.status_code == 206:
            try:
                full = SESSION.head(url, timeout=12, allow_redirects=True)
                total_size = int(full.headers.get("Content-Length", total_size))
            except Exception:
                pass

        mode = "ab" if resume > 0 else "wb"
        downloaded = resume
        task_desc = f"[bold]Downloading[/] {out_path.name}"
        with Progress(
            TextColumn(task_desc, justify="left"),
            BarColumn(),
            TransferSpeedColumn(),
            TextColumn("{task.completed:>10.0f}/{task.total:>10.0f} B"),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task("dl", total=total_size, completed=downloaded)
            with open(tmp_path, mode) as f:
                for chunk in r.iter_content(chunk_size=128 * 1024):
                    if not chunk: continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress.update(task_id, completed=downloaded)
        tmp_path.rename(out_path)

    if expected_hash:
        console.print("Verifying checksum...")
        algo = "sha256" if len(expected_hash) == 64 else ("sha1" if len(expected_hash) == 40 else "md5")
        if algo == "sha256":
            digest = sha256_file(out_path)
        elif algo == "sha1":
            import hashlib as _h; h = _h.sha1()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        else:
            import hashlib as _h; h = _h.md5()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        if digest.lower() != expected_hash.lower():
            console.print(f"[red]Checksum mismatch![/] expected {expected_hash}, got {digest}")
        else:
            console.print("[green]Checksum OK[/]")

# ────────────────────────── Selection UI ──────────────────────────
def show_candidates(title: str, tried: List[str], hits: List[str]) -> None:
    section(title, "Auto-normalized inputs and which matched the API")
    tbl = Table(show_lines=False, header_style="bold magenta")
    tbl.add_column("Tried", overflow="fold"); tbl.add_column("Matched", overflow="fold")
    maxlen = max(len(tried), len(hits))
    tried += [""] * (maxlen - len(tried)); hits += [""] * (maxlen - len(hits))
    for a, b in zip(tried, hits):
        tbl.add_row(a, b)
    console.print(tbl)

def select_from_rows(rows: List[Dict[str, Any]], title: str) -> Optional[Dict[str, Any]]:
    while True:
        section(title, "Select a package to download (0 to cancel)")
        if not rows:
            console.print("[red]No results.[/]"); return None
        table = Table(title=title, show_lines=False, header_style="bold magenta")
        cols = [("id","#"),("source","Source"),("title","Title"),("version","Version"),("date","Date"),("size","Size"),("url","URL")]
        for _, header in cols:
            table.add_column(header, overflow="fold")
        for r in rows:
            row = [str(r.get(k,"")) for k,_ in cols]
            table.add_row(*row)
        console.print(table)
        raw = Prompt.ask("Select #", default="1").strip()
        if raw == "0": clear_screen(); return None
        if raw.isdigit():
            i = int(raw)
            if 1 <= i <= len(rows): clear_screen(); return rows[i-1]

# ────────────────────────── Manual URL ──────────────────────────
def manual_url_flow() -> None:
    section("Manual URL", "Paste a direct firmware URL from ATOTO")
    url = Prompt.ask("Direct URL (or leave blank to abort)", default="").strip()
    if not url: section("Canceled"); return
    title = url_leaf_name(url)
    out_dir = Path("ATOTO_Firmware") / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / safe_filename(title)
    section("Download Ready", f"Saving to: {out_path}\n\nPress Ctrl+C to cancel")
    try:
        download_with_progress(url, out_path)
        section("Download Complete"); console.print(f"[green]Done![/] File saved:\n[bold]{out_path}[/]")
    except KeyboardInterrupt:
        section("Interrupted"); console.print("[yellow]Interrupted by user.[/]")
    except Exception as e:
        section("Download Failed"); console.print(f"[red]Download failed:[/] {e}")

# ────────────────────────── Main lookup orchestration ──────────────────────────
def try_lookup(model: str, mcu: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Returns (merged_packages, hit_candidates_list)."""
    cands = normalize_candidates(model)
    matched_api: List[Tuple[str, List[Dict[str, Any]]]] = []
    hits_list: List[str] = []

    # API first (aggregate across candidates)
    for cand in cands:
        section("Looking up Firmware (API)…", f"Trying: {cand}")
        pkgs = fetch_api_packages(cand, mcu)
        if pkgs:
            # annotate source (defensive)
            for p in pkgs:
                p.setdefault("source", "API")
            matched_api.append((cand, pkgs))
            hits_list.append(cand)

    merged: List[Dict[str, Any]] = []
    for src, pkgs in matched_api:
        for p in pkgs:
            q = p.copy()
            q["title"] = f"[{src}] {q['title']}"
            merged.append(q)

    # JSON probe: try candidates in order, add the first hit list we find
    if True:
        for cand in cands:
            section("Trying Fallback Discovery…", f"JSON probe: {cand}")
            pkgs_json, endpoint_used = discover_packages_via_json(cand)
            if pkgs_json:
                # annotate title with endpoint/series hint
                for p in pkgs_json:
                    p["title"] = f"[{cand}] {p['title']}"
                merged.extend(pkgs_json)
                break

    # Always offer mirrors for S8G2 family
    fam = cands[0] if cands else model
    mirror_pkgs = known_links_for_model(fam)
    merged.extend(mirror_pkgs)

    # De-dupe and number rows
    merged = dedupe_rows(merged)
    for i, p in enumerate(merged, 1):
        p["id"] = str(i)
        p.setdefault("source", "?")

    return merged, hits_list

def suggestions_menu(raw: str) -> Optional[str]:
    suggs = build_suggestions(raw)
    section("Did you mean…?", "Pick a nearby model to retry (M = Manual URL, 0 = cancel)")
    table = Table(show_lines=False, header_style="bold magenta")
    table.add_column("#"); table.add_column("Candidate")
    for i, s in enumerate(suggs, 1):
        table.add_row(str(i), s)
    console.print(table)
    ans = Prompt.ask("Select # / M for manual / 0 to cancel", default="1").strip().upper()
    if ans == "0": return None
    if ans == "M": manual_url_flow(); return None
    if ans.isdigit():
        i = int(ans)
        if 1 <= i <= len(suggs): return suggs[i-1]
    return None

def main() -> None:
    splash()
    section("Search Models", "Enter retail code or device name; I’ll normalize it automatically")
    raw_model = Prompt.ask("[bold]Product model / device name[/]", default="S8EG2A74MSB").strip().upper()
    mcu = Prompt.ask("[bold]MCU version[/] (blank if unsure)", default="").strip()

    pkgs, hits_list = try_lookup(raw_model, mcu)
    show_candidates("Normalization Results", normalize_candidates(raw_model), hits_list)

    if not pkgs:
        section("No Packages Found",
                "Could not find firmware via API/JSON/mirrors.\n"
                "Tip: check the unit's About page for the exact model line or try Manual URL.")
        cand = suggestions_menu(raw_model)
        if not cand: return
        pkgs, hits_list = try_lookup(cand, mcu)
        if not pkgs:
            section("Still No Packages",
                    f"Tried: {cand}\nYou can retry another suggestion or use Manual URL.")
            cand2 = suggestions_menu(cand)
            if not cand2: return
            pkgs, hits_list = try_lookup(cand2, mcu)
            if not pkgs:
                section("No Packages Found", "Last attempt also failed. Try Manual URL from ATOTO.")
                manual_url_flow()
                return

    chosen = select_from_rows(pkgs, "Available Packages")
    if not chosen:
        section("Canceled"); return

    model_for_path = (hits_list[0] if hits_list else raw_model)
    out_dir = Path("ATOTO_Firmware") / safe_filename(model_for_path)
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        section("Interrupted"); console.print("[yellow]Interrupted by user.[/]")
