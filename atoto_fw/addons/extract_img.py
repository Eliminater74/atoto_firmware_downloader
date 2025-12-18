#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atoto_fw.addons.extract_img

Add-on: Extract .img contents using 7-Zip (Windows).
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from ..tui import Menu, FolderPicker, section, safe_filename
from . import register

# Common Windows paths for 7-Zip
SEVEN_ZIP_PATHS = [
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
]

def find_7zip() -> str | None:
    """Find 7z.exe in PATH or common locations."""
    # 1. Check local bin (Standalone)
    local_7z = Path("bin") / "7za.exe"
    if local_7z.exists():
        return str(local_7z.resolve())

    # 2. Check PATH
    path_exe = shutil.which("7z")
    if path_exe:
        return path_exe
    
    # 3. Check explicitly
    for p in SEVEN_ZIP_PATHS:
        if os.path.exists(p):
            return p
            
    return None

def _addon_extract_img(console: Console, **kwargs):
    section(console, "Extract Image Content (Ext4)", "Unpack .img files using 7-Zip")
    
    # 1. Check for 7-Zip
    exe_7z = find_7zip()
    if not exe_7z:
        console.print("[red]Error:[/] [bold]7z.exe[/] not found.")
        console.print("Please install 7-Zip or ensure it is in your PATH.")
        if not Confirm.ask("Back", default=True):
            return
        return
        
    console.print(f"[dim]Using 7-Zip: {exe_7z}[/]")

    # 2. Select Folder
    console.print("\n[dim]Select the folder containing your .img files.[/]")
    fp = FolderPicker(console, start_path=".")
    root_str = fp.show()
    if not root_str:
        return
    root = Path(root_str)
    
    # Scan for .img
    imgs = sorted([p for p in root.glob("*.img")])
    if not imgs:
        console.print("[yellow]No .img files found in folder.[/]")
        Confirm.ask("Back", default=True)
        return

    # Menu
    items = []
    for p in imgs:
        sz = p.stat().st_size / (1024*1024)
        items.append((f"{p.name} [dim]({sz:.1f} MB)[/]", p))
    
    menu = Menu(console, items, title="Select Image to Extract")
    # For now, single select to keep it simple, but we could do multi
    target_img: Path = menu.show()
    
    if not target_img:
        return

    # 3. Extract
    out_dir = root / f"{target_img.stem}_extracted"
    
    console.line()
    console.print(f"Target: [bold]{target_img.name}[/]")
    console.print(f"Output: [bold]{out_dir.name}[/]")
    console.print("[yellow]Note: Extracted files on Windows lose Linux permissions.[/]")
    console.print("[yellow]      Repacking them back to .img might result in a non-bootable system.[/]")
    
    if Confirm.ask("Proceed with extraction?", default=True):
        if out_dir.exists():
            console.print(f"[yellow]Output folder exists.[/]")
            if not Confirm.ask("Overwrite (7-Zip will merge/overwrite)?", default=True):
                return
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            
        console.print("Extracting...")
        # 7z x -y -o<out> <in>
        cmd = [exe_7z, "x", "-y", f"-o{str(out_dir)}", str(target_img)]
        
        try:
            # We assume 7z outputs to stdout, which we can capture or let flow
            # Let's let it flow but indented? Or capture and show spinner?
            # 7z output is verbose. Let's redirect to pipe and update spinner.
            
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
                 while True:
                    line = proc.stdout.readline()
                    if not line: break
                    # print(line.strip()) # Debug
            
            if proc.returncode == 0:
                console.print(f"[green]Success![/] Extracted to: {out_dir}")
                # Open folder?
                if Confirm.ask("Open extracted folder?", default=True):
                    os.startfile(out_dir)
            else:
                console.print(f"[red]Extraction failed with code {proc.returncode}[/]")
                
        except Exception as e:
            console.print(f"[red]Error running 7-Zip:[/] {e}")

    Confirm.ask("Done. Press Enter to return.", default=True)

# Register
register("Extract Image Content (View Only)", _addon_extract_img)
