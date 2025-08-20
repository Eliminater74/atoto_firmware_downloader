# atoto_fw/ui.py
from __future__ import annotations
from pathlib import Path

from rich.prompt import Prompt, Confirm

# Pull the shared console + helpers from core so we render consistently
from .core import (
    console, section, config_path,
    load_cfg, save_cfg, prompt_profile, profile_menu,
    run_search_download_flow, manual_url_flow,
)

def main_menu(out_dir: Path) -> None:
    """Top-level interactive menu."""
    cfg = load_cfg()
    while True:
        default_name = cfg.get("last_profile") or "(none)"
        section(
            "ATOTO Firmware Downloader",
            f"Default profile: [bold]{default_name}[/]\nConfig: {config_path()}",
        )
        console.print(
            "[1] Quick Search (use default profile)\n"
            "[2] Profiles (create/edit/select)\n"
            "[3] Ad-hoc Search (don’t save)\n"
            "[4] Manual URL Download\n"
            "[5] Settings / Info\n"
            "[0] Exit"
        )
        ans = Prompt.ask("Select", default="1").strip()
        if ans == "0":
            # exit menu
            return

        elif ans == "1":
            # Quick search with default profile (or force picking one)
            name = cfg.get("last_profile", "")
            if name and name in cfg["profiles"]:
                run_search_download_flow(cfg["profiles"][name], out_dir)
            else:
                console.print("[yellow]No default profile set. Opening Profiles…[/]")
                p = profile_menu(cfg)
                if p:
                    run_search_download_flow(p, out_dir)

        elif ans == "2":
            # Manage profiles; optionally run a search after
            p = profile_menu(cfg)
            if p and Confirm.ask("Run Quick Search with this profile now?", default=True):
                run_search_download_flow(p, out_dir)

        elif ans == "3":
            # Temporary profile that isn’t saved
            p = prompt_profile({})
            run_search_download_flow(p, out_dir)

        elif ans == "4":
            # Manual URL downloader
            manual_url_flow(out_dir / "manual")

        elif ans == "5":
            # Placeholder settings screen
            section("Settings / Info", f"Config: {config_path()}\nOutput: {out_dir}")
            console.print("[dim]Nothing else here yet. Future: proxy, mirror toggles, cache clear.[/]")
            Confirm.ask("Back", default=True)

        # any other key => redraw
