import sys, re, zipfile, pathlib

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
KEYWORDS = re.compile(rb"(factory|service|secret|code|passwd|password|verify|admin|unlock|dvd|radio|region)", re.I)
DIGITS   = re.compile(rb"\b\d{4,6}\b")

def scan_apk(apk_path: pathlib.Path):
    try:
        with zipfile.ZipFile(apk_path) as z:
            for e in z.infolist():
                if e.filename.endswith(".dex") and e.filename.startswith("classes"):
                    data = z.read(e)
                    for m in DIGITS.finditer(data):
                        start = max(0, m.start()-80); end = min(len(data), m.end()+80)
                        ctx = data[start:end]
                        if KEYWORDS.search(ctx):  # only show numbers near interesting words
                            try:
                                print(f"{apk_path}  ->  {m.group(0).decode()}")
                            except:
                                pass
    except Exception as ex:
        pass

for apk in ROOT.rglob("*.apk"):
    scan_apk(apk)
