#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atoto_fw.addons.extract_zip

Add-on: Extract downloaded firmware Zip files.
"""
from __future__ import annotations
import os
import zipfile
from pathlib import Path
from typing import Optional, List, Any

def scan_for_zips(root: Path) -> List[Path]:
    zips = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith(".zip"):
                zips.append(Path(dirpath) / f)
    return sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True)

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TimeRemainingColumn
    from ..tui import Menu, FolderPicker, section
    from . import register

    def _addon_unzip(console: Console, **kwargs):
        section(console, "Unzip Firmware Package")
        
        # 1. Select Source
        console.print("[dim]Select the folder that contains your firmware zip files.[/]")
        fp = FolderPicker(console, start_path="ATOTO_Firmware")
        root_str = fp.show()
        if not root_str:
            return
        root = Path(root_str)
        
        zips = scan_for_zips(root)
        if not zips:
            console.print("[yellow]No .zip files found in scan path.[/]")
            Confirm.ask("Back", default=True)
            return

        # Menu to pick zip
        items = []
        for z in zips:
            # label: filename (size)
            sz = z.stat().st_size / (1024*1024)
            items.append((f"{z.name} [dim]({sz:.1f} MB)[/]", z))
        
        items.append(("Cancel", None))
        
        menu = Menu(console, items, title="Select Firmware Zip", subtitle=f"Found {len(zips)} files in {root}")
        target_zip: Optional[Path] = menu.show()
        
        if not target_zip:
            return

        # 2. Select Dest
        default_out = target_zip.with_suffix("") # remove .zip
        out_str = Prompt.ask("Extract to", default=str(default_out))
        out_dir = Path(out_str)

        if out_dir.exists():
            if not Confirm.ask(f"Output folder exists: {out_dir}\nOverwrite?", default=False):
                return
        
        # 3. Extract
        console.print(f"\n[bold]Extracting[/] {target_zip.name} ...")
        try:
            with zipfile.ZipFile(target_zip, 'r') as zf:
                infos = zf.infolist()
                total_size = sum(i.file_size for i in infos)
                
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    TimeRemainingColumn(),
                    console=console
                ) as progress:
                    # One task for total bytes
                    task = progress.add_task("Unzipping", total=total_size)
                    
                    # ZipFile doesn't give callback, so we iterate files.
                    # Simplest is 'extractall' but no progress. 
                    # We'll extract one by one for progress bar.
                    extracted_size = 0
                    for info in infos:
                        zf.extract(info, path=out_dir)
                        extracted_size += info.file_size
                        progress.update(task, completed=extracted_size)

            console.print(f"[green]Success![/] Extracted to: [bold]{out_dir}[/]")
        except Exception as e:
            console.print(f"[red]Extraction failed:[/r] {e}")
            Confirm.ask("Back", default=True)
            return

        # 4. Chain to OTA Extractor?
        # Check if we see payload.bin or .new.dat.br inside
        has_ota_files = False
        for root_scan, _, files in os.walk(out_dir):
            for f in files:
                if f.endswith(".new.dat.br") or f.endswith(".transfer.list"):
                    has_ota_files = True
                    break
            if has_ota_files: break
        
        # Also check if there's an inner 'update.zip' we should mention
        inner_zip = out_dir / "update.zip"
        if inner_zip.exists():
             console.print("[yellow]Note:[/r] Found an inner [bold]update.zip[/]. You might need to unzip that one too.")

        if has_ota_files:
            if Confirm.ask("\nFound OTA files (dat.br/transfer.list). Run [bold]OTA Extractor[/] now?", default=True):
                 # Try to import and run the other addon
                 try:
                     from .extract_ota import _ui_ota_extract
                     console.print(f"[dim]Tip: Enter '{out_dir}' as the root folder in the next step.[/]")
                     _ui_ota_extract(console)
                 except ImportError:
                     console.print("[red]OTA Extractor addon not found.[/]")
        
        Confirm.ask("Done. Press Enter to return.", default=True)

    # Register
    register("Unzip Firmware Package (.zip)", _addon_unzip)

except ImportError as e:
    print(f"DEBUG: extract_zip import failed: {e}")
    pass
