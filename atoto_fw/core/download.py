# atoto_fw/core/download.py
from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional
import logging

from .http import SESSION
from .utils import sha256_file

logger = logging.getLogger(__name__)

ProgressCB = Callable[[int, int], None]  # (downloaded_bytes, total_bytes)

def download_with_resume(
    url: str,
    out_path: Path,
    expected_hash: str = "",
    on_progress: Optional[ProgressCB] = None,
    chunk_size: int = 128 * 1024,
) -> None:
    """
    Core downloader: resumable, no UI dependencies.
    - Writes to <file>.part and renames atomically at end
    - Calls on_progress(downloaded, total) if provided
    - Optional checksum verify (sha256/sha1/md5 detected by length)
    """
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    resume = tmp.stat().st_size if tmp.exists() else 0
    headers = {"Range": f"bytes={resume}-"} if resume > 0 else {}

    logger.debug("Starting download %s -> %s (resume=%d)", url, out_path, resume)

    with SESSION.get(url, stream=True, headers=headers, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", "0"))
        # If partial, try to compute full total
        if r.status_code == 206 and total:
            try:
                head = SESSION.head(url, timeout=10, allow_redirects=True)
                full_total = int(head.headers.get("Content-Length", total))
                total = resume + (full_total - resume)
            except Exception:
                total = resume + total

        mode = "ab" if resume > 0 else "wb"
        downloaded = resume
        with open(tmp, mode) as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress:
                    on_progress(downloaded, total)

    tmp.rename(out_path)
    logger.debug("Download finished: %s (%d bytes)", out_path, out_path.stat().st_size)

    if expected_hash:
        logger.debug("Verifying checksum (%s)", "auto")
        algo = "sha256" if len(expected_hash) == 64 else ("sha1" if len(expected_hash) == 40 else "md5")
        if algo == "sha256":
            digest = sha256_file(out_path)
        else:
            import hashlib
            h = getattr(hashlib, algo)()
            with out_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        if digest.lower() != expected_hash.lower():
            raise RuntimeError(f"Checksum mismatch: expected {expected_hash}, got {digest}")
        logger.debug("Checksum OK")
