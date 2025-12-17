#!/usr/bin/env python3
import re, sys, zipfile, io, os, pathlib
from collections import defaultdict

FOCUS_EXTS = {
    ".xml",".smali",".java",".kt",".txt",".csv",".json",".yml",".yaml",
    ".properties",".ini",".cfg",".conf",".html",".htm",".svg",".prop"
}
ARCHIVE_EXTS = {".apk",".jar",".zip"}
FOUR = re.compile(rb'(?<!\d)(\d{4})(?!\d)')
KEYWORDS = re.compile(rb'(factory|engineer|service|password|passcode|pin|code|update|hidden|secret)', re.I)

RED = "\x1b[1;37;41m"; RESET = "\x1b[0m"

def extract_4digit_chunks(data: bytes):
    # Return unique 4-digit strings and whether keywords are nearby
    hits = []
    for m in FOUR.finditer(data):
        s = m.group(1)
        start = max(0, m.start()-160)
        end   = min(len(data), m.end()+160)
        ctx = data[start:end]
        kw  = bool(KEYWORDS.search(ctx))
        hits.append((s.decode('ascii', 'ignore'), kw))
    return hits

def scan_bytes(name, data, results):
    # Skip very binary-looking blobs unless they contain some ASCII
    if not any(x in data for x in (b"<", b">", b"\"", b"'", b"{", b"}", b"=", b"\n", b"\r", b"\t")):
        # Still allow “strings()” style scan so we don’t miss smali-in-zip, etc.
        pass
    hits = extract_4digit_chunks(data)
    if hits:
        d = results[name]
        for code, kw in hits:
            d["codes"].add(code)
            d["kw"]  += int(kw)

def scan_path(p: pathlib.Path, results):
    if p.is_dir():
        for root, _, files in os.walk(p):
            for f in files:
                fp = pathlib.Path(root)/f
                ext = fp.suffix.lower()
                if ext in ARCHIVE_EXTS:
                    scan_archive(fp, results)
                elif ext in FOCUS_EXTS:
                    try:
                        scan_bytes(str(fp), fp.read_bytes(), results)
                    except Exception:
                        pass
    else:
        ext = p.suffix.lower()
        if ext in ARCHIVE_EXTS:
            scan_archive(p, results)
        elif ext in FOCUS_EXTS:
            try:
                scan_bytes(str(p), p.read_bytes(), results)
            except Exception:
                pass

def scan_archive(zp: pathlib.Path, results):
    try:
        with zipfile.ZipFile(zp, 'r') as z:
            for info in z.infolist():
                inner = info.filename
                ext = pathlib.Path(inner).suffix.lower()
                if ext in FOCUS_EXTS or inner.endswith(("/AndroidManifest.xml","/resources.arsc","classes.dex")):
                    try:
                        data = z.read(info)
                        # For binary resources/classes, still try extracting ASCII-ish runs
                        if ext not in FOCUS_EXTS:
                            # crude “strings” filter
                            data = b" ".join(ch for ch in re.findall(rb"[ -~]{4,}", data)[:])[:2_000_000]
                        scan_bytes(f"{zp}!{inner}", data, results)
                    except Exception:
                        pass
    except zipfile.BadZipFile:
        pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python scan_pins_strict.py <dir_or_apk> [more paths...]")
        sys.exit(1)

    results = defaultdict(lambda: {"codes": set(), "kw": 0})
    for arg in sys.argv[1:]:
        scan_path(pathlib.Path(arg), results)

    # Build list of (score, file, codes)
    rows = []
    for name, d in results.items():
        codes = sorted(d["codes"])
        if not codes: continue
        # prefer files with keywords; then those that contain 3368; then fewer unique codes
        score = d["kw"]*100 + (50 if "3368" in codes else 0) - len(codes)
        rows.append((score, name, codes))

    rows.sort(reverse=True)

    for _, name, codes in rows:
        # only 4-digit codes; show 3368 highlighted
        disp = []
        for c in codes:
            if c == "3368":
                disp.append(f"{RED}{c}{RESET}")
            else:
                disp.append(c)
        print("\n" + name)
        print("  →", " ".join(disp))

if __name__ == "__main__":
    main()
