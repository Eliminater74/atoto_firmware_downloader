#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATOTO Firmware Downloader (API-first, normalization, clean screens)
- Robust against API responses with data=None or unexpected shapes
- Uses official getIbookList API; falls back to JSON probing if needed
- Clear-screen UI + resumable downloads

Deps:
  pip install requests rich
"""

from __future__ import annotations
import json, math, re, hashlib
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

BASE = "https://resources.myatoto.com/atoto-product-ibook/ibMobile"
API_GET_IBOOK_LIST = f"{BASE}/getIbookList"
UA = "ATOTO-Firmware-CLI/2.2 (+https://github.com/Eliminater74)"

# ───────────── UI helpers ─────────────
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

# ───────────── HTTP session ─────────────
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

# ───────────── utils ─────────────
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

# ───────────── model normalization ─────────────
COMMON_VARIANTS = ["-S01", "-S10", "-S01W", "-S01R", "S01", "S10", "S01W", "S01R"]

def normalize_candidates(raw: str) -> List[str]:
    r = (raw or "").strip().upper()
    r = re.sub(r"\s+", "", r)

    cands = [r]

    base = re.sub(r"([A-Z0-9-]*[A-Z0-9])(?!-S\d{2}[A-Z]?)?[A-Z]*$", r"\1", r)
    if base not in cands:
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

# ───────────── small helpers ─────────────
def dig(obj: Any, *keys: str) -> Any:
    """Safely descend nested dicts; returns None on any mismatch."""
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur

# ───────────── API-first discovery ─────────────
def fetch_api_packages(model: str, mcu_version: str = "") -> List[Dict[str, Any]]:
    """
    Call ATOTO getIbookList; be defensive about shapes:
    - sometimes {"data": null}
    - sometimes different nesting
    """
    params = {
        "skuModel": model,
        "mcuVersion": mcu_version,
        "langType": 1,   # English
        "iBookType": 2,  # firmware/software page
    }
    try:
        r = SESSION.get(API_GET_IBOOK_LIST, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    # If API returns an error code, bail quietly
    code = data.get("code") or data.get("status")
    if code not in (None, 0, "0", 200, "200"):
        return []

    pkgs: List[Dict[str, Any]] = []

    # Primary known field (guarded)
    soc_url = dig(data, "data", "softwareVo", "socVo", "socUrl")
    if isinstance(soc_url, str) and soc_url.startswith("http"):
        title = Path(soc_url).name
        ver = re.findall(r'([rv]?[\d._-]+)', title.replace(" ", ""))[:1] or ["N/A"]
        pkgs.append({
            "id": "1", "title": title, "version": ver[0], "date": "",
            "size": None, "url": soc_url, "hash": ""
        })

    # Also scan for arrays in a few likely places (all guarded)
    candidate_arrays = [
        dig(data, "data", "softwareVo", "fileList"),
        dig(data, "data", "softwareVo", "socVo", "files"),
        dig(data, "data", "files"),
        dig(data, "files"),
    ]
    for arr in candidate_arrays:
        if isinstance(arr, list):
            for e in arr:
                if not isinstance(e, dict):
                    continue
                url = e.get("url") or e.get("file") or e.get("download")
                if not url:
                    continue
                pkgs.append({
                    "id": str(len(pkgs) + 1),
                    "title": e.get("title") or e.get("name") or Path(url).name,
                    "version": e.get("version") or "N/A",
                    "date": e.get("date") or "",
                    "size": e.get("size") or None,
                    "url": url,
                    "hash": e.get("sha256") or e.get("sha1") or e.get("md5") or "",
                })

    return pkgs

# ───────────── Fallback JSON probing ─────────────
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
            if not isinstance(e, dict):
                continue
            url = e.get("url") or e.get("file") or e.get("download") or e.get("href")
            if not url:
                continue
            title = e.get("title") or e.get("name") or Path(url).name
            version = e.get("version") or re.findall(r'([rv]?[\d._-]+)', (title or "").replace(" ", ""))[:1]
            version = version[0] if isinstance(version, list) and version else (version or "N/A")
            size = e.get("size") or None
            date = e.get("date") or e.get("time") or e.get("released") or ""
            sha = e.get("sha256") or e.get("sha1") or e.get("md5") or ""
            full_url = url if url.startswith("http") else f"{BASE.rstrip('/')}/{url.lstrip('/')}"
            pkgs.append({"id": str(idx), "title": title, "version": version, "date": date,
                         "size": size, "url": full_url, "hash": sha})
        if pkgs:
            return pkgs, u
    return [], ""

# ───────────── download ─────────────
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
            import hashlib as _h
            h = _h.sha1()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        else:
            import hashlib as _h
            h = _h.md5()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        if digest.lower() != expected_hash.lower():
            console.print(f"[red]Checksum mismatch![/] expected {expected_hash}, got {digest}")
        else:
            console.print("[green]Checksum OK[/]")

# ───────────── selection UI ─────────────
def show_candidates(title: str, tried: List[str], hits: List[str]) -> None:
    section(title, "Auto-normalized model inputs and which ones matched")
    tbl = Table(show_lines=False, header_style="bold magenta")
    tbl.add_column("Tried", overflow="fold")
    tbl.add_column("Matched", overflow="fold")
    maxlen = max(len(tried), len(hits))
    tried += [""] * (maxlen - len(tried))
    hits  += [""] * (maxlen - len(hits))
    for a, b in zip(tried, hits):
        tbl.add_row(a, b)
    console.print(tbl)

def select_from_rows(rows: List[Dict[str, Any]], title: str) -> Optional[Dict[str, Any]]:
    while True:
        section(title, "Select a package to download (0 to cancel)")
        if not rows:
            console.print("[red]No results.[/]")
            return None
        table = Table(title=title, show_lines=False, header_style="bold magenta")
        for key, header in [("id","#"),("title","Title"),("version","Version"),("date","Date"),("size","Size"),("url","URL")]:
            table.add_column(header, overflow="fold")
        for r in rows:
            table.add_row(*[str(r.get(k,"")) for k,_ in [("id","#"),("title","Title"),("version","Version"),("date","Date"),("size","Size"),("url","URL")]])
        console.print(table)
        raw = Prompt.ask("Select #", default="1").strip()
        if raw == "0":
            clear_screen()
            return None
        if raw.isdigit():
            i = int(raw)
            if 1 <= i <= len(rows):
                clear_screen(); return rows[i-1]

# ───────────── main ─────────────
def main() -> None:
    splash()
    section("Search Models", "Enter the retail code; I’ll normalize it automatically")
    raw_model = Prompt.ask("[bold]Product model[/]", default="S8EG2A74MSB").strip().upper()
    mcu = Prompt.ask("[bold]MCU version[/] (blank if unsure)", default="").strip()

    cands = normalize_candidates(raw_model)
    matched: List[Tuple[str, List[Dict[str, Any]]]] = []
    hits_list: List[str] = []

    for cand in cands:
        section("Looking up Firmware (API)…", f"Trying: {cand}")
        pkgs = fetch_api_packages(cand, mcu)
        if pkgs:
            matched.append((cand, pkgs))
            hits_list.append(cand)

    show_candidates("Normalization Results", cands.copy(), hits_list.copy())

    if not matched:
        base = cands[2] if len(cands) >= 3 else (cands[0] if cands else raw_model)
        section("Trying Fallback Discovery…", f"Base: {base}")
        pkgs, endpoint_used = discover_packages_via_json(base)
        if not pkgs:
            section("No Packages Found",
                    "Could not find firmware via API or JSON probing.\n"
                    "Tip: check the unit's About page for the exact model line.")
            return
        for i, p in enumerate(pkgs, 1):
            p["id"] = str(i)
        chosen = select_from_rows(pkgs, f"Available Packages (fallback via {endpoint_used})")
    else:
        merged: List[Dict[str, Any]] = []
        for src, pkgs in matched:
            for p in pkgs:
                q = p.copy()
                q["title"] = f"[{src}] {q['title']}"
                merged.append(q)
        for i, p in enumerate(merged, 1):
            p["id"] = str(i)
        chosen = select_from_rows(merged, "Available Packages (API)")

    if not chosen:
        section("Canceled"); return

    model_for_path = hits_list[0] if hits_list else raw_model
    out_dir = Path("ATOTO_Firmware") / safe_filename(model_for_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(f"{model_for_path}_{chosen.get('version','NAv')}_{Path(chosen['url']).name}")
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
