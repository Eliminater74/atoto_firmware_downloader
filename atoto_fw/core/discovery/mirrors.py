import re
from typing import Any, Dict, List
from ..utils import head_info, url_leaf_name, human_size

KNOWN_LINKS: List[Dict[str,str]] = [
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
                
                # Smart parse version/date from filename like 6315-SYSTEM20250401-APP20250514.zip
                # 1. Look for YYYYMMDD patterns
                dates = re.findall(r'(20\d{6})', fname)
                best_date = max(dates) if dates else ""
                
                # 2. Extract Version: Use full filename stem (minus extension) to capture all details
                ver = fname
                if ver.lower().endswith(".zip"):
                    ver = ver[:-4]
                
                # Format date nicely if available
                if best_date and len(best_date) == 8:
                    date_fmt = f"{best_date[:4]}-{best_date[4:6]}-{best_date[6:]}"
                else:
                    date_fmt = ""

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
