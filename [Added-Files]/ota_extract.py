#!/usr/bin/env python3
"""
ota_extract.py
Recursively:
  1) Decompress *.new.dat.br -> *.new.dat  (uses 'brotli' or 'brotlicffi')
  2) Convert <name>.transfer.list + <name>.new.dat -> <name>.img
     (supports transfer.list v1–v4; v4 header: version, total, stashed, block_size)
Optional:
  --raw  : if 'simg2img.exe' is available, also produce <name>_raw.img
  --overwrite : redo existing outputs
"""

import argparse, os, sys, shutil, subprocess

# --- Brotli import (either package works) ---
try:
    import brotli  # pip install brotli
except ImportError:
    try:
        import brotlicffi as brotli  # pip install brotlicffi
    except ImportError:
        brotli = None

KNOWN_CMDS = {"new","zero","erase","move","stash","free","append","bsdiff","imgdiff"}

def eprint(*a): print(*a, file=sys.stderr)

# ---------- Brotli ----------
def decompress_brotli_file(src, dst):
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
def parse_header(lines):
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
            try: bs = int(L[idx])
            except: bs = 0
            block_size = bs if bs > 0 else 4096
        idx += 1
    elif version == 4:
        idx += 1  # stashed_blocks (ignored)
        if idx < len(L):
            try: bs = int(L[idx])
            except: bs = 0
            block_size = bs if bs > 0 else 4096
        idx += 1

    # advance to first command line
    while idx < len(L):
        tok = L[idx].split(' ', 1)[0].lower()
        if tok in KNOWN_CMDS:
            break
        idx += 1

    return version, total_blocks, block_size, idx, L

def parse_ranges_count_integers(ranges_str):
    """
    Ranges format: <count>,<i1>,<i2>,...,<icount>
    'count' is the NUMBER OF INTEGERS (must be even → (start,end) pairs).
    """
    toks = [t for t in ranges_str.replace(',', ' ').split() if t!='']
    if not toks: return []
    cnt = int(toks[0])
    nums = list(map(int, toks[1:]))
    if len(nums) != cnt:
        raise ValueError("Bad ranges length")
    if cnt % 2 != 0:
        raise ValueError("Bad ranges: odd integer count")
    return [(nums[i], nums[i+1]) for i in range(0, cnt, 2)]

def sdat2img(transfer_list_path, new_dat_path, out_img_path):
    with open(transfer_list_path, 'r', errors='ignore') as f:
        version, total_blocks, block_size, idx, L = parse_header(f.readlines())
    print(f"[sdat2img] {os.path.basename(transfer_list_path)}  v{version}  "
          f"blocks={total_blocks}  block_size={block_size}")

    cmds = []
    for l in L[idx:]:
        l = l.strip()
        if not l: continue
        c, a = (l.split(' ',1) + [""])[:2]
        cmds.append((c.lower(), a.strip()))

    with open(out_img_path, 'wb') as fout, open(new_dat_path, 'rb') as fdat:
        fout.truncate(total_blocks * block_size)
        for cmd, arg in cmds:
            if cmd == 'new':
                for start, end in parse_ranges_count_integers(arg):
                    length = (end - start) * block_size
                    if length <= 0: continue
                    data = fdat.read(length)
                    if len(data) != length:
                        raise EOFError("new.dat ended unexpectedly")
                    fout.seek(start * block_size)
                    fout.write(data)
            elif cmd in ('zero','erase'):
                continue
            else:
                # incremental-only ops (ignored for full OTAs)
                continue

# ---------- helpers ----------
def find_all(root):
    br_files, lists = [], []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ln = name.lower()
            full = os.path.join(dirpath, name)
            if ln.endswith(".new.dat.br"):
                br_files.append(full)
            elif ln.endswith(".transfer.list"):
                lists.append(full)
    return br_files, lists

def list_basename_without_transfer_dot_list(path):
    """Return 'system' from '...\system.transfer.list' (not 'system.transfer')."""
    name = os.path.basename(path)
    if name.lower().endswith(".transfer.list"):
        return name[:-len(".transfer.list")]
    return os.path.splitext(name)[0]

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(
        description="Decompress *.new.dat.br and build *.img from *.transfer.list + *.new.dat (recursively).")
    ap.add_argument("root", nargs="?", default=".", help="Root folder to process (default: current dir)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing .new.dat / .img")
    ap.add_argument("--raw", action="store_true", help="If simg2img.exe is available, also create *_raw.img")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    print(f"==> Scanning: {root}")

    br_files, lists = find_all(root)

    # 1) Decompress .br
    if br_files:
        print(f"==> Decompressing {len(br_files)} *.new.dat.br files")
    for br in br_files:
        out_dat = br[:-3]  # strip '.br'
        if (not args.overwrite) and os.path.exists(out_dat):
            print(f"  - skip (exists): {os.path.relpath(out_dat, root)}")
            continue
        print(f"  - brotli: {os.path.relpath(br, root)}  ->  {os.path.relpath(out_dat, root)}")
        decompress_brotli_file(br, out_dat)

    # 2) Convert each pair to .img
    if lists:
        print(f"\n==> Converting {len(lists)} *.transfer.list -> *.img")
    errors = 0
    for lst in lists:
        base = list_basename_without_transfer_dot_list(lst)  # e.g., "system"
        dirp = os.path.dirname(lst)
        dat  = os.path.join(dirp, f"{base}.new.dat")
        img  = os.path.join(dirp, f"{base}.img")

        if not os.path.exists(dat):
            print(f"  - skip {base}: {os.path.basename(dat)} not found next to {os.path.basename(lst)}")
            continue
        if (not args.overwrite) and os.path.exists(img):
            print(f"  - skip (exists): {os.path.relpath(img, root)}")
            continue

        try:
            print(f"  - build: {base}.img")
            sdat2img(lst, dat, img)
        except Exception as ex:
            errors += 1
            eprint(f"  ! FAILED {base}: {ex}")
            continue

        # Optional: sparse -> raw using simg2img.exe if requested and available
        if args.raw:
            simg2img = shutil.which("simg2img.exe")
            if simg2img:
                raw = os.path.join(dirp, f"{base}_raw.img")
                if (not args.overwrite) and os.path.exists(raw):
                    print(f"    -> skip raw (exists): {os.path.relpath(raw, root)}")
                else:
                    print(f"    -> simg2img: {os.path.basename(raw)}")
                    try:
                        r = subprocess.run([simg2img, img, raw], capture_output=True, text=True)
                        if r.returncode != 0:
                            # If it fails, remove empty file (if any)
                            if os.path.exists(raw) and os.path.getsize(raw) == 0:
                                os.remove(raw)
                            msg = r.stderr.strip() or r.stdout.strip() or "simg2img error"
                            print(f"       (not sparse or failed) {msg}")
                        else:
                            if os.path.getsize(raw) == 0:
                                os.remove(raw)
                                print("       (not sparse) raw not created")
                            else:
                                print("       OK")
                    except Exception as ex:
                        print(f"       simg2img failed (ignored): {ex}")
            else:
                print("    -> simg2img.exe not found; skipping raw")

    print("\n==> Done." + (f"  (with {errors} error(s))" if errors else ""))

if __name__ == "__main__":
    main()
