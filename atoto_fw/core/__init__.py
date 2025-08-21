# atoto_fw/core/__init__.py
from .assemble import try_lookup
from .discovery.normalize import normalize_candidates
from .grouping import tag_rows, group_by_url
from .utils import human_size, sha256_file, url_leaf_name
from .http import SESSION
from .config import load_cfg, save_cfg, config_path

# Optional: downloader (UI can switch to this later)
try:
    from .download import download_with_resume
except Exception:  # not fatal if file not present yet
    download_with_resume = None  # type: ignore

__all__ = [
    "try_lookup", "normalize_candidates", "tag_rows", "group_by_url",
    "human_size", "sha256_file", "url_leaf_name",
    "SESSION",
    "load_cfg", "save_cfg", "config_path",
    "download_with_resume",
    "setup_logging",
]

# ---- simple logging toggle for the package ----
import logging

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s"
    )
    # quiet down noisy deps
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
