#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atoto_fw.addons.ota_extract

Add-on: Extract Android OTA partitions from firmware folders.

Features
--------
1) Decompress:  *.new.dat.br  →  *.new.dat   (Brotli / BrotliCFFI)
2) Convert:     <name>.transfer.list + <name>.new.dat  →  <name>.img
   (supports transfer.list v1–v4; v4 header: version, total, stashed, block_size)
3) Optional:    Try 'simg2img' to produce <name>_raw.img from sparse images.

Public API
----------
run_ota_extract(root, overwrite=False, raw=False, progress=None) -> dict
  Returns stats: {'decompressed': N, 'converted': M, 'raw_ok': R, 'errors': E}

UI hook (auto-registered in Add-ons menu)
-----------------------------------------
Registers a Rich-based action: "Extract OTA (dat.br → dat → img)"
"""

from __future__ import annotations
import argparse
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# --- Brotli import (either package works) ---
try:
    import brotli  # pip install brotli
except ImportError:
    try:
        import brotlicffi as brotli  # pip install brotlicffi
    except ImportError:
        brotli = None

KNOWN_CMDS = {"new","zero","erase","move","stash","free","append","bsdiff","imgdiff"}

# ====================== internals ======================

def _eprint(*a):  # stderr helper
    print(*a, file=sys.stderr)

def _progress_emit(progress: Optional[Callable[[str], None]], msg: str) -> None:
    try:
        if progress:
            progress(msg)
    except Exception:
        pass

# ---------- Brotli ----------
def decompress_brotli_file(src: Path, dst: Path) -> None:
    """One-shot Brotli decompress (works across brotli variants)."""
    if brotli is None:
        raise RuntimeError(
            "Brotli module not found. Install one of:\n"
            "  pip install brotli   (or)\n"
            "  pip install brotlicffi"
        )
    with open(src, "rb") as fin:
        comp = fin.read()

    if hasattr(brotli, "decompress"):
        out = brotli.decompress(comp)
    else:
        dec_cls = getattr(brotli, "Decompressor", None)
        if dec_cls is None:
            raise RuntimeError("No compatible brotli API found")
        dec = dec_cls()
        if hasattr(dec, "process"):
            out = dec.process(comp)
        elif hasattr(dec, "decompress"):
            out = dec.decompress(comp)
        else:
            raise RuntimeError("Unsupported brotli Decompressor interface")

    with open(dst, "wb") as fout:
        fout.write(out)

# ---------- transfer.list parsing ----------
def parse_header(lines: List[str]) -> Tuple[int, int, int, int, List[str]]:
    """Return (version, total_blocks, block_size, first_cmd_idx, cleaned_lines)."""
    L = [l.strip() for l in lines if l.strip()!='']
    if len(L) < 2:
        raise ValueError("transfer.list too short")
    version = int(L[0])
    if version not in (1,2,3,4):
        raise ValueError(f"Unsupported transfer.list version: {version}")
    total_blocks = int(L[1])

    idx = 2
    block_size = 4096
    if version == 3:
        if idx < len(L):
            try:
                bs = int(L[idx])
            except Exception:
                bs = 0
            block_size = bs if bs > 0 else 4096
        idx += 1
    elif version == 4:
        idx += 1  # stashed_blocks (ignored)
        if idx < len(L):
            try:
                bs = int(L[idx])
            except Exception:
                bs = 0
            block_size = bs if bs > 0 else 4096
        idx += 1

    # advance to first command line
    while idx < len(L):
        tok = L[idx].split(' ', 1)[0].lower()
        if tok in KNOWN_CMDS:
            break
        idx += 1

    return version, total_blocks, block_size, idx, L

def parse_ranges_count_integers(ranges_str: str) -> List[Tuple[int,int]]:
    """
    Ranges format: <count>,<i1>,<i2>,...,<icount>
    'count' is the NUMBER OF INTEGERS (must be even → (start,end) pairs).
    """
    toks = [t for t in ranges_str.replace(',', ' ').split() if t!='']
    if not toks:
        return []
    cnt = int(toks[0])
    nums = list(map(int, toks[1:]))
    if len(nums) != cnt:
        raise ValueError("Bad ranges length")
    if cnt % 2 != 0:
        raise ValueError("Bad ranges: odd integer count")
    return [(nums[i], nums[i+1]) for i in range(0, cnt, 2)]

def sdat2img(transfer_list_path: Path, new_dat_path: Path, out_img_path: Path) -> None:
    with open(transfer_list_path, 'r', errors='ignore') as f:
        version, total_blocks, block_size, idx, L = parse_header(f.readlines())
    print(f"[sdat2img] {transfer_list_path.name}  v{version}  blocks={total_blocks}  block_size={block_size}")

    cmds: List[Tuple[str, str]] = []
    for l in L[idx:]:
        l = l.strip()
        if not l:
            continue
        c, a = (l.split(' ',1) + [""])[:2]
        cmds.append((c.lower(), a.strip()))

    with open(out_img_path, 'wb') as fout, open(new_dat_path, 'rb') as fdat:
        fout.truncate(total_blocks * block_size)
        for cmd, arg in cmds:
            if cmd == 'new':
                for start, end in parse_ranges_count_integers(arg):
                    length = (end - start) * block_size
                    if length <= 0:
                        continue
                    data = fdat.read(length)
                    if len(data) != length:
                        raise EOFError("new.dat ended unexpectedly")
                    fout.seek(start * block_size)
                    fout.write(data)
            elif cmd in ('zero','erase'):
                # sparse zero-fill — nothing to write
                continue
            else:
                # incremental-only ops (ignored for full OTAs)
                continue

# ---------- helpers ----------
def find_all(root: Path) -> Tuple[List[Path], List[Path]]:
    br_files: List[Path] = []
    lists: List[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ln = name.lower()
            full = Path(dirpath) / name
            if ln.endswith(".new.dat.br"):
                br_files.append(full)
            elif ln.endswith(".transfer.list"):
                lists.append(full)
    return br_files, lists

def list_basename_without_transfer_dot_list(path: Path) -> str:
    """Return 'system' from '...\system.transfer.list' (not 'system.transfer')."""
    name = path.name
    if name.lower().endswith(".transfer.list"):
        return name[:-len(".transfer.list")]
    return os.path.splitext(name)[0]

# ====================== public runner ======================

def run_ota_extract(
    root: str | Path,
    overwrite: bool = False,
    raw: bool = False,
    progress: Optional[Callable[[str], None]] = None,
) -> Dict[str,int]:
    """
    Execute OTA extraction in 'root'.
    Returns stats: {'decompressed': N, 'converted': M, 'raw_ok': R, 'errors': E}
    """
    root = Path(root).resolve()
    _progress_emit(progress, f"Scanning: {root}")

    br_files, lists = find_all(root)
    stats = {"decompressed": 0, "converted": 0, "raw_ok": 0, "errors": 0}

    # 1) Decompress .br
    if br_files:
        _progress_emit(progress, f"Decompressing {len(br_files)} *.new.dat.br")
    for br in br_files:
        out_dat = br.with_suffix("")  # strip '.br'
        if (not overwrite) and out_dat.exists():
            _progress_emit(progress, f"  - skip (exists): {out_dat.relative_to(root)}")
            continue
        _progress_emit(progress, f"  - brotli: {br.relative_to(root)}  ->  {out_dat.relative_to(root)}")
        try:
            decompress_brotli_file(br, out_dat)
            stats["decompressed"] += 1
        except Exception as ex:
            stats["errors"] += 1
            _eprint(f"! FAILED brotli {br}: {ex}")

    # 2) Convert each pair to .img
    if lists:
        _progress_emit(progress, f"Converting {len(lists)} *.transfer.list -> *.img")
    for lst in lists:
        base = list_basename_without_transfer_dot_list(lst)  # e.g., "system"
        dirp = lst.parent
        dat  = dirp / f"{base}.new.dat"
        img  = dirp / f"{base}.img"

        if not dat.exists():
            _progress_emit(progress, f"  - skip {base}: {dat.name} not found next to {lst.name}")
            continue
        if (not overwrite) and img.exists():
            _progress_emit(progress, f"  - skip (exists): {img.relative_to(root)}")
            continue

        try:
            _progress_emit(progress, f"  - build: {img.name}")
            sdat2img(lst, dat, img)
            stats["converted"] += 1
        except Exception as ex:
            stats["errors"] += 1
            _eprint(f"! FAILED {base}: {ex}")
            continue

        # Optional: sparse -> raw using simg2img if requested and available
        if raw:
            simg2img = shutil.which("simg2img.exe") or shutil.which("simg2img")
            if simg2img:
                raw_path = dirp / f"{base}_raw.img"
                if (not overwrite) and raw_path.exists():
                    _progress_emit(progress, f"    -> skip raw (exists): {raw_path.relative_to(root)}")
                else:
                    _progress_emit(progress, f"    -> simg2img: {raw_path.name}")
                    try:
                        r = subprocess.run([simg2img, str(img), str(raw_path)], capture_output=True, text=True)
                        if r.returncode != 0:
                            # If it fails, remove empty file (if any)
                            if raw_path.exists() and raw_path.stat().st_size == 0:
                                raw_path.unlink()
                            msg = r.stderr.strip() | r.stdout.strip() if (r.stderr or r.stdout) else "simg2img error"
                            _progress_emit(progress, f"       (not sparse or failed) {msg}")
                        else:
                            if raw_path.exists() and raw_path.stat().st_size > 0:
                                stats["raw_ok"] += 1
                            else:
                                if raw_path.exists():
                                    raw_path.unlink()
                                _progress_emit(progress, "       (not sparse) raw not created")
                    except Exception as ex:
                        _progress_emit(progress, f"       simg2img failed (ignored): {ex}")
            else:
                _progress_emit(progress, "    -> simg2img not found; skipping raw")

    _progress_emit(progress, "Done.")
    return stats

# ====================== UI bridge (self-register) ======================

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.status import Status
    from . import register  # registry from addons/__init__.py

    def _section(console: Console, title: str, subtitle: str = "") -> None:
        art = r"""
   ___   ______ ____  ______ ____ 
  /   | /_  __// __ \_  __// __ \
 / /| |  / /  / / / / / /  / / / /
/ ___ | / /  / /_/ / / /  / /_/ / 
/_/  |_|/_/   \____/ /_/   \____/
"""
        msg = f"[bold magenta]{art}[/]\n[bold]{title}[/]"
        if subtitle:
            msg += f"\n[dim]{subtitle}[/]"
        console.clear()
        console.print(Panel.fit(msg, border_style="magenta"))

    def _addon_action(console: Console, **kwargs):
        _section(console, "OTA Extractor",
                 "Convert *.new.dat.br → *.new.dat → *.img (optional *_raw.img)")
        root = Prompt.ask("Root folder to scan", default=".")
        overwrite = Confirm.ask("Overwrite existing .new.dat / .img if present?", default=False)
        want_raw  = Confirm.ask("Also try simg2img to produce *_raw.img?", default=False)

        def cb(msg: str):
            console.print(f"• {msg}")

        with Status("[bold]Working…[/] scanning & processing", console=console, spinner="dots"):
            stats = run_ota_extract(root, overwrite=overwrite, raw=want_raw, progress=cb)

        _section(console, "OTA Extractor — Done")
        console.print(
            f"[green]Decompressed[/]: {stats['decompressed']}  "
            f"[green]Converted[/]: {stats['converted']}  "
            f"[green]Raw OK[/]: {stats['raw_ok']}  "
            f"[red]Errors[/]: {stats['errors']}"
        )
        Confirm.ask("Back", default=True)

    # Register in the global add-ons menu
    register("Extract OTA (dat.br → dat → img)", _addon_action)

except Exception:
    # If Rich or registry isn't present, quietly skip the UI hook.
    pass

# ====================== optional CLI (standalone) ======================

def _cli():
    ap = argparse.ArgumentParser(
        description="Decompress *.new.dat.br and build *.img from *.transfer.list + *.new.dat (recursively)."
    )
    ap.add_argument("root", nargs="?", default=".", help="Root folder to process (default: current dir)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing .new.dat / .img")
    ap.add_argument("--raw", action="store_true", help="Also attempt simg2img → *_raw.img if available")
    args = ap.parse_args()
    stats = run_ota_extract(args.root, overwrite=args.overwrite, raw=args.raw, progress=print)
    print(
        f"\n==> Done. "
        f"Decompressed={stats['decompressed']}  "
        f"Converted={stats['converted']}  "
        f"RawOK={stats['raw_ok']}  "
        f"Errors={stats['errors']}"
    )

if __name__ == "__main__":
    _cli()

# ---- UI wrapper + registration (append to the end of ota_extract.py) ----
from . import register
from rich.prompt import Prompt, Confirm

def _ui_ota_extract(console, **kwargs):
    """Interactive wrapper that calls run_ota_extract()."""
    root = Prompt.ask("Folder to scan for OTA files", default=".")
    overwrite = Confirm.ask("Overwrite existing .new.dat/.img?", default=False)
    raw = Confirm.ask("Also try simg2img to create *_raw.img (if available)?", default=False)

    def progress(msg: str):
        try:
            console.log(msg)
        except Exception:
            pass

    stats = run_ota_extract(root, overwrite=overwrite, raw=raw, progress=progress)
    console.print(
        f"[green]Done.[/] Decompressed={stats['decompressed']}  "
        f"Converted={stats['converted']}  RawOK={stats['raw_ok']}  Errors={stats['errors']}"
    )
    Confirm.ask("Back", default=True)

# Register in the add-ons menu
register("OTA Extractor (.new.dat.br → .img)", _ui_ota_extract)
