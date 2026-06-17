#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI layer for ATOTO Firmware Downloader

- Profiles (persisted): model / MCU / resolution / variant prefs / prefer-universal
- Rich menu + results table
- Live status while probing API/JSON/mirrors (no more "stuck at starting")
- Resume download with progress + optional checksum verify
- Advanced / Add-ons menu (e.g., OTA extractor)
"""

from __future__ import annotations
import re
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box
from rich.status import Status
from rich.progress import (
    BarColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn
)

# Core primitives we render/use from the UI
from .core import (
    try_lookup,
    normalize_candidates,
    tag_rows,
    group_by_url,
    human_size,
    sha256_file,
    load_cfg,
    save_cfg,
    config_path,
    add_history_entry,
)
from .core.utils import url_leaf_name  # leaf filename helper
from .tui import Menu, header_art, clear_screen, safe_filename, msvcrt, section

# Add-ons registry (optional, used by Advanced / Add-ons menu)
try:
    from .addons import available as addons_available
except Exception:
    addons_available = lambda: []  # graceful fallback if addons package is absent

console = Console()

# ── Thread-safe background update check ──────────────────────────────────────
import threading as _threading
_update_result: list = []
_update_lock   = _threading.Lock()
_update_thread: "Optional[_threading.Thread]" = None

def _start_update_check() -> None:
    global _update_thread
    if _update_thread is not None:
        return
    def _worker():
        try:
            from . import __version__ as _ver
            from .core.utils import check_github_update
            res = check_github_update(_ver)
            if res:
                with _update_lock:
                    _update_result.append(res)
        except Exception:
            pass
    _update_thread = _threading.Thread(target=_worker, daemon=True)
    _update_thread.start()

def _poll_update() -> "Optional[tuple]":
    """Return (tag, url) if an update was found, else None. Non-blocking."""
    with _update_lock:
        return _update_result[0] if _update_result else None

def _open_folder(path: Path) -> None:
    """Open a folder in the OS file manager (best-effort, never raises)."""
    import subprocess, sys
    try:
        if sys.platform == "win32":
            import os; os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass

# ────────────────────────── Profile UI ──────────────────────────
def prompt_profile(existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    clear_screen(console)
    console.print(Panel.fit("Create / Edit Profile", border_style="cyan"))
    prof = dict(existing or {})
    while True:
        name = Prompt.ask("Profile name", default=prof.get("name", "My S8")).strip()
        if name:
            prof["name"] = name
            break
        console.print("[red]Profile name cannot be empty.[/]")
    prof["model"] = Prompt.ask("Model / Device name", default=prof.get("model", "S8EG2A74MSB")).upper().strip()
    prof["mcu"]   = Prompt.ask("MCU version (Optional - helps find newer firmware)", default=prof.get("mcu", "")).strip()
    _res_items = [
        ("1280x720  (S8 / A6 QLED / F7 PE / X10)", "1280x720"),
        ("1024x600  (Standard 7- / 9- / 10-inch)",  "1024x600"),
        ("800x480   (Older / budget units)",         "800x480"),
        ("Custom / Other",                           "CUSTOM"),
    ]
    _cur_res = prof.get("res", "1280x720")
    _res_menu = Menu(console, _res_items,
                     title="Display Resolution",
                     subtitle=f"Current: {_cur_res} — arrow keys to select")
    _res_pick = _res_menu.show()
    if _res_pick == "CUSTOM" or not _res_pick:
        prof["res"] = Prompt.ask("Enter resolution (e.g. 800x480)", default=_cur_res).strip()
    else:
        prof["res"] = _res_pick

    vdefault = prof.get("variants", "ANY")
    v = Prompt.ask("Variant prefs (MS,PE,PM or ANY)", default=vdefault).upper().replace(" ", "")
    if v in ("", "ANY"):
        prof["variants"] = "ANY"
    else:
        keep = [t for t in v.split(",") if t in ("MS", "PE", "PM")]
        prof["variants"] = ",".join(sorted(set(keep))) if keep else "ANY"

    prof["prefer_universal"] = Confirm.ask(
        "Prefer Universal packages?",
        default=bool(prof.get("prefer_universal", True))
    )
    return prof

def prompt_adhoc_params() -> Optional[Dict[str, Any]]:
    clear_screen(console)
    console.print(Panel.fit("Ad-hoc Search (One-time)", border_style="cyan"))
    
    # 1. Model (Text is still best here)
    model = Prompt.ask("Model / Device name (e.g. F7G2B7WE)", default="S8EG2A74MSB").upper().strip()
    if not model: return None

    # 2. Resolution (Menu is faster/nicer)
    res_items = [
        ("1280x720 (S8/A6 QLED, F7 PE)", "1280x720"),
        ("1024x600 (Standard 7/9/10 inch)", "1024x600"),
        ("Custom / Other", "CUSTOM")
    ]
    res_menu = Menu(console, res_items, title="Select Resolution", subtitle=f"Model: {model}")
    choice = res_menu.show()
    if not choice: return None
    
    if choice == "CUSTOM":
        res = Prompt.ask("Enter resolution (e.g. 800x480)", default="1024x600").strip()
    else:
        res = choice

    # 3. MCU (optional — press Enter to skip)
    mcu = Prompt.ask(
        "MCU version [dim](optional — press Enter to skip)[/]",
        default=""
    ).strip()

    # 4. Deep Search toggle
    deep = Confirm.ask(
        "Enable Deep Search? [dim](slower — tries many more model variants)[/]",
        default=False
    )

    return {
        "name": "Ad-hoc",
        "model": model,
        "res": res,
        "mcu": mcu,
        "variants": "ANY",
        "prefer_universal": True,
        "_deep": deep,
    }

def profile_menu(cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    while True:
        # Build menu items
        names = sorted(cfg["profiles"].keys())
        items = []
        for name in names:
            p = cfg["profiles"][name]
            desc = f"{name} [dim]({p.get('model','')}, {p.get('res','')})[/]"
            items.append((desc, name))
        
        # Actions
        items.append(("---", None))
        items.append(("[bold green]Create New Profile[/]", "CREATE"))
        items.append(("[bold red]Delete a Profile[/]", "DELETE"))
        items.append(("[bold yellow]Edit a Profile[/]", "EDIT"))
        items.append(("[dim]Back[/]", "BACK"))

        # Pre-select based on last usage if possible
        menu = Menu(console, items, 
                    title="Profiles", 
                    subtitle=f"Config: {config_path()}\nSelect a profile to use it, or manage them.")
        
        # If we just want to select, we run show(). 
        # But here we have mixed actions (Select vs Manage).
        # We'll handle the generic "name" return as "Select this profile".
        
        choice = menu.show()
        if not choice or choice == "BACK":
            return None
        
        if choice == "CREATE":
            p = prompt_profile({})
            cfg["profiles"][p["name"]] = p
            save_cfg(cfg)
        elif choice == "DELETE":
            # Sub-menu for deletion
            del_items = [(n, n) for n in names]
            del_items.append(("Cancel", None))
            to_del = Menu(console, del_items, title="Delete Profile").show()
            if to_del and Confirm.ask(f"Delete profile '{to_del}'?", default=False):
                del cfg["profiles"][to_del]
                if cfg.get("last_profile") == to_del:
                    cfg["last_profile"] = ""
                save_cfg(cfg)
        elif choice == "EDIT":
             # Sub-menu for edit
            edit_items = [(n, n) for n in names]
            edit_items.append(("Cancel", None))
            to_edit = Menu(console, edit_items, title="Edit Profile").show()
            if to_edit:
                p = prompt_profile(cfg["profiles"][to_edit])
                if p["name"] != to_edit:
                    del cfg["profiles"][to_edit]
                cfg["profiles"][p["name"]] = p
                save_cfg(cfg)
        else:
             # It's a profile name
            key = choice
            cfg["last_profile"] = key
            save_cfg(cfg)
            return cfg["profiles"][key]

# ────────────────────────── Results table & selection ──────────────────────────
def _parse_selection(raw: str, max_n: int) -> List[int]:
    """Parse '1', '1,3', '1-3', '1,3-5' into sorted 0-based indices."""
    indices: set = set()
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            lo_s, _, hi_s = part.partition("-")
            try:
                lo, hi = int(lo_s.strip()), int(hi_s.strip())
                indices.update(range(max(1, lo), min(max_n, hi) + 1))
            except ValueError:
                pass
        elif part.isdigit():
            v = int(part)
            if 1 <= v <= max_n:
                indices.add(v)
    return sorted(i - 1 for i in indices)


def render_and_pick(
    rows: List[Dict[str, Any]],
    my_res: str,
    prefer_universal: bool,
    want_variants: List[str],
    downloaded_urls: "Optional[set]" = None,
) -> List[Dict[str, Any]]:
    """Return a list of selected packages (empty = canceled)."""
    tag_rows(rows, my_res)
    grouped = group_by_url(rows)
    if isinstance(grouped, dict):
        grouped = list(grouped.values())

    if downloaded_urls:
        for r in grouped:
            if r.get("url") in downloaded_urls:
                r["fit"] = "✓ DL"

    def row_ok(r: Dict[str, Any]) -> bool:
        if prefer_universal and not r.get("scope", "").startswith("Universal"):
            return False
        if want_variants and r.get("variants") not in ("-", "", None):
            row_vars = set(r["variants"].split(","))
            if not (row_vars & set(want_variants)):
                return False
        return True

    filt = [r for r in grouped if row_ok(r)] or grouped

    idx = 0
    selected: set = set()  # 0-based indices toggled via Space (msvcrt only)

    _src_color = {"API": "green", "JSON": "cyan", "MIRROR": "yellow", "Redstone": "magenta"}
    cols = [
        ("id", "#"), ("source", "Src"), ("title", "Title"), ("version", "Ver"),
        ("date", "Date"), ("size", "Size"), ("res", "Res"), ("scope", "Scope"),
        ("variants", "Variants"), ("fit", "Fit"), ("url", "URL")
    ]
    col_specs = {
        "Title":    {"max_width": 40, "overflow": "ellipsis", "no_wrap": True},
        "URL":      {"max_width": 30, "overflow": "ellipsis", "no_wrap": True},
        "Ver":      {"max_width": 20, "overflow": "ellipsis", "no_wrap": True},
        "Date":     {"no_wrap": True, "min_width": 10},
        "Size":     {"no_wrap": True, "min_width": 8},
        "Res":      {"no_wrap": True},
        "Src":      {"no_wrap": True},
        "Scope":    {"max_width": 15, "overflow": "ellipsis", "no_wrap": True},
        "Variants": {"max_width": 10, "overflow": "fold"},
    }

    while True:
        section(
            console,
            "Firmware Results",
            "Universal = not tied to a specific resolution. "
            "Res-specific = package names that explicitly mention 1024x600 or 1280x720."
        )
        hint_nav = "Use arrows + Space to multi-select, Enter to confirm" if msvcrt else "Enter numbers to select (e.g. 1  or  1,3  or  1-3)"
        console.print(Panel.fit(
            f"[bold]Tip[/]: Prefer Universal packages for the same device family; "
            "use Res-specific only when a package explicitly targets your screen.\n"
            f"[dim]Profile Fit: {my_res or '?'} · Variant prefs: "
            f"{', '.join(want_variants) if want_variants else 'ANY'} · "
            f"Scope: {'Universal preferred' if prefer_universal else 'All'} · {hint_nav}[/]",
            border_style="cyan"
        ))

        table = Table(
            title="Available Packages",
            show_lines=False,
            header_style="bold magenta",
            box=box.SIMPLE_HEAVY
        )
        for _, hdr in cols:
            spec = col_specs.get(hdr, {"overflow": "fold"})
            table.add_column(hdr, **spec)

        for i, r in enumerate(filt):
            r_view = r.copy()
            r_view["id"] = "[x]" if i in selected else str(i + 1)
            r_view["size"] = human_size(r.get("size"))
            src = r.get("source", "?")
            r_view["source"] = f"[{_src_color.get(src, 'dim')}]{src}[/]"

            is_cursor = bool(msvcrt) and (i == idx)
            is_sel    = i in selected
            if is_cursor and is_sel:
                style = "reverse bold green"
            elif is_cursor:
                style = "reverse bold cyan"
            elif is_sel:
                style = "bold green"
            else:
                style = ""
            table.add_row(*[str(r_view.get(k, "")) for k, _ in cols], style=style)

        console.print(table)

        if not msvcrt:
            console.print(f"[dim]Total {len(filt)} packages[/]")
            raw = Prompt.ask(
                "Select #s (e.g. 1  or  1,3  or  1-3; 0 to cancel)",
                default="1"
            ).strip()
            if raw == "0" or not raw:
                return []
            indices = _parse_selection(raw, len(filt))
            if not indices:
                return []
            chosen_items = [filt[i] for i in indices]
            result = []
            for item in chosen_items:
                if item.get("fit") == "⚠":
                    console.print(
                        f"[yellow]Heads-up:[/] {item.get('title', '')} looks like "
                        f"[bold]{item.get('res', '?')}[/], profile is [bold]{my_res}[/]."
                    )
                    if not Confirm.ask("Include anyway?", default=False):
                        continue
                result.append(item)
            return result

        sel_info = f" · {len(selected)} marked" if selected else ""
        console.print(
            f"[dim]Cursor: #{idx+1}/{len(filt)}{sel_info} · "
            "arrows=navigate · Space=mark · a=all · Enter=confirm · Esc=cancel[/]"
        )

        key = msvcrt.getch()
        if key in (b'\000', b'\xe0'):
            key = msvcrt.getch()
            if key == b'H':
                idx = max(0, idx - 1)
            elif key == b'P':
                idx = min(len(filt) - 1, idx + 1)
        elif key == b' ':
            if idx in selected:
                selected.discard(idx)
            else:
                selected.add(idx)
        elif key in (b'a', b'A'):
            if len(selected) == len(filt):
                selected.clear()
            else:
                selected.update(range(len(filt)))
        elif key == b'\r':
            break
        elif key in (b'\x1b', b'0'):
            return []

    # msvcrt: build result from marked rows (or cursor row if nothing marked)
    chosen_items = [filt[i] for i in sorted(selected)] if selected else [filt[idx]]
    result = []
    for item in chosen_items:
        if item.get("fit") == "⚠":
            console.print(
                f"[yellow]Heads-up:[/] {item.get('title', '')} looks like "
                f"[bold]{item.get('res', '?')}[/], profile is [bold]{my_res}[/]."
            )
            if not Confirm.ask("Include anyway?", default=False):
                continue
        result.append(item)
    return result

# ────────────────────────── Download ──────────────────────────
_RETRY_ON = (
    "requests.exceptions.ChunkedEncodingError",
    "requests.exceptions.ConnectionError",
    "requests.exceptions.Timeout",
)
_MAX_DL_RETRIES = 3

def download_with_progress(url: str, out_path: Path, expected_hash: str = "", session=None) -> None:
    import time, hashlib
    import requests as _req

    from .core import SESSION
    sess = session if session else SESSION

    tmp = out_path.with_suffix(out_path.suffix + ".part")

    for attempt in range(_MAX_DL_RETRIES + 1):
        # Re-read resume point each attempt so partial progress is kept
        resume = tmp.stat().st_size if tmp.exists() else 0
        headers = {"Range": f"bytes={resume}-"} if resume > 0 else {}

        try:
            with sess.get(url, stream=True, headers=headers, timeout=30) as r:
                r.raise_for_status()

                # Server ignored Range header — discard stale .part to avoid corruption
                if resume > 0 and r.status_code == 200:
                    console.print("[yellow]Server does not support resume — restarting.[/]")
                    tmp.unlink(missing_ok=True)
                    resume = 0

                total = int(r.headers.get("Content-Length", "0"))
                if r.status_code == 206 and total:
                    try:
                        full = SESSION.head(url, timeout=8, allow_redirects=True)
                        total = int(full.headers.get("Content-Length", 0))
                    except Exception:
                        total = resume + total

                p_total = (resume + total) if total > 0 else None
                mode = "ab" if resume > 0 else "wb"
                downloaded = resume

                task_desc = f"[bold]Downloading[/] {out_path.name}"
                try:
                    with Progress(
                        TextColumn(task_desc, justify="left"),
                        BarColumn(),
                        TransferSpeedColumn(),
                        TextColumn("{task.completed:>10.0f}/{task.total:>10.0f} B"),
                        TimeRemainingColumn(),
                        console=console,
                        transient=False,
                    ) as progress:
                        task_id = progress.add_task("dl", total=p_total, completed=downloaded)
                        with open(tmp, mode) as f:
                            for chunk in r.iter_content(chunk_size=128 * 1024):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                downloaded += len(chunk)
                                progress.update(task_id, completed=downloaded)
                except KeyboardInterrupt:
                    console.print(
                        f"\n[yellow]Download paused.[/] Partial file kept — next run will resume.\n"
                        f"[dim]{tmp}[/]"
                    )
                    raise
            break  # success — exit retry loop

        except KeyboardInterrupt:
            raise
        except (_req.exceptions.ChunkedEncodingError,
                _req.exceptions.ConnectionError,
                _req.exceptions.Timeout) as exc:
            if attempt >= _MAX_DL_RETRIES:
                raise
            wait = 2 ** attempt
            console.print(
                f"[yellow]Network error ({exc.__class__.__name__}) — "
                f"retrying in {wait}s ({attempt + 1}/{_MAX_DL_RETRIES})…[/]"
            )
            time.sleep(wait)

    tmp.rename(out_path)

    if expected_hash:
        console.print("Verifying checksum…")
        algo = "sha256" if len(expected_hash) == 64 else ("sha1" if len(expected_hash) == 40 else "md5")
        h = hashlib.new(algo)
        with out_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        digest = h.hexdigest()
        if digest.lower() != expected_hash.lower():
            console.print(f"[red]Checksum mismatch![/] expected {expected_hash}, got {digest}")
        else:
            console.print(f"[green]Checksum OK[/] ({algo})")

    console.print(f"\n[bold green]Download Complete![/] Saved to: {out_path.name}")
    console.input("[dim]Press Enter to continue...[/]")

# ────────────────────────── Search & Download flow ──────────────────────────
def run_search_download_flow(profile: Dict[str, Any], out_base: Path, verbose: bool, deep_scan: bool = False, include_beta: bool = False) -> None:
    model = profile.get("model", "").strip() or Prompt.ask("Model / Device", default="S8EG2A74MSB").strip()
    mcu   = profile.get("mcu", "").strip()
    my_res = profile.get("res", "1280x720").strip()
    variants_pref = [] if profile.get("variants", "ANY") == "ANY" else profile.get("variants", "ANY").split(",")
    prefer_universal = bool(profile.get("prefer_universal", True))

    # searching screen + live spinner
    section(
        console,
        "Searching…",
        f"Model {model} • MCU {mcu or 'n/a'} • Res {my_res}\n"
        "[dim]Probing API, JSON and mirrors. This may take several seconds.[/]"
    )

    with Status("[bold]Searching firmware…[/] starting", console=console, spinner="dots") as status:
        def progress_cb(msg: str):
            status.update(f"[bold]Searching firmware…[/] {msg}")
            if verbose:
                console.log(msg)

        rows, hits = try_lookup(model, mcu, progress=progress_cb, deep_scan=deep_scan, include_beta=include_beta)

    # optional verbose normalization view
    if verbose:
        tbl = Table(
            title="Normalization Results",
            show_lines=False,
            header_style="bold magenta",
            box=box.SIMPLE_HEAVY
        )
        tbl.add_column("Tried", overflow="fold")
        tbl.add_column("Matched", overflow="fold")
        tried = normalize_candidates(model)
        L = max(len(tried), len(hits))
        tried += [""] * (L - len(tried))
        hits  += [""] * (L - len(hits))
        for a, b in zip(tried, hits):
            tbl.add_row(a, b)
        console.print(tbl)

    if not rows:
        tips = [
            "1. Try a simpler model name in [cyan]Ad-hoc Search[/] (e.g. just [bold]F7[/] or [bold]S8[/]).",
            "2. If you have a download link from support, use [cyan]Manual URL Download[/].",
        ]
        if not deep_scan:
            tips.insert(0, "0. [bold green]Enable Deep Search[/] — it tries many more model variants and platforms.")
        if mcu:
            tips.append(f"3. Remove the MCU version ([bold]{mcu}[/]) from your profile and try again.")
        section(
            console,
            "No Packages Found",
            f"[yellow]Nothing found for '[bold]{model}[/]' across API, JSON, and mirrors.[/]\n\n"
            "[bold]Suggestions:[/]\n" + "\n".join(tips)
        )
        return

    import shutil
    from datetime import datetime

    _dl_urls = {e["url"] for e in load_cfg().get("history", [])}
    model_for_path = (hits[0] if hits else model)

    while True:
        chosen_list = render_and_pick(rows, my_res, prefer_universal, variants_pref,
                                      downloaded_urls=_dl_urls)
        if not chosen_list:
            section(console, "Canceled")
            return

        if len(chosen_list) == 1:
            chosen_single = chosen_list[0]
            console.print(Panel(
                f"[bold cyan]Title:[/] {chosen_single.get('title')}\n"
                f"[bold cyan]Version:[/] {chosen_single.get('version')}\n"
                f"[bold cyan]Date:[/] {chosen_single.get('date')}\n"
                f"[bold cyan]Size:[/] {human_size(chosen_single.get('size'))}\n"
                f"[bold cyan]Resolution:[/] {chosen_single.get('res')}\n"
                f"[bold cyan]Scope:[/] {chosen_single.get('scope')}\n"
                f"[bold cyan]URL:[/] [link={chosen_single.get('url')}]{chosen_single.get('url')}[/]",
                title="Selected Package Details",
                border_style="green",
                expand=False
            ))
            if Confirm.ask("Download this firmware?", default=True):
                items_to_download = chosen_list
                break
            console.print("[dim]Returning to list...[/]")
        else:
            batch_tbl = Table(
                title=f"Batch Download — {len(chosen_list)} packages",
                box=box.SIMPLE_HEAVY,
                header_style="bold magenta"
            )
            batch_tbl.add_column("#", style="dim", no_wrap=True)
            batch_tbl.add_column("Title", max_width=40, overflow="ellipsis")
            batch_tbl.add_column("Version", max_width=20, overflow="ellipsis")
            batch_tbl.add_column("Size", no_wrap=True)
            for bi, bitem in enumerate(chosen_list, 1):
                batch_tbl.add_row(
                    str(bi),
                    bitem.get("title", ""),
                    bitem.get("version", ""),
                    human_size(bitem.get("size")),
                )
            console.print(batch_tbl)
            if Confirm.ask(f"Download all {len(chosen_list)} packages?", default=True):
                items_to_download = chosen_list
                break
            console.print("[dim]Returning to list...[/]")

    out_dir = out_base / safe_filename(model_for_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    for dl_idx, chosen in enumerate(items_to_download, 1):
        if len(items_to_download) > 1:
            section(console, f"Item {dl_idx}/{len(items_to_download)}", chosen.get("title", ""))

        filename = safe_filename(
            f"{model_for_path}_{chosen.get('version', 'NAv')}_{url_leaf_name(chosen['url'])}"
        )
        out_path = out_dir / filename

        # ── File-exists check ─────────────────────────────────────────────────
        if out_path.exists():
            existing_mb = out_path.stat().st_size / 1_048_576
            console.print(
                f"\n[yellow]File already exists:[/] {out_path.name} "
                f"([bold]{existing_mb:.1f} MB[/])"
            )
            fc = Menu(console, [
                ("Re-download (overwrite)",   "overwrite"),
                ("Skip — keep existing file", "skip"),
            ], title="File Exists").show()
            if fc == "skip" or not fc:
                console.print("[dim]Skipped — using existing file.[/]")
                continue
            out_path.unlink()

        # ── Disk-space check ──────────────────────────────────────────────────
        pkg_size = chosen.get("size") or 0
        if pkg_size:
            free = shutil.disk_usage(out_dir).free
            if free < pkg_size:
                console.print(
                    f"\n[red]Not enough disk space.[/] "
                    f"Need [bold]{human_size(pkg_size)}[/], "
                    f"only [bold]{human_size(free)}[/] free on that drive."
                )
                if not Confirm.ask("Try anyway?", default=False):
                    continue

        section(
            console,
            "Download Ready",
            f"Saving to: {out_path}\nReported size: {human_size(pkg_size or None)}\n\nPress Ctrl+C to pause"
        )
        try:
            download_with_progress(chosen["url"], out_path, expected_hash=chosen.get("hash", ""))
            section(console, "Download Complete" if len(items_to_download) == 1 else f"Done {dl_idx}/{len(items_to_download)}")
            console.print(f"[green]Saved:[/] {out_path}")

            _cfg = load_cfg()
            add_history_entry(_cfg, {
                "model":         model,
                "title":         chosen.get("title", ""),
                "version":       chosen.get("version", ""),
                "date":          chosen.get("date", ""),
                "url":           chosen.get("url", ""),
                "file":          str(out_path),
                "downloaded_at": datetime.now().isoformat(timespec="seconds"),
            })
            _dl_urls.add(chosen["url"])

            if dl_idx == len(items_to_download):
                if _cfg.get("auto_open_folder"):
                    _open_folder(out_dir)
                elif Confirm.ask("Open download folder?", default=True):
                    _open_folder(out_dir)

        except KeyboardInterrupt:
            section(console, "Paused")
            console.print(
                "[yellow]Download paused.[/] The partial file has been kept.\n"
                "Run the same search and select this firmware again to resume."
            )
            break
        except Exception as e:
            section(console, "Download Failed")
            console.print(f"[red]Download failed:[/] {e}")
            if len(items_to_download) > 1:
                if not Confirm.ask("Continue with remaining packages?", default=True):
                    break

# ────────────────────────── Advanced / Add-ons menu ──────────────────────────
def addons_menu() -> None:
    items_avail = addons_available()
    if not items_avail:
        console.clear()
        console.print("[yellow]No add-ons registered.[/]")
        Confirm.ask("Back", default=True)
        return

    # Convert to Menu items
    # items_avail is List[Tuple[name, func]]
    menu_items = []
    for name, func in items_avail:
        menu_items.append((name, func))
    
    menu_items.append(("---", None))
    menu_items.append(("Back", None))

    menu = Menu(console, menu_items, title="Advanced / Add-ons")
    func = menu.show()

    if func:
        # run the add-on action (callable expects Console)
        try:
            func(console)
        except TypeError:
            # if your callable signature differs, you can adapt here
            func(console=console)

# ────────────────────────── Manual URL ──────────────────────────
def manual_url_flow(download_dir: Path) -> None:
    section(console, "Manual URL", "Paste a direct firmware URL from ATOTO")
    url = Prompt.ask("Direct URL (or leave blank to abort)", default="").strip()
    if not url:
        section(console, "Canceled")
        return
    download_dir.mkdir(parents=True, exist_ok=True)
    out = download_dir / safe_filename(url_leaf_name(url))

    if out.exists():
        console.print(f"\n[yellow]File already exists:[/] {out.name} ({out.stat().st_size / 1_048_576:.1f} MB)")
        skip = not Confirm.ask("Re-download (overwrite)?", default=False)
        if skip:
            console.print("[dim]Skipped.[/]")
            return
        out.unlink()

    section(console, "Download Ready", f"Saving to: {out}\n\nPress Ctrl+C to pause")
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; X10G2A7E Build/QUokka)",
            "Accept": "*/*"
        })
        download_with_progress(url, out, session=s)
        section(console, "Download Complete")
        console.print(f"[green]Done![/] File saved:\n[bold]{out}[/]")
        if Confirm.ask("Open download folder?", default=True):
            _open_folder(download_dir)
    except KeyboardInterrupt:
        section(console, "Paused")
        console.print(
            "[yellow]Download paused.[/] Partial file kept — run again to resume.\n"
            f"[dim]{out.with_suffix(out.suffix + '.part')}[/]"
        )
    except Exception as e:
        section(console, "Download Failed")
        console.print(f"[red]Download failed:[/] {e}")

# ────────────────────────── Settings menu ──────────────────────────
def _settings_menu(cfg: Dict[str, Any], out_dir: Path) -> None:
    from . import __version__
    while True:
        verbose_lbl    = "[green]ON[/]"  if cfg.get("verbose")          else "[dim]off[/]"
        auto_open_lbl  = "[green]ON[/]"  if cfg.get("auto_open_folder") else "[dim]off[/]"
        beta_lbl       = "[yellow]ON[/]" if cfg.get("include_beta")     else "[dim]off[/]"
        hist_count     = len(cfg.get("history", []))
        upd = _poll_update()
        ver_line = (
            f"v{__version__} — [green]up to date[/]" if upd is None
            else f"v{__version__} — [yellow]v{upd[0]} available[/]"
        )

        items = [
            (f"Verbose logging          {verbose_lbl}",         "VERBOSE"),
            (f"Auto-open folder         {auto_open_lbl}",       "AUTO_OPEN"),
            (f"Include beta firmware    {beta_lbl}",            "BETA"),
            (f"Download history         {hist_count} entries",  "HISTORY"),
            ("Open output folder",                               "OPEN_OUT"),
            ("Open config folder",                               "OPEN_CFG"),
            (f"Version                  {ver_line}",            None),
            ("[dim]Back[/]",                                     "BACK"),
        ]
        choice = Menu(
            console, items,
            title="Settings / Info",
            subtitle=f"Config: {config_path()}"
        ).show()

        if not choice or choice == "BACK":
            break
        elif choice == "VERBOSE":
            cfg["verbose"] = not cfg.get("verbose", False)
            save_cfg(cfg)
        elif choice == "AUTO_OPEN":
            cfg["auto_open_folder"] = not cfg.get("auto_open_folder", False)
            save_cfg(cfg)
            state = "enabled" if cfg["auto_open_folder"] else "disabled"
            console.print(f"[dim]Auto-open folder {state}.[/]")
        elif choice == "BETA":
            cfg["include_beta"] = not cfg.get("include_beta", False)
            save_cfg(cfg)
            state = "enabled" if cfg["include_beta"] else "disabled"
            console.print(
                f"[dim]Beta firmware search {state}. "
                "Beta builds may be unstable — use at your own risk.[/]"
            )
        elif choice == "HISTORY":
            if hist_count == 0:
                console.print("[dim]No downloads recorded yet.[/]")
                console.input("[dim]Press Enter to continue…[/]")
                continue
            # Show last 10 entries
            section(console, "Download History", f"Showing last {min(hist_count, 10)} of {hist_count}")
            for e in cfg.get("history", [])[:10]:
                console.print(
                    f"  [cyan]{e.get('downloaded_at','?')}[/]  "
                    f"[bold]{e.get('model','?')}[/]  "
                    f"{e.get('version','?')}  "
                    f"[dim]{e.get('file','?')}[/]"
                )
            console.print()
            if Confirm.ask(f"Clear all {hist_count} history entries?", default=False):
                cfg["history"] = []
                save_cfg(cfg)
                console.print("[dim]History cleared.[/]")
            else:
                console.input("[dim]Press Enter to continue…[/]")
        elif choice == "OPEN_OUT":
            _open_folder(out_dir)
        elif choice == "OPEN_CFG":
            _open_folder(config_path().parent)

# ────────────────────────── Main menu ──────────────────────────
def main_menu(out_dir: Path) -> None:
    _start_update_check()   # fire-and-forget; result readable via _poll_update()
    cfg = load_cfg()
    while True:
        upd = _poll_update()
        if upd:
            ver, url = upd
            console.print(Panel(
                f"[bold green]New Version Available: v{ver}[/]\n[link={url}]Click here to download[/]",
                border_style="green", expand=False), justify="center")

        default_name = cfg.get("last_profile") or "(none)"
        
        items = [
            ("Quick Search [dim](use default profile)[/]", "QUICK"),
            ("Deep Search [dim](slow, aggressive probing)[/]", "DEEP"),
            ("Profiles [dim](create/edit/select)[/]", "PROFILES"),
            ("Ad-hoc Search [dim](don't save)[/]", "ADHOC"),
            ("Manual URL Download", "MANUAL"),
            ("Settings / Info", "SETTINGS"),
            ("Advanced / Add-ons", "ADDONS"),
            ("Exit", "EXIT")
        ]
        
        menu = Menu(console, items, 
                    title="ATOTO Firmware Downloader",
                    subtitle=f"Default profile: {default_name}\nConfig: {config_path()}")
        
        ans = menu.show()

        _beta = cfg.get("include_beta", False)
        _verb = cfg.get("verbose", False)

        if ans == "EXIT" or ans is None:
            clear_screen(console)
            return

        elif ans == "QUICK":
            name = cfg.get("last_profile", "")
            if name and name in cfg["profiles"]:
                run_search_download_flow(cfg["profiles"][name], out_dir, _verb, include_beta=_beta)
            else:
                console.print("[yellow]No default profile set. Opening Profiles…[/]")
                p = profile_menu(cfg)
                if p:
                    run_search_download_flow(p, out_dir, _verb, include_beta=_beta)

        elif ans == "PROFILES":
            p = profile_menu(cfg)
            if p and Confirm.ask("Run Quick Search with this profile now?", default=True):
                run_search_download_flow(p, out_dir, _verb, include_beta=_beta)

        elif ans == "DEEP":
            name = cfg.get("last_profile", "")
            p = None
            if name and name in cfg["profiles"]:
                p = cfg["profiles"][name]
            else:
                p = profile_menu(cfg)
            if p:
                run_search_download_flow(p, out_dir, _verb, deep_scan=True, include_beta=_beta)

        elif ans == "ADHOC":
            p = prompt_adhoc_params()
            if p:
                run_search_download_flow(p, out_dir, _verb,
                                         deep_scan=p.pop("_deep", False), include_beta=_beta)

        elif ans == "MANUAL":
            manual_url_flow(out_dir / "manual")

        elif ans == "SETTINGS":
            _settings_menu(cfg, out_dir)
            
        elif ans == "ADDONS":
            addons_menu()

# ────────────────────────── CLI entry (optional direct run) ──────────────────────────
def parse_args():
    import argparse
    ap = argparse.ArgumentParser(description="ATOTO firmware downloader (menu + profiles)")
    ap.add_argument("--out", default="ATOTO_Firmware", help="Output directory")
    ap.add_argument("--model", help="Search for specific model (bypass menu)")
    ap.add_argument("--res", default="1280x720", help="Resolution for search (default 1280x720)")
    ap.add_argument("--deep", action="store_true", help="Enable Deep Search")
    ap.add_argument("--manual", help="Direct URL download")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging")
    return ap.parse_args()

def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # CLI mode
    if args.manual:
        manual_url_flow(out_dir / "manual")
        return
        
    if args.model:
        # Create ad-hoc profile from args
        p = {
            "name": "CLI",
            "model": args.model,
            "res": args.res,
            "mcu": "",
            "variants": "ANY",
            "prefer_universal": True
        }
        run_search_download_flow(p, out_dir, args.verbose, deep_scan=args.deep)
        return

    main_menu(out_dir)
