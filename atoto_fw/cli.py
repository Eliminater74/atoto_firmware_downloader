# atoto_fw/cli.py
from __future__ import annotations
import argparse
from pathlib import Path

from .ui import main_menu
from .core import manual_url_flow  # used when --manual is passed

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ATOTO firmware downloader (menu + profiles)")
    ap.add_argument("--out", default="ATOTO_Firmware",
                    help="Output directory (default: ATOTO_Firmware)")
    ap.add_argument("--manual", action="store_true",
                    help="Open manual-URL downloader and exit")
    return ap.parse_args()

def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.manual:
        manual_url_flow(out_dir / "manual")
        return
    main_menu(out_dir)
