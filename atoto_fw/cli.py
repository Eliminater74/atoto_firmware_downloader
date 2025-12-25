# atoto_fw/cli.py
from __future__ import annotations
import argparse
from pathlib import Path

from .ui import main_menu, run_search_download_flow, manual_url_flow
from .core import setup_logging

def parse_args():
    ap = argparse.ArgumentParser(description="ATOTO Firmware Downloader (launcher)")
    ap.add_argument("--out", default="ATOTO_Firmware", help="Output directory")
    ap.add_argument("--verbose", action="store_true", help="Enable debug logging for core/network")
    ap.add_argument("--model", help="Search for specific model (bypass menu)")
    ap.add_argument("--res", default="1280x720", help="Resolution for search (default 1280x720)")
    ap.add_argument("--deep", action="store_true", help="Enable Deep Search")
    ap.add_argument("--manual", help="Direct URL download")
    return ap.parse_args()

def main():
    args = parse_args()
    setup_logging(verbose=args.verbose)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # CLI mode
    if args.manual:
        manual_url_flow(out_dir / "manual")
        return
        
    if args.model:
        # Create ad-hoc profile from args
        p = {
            "name": "CLI",
            "model": args.model,
            "res": args.res,
            "mcu": "",
            "variants": "ANY",
            "prefer_universal": True
        }
        run_search_download_flow(p, out_dir, args.verbose, deep_scan=args.deep)
        return

    main_menu(out_dir)
