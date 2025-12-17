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

def _addon_repack(console: Console, **kwargs):
    section(console, "Repack Firmware Image", "Convert .img -> .new.dat.br + .transfer.list")
    
    if not brotli:
        console.print("[red]Warning: 'brotli' module is missing. You can only generate .dat and .list, not .br.[/]")
        if not Confirm.ask("Continue anyway?", default=False):
            return

    # 1. Select Folder or File
    # Using FolderPicker to pick dir, then Menu to pick .img?
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
        items.append((f"{p.name} [dim]({sz:.1f} MB)[/]", p))
    items.append(("Cancel", None))
    
    menu = Menu(console, items, title="Select Image to Repack")
    target_img: Path = menu.show()
    if not target_img:
        return

    # Check sparse
    if is_sparse_image(target_img):
        console.print("[red]Error:[/] This appears to be an Android Sparse Image.[/]")
        console.print("Repacking requires a [bold]RAW[/] image (unsparsed).")
        console.print("If you extracted this with our tool, use the converted .img, not a sparse one.")
        if not Confirm.ask("Try to proceed anyway (result might be invalid)?", default=False):
            return
            
    # Calculate info
    size = target_img.stat().st_size
    blocks = math.ceil(size / BLOCK_SIZE)
    # Used size is blocks * 4096. If file is smaller, we might need to pad .dat?
    # Actually, Android updater writes blocks. If we say "new 2,0,100", it expects 100*4096 bytes in .new.dat.
    # So we MUST pad the .new.dat to align to 4KB.
    
    base_name = target_img.stem # e.g. "product"
    out_transfer = root / f"{base_name}.transfer.list"
    out_patch = root / f"{base_name}.patch.dat"
    out_new_dat = root / f"{base_name}.new.dat"
    out_br = root / f"{base_name}.new.dat.br"
    
    console.line()
    if Confirm.ask(f"Ready to repack [bold]{base_name}[/]?\nOutput: {out_br.name}, {out_transfer.name}", default=True):
        
        # 1. Generate transfer.list
        console.print(f"Generating [bold]{out_transfer.name}[/] (blocks={blocks})...")
        write_transfer_list(out_transfer, blocks)
        
        # 2. Generate patch.dat (empty)
        console.print(f"Creating empty [bold]{out_patch.name}[/]...")
        out_patch.write_bytes(b"NEWPATCH") # Actually header is usually "NEWPATCH" for some versions, or just empty?
        # Standard AOSP: .patch.dat usually has "NEWPATCH" magic if using imgdiff, but for full OTA 'new' command, it might be ignored.
        # However, checking `ota_from_target_files`, `patch.dat` is created.
        # For "new" commands only, patch.dat is unused effectively. 
        # But commonly it contains `block_img_diff` header if strictly compliant.
        # Let's write "NEWPATCH" as a safe bet for v3/v4 listeners or just empty.
        # Actually, if we use "new", there are no patch commands. So empty might be fine.
        # Safest: "NEWPATCH" encoded bytes.
        with open(out_patch, 'wb') as f:
            f.write(b"NEWPATCH")

        # 3. Create .new.dat (Padded)
        console.print(f"Creating [bold]{out_new_dat.name}[/] (padded)...")
        pad_len = (blocks * BLOCK_SIZE) - size
        
        # Copy + Pad
        with open(target_img, 'rb') as fin, open(out_new_dat, 'wb') as fout:
            # We can stream copy
            while True:
                chunk = fin.read(1024*1024)
                if not chunk: break
                fout.write(chunk)
            if pad_len > 0:
                fout.write(b'\x00' * pad_len)
                
        # 4. Compress
        console.print("Compressing...")
        if compress_file(console, out_new_dat, out_br):
            console.print("[green]Success![/] Created .br file.")
            # Verify?
            
            # Offer to delete .new.dat (temp)
            if Confirm.ask(f"Delete intermediate [bold]{out_new_dat.name}[/]?", default=True):
                os.remove(out_new_dat)
                console.print("Deleted intermediate .dat.")
        else:
            console.print("[red]Compression failed[/]. .new.dat kept.")
            
        Confirm.ask("Done. Press Enter to return.", default=True)

# Register
register("Repack Firmware Image (.img → .dat.br)", _addon_repack)
