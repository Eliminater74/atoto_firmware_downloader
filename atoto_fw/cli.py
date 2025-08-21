# atoto_fw/cli.py
from __future__ import annotations
import argparse
from pathlib import Path

from .ui import main_menu
from .core import setup_logging

def parse_args():
    ap = argparse.ArgumentParser(description="ATOTO Firmware Downloader (launcher)")
    ap.add_argument("--out", default="ATOTO_Firmware", help="Output directory")
    ap.add_argument("--verbose", action="store_true", help="Enable debug logging for core/network")
    return ap.parse_args()

def main():
    args = parse_args()
    setup_logging(verbose=args.verbose)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    main_menu(out_dir)
