from .assemble import try_lookup
from .discovery import normalize_candidates
from .grouping import tag_rows, group_by_url
from .utils import human_size, sha256_file, url_leaf_name
from .http import SESSION, setup_logging        # <-- add setup_logging here
from .config import config_dir, config_path, load_cfg, save_cfg

__all__ = [
    "try_lookup",
    "normalize_candidates",
    "tag_rows",
    "group_by_url",
    "human_size",
    "sha256_file",
    "url_leaf_name",
    "SESSION",
    "setup_logging",                             # <-- and list it here
    "config_dir",
    "config_path",
    "load_cfg",
    "save_cfg",
]
