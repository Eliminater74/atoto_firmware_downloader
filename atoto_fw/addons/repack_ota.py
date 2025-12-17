#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atoto_fw.addons.repack_ota

Add-on: Repack raw .img files into Android OTA formats (.new.dat.br + .transfer.list).
"""
from __future__ import annotations
import os
import math
import struct
from pathlib import Path

try:
    import brotli
except ImportError:
    brotli = None

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from ..tui import Menu, FolderPicker, section, safe_filename
from . import register

VERSION = 4
BLOCK_SIZE = 4096

def is_sparse_image(filepath: Path) -> bool:
    """Check for Android Sparse Image magic header (0xED26FF3A)."""
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            return magic == b'\x3a\xff\x26\xed'
    except Exception:
        return False

def write_transfer_list(path: Path, count: int):
    """Write a v4 transfer.list for a full new image (type 'new')."""
    # Header:
    # 4 (version)
    # <count> (total blocks)
    # 0 (stashed lines - unused in new)
    # 0 (max stashed blocks - unused in new)
    
    # Command:
    # new 2,0,<count>
    
    with open(path, 'w', newline='\n') as f:
        f.write(f"{VERSION}\n")
        f.write(f"{count}\n")
        f.write("0\n")
        f.write("0\n")
        f.write(f"new 2,0,{count}\n")

def compress_file(console: Console, src: Path, dst: Path):
    """Compress src to dst using Brotli with progress bar."""
    if not brotli:
        console.print("[red]Error:[/] Brotli module not installed. Cannot compress.")
        return False

    total_size = src.stat().st_size
    
    # Brotli one-shot is easiest for now, but no progress for the compression itself easily 
    # unless we use a chunked compressor. 
    # Standard brotli.compress is bytes->bytes.
    # brotli.Compressor allows streaming.
    
    console.print(f"  - Reading [bold]{src.name}[/] ({total_size/1024/1024:.1f} MB)...")
    with open(src, 'rb') as f:
        data = f.read()

    console.print(f"  - Compressing to [bold]{dst.name}[/]...")
    # There is no easy progress callback for brotli.compress. 
    # We'll just show a spinner.
    try:
        compressed = brotli.compress(data, quality=6) # 6 is default, 11 is max (slow)
        with open(dst, 'wb') as f:
            f.write(compressed)
        return True
    except Exception as e:
        console.print(f"[red]Compression failed:[/] {e}")
        return False

def repack_image(console: Console, target_img: Path) -> Optional[Path]:
    """Repack a single image. Returns path to temp .dat file if successful, else None."""
    # Check sparse
    if is_sparse_image(target_img):
        console.print(f"[red]Error:[/] [bold]{target_img.name}[/] is a Sparse Image. Repacking requires RAW.")
        return None
            
    # Calculate info
    size = target_img.stat().st_size
    blocks = math.ceil(size / BLOCK_SIZE)
    
    base_name = target_img.stem
    root = target_img.parent
    out_transfer = root / f"{base_name}.transfer.list"
    out_patch = root / f"{base_name}.patch.dat"
    out_new_dat = root / f"{base_name}.new.dat"
    out_br = root / f"{base_name}.new.dat.br"
    
    console.print(f"\nProcessing [bold cyan]{base_name}[/] ...")
    
    # 1. Generate transfer.list
    console.print(f"  - Generating [bold]{out_transfer.name}[/] (blocks={blocks})...")
    write_transfer_list(out_transfer, blocks)
    
    # 2. Generate patch.dat
    with open(out_patch, 'wb') as f:
        f.write(b"NEWPATCH")

    # 3. Create .new.dat (Padded)
    console.print(f"  - Creating [bold]{out_new_dat.name}[/] (padded)...")
    pad_len = (blocks * BLOCK_SIZE) - size
    
    with open(target_img, 'rb') as fin, open(out_new_dat, 'wb') as fout:
        while True:
            chunk = fin.read(1024*1024)
            if not chunk: break
            fout.write(chunk)
        if pad_len > 0:
            fout.write(b'\x00' * pad_len)
            
    # 4. Compress
    if compress_file(console, out_new_dat, out_br):
        console.print(f"  - [green]Success![/] Created {out_br.name}")
        return out_new_dat
    else:
        # Failed, but maybe kept .dat
        return None

def _addon_repack(console: Console, **kwargs):
    section(console, "Repack Firmware Image", "Convert .img -> .new.dat.br + .transfer.list")
    
    if not brotli:
        console.print("[red]Warning: 'brotli' module is missing. You can only generate .dat and .list, not .br.[/]")
        if not Confirm.ask("Continue anyway?", default=False):
            return

    # 1. Select Folder
    console.print("[dim]Select the folder containing your .img files.[/]")
    fp = FolderPicker(console, start_path=".")
    root_str = fp.show()
    if not root_str:
        return
    root = Path(root_str)
    
    # Scan for .img
    imgs = sorted([p for p in root.glob("*.img") if not p.name.endswith("_raw.img")])
    if not imgs:
        console.print("[yellow]No .img files found in folder.[/]")
        Confirm.ask("Back", default=True)
        return

    # Menu
    items = []
    for p in imgs:
        sz = p.stat().st_size / (1024*1024)
        name_lower = p.name.lower()
        note = ""
        if "boot.img" in name_lower or "dtbo.img" in name_lower:
            note = " [yellow](Warning: usually stays as .img)[/]"
        
        items.append((f"{p.name} [dim]({sz:.1f} MB)[/]{note}", p))
    
    menu = Menu(console, items, title="Select Images to Repack (Space to toggle)")
    selected_imgs: List[Path] = menu.show_multiselect()
    
    if not selected_imgs:
        return

    # Batch Process
    temp_dats: List[Path] = []
    
    console.line()
    console.print(f"Selected {len(selected_imgs)} files.")
    
    for img in selected_imgs:
        res = repack_image(console, img)
        if res:
            temp_dats.append(res)
            
    # Cleanup
    if temp_dats:
        console.line()
        if Confirm.ask(f"Process complete. Delete {len(temp_dats)} intermediate .dat files?", default=True):
            for p in temp_dats:
                try:
                    os.remove(p)
                    console.print(f"  - Deleted {p.name}")
                except Exception as e:
                    console.print(f"  - Failed to delete {p.name}: {e}")
            
    Confirm.ask("Done. Press Enter to return.", default=True)

# Register
register("Repack Firmware Image (.img → .dat.br)", _addon_repack)
