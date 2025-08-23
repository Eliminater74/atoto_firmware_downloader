#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firmware Tools (step-by-step)

Step 1: Extract top-level firmware ZIP(s) into folders
Step 2: Extract nested MCU ZIP(s) (e.g., 6315_*.zip) found recursively
Step 3: Run OTA extractor: .new.dat.br -> .new.dat -> .img  (and optional *_raw.img)

This module accepts an optional 'console' kwarg so it works with the UI's
add-ons launcher which calls funcs as: func(console=console).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

# Add-on registry
from . import register

# Optional import: OTA extractor (we’ll show a friendly message if missing)
try:
    from .ota_extract import run_ota_extract
except Exception:  # pragma: no cover
    run_ota_extract = None  # type: ignore


# ───────────────────────── helpers ─────────────────────────

def _sec(console: Console, title: str, subtitle: str = "") -> None:
    msg = f"[bold]{title}[/]"
    if subtitle:
        msg += f"\n[dim]{subtitle}[/]"
    console.print(Panel.fit(msg, border_style="magenta"))

def _list_zip_files(root: Path, recursive: bool) -> List[Path]:
    if recursive:
        return [p for p in root.rglob("*.zip") if p.is_file()]
    else:
        return [p for p in root.glob("*.zip") if p.is_file()]

def _extract_zip(console: Console, zpath: Path, dest: Optional[Path] = None) -> Path:
    """Extract zpath to dest (defaults to sibling folder named after stem)."""
    dest = dest or (zpath.parent / zpath.stem)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath, "r") as zf:
        zf.extractall(dest)
    console.print(f"[green]✓[/] Extracted: [bold]{zpath.name}[/] → {dest}")
    return dest

def _filter_mcu_zip_candidates(paths: Iterable[Path]) -> List[Path]:
    """
    Heuristics for 'MCU' / inner payload zips.
    We keep files whose name looks like '6315_*.zip' OR live under a plausible extracted folder.
    """
    out: List[Path] = []
    pat_6315 = re.compile(r"^6315[_-].*\.zip$", re.IGNORECASE)
    for p in paths:
        name = p.name
        if pat_6315.match(name):
            out.append(p)
            continue
        # also accept generic inner payload zips that are not the outer firmware names
        if p.parent.name not in ("manual", "docs") and "MCU" in name.upper():
            out.append(p)
    # de-dup while preserving order
    seen = set()
    uniq: List[Path] = []
    for p in out:
        if p not in seen:
            uniq.append(p); seen.add(p)
    return uniq

def _choose_dir(console: Console, prompt: str, default: Path) -> Path:
    s = Prompt.ask(prompt, default=str(default)).strip()
    path = Path(s).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


# ───────────────────────── steps ─────────────────────────

def _step1_extract_top(console: Console, base: Path) -> None:
    _sec(console, "Step 1 — Extract top-level firmware ZIP(s)")
    zips = _list_zip_files(base, recursive=False)
    if not zips:
        console.print("[yellow]No *.zip files found in this folder.[/]")
        return

    tbl = Table(show_lines=False, header_style="bold magenta", box=box.SIMPLE_HEAVY)
    tbl.add_column("#"); tbl.add_column("ZIP")
    for i, z in enumerate(zips, 1):
        tbl.add_row(str(i), z.name)
    console.print(tbl)

    if not Confirm.ask("Extract all of these here?", default=True):
        return

    for z in zips:
        try:
            _extract_zip(console, z)
        except Exception as ex:
            console.print(f"[red]![/] Failed to extract {z.name}: {ex}")

def _step2_extract_nested(console: Console, base: Path) -> None:
    _sec(console, "Step 2 — Extract nested MCU ZIP(s)", "Search is recursive from the chosen folder.")
    zips = _list_zip_files(base, recursive=True)
    zips = _filter_mcu_zip_candidates(zips)
    if not zips:
        console.print("[yellow]No nested MCU *.zip files found.[/]")
        return

    tbl = Table(show_lines=False, header_style="bold magenta", box=box.SIMPLE_HEAVY)
    tbl.add_column("#"); tbl.add_column("Path (relative)")
    for i, z in enumerate(zips, 1):
        try:
            rel = z.relative_to(base)
        except Exception:
            rel = z
        tbl.add_row(str(i), str(rel))
    console.print(tbl)

    if not Confirm.ask("Extract ALL nested zips?", default=True):
        return

    for z in zips:
        try:
            _extract_zip(console, z)
        except Exception as ex:
            console.print(f"[red]![/] Failed to extract {z}: {ex}")

def _step3_run_ota_extract(console: Console, base: Path) -> None:
    _sec(console, "Step 3 — OTA extractor (.new.dat.br → .dat → .img)")
    if run_ota_extract is None:
        console.print(
            "[red]Brotli extractor not available.[/]\n"
            "Install one of: [bold]brotli[/] or [bold]brotlicffi[/] and make sure "
            "your add-on module [bold]ota_extract[/] is present."
        )
        return

    overwrite = Confirm.ask("Overwrite existing .dat/.img if present?", default=False)
    raw = Confirm.ask("Also try creating *_raw.img via simg2img (if available)?", default=False)

    def progress(msg: str):
        console.print(f"[dim]{msg}[/]")

    stats = run_ota_extract(base, overwrite=overwrite, raw=raw, progress=progress)
    console.print(
        f"[green]Done.[/] Decompressed={stats.get('decompressed',0)}  "
        f"Converted={stats.get('converted',0)}  RawOK={stats.get('raw_ok',0)}  "
        f"Errors={stats.get('errors',0)}"
    )


# ───────────────────────── menu ─────────────────────────

def run_workflow_menu(console: Optional[Console] = None, **_: object) -> None:
    """
    Entry point used by the UI's add-ons launcher.
    Accepts 'console' kwarg (ignored if None; we create our own Console in that case).
    """
    c = console or Console()
    c.clear()
    _sec(c, "Firmware Tools (step-by-step)")

    base = _choose_dir(c, "Folder to work in", Path(".").resolve())

    while True:
        c.print(
            "[1] Extract top-level firmware ZIP(s)\n"
            "[2] Extract nested MCU ZIP(s)\n"
            "[3] OTA extractor (.new.dat.br → .img)\n"
            "[0] Back"
        )
        ans = Prompt.ask("Select", default="0").strip()

        if ans == "0":
            return
        elif ans == "1":
            _step1_extract_top(c, base)
        elif ans == "2":
            _step2_extract_nested(c, base)
        elif ans == "3":
            _step3_run_ota_extract(c, base)
        else:
            c.print("[yellow]Invalid choice.[/]")


# Register with the add-on registry so the UI can list it.
register("Firmware Tools (step-by-step)", run_workflow_menu)
