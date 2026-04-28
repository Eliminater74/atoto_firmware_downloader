import re
from typing import Any, Dict, List
from ..utils import head_info, url_leaf_name, human_size

KNOWN_LINKS: List[Dict[str,str]] = [
    # ── S8 Gen2 ───────────────────────────────────────────────────────────────
    {
        "match": r"^(S8G2|S8EG2|ATL-S8).*$",
        "title": "S8 Gen2 (UIS7862 6315) — 2025-04-01 / 05-14",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2025/FILE_UPLOAD_URL_2/85129692/6315-SYSTEM20250401-APP20250514.zip",
    },
    {
        "match": r"^(S8G2|S8EG2|ATL-S8).*$",
        "title": "S8 Gen2 (UIS7862 6315, 1024×600) — 2023-11-10 / 20",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1024x600_system231110_app_231120.zip",
    },
    {
        "match": r"^(S8G2|S8EG2|ATL-S8).*$",
        "title": "S8 Gen2 (UIS7862 6315, 1280×720) — 2023-11-10 / 20",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1280x720_system231110_app_231120.zip",
    },

    # ── F7 Gen2 ───────────────────────────────────────────────────────────────
    # GDB6P platform (older hardware, checksum variant) — 2022-12-17
    {
        "match": r"^(F7G2|F7|DS7P|U10).*$",
        "title": "F7 Gen2 (GDB6P platform) — 2022-12-17",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com//2023/FILE_UPLOAD_URL_3/33301859/F7-GDB6P-221217_checksum0xA7D847.zip",
    },
    # SOC5P platform (newer SoC revision) — 2023-06-09
    {
        "match": r"^(F7G2|F7|DS7P|U10).*$",
        "title": "F7 Gen2 (SOC5P platform) — 2023-06-09",
        "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com//2023/FILE_UPLOAD_URL_3/53166561/F7-SOC5P-230609.zip",
    },
]

def known_links_for_model(model: str) -> List[Dict[str, Any]]:
    out=[]
    for entry in KNOWN_LINKS:
        if re.search(entry["match"], model):
            url = entry["url"]
            info = head_info(url, timeout=3)
            
            if info["ok"]:
                fname = url_leaf_name(url)
                title = entry.get("title") or fname
                
                # Smart parse version/date from filename.
                # Try YYYYMMDD first (e.g. 20250401), then YYMMDD (e.g. 221217 → 2022-12-17).
                dates_8 = re.findall(r'(20\d{6})', fname)
                dates_6 = re.findall(r'(?<!\d)([2-9]\d{5})(?!\d)', fname)
                best_date = ""
                if dates_8:
                    raw_d = max(dates_8)
                    best_date = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:]}"
                elif dates_6:
                    raw_d = max(dates_6)
                    best_date = f"20{raw_d[:2]}-{raw_d[2:4]}-{raw_d[4:]}"

                ver = fname
                if ver.lower().endswith(".zip"):
                    ver = ver[:-4]

                date_fmt = best_date

                out.append({
                    "id": "0",
                    "title": f"[mirror] {title}",
                    "version": ver,
                    "date": date_fmt,
                    "size": info["size"], # int or None
                    "url": url,
                    "hash": "",
                    "source": "MIRROR"
                })
    for i,p in enumerate(out,1): p["id"]=str(i)
    return out
