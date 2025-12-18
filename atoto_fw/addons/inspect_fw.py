#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atoto_fw.addons.inspect_fw

Add-on: Scans a folder and explains the purpose of each firmware file found.
Helps users distinguish between modifiable images and raw hardware binaries.
"""
from __future__ import annotations
import os
from pathlib import Path
from fnmatch import fnmatch
from typing import List, Dict, Tuple

from rich.console import Console
from rich.table import Table
from rich import box
from rich.prompt import Confirm
from ..tui import Menu, FolderPicker, section, safe_filename
from . import register

# Knowledge Base: Patterns -> (Type, Description, Color)
# Order matters: first match wins.
KNOWLEDGE_BASE = [
    # Boot / Kernel
    ("boot.img", "Kernel (Boot)", "Android Kernel & Ramdisk. Rooting happens here.", "green"),
    ("recovery.img", "Recovery", "Recovery OS. Flashing zips/factory reset.", "green"),
    ("dtbo.img", "DTBO", "Device Tree Overlay. Hardware config.", "yellow"),
    ("vbmeta.img", "VBMeta", "Verified Boot Metadata. Signing keys.", "red"),

    # Core Android Partitions (Ext4/EroFS)
    ("system.img", "System", "Android OS core (Framework, Apps).", "cyan"),
    ("vendor.img", "Vendor", "Hardware drivers & HALs.", "cyan"),
    ("product.img", "Product", "Google apps & device-specific customizations.", "cyan"),
    ("odm.img", "ODM", "Original Design Manufacturer customizations.", "cyan"),
    
    # OTA Formats (Compressed)
    ("*.new.dat.br", "Compressed Partition", "Brotli-compressed filesystem data. Needs repacking.", "blue"),
    ("*.new.dat", "Raw Data", "Uncompressed filesystem data (sparse).", "blue"),
    ("*.transfer.list", "OTA Map", "Block map for the .new.dat file.", "dim"),
    ("*.patch.dat", "OTA Patch", "Binary patch data (usually empty for full OTAs).", "dim"),

    # Raw Binaries (Hardware/Firmware) - DANGEROUS to touch
    ("u-boot*.bin", "Bootloader", "Primary Bootloader. Initializes hardware. **DO NOT MODIFY**.", "bold red"),
    ("preloader*.bin", "Preloader", "First-stage SoC Bootloader. **DO NOT MODIFY**.", "bold red"),
    ("logo.bin", "Boot Logo", "Splash screen image (Raw bitmap container).", "magenta"),
    ("tos.bin", "TrustZone", "Secure OS (TEE). Handles encryption/DRM.", "red"),
    ("tee.bin", "TrustZone", "Secure OS (TEE).", "red"),
    ("*modem.bin", "Modem/Radio", "Cellular/WiFi/BT/GPS Firmware.", "red"),
    ("*dsp.bin", "DSP", "Digital Signal Processor Firmware (Audio/Sensors).", "red"),
    ("nvram.bin", "NVRAM", "Calibration data (IMEI/MAC).", "red"),
    ("secro.bin", "SECRO", "Security Read-Only data.", "red"),
    ("lk.bin", "Little Kernel", "Alternative bootloader stage.", "red"),

    # Metadata
    ("scatter.txt", "Scatter File", "MTK Partition Map for Flash Tool.", "yellow"),
    ("dynamic_partitions_op_list", "Partition List", "List of dynamic partitions to resize/extract.", "yellow"),
    ("compatibility.zip", "Compatibility", "Checks device eligibility before flashing.", "dim"),

    # Archives
    ("*.zip", "Archive", "Compressed package.", "white"),
    ("*.bin", "Unknown Binary", "Likely raw firmware or payload.", "dim"),
    ("*.img", "Unknown Image", "Likely a filesystem image.", "white"),
]

def format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def identify_file(filename: str) -> Tuple[str, str, str]:
    """Return (Type, Description, Color) for a filename."""
    name_lower = filename.lower()
    for pattern, ftype, desc, color in KNOWLEDGE_BASE:
        if fnmatch(name_lower, pattern):
            return ftype, desc, color
    return "File", "Unknown file type.", "white"

def _addon_inspect(console: Console, **kwargs):
    section(console, "Explain Firmware Files", "Analyze folder contents and identify firmware components")

    # 1. Select Folder
    console.print("[dim]Select the folder to scan.[/]")
    fp = FolderPicker(console, start_path=".")
    root_str = fp.show()
    if not root_str:
        return
    root = Path(root_str)
    
    # 2. Scan
    files = sorted([p for p in root.iterdir() if p.is_file()])
    if not files:
        console.print("[yellow]Folder is empty.[/]")
        Confirm.ask("Back", default=True)
        return

    # 3. Render Table
    table = Table(title=f"Contents of {root.name}", box=box.SIMPLE_HEAVY, header_style="bold magenta")
    table.add_column("Filename", style="bold")
    table.add_column("Size", justify="right")
    table.add_column("Type")
    table.add_column("Description")

    # Group by broad category for nicer sorting? Nah, name sort is fine.
    
    for p in files:
        ftype, desc, color = identify_file(p.name)
        sz = format_size(p.stat().st_size)
        
        table.add_row(
            p.name,
            sz,
            f"[{color}]{ftype}[/]",
            desc
        )

    console.print(table)
    console.print("\n[dim]Green/Blue = Likely modifiable (carefully). Red = Dangerous/Raw hardware code.[/]")
    
    Confirm.ask("Done. Press Enter to return.", default=True)

# Register
register("Explain Firmware Files (Inspector)", _addon_inspect)
