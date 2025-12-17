#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared TUI components (Menu, helpers) for ATOTO Firmware Downloader.
"""
from __future__ import annotations
import re
from typing import Any, List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

try:
    import msvcrt
except ImportError:
    msvcrt = None

def clear_screen(console: Console) -> None:
    console.clear()

def header_art() -> str:
    return r"""
   ___   ______ ____  ______ ____ 
  /   | /_  __// __ \_  __// __ \
 / /| |  / /  / / / / / /  / / / /
/ ___ | / /  / /_/ / / /  / /_/ / 
/_/  |_|/_/   \____/ /_/   \____/  
"""

def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]+', "_", (name or "")).strip() or "file"

def section(console: Console, title: str, subtitle: str = "") -> None:
    clear_screen(console)
    msg = f"[bold magenta]{header_art()}[/]\n[bold]{title}[/]"
    if subtitle:
        msg += f"\n[dim]{subtitle}[/]"
    console.print(Panel.fit(msg, border_style="magenta"))

class Menu:
    """Simple Interactive Menu for Windows (falls back to prompt on others)"""
    def __init__(self, console_: Console, items: List[Tuple[str, Any]], title: str = "", subtitle: str = ""):
        self.console = console_
        self.items = items  # list of (label, return_value)
        self.title = title
        self.subtitle = subtitle
        self.idx = 0

    def show(self) -> Any:
        # Fallback if not Windows or msvcrt missing
        if not msvcrt:
            self.console.print(f"[bold]{self.title}[/]")
            for i, (label, _) in enumerate(self.items, 1):
                self.console.print(f"[{i}] {label}")
            ans = Prompt.ask("Select", default="1")
            if ans.isdigit() and 1 <= int(ans) <= len(self.items):
                return self.items[int(ans)-1][1]
            return None

        while True:
            # Render
            self.console.clear()
            msg = f"[bold magenta]{header_art()}[/]\n[bold]{self.title}[/]"
            if self.subtitle:
                msg += f"\n[dim]{self.subtitle}[/]"
            self.console.print(Panel.fit(msg, border_style="magenta"))

            # Render items
            lines = []
            for i, (label, _) in enumerate(self.items):
                cursor = "➤ " if i == self.idx else "  "
                style = "reverse bold cyan" if i == self.idx else ""
                if style:
                    lines.append(f"[{style}]{cursor}{label}[/]")
                else:
                    lines.append(f"{cursor}{label}")
            
            self.console.print("\n".join(lines))
            self.console.print("\n[dim]Use ↑/↓ and Enter to select. Esc/0 to Cancel.[/]")

            # Input
            key = msvcrt.getch()
            if key in (b'\000', b'\xe0'): # Arrows
                key = msvcrt.getch()
                if key == b'H': # Up
                    self.idx = max(0, self.idx - 1)
                elif key == b'P': # Down
                    self.idx = min(len(self.items) - 1, self.idx + 1)
            elif key == b'\r': # Enter
                return self.items[self.idx][1]
            elif key in (b'\x1b', b'0'): # Esc or 0
                return None
            elif key == b'q': # q for quit (mapped to None)
                return None

class FolderPicker:
    """Interactive Folder Selection Menu"""
    def __init__(self, console_: Console, start_path: str = ".", title: str = "Select Folder"):
        self.console = console_
        import os
        self.path = os.path.abspath(start_path)
        self.title = title
        self.idx = 0

    def show(self) -> Optional[str]:
        # Fallback if no msvcrt
        import os
        if not msvcrt:
            self.console.print(f"[bold]{self.title}[/]")
            p = Prompt.ask("Enter path", default=self.path)
            return p if os.path.exists(p) else None

        from pathlib import Path

        while True:
            # Gather subfolders
            try:
                entries = [d for d in os.listdir(self.path) if os.path.isdir(os.path.join(self.path, d))]
                entries = sorted([d for d in entries if not d.startswith('.')]) # Skip hidden
            except PermissionError:
                entries = []

            # Menu items: 
            # 0. [ SELECT THIS FOLDER ]
            # 1. .. (Up)
            # 2..N subfolders
            
            menu_items = [
                ("[bold green]✓ USE THIS FOLDER[/]", "SELECT"),
                ("[bold yellow].. (Go Up)[/]", "UP")
            ]
            for e in entries:
                menu_items.append((f"📂 {e}", e))

            # Clamp idx
            if self.idx >= len(menu_items):
                self.idx = 0

            # Render
            clear_screen(self.console)
            msg = f"[bold magenta]{header_art()}[/]\n[bold]{self.title}[/]\n[dim]Current: {self.path}[/]"
            self.console.print(Panel.fit(msg, border_style="magenta"))

            lines = []
            for i, (label, _) in enumerate(menu_items):
                cursor = "➤ " if i == self.idx else "  "
                style = "reverse bold cyan" if i == self.idx else ""
                if style:
                    lines.append(f"[{style}]{cursor}{label}[/]")
                else:
                    lines.append(f"{cursor}{label}")

            self.console.print("\n".join(lines))
            self.console.print("\n[dim]Enter=Open/Select. Esc/q=Cancel.[/]")

            # Input
            key = msvcrt.getch()
            if key in (b'\000', b'\xe0'):
                key = msvcrt.getch()
                if key == b'H': self.idx = max(0, self.idx - 1)
                elif key == b'P': self.idx = min(len(menu_items) - 1, self.idx + 1)
            elif key == b'\r':
                val = menu_items[self.idx][1]
                if val == "SELECT":
                    return self.path
                elif val == "UP":
                    parent = os.path.dirname(self.path)
                    if parent and parent != self.path:
                        self.path = parent
                        self.idx = 0
                else:
                    # Descend
                    new_path = os.path.join(self.path, val)
                    if os.path.isdir(new_path):
                        self.path = new_path
                        self.idx = 0 # reset selection
            elif key in (b'\x1b', b'0', b'q'):
                return None
