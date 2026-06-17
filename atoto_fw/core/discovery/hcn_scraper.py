"""
atoto_fw.core.discovery.hcn_scraper
Scraper for hcn2000 open directory server to fetch direct firmware download links.
"""

import re
import urllib.request
from urllib.parse import urljoin
from typing import List, Dict, Any

BASE_URL = "http://www.hcn2000.com/uploadsoft/cheji/"

# Mapping from query substring to folder substrings
KEYWORD_MAPPING = {
    "S8": ["uis8581"],
    "8581": ["uis8581"],
    "7862": ["uis8581"],
    "X10": ["sm6225", "6225", "6125", "680"],
    "6225": ["sm6225", "6225"],
    "6125": ["sm6225", "6125"],
    "680": ["sm6225", "680"],
    "T527": ["t527"],
    "A6": ["ac8257", "8257"],
    "F7": ["ac8257", "8257"],
    "8257": ["ac8257", "8257"],
    "8227": ["ac8227l", "8227"],
    "A7": ["g36", "6765", "8768"],
    "HN7": ["g36", "6765", "8768"],
    "MQ001": ["g36", "6765", "8768"],
    "G36": ["g36", "6765", "8768"],
    "8768": ["g36", "8768"],
    "6765": ["g36", "6765"],
    "8163": ["mt8163", "8163"],
    "2712": ["mt2712", "2712"],
    "3561": ["mt3561", "3561"],
    "8127": ["mt8127", "8127"],
    "8321": ["mt8321", "8321"],
    "3326": ["rk3326", "3326"],
    "3562": ["rk3562", "3562"],
}

CACHED_FOLDERS: List[str] = []

def fetch_directories(url: str) -> List[str]:
    """Fetch directories from a given IIS directory URL."""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read().decode('utf-8', errors='ignore')
            links = re.findall(r'href=["\']([^"\']+/?)["\']', html, re.IGNORECASE)
            dirs = []
            for link in links:
                if link.endswith('/') and not link.startswith('?') and '..' not in link:
                    part = link
                    if part.startswith('/uploadsoft/cheji/'):
                        part = part[len('/uploadsoft/cheji/'):]
                    if part and part != '/':
                        dirs.append(part)
            return sorted(list(set(dirs)))
    except Exception:
        return []

def get_all_folders() -> List[str]:
    """Retrieve and cache all release/debug folders on the server (including apd/ subdirs)."""
    global CACHED_FOLDERS
    if CACHED_FOLDERS:
        return CACHED_FOLDERS
    
    root_dirs = fetch_directories(BASE_URL)
    folders = []
    for d in root_dirs:
        if d == "apd/":
            subdirs = fetch_directories(urljoin(BASE_URL, "apd/"))
            for sd in subdirs:
                folders.append(f"apd/{sd}")
        else:
            folders.append(d)
            
    CACHED_FOLDERS = folders
    return folders

def get_platform_paths_for_model(model: str) -> List[str]:
    """Determine target platform folders to scan based on searched model string."""
    m_upper = model.upper()
    folders = get_all_folders()
    
    targets = []
    for kw, tags in KEYWORD_MAPPING.items():
        if kw in m_upper:
            targets.extend(tags)
            
    targets.append(model.lower())
    targets = list(set([t.lower() for t in targets if t]))
    
    matched_folders = []
    for f in folders:
        f_lower = f.lower()
        if any(t in f_lower for t in targets):
            matched_folders.append(f)
            
    if not matched_folders:
        # Fallback to all release folders if no specific match
        matched_folders = [f for f in folders if "release" in f.lower() and "debug" not in f.lower()]
        
    return matched_folders


def fetch_hcn_server_packages(model: str) -> List[Dict[str, Any]]:
    """Scan the HCN update server folders matching the model and extract firmware candidates."""
    targets = get_platform_paths_for_model(model)
    pkgs = []
    
    # Regex to parse IIS directory listing:
    # Example line: 2025/12/2    10:40        23932928 <A HREF="filename.zip">filename.zip</A><br>
    # Group 1: Date, Group 2: Size (or &lt;dir&gt;), Group 3: Href, Group 4: Name
    line_pattern = re.compile(
        r"(\d{4}/\d{1,2}/\d{1,2})\s+\d{1,2}:\d{2}\s+(\d+|&lt;dir&gt;)\s+<A[^>]+HREF=[\"']([^\"']+)[\"'][^>]*>([^<]+)</A>",
        re.IGNORECASE
    )
    
    for folder_path in targets:
        url = urljoin(BASE_URL, folder_path)
        label = folder_path.rstrip('/')
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
                # Scan lines
                matches = line_pattern.findall(html)
                for date_str, size_or_type, href, name in matches:
                    if size_or_type == "&lt;dir&gt;":
                        continue # Skip directories
                        
                    file_lower = name.lower()
                    if file_lower.endswith((".zip", ".rar", ".bin", ".img", ".apk")):
                        # Format version from filename
                        ver_match = re.findall(r'([rv]?[\d._-]+)', name.replace(" ",""))
                        version = ver_match[0] if ver_match else "N/A"
                        if version.endswith("-") or version.endswith("."):
                            version = version[:-1]
                            
                        # Format date string: YYYY/MM/DD -> YYYY-MM-DD
                        date_fmt = date_str.replace("/", "-")
                        
                        # Calculate full url
                        full_url = urljoin(url, href)
                        
                        pkgs.append({
                            "id": "0",
                            "title": f"[{label}] {name}",
                            "version": version,
                            "date": date_fmt,
                            "size": int(size_or_type) if size_or_type.isdigit() else None,
                            "url": full_url,
                            "hash": "",
                            "source": "HCN_SERVER",
                            "mirror": False,
                            "desc": f"Source: HCN Open Directory ({label})"
                        })
        except Exception:
            pass
            
    return pkgs
