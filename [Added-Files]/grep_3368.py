#!/usr/bin/env python3
# Finds the literal code 3368 (ASCII and UTF-16LE) in files and inside APK/JAR/ZIP.
# Prints BIG markers so you see it even if ANSI colors are off.

import sys, os, zipfile, pathlib

RED = "\x1b[1;37;41m"; RESET = "\x1b[0m"
MARK = f"{RED} 3368 {RESET}"  # ANSI highlight
PLAIN_MARK = "[[3368]]"       # fallback marker for consoles without ANSI

def supports_color():
    # crude check; if you don't see colors, set USE_COLOR=False below
    return sys.stdout.isatty() and (os.name != "nt" or "WT_SESSION" in os.environ or "ANSICON" in os.environ)

USE_COLOR = supports_color()

def show_hit(path, inner=None, kind="ASCII", offset=None):
    tag = MARK if USE_COLOR else PLAIN_MARK
    loc = f"{path}" + (f"!{inner}" if inner else "")
    extra = f" ({kind} @ {offset})" if offset is not None else f" ({kind})"
    print(f"\n{tag}  found in: {loc}{extra}")

def scan_bytes(blob: bytes, path, inner=None):
    # ASCII 3368 with digit boundaries
    i = 0
    while True:
        i = blob.find(b"3368", i)
        if i < 0: break
        pre = blob[i-1:i]
        post = blob[i+4:i+5]
        if not (pre.isdigit() or post.isdigit()):
            show_hit(path, inner, "ASCII", i)
        i += 4

    # UTF-16LE: 3\0 3\0 6\0 8\0 with digit boundaries in UTF-16LE
    pat = b"3\x003\x006\x008\x00"
    j = 0
    while True:
        j = blob.find(pat, j)
        if j < 0: break
        # check preceding UTF-16LE code unit is not a digit
        ok_prev = True
        if j >= 2:
            prev = blob[j-2:j]
            ok_prev = not (prev[0:1].isdigit() and prev[1] == 0)
        # check following UTF-16LE code unit is not a digit
        ok_next = True
        if j+8 <= len(blob)-2:
            nxt = blob[j+8:j+10]
            ok_next = not (nxt[0:1].isdigit() and nxt[1] == 0)
        if ok_prev and ok_next:
            show_hit(path, inner, "UTF-16LE", j)
        j += 2

def scan_file(p: pathlib.Path):
    try:
        data = p.read_bytes()
        scan_bytes(data, str(p))
    except Exception:
        pass

def scan_zip(zp: pathlib.Path):
    try:
        with zipfile.ZipFile(zp, "r") as z:
            for info in z.infolist():
                # Read everything but limit size to keep things fast
                try:
                    data = z.read(info)
                except Exception:
                    continue
                scan_bytes(data, str(zp), info.filename)
    except Exception:
        pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python grep_3368.py <file_or_dir> [more...]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        p = pathlib.Path(arg)
        if p.is_dir():
            for root, _, files in os.walk(p):
                for f in files:
                    fp = pathlib.Path(root)/f
                    ext = fp.suffix.lower()
                    if ext in {".apk",".jar",".zip"}:
                        scan_zip(fp)
                    else:
                        scan_file(fp)
        else:
            ext = p.suffix.lower()
            if ext in {".apk",".jar",".zip"}:
                scan_zip(p)
            else:
                scan_file(p)

if __name__ == "__main__":
    main()
