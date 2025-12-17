#!/usr/bin/env python3
import sys, re, zipfile, pathlib, argparse

# ----- patterns (4-char only) -----
RE_MANIFEST_HOST = re.compile(rb'android_secret_code[^>]*?host="([0-9A-Za-z]{4})"', re.I)
RE_MANIFEST_URI  = re.compile(rb'android_secret_code://([0-9A-Za-z]{4})', re.I)

# DEX context heuristics
NEAR = re.compile(rb'(factory|service|secret[^a-z]|password|passwd|pin|engineer|admin|unlock)', re.I)
AVOID = re.compile(rb'(codec|media[_-]?codec|iso[-_]?8859)', re.I)

# four-digit candidate (exactly 4 digits)
FOUR_DIGITS = re.compile(rb'(?<!\d)(\d{4})(?!\d)')

# optional: 4-char alnum token (enable with --alnum)
FOUR_ALNUM = re.compile(rb'\b([0-9A-Z]{4})\b')

BORING_4 = {
    b'0000', b'1111', b'1234',
    b'1024', b'2048', b'3072', b'4096',
    b'6500', b'8000', b'8859',
}

def read_member(zf, name):
    try:
        return zf.read(name)
    except Exception:
        return b""

def scan_apk(apk: pathlib.Path, ctx_window: int, alnum: bool):
    hits = []
    try:
        with zipfile.ZipFile(apk) as z:
            # 1) Manifest: secret-code hosts and URIs (4 chars only)
            manifest = read_member(z, "AndroidManifest.xml")
            if manifest:
                for m in RE_MANIFEST_HOST.findall(manifest):
                    tok = m.upper()
                    if tok not in BORING_4:
                        hits.append(("MANIFEST", tok.decode(errors="ignore")))
                for m in RE_MANIFEST_URI.findall(manifest):
                    tok = m.upper()
                    if tok not in BORING_4:
                        hits.append(("MANIFEST", tok.decode(errors="ignore")))
                if (b"android.provider.Telephony.SECRET_CODE" in manifest) and not any(h[0]=="MANIFEST" for h in hits):
                    hits.append(("MANIFEST", "SECRET_CODE present (no explicit 4-char host)"))

            # 2) DEX: look for 4-digit (or 4-alnum) near interesting words
            for e in z.infolist():
                if not (e.filename.endswith(".dex") and e.filename.startswith("classes")):
                    continue
                data = z.read(e)
                # numbers first
                for m in FOUR_DIGITS.finditer(data):
                    tok = m.group(1)
                    if tok in BORING_4: 
                        continue
                    s = max(0, m.start()-ctx_window); epos = min(len(data), m.end()+ctx_window)
                    ctx = data[s:epos]
                    if NEAR.search(ctx) and not AVOID.search(ctx):
                        hits.append((e.filename, tok.decode()))
                # optional: 4-char alnum
                if alnum:
                    for m in FOUR_ALNUM.finditer(data):
                        tok = m.group(1)
                        if tok.isdigit() and tok in BORING_4: 
                            continue
                        s = max(0, m.start()-ctx_window); epos = min(len(data), m.end()+ctx_window)
                        ctx = data[s:epos]
                        if NEAR.search(ctx) and not AVOID.search(ctx):
                            hits.append((e.filename, tok.decode()))
    except zipfile.BadZipFile:
        pass
    except Exception:
        pass

    if hits:
        # de-dup while preserving order
        seen = set(); ordered = []
        for h in hits:
            key = (h[0], h[1])
            if key in seen: 
                continue
            seen.add(key); ordered.append(h)

        print(f"\n{apk}")
        for where, token in ordered:
            print(f"   -> {where:10s} {token}")

def main():
    p = argparse.ArgumentParser(description="Find 4-char secret codes in APKs (exact 4 only).")
    p.add_argument("path", help="root folder of unpacked system (e.g., 6315_1)")
    p.add_argument("--ctx", type=int, default=120, help="DEX context window (bytes)")
    p.add_argument("--alnum", action="store_true", help="also allow 4-char alphanumeric tokens")
    args = p.parse_args()

    root = pathlib.Path(args.path)
    if not root.exists():
        print("Path not found:", root); sys.exit(1)

    apks = sorted(root.rglob("*.apk"))
    for apk in apks:
        scan_apk(apk, ctx_window=args.ctx, alnum=args.alnum)

if __name__ == "__main__":
    main()
