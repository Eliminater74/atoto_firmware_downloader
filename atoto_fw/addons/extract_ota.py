from __future__ import annotations
from . import register

def _run(console, **kwargs):
    console.print("[cyan]Extractor addon placeholder[/]. Drop your OTA extraction code here.")
    console.print("Later: auto-detect *.new.dat(.br) + transfer.list and build *.img")

register("Extract firmware (OTA → img)", _run)
