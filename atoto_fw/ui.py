#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI layer for ATOTO Firmware Downloader

- Profiles (persisted): model / MCU / resolution / variant prefs / prefer-universal
- Rich menu + results table
- Live status while probing API/JSON/mirrors (no more “stuck at starting”)
- Resume download with progress + optional checksum verify
"""

from __future__ import annotations
import re
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
)
from .core.utils import url_leaf_name  # leaf filename helper

console = Console()

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
    if subtitle:
        msg += f"\n[dim]{subtitle}[/]"
    console.print(Panel.fit(msg, border_style="magenta"))

def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]+', "_", (name or "")).strip() or "file"

# ────────────────────────── Profile UI ──────────────────────────
def prompt_profile(existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    console.print(Panel.fit("Create / Edit Profile", border_style="cyan"))
    prof = dict(existing or {})
    prof["name"]  = Prompt.ask("Profile name", default=prof.get("name", "My S8"))
    prof["model"] = Prompt.ask("Model / Device name", default=prof.get("model", "S8EG2A74MSB")).upper().strip()
    prof["mcu"]   = Prompt.ask("MCU version (blank if unknown)", default=prof.get("mcu", "")).strip()
    prof["res"]   = Prompt.ask("Display resolution", default=prof.get("res", "1280x720")).strip()

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

def profile_menu(cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    while True:
        section("Profiles", f"Config file: {config_path()}")
        tbl = Table(show_lines=False, header_style="bold magenta", box=box.SIMPLE_HEAVY)
        tbl.add_column("#"); tbl.add_column("Name"); tbl.add_column("Model")
        tbl.add_column("MCU"); tbl.add_column("Res"); tbl.add_column("Variants")
        tbl.add_column("Universal?")
        names = sorted(cfg["profiles"].keys())
        for i, name in enumerate(names, 1):
            p = cfg["profiles"][name]
            tbl.add_row(
                str(i), name, p.get("model", ""), p.get("mcu", ""), p.get("res", ""),
                p.get("variants", "ANY"), "Yes" if p.get("prefer_universal", True) else "No"
            )
        console.print(tbl)
        console.print("[dim]A=Add  E=Edit  D=Delete  S=Select default  Q=Back[/]")
        ans = Prompt.ask("Action", default="S").strip().upper()

        if ans == "Q":
            return None
        if ans == "A":
            p = prompt_profile({})
            cfg["profiles"][p["name"]] = p
            save_cfg(cfg)
        elif ans == "E" and names:
            idx = Prompt.ask("Edit #", default="1").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(names):
                key = names[int(idx) - 1]
                p = prompt_profile(cfg["profiles"][key])
                if p["name"] != key:
                    del cfg["profiles"][key]
                cfg["profiles"][p["name"]] = p
                save_cfg(cfg)
        elif ans == "D" and names:
            idx = Prompt.ask("Delete #", default="1").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(names):
                key = names[int(idx) - 1]
                if Confirm.ask(f"Delete profile '{key}'?", default=False):
                    del cfg["profiles"][key]
                    if cfg.get("last_profile") == key:
                        cfg["last_profile"] = ""
                    save_cfg(cfg)
        elif ans == "S" and names:
            idx = Prompt.ask("Select # as default", default="1").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(names):
                key = names[int(idx) - 1]
                cfg["last_profile"] = key
                save_cfg(cfg)
                return cfg["profiles"][key]

# ────────────────────────── Results table & selection ──────────────────────────
def render_and_pick(
    rows: List[Dict[str, Any]],
    my_res: str,
    prefer_universal: bool,
    want_variants: List[str],
) -> Optional[Dict[str, Any]]:
    # annotate & merge
    tag_rows(rows, my_res)
    grouped = group_by_url(rows)
    if isinstance(grouped, dict):  # robustness if backend returns a dict someday
        grouped = list(grouped.values())

    def row_ok(r: Dict[str, Any]) -> bool:
        if prefer_universal and not r.get("scope", "").startswith("Universal"):
            return False
        if want_variants and r.get("variants") not in ("-", ""):
            row_vars = set(r["variants"].split(","))
            if not (row_vars & set(want_variants)):
                return False
        return True

    filt = [r for r in grouped if row_ok(r)] or grouped

    section(
        "Firmware Results",
        "Universal = not tied to a specific resolution. "
        "Res-specific = package names that explicitly mention 1024×600 or 1280×720."
    )
    console.print(Panel.fit(
        "[bold]Tip[/]: Prefer Universal packages for the same device family; "
        "use Res-specific only when a package explicitly targets your screen.\n"
        f"[dim]Profile Fit: {my_res or '?'} · Variant prefs: "
        f"{', '.join(want_variants) if want_variants else 'ANY'} · "
        f"Scope: {'Universal preferred' if prefer_universal else 'All'}[/]",
        border_style="cyan"
    ))

    table = Table(
        title="Available Packages",
        show_lines=False,
        header_style="bold magenta",
        box=box.SIMPLE_HEAVY
    )
    cols = [
        ("id", "#"), ("source", "Src"), ("title", "Title"), ("version", "Ver"),
        ("date", "Date"), ("size", "Size"), ("res", "Res"), ("scope", "Scope"),
        ("variants", "Variants"), ("fit", "Fit"), ("url", "URL")
    ]
    for _, hdr in cols:
        table.add_column(hdr, overflow="fold")

    for idx, r in enumerate(filt, 1):
        r_view = r.copy()
        r_view["id"] = str(idx)
        r_view["size"] = human_size(r.get("size"))
        table.add_row(*[str(r_view.get(k, "")) for k, _ in cols])

    console.print(table)

    raw = Prompt.ask("Select # (0 to cancel)", default="1" if filt else "0").strip()
    if raw == "0" or not raw.isdigit():
        return None
    i = int(raw)
    if not (1 <= i <= len(filt)):
        return None

    choice = filt[i - 1]
    if choice.get("fit") == "⚠":
        console.print(
            f"[yellow]Heads-up:[/] package looks like [bold]{choice.get('res','?')}[/], "
            f"profile is [bold]{my_res}[/]."
        )
        if not Confirm.ask("Continue anyway?", default=False):
            return None
    return choice

# ────────────────────────── Download ──────────────────────────
def download_with_progress(url: str, out_path: Path, expected_hash: str = "") -> None:
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    resume = tmp.stat().st_size if tmp.exists() else 0
    headers = {"Range": f"bytes={resume}-"} if resume > 0 else {}

    # late import to avoid circulars
    from .core import SESSION

    with SESSION.get(url, stream=True, headers=headers, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", "0"))
        if r.status_code == 206:
            # try to learn the *full* size for progress bar
            try:
                full = SESSION.head(url, timeout=8, allow_redirects=True)
                total = int(full.headers.get("Content-Length", total))
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
            transient=False
        ) as progress:
            task_id = progress.add_task("dl", total=total, completed=downloaded)
            with open(tmp, mode) as f:
                for chunk in r.iter_content(chunk_size=128 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress.update(task_id, completed=downloaded)
        tmp.rename(out_path)

    if expected_hash:
        console.print("Verifying checksum…")
        algo = "sha256" if len(expected_hash) == 64 else ("sha1" if len(expected_hash) == 40 else "md5")
        if algo == "sha256":
            digest = sha256_file(out_path)
        elif algo == "sha1":
            import hashlib
            h = hashlib.sha1()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        else:
            import hashlib
            h = hashlib.md5()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()

        if digest.lower() != expected_hash.lower():
            console.print(f"[red]Checksum mismatch![/] expected {expected_hash}, got {digest}")
        else:
            console.print("[green]Checksum OK[/]")

# ────────────────────────── Search & Download flow ──────────────────────────
def run_search_download_flow(profile: Dict[str, Any], out_base: Path, verbose: bool) -> None:
    model = profile.get("model", "").strip() or Prompt.ask("Model / Device", default="S8EG2A74MSB").strip()
    mcu   = profile.get("mcu", "").strip()
    my_res = profile.get("res", "1280x720").strip()
    variants_pref = [] if profile.get("variants", "ANY") == "ANY" else profile.get("variants", "ANY").split(",")
    prefer_universal = bool(profile.get("prefer_universal", True))

    # searching screen + live spinner
    section(
        "Searching…",
        f"Model {model} • MCU {mcu or 'n/a'} • Res {my_res}\n"
        "[dim]Probing API, JSON and mirrors. This may take several seconds.[/]"
    )

    with Status("[bold]Searching firmware…[/] starting", console=console, spinner="dots") as status:
        def progress_cb(msg: str):
            status.update(f"[bold]Searching firmware…[/] {msg}")
            if verbose:
                console.log(msg)

        rows, hits = try_lookup(model, mcu, progress=progress_cb)

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
        section(
            "No Packages Found",
            "Could not find firmware via API/JSON/mirrors.\n"
            "Try a nearby model name or use Manual URL."
        )
        return

    chosen = render_and_pick(rows, my_res, prefer_universal, variants_pref)
    if not chosen:
        section("Canceled")
        return

    model_for_path = (hits[0] if hits else model)
    out_dir = out_base / safe_filename(model_for_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(f"{model_for_path}_{chosen.get('version','NAv')}_{url_leaf_name(chosen['url'])}")
    out_path = out_dir / filename

    section(
        "Download Ready",
        f"Saving to: {out_path}\nReported size: {human_size(chosen.get('size'))}\n\nPress Ctrl+C to cancel"
    )
    try:
        download_with_progress(chosen["url"], out_path, expected_hash=chosen.get("hash", ""))
        section("Download Complete")
        console.print(f"[green]Done![/] File saved:\n[bold]{out_path}[/]")
    except KeyboardInterrupt:
        section("Interrupted")
        console.print("[yellow]Interrupted by user.[/]")
    except Exception as e:
        section("Download Failed")
        console.print(f"[red]Download failed:[/] {e}")

# ────────────────────────── Manual URL ──────────────────────────
def manual_url_flow(download_dir: Path) -> None:
    section("Manual URL", "Paste a direct firmware URL from ATOTO")
    url = Prompt.ask("Direct URL (or leave blank to abort)", default="").strip()
    if not url:
        section("Canceled")
        return
    download_dir.mkdir(parents=True, exist_ok=True)
    out = download_dir / safe_filename(url_leaf_name(url))
    section("Download Ready", f"Saving to: {out}\n\nPress Ctrl+C to cancel")
    try:
        download_with_progress(url, out)
        section("Download Complete")
        console.print(f"[green]Done![/] File saved:\n[bold]{out}[/]")
    except KeyboardInterrupt:
        section("Interrupted")
        console.print("[yellow]Interrupted by user.[/]")
    except Exception as e:
        section("Download Failed")
        console.print(f"[red]Download failed:[/] {e}")

# ────────────────────────── Main menu ──────────────────────────
def main_menu(out_dir: Path) -> None:
    cfg = load_cfg()
    while True:
        default_name = cfg.get("last_profile") or "(none)"
        section(
            "ATOTO Firmware Downloader",
            f"Default profile: {default_name}\nConfig: {config_path()}"
        )
        console.print(
            "[1] Quick Search (use default profile)\n"
            "[2] Profiles (create/edit/select)\n"
            "[3] Ad-hoc Search (don’t save)\n"
            "[4] Manual URL Download\n"
            "[5] Settings / Info\n"
            "[0] Exit"
        )
        ans = Prompt.ask("Select", default="1").strip()

        if ans == "0":
            clear_screen()
            return

        elif ans == "1":
            name = cfg.get("last_profile", "")
            if name and name in cfg["profiles"]:
                run_search_download_flow(cfg["profiles"][name], out_dir, cfg.get("verbose", False))
            else:
                console.print("[yellow]No default profile set. Opening Profiles…[/]")
                p = profile_menu(cfg)
                if p:
                    run_search_download_flow(p, out_dir, cfg.get("verbose", False))

        elif ans == "2":
            p = profile_menu(cfg)
            if p and Confirm.ask("Run Quick Search with this profile now?", default=True):
                run_search_download_flow(p, out_dir, cfg.get("verbose", False))

        elif ans == "3":
            p = prompt_profile({})
            run_search_download_flow(p, out_dir, cfg.get("verbose", False))

        elif ans == "4":
            manual_url_flow(out_dir / "manual")

        elif ans == "5":
            section("Settings / Info", f"Config: {config_path()}\nOutput: {out_dir}")
            console.print(f"Verbose logs: {'ON' if cfg.get('verbose', False) else 'OFF'}")
            if Confirm.ask("Toggle verbose?", default=False):
                cfg["verbose"] = not cfg.get("verbose", False)
                save_cfg(cfg)
            Confirm.ask("Back", default=True)

# ────────────────────────── CLI entry (optional direct run) ──────────────────────────
def parse_args():
    import argparse
    ap = argparse.ArgumentParser(description="ATOTO firmware downloader (menu + profiles)")
    ap.add_argument("--out", default="ATOTO_Firmware", help="Output directory")
    return ap.parse_args()

def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    main_menu(out_dir)
