import re
from typing import Any, Dict, List
from ..utils import head_info, url_leaf_name, human_size, oss_alternates, normalize_oss_url

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

    # ── A6 Gen2 PF ───────────────────────────────────────────────────────────
    # Filename: ATOTO_A6_PF_7_Inch_OS_240627_APP_240613.zip (OS=June 27 2024)
    {
        "match": r"^(A6G2A7PF|A6G2A7|A6TYC7PF|A6VW07APF|A6G2B7PF).*$",
        "title": "A6 Gen2 PF 7-inch — OS 2024-06-27 / App 2024-06-13",
        "url":   "https://file.myatoto.com/2024/FILE_UPLOAD_URL_2/64147874/ATOTO_A6_PF_7_Inch_OS_240627_APP_240613.zip",
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

def _head_with_fallback(url: str, timeout: int = 3) -> Dict[str, Any]:
    """Try the primary URL then its CDN/OSS alias; return first successful HEAD."""
    for candidate in oss_alternates(url):
        info = head_info(candidate, timeout=timeout)
        if info["ok"]:
            return {**info, "_url": candidate}
    return {"ok": False, "size": None, "date": "", "_url": url}


def known_links_for_model(model: str) -> List[Dict[str, Any]]:
    out = []
    for entry in KNOWN_LINKS:
        if re.search(entry["match"], model):
            url = normalize_oss_url(entry["url"])
            info = _head_with_fallback(url, timeout=3)
            resolved_url = info.pop("_url", url)
            
            if info["ok"]:
                fname = url_leaf_name(resolved_url)
                title = entry.get("title") or fname

                dates_8 = re.findall(r'(20\d{6})', fname)
                dates_6 = re.findall(r'(?<!\d)([2-9]\d{5})(?!\d)', fname)
                best_date = ""
                if dates_8:
                    raw_d = max(dates_8)
                    best_date = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:]}"
                elif dates_6:
                    raw_d = max(dates_6)
                    best_date = f"20{raw_d[:2]}-{raw_d[2:4]}-{raw_d[4:]}"

                # Month-year fallback for filenames like "v1.1.1_April2024"
                if not best_date:
                    m = re.search(
                        r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
                        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
                        r'[\s_-]?(\d{4})',
                        fname, re.IGNORECASE
                    )
                    if m:
                        _months = {
                            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
                            "may": "05", "jun": "06", "jul": "07", "aug": "08",
                            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
                        }
                        mon = _months.get(m.group(1)[:3].lower(), "01")
                        best_date = f"{m.group(2)}-{mon}"

                # Semver extraction for version-numbered firmware (e.g. v1.1.1, V1.0.3)
                semver_m = re.search(r'[Vv](\d+\.\d+(?:\.\d+)?)', fname)
                base_ver = fname[:-4] if fname.lower().endswith(".zip") else fname
                ver = semver_m.group(0) if semver_m else base_ver

                out.append({
                    "id": "0",
                    "title": f"[mirror] {title}",
                    "version": ver,
                    "date": best_date,
                    "size": info["size"],
                    "url": resolved_url,
                    "hash": "",
                    "source": "MIRROR",
                })
    for i,p in enumerate(out,1): p["id"]=str(i)
    return out
