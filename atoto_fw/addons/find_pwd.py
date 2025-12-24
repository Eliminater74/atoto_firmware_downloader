# atoto_fw/addons/find_pwd.py
import os
import re
import zipfile
import zlib
from pathlib import Path
from rich import print
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from atoto_fw.addons import register

# Regex for the password format we found (32 hex chars)
# It appeared as a standalone null-terminated string/or just surrounded by non-alphanums in the binary
RE_HEX_32 = re.compile(rb'(?<![a-fA-F0-9])([a-fA-F0-9]{32})(?![a-fA-F0-9])')

KNOWN_KEYS = {
    b'048a02243bb74474b25233bda3cd02f8',  # S8 Gen2 (6315) found in lsec6315update
}

def find_candidate_strings(file_path: Path) -> set[bytes]:
    """Scans a binary file for 32-char hex strings."""
    candidates = set()
    try:
        data = file_path.read_bytes()
        # Find all matches
        for m in RE_HEX_32.finditer(data):
            candidates.add(m.group(1))
    except Exception as e:
        print(f"[red]Error reading {file_path.name}: {e}[/]")
    return candidates

def try_unlock(zip_path: Path, password: bytes) -> bool:
    """Attempts to unlock the zip file with the given password."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            # Try to read a small file or the first file to verify password
            # 'Ver' was the file we used before, but we can try any.
            # We'll just list namelist -> pick smallest -> try read
            target = None
            # Prefer 'Ver' if it exists
            if 'Ver' in zf.namelist():
                target = 'Ver'
            else:
                # Pick the smallest file
                infos = sorted(zf.infolist(), key=lambda x: x.file_size)
                for info in infos:
                    if not info.is_dir():
                        target = info.filename
                        break
            
            if not target:
                return False

            # Force read with crc check
            zf.open(target, 'r', pwd=password).read()
            return True
            
    except (RuntimeError, zipfile.BadZipFile, zlib.error):
        return False
    except Exception:
        return False

def run_find_pwd_tool(console):
    """
    Scans for lsec* binaries and AllAppUpdate.bin to find the password.
    """
    console.clear()
    console.print(Panel.fit("Find Firmware Password", border_style="blue"))
    console.print("This tool searches for 'lsec*update' binaries and scans them for potential passwords (32-char hex keys).")
    console.print(f"[dim]Includes {len(KNOWN_KEYS)} known hardcoded fallback keys.[/]")
    
    # Default to current directory or ask user
    from atoto_fw.tui import FolderPicker
    start_dir_str = FolderPicker(console, start_path=os.getcwd(), title="Select Scan Directory").show()
    
    if not start_dir_str:
        return

    start_dir = Path(start_dir_str)
    
    if not start_dir.exists():
        console.print(f"[red]Directory not found: {start_dir}[/]")
        Prompt.ask("Press Enter to return")
        return

    # 1. Locate AllAppUpdate.bin (target)
    # 2. Locate lsec* files (sources)
    
    target_files = sorted(start_dir.rglob("AllAppUpdate.bin"))
    source_files = sorted(list(start_dir.rglob("lsec*update*")) + list(start_dir.rglob("update-binary")))
    
    if not target_files:
        console.print("[yellow]No 'AllAppUpdate.bin' found in this directory tree.[/]")
        if not Confirm.ask("Scan for passwords anyway?", default=True):
            return
    else:
        console.print(f"[green]Found possible target(s):[/]")
        for t in target_files:
            console.print(f" - {t}")

    # Initialize with known keys
    found_keys = set(KNOWN_KEYS)

    if not source_files:
        console.print("[yellow]No candidate binary files found to scan. Using known keys only.[/]")
    else:
        console.print(f"\n[bold]Scanning {len(source_files)} binaries for keys...[/]")
        for src in source_files:
            console.print(f"Scanning [cyan]{src.name}[/]...", end=" ")
            keys = find_candidate_strings(src)
            if keys:
                console.print(f"[green]Found {len(keys)} candidates[/]")
                found_keys.update(keys)
            else:
                console.print("[dim]None[/]")

    console.print(f"\n[bold]Total candidates to try: {len(found_keys)}[/]")
    
    if not found_keys:
        console.print("[red]No keys found (and no known Keys??).[/]")
        Prompt.ask("Press Enter to return")
        return
        
    # If we have targets, try to unlock them
    if target_files:
        for target in target_files:
            console.print(f"\n[bold]Attempting to crack {target.name}...[/]")
            success_pwd = None
            
            # Try all keys
            for key in found_keys:
                if try_unlock(target, key):
                    success_pwd = key
                    break
            
            if success_pwd:
                console.print(Panel(f"[bold green]SUCCESS![/]\n\nFile: {target}\nPassword: [bold yellow]{success_pwd.decode('utf-8')}[/]", border_style="green"))
                
                # Check if extracted dir exists
                extract_dir = target.parent / f"{target.stem}_extracted"
                if Confirm.ask(f"Extract now to [cyan]{extract_dir.name}[/]?", default=True):
                    try:
                        with zipfile.ZipFile(target) as zf:
                            zf.extractall(extract_dir, pwd=success_pwd)
                        console.print(f"[green]Extracted to {extract_dir}[/]")
                    except Exception as e:
                        console.print(f"[red]Extraction failed: {e}[/]")
            else:
                console.print(f"[red]Failed to unlock {target.name} with {len(found_keys)} candidates.[/]")
    else:
        # Just list the keys
        console.print("\n[bold]Found Potential Keys:[/]")
        for k in found_keys:
            console.print(f" - {k.decode('utf-8')}")

    Prompt.ask("\nPress Enter to return")

# Register ourselves
register("Find Firmware Password", run_find_pwd_tool)
