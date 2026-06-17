# ATOTO Firmware Downloader & Modding Toolkit

![Visitor Count](https://hits.sh/github.com/Eliminater74/atoto_firmware_downloader.svg?style=flat-square&label=Page+Views&color=blue)
[![GitHub Stars](https://img.shields.io/github/stars/Eliminater74/atoto_firmware_downloader?style=flat-square&logo=github)](https://github.com/Eliminater74/atoto_firmware_downloader/stargazers)
[![Latest Release](https://img.shields.io/github/v/release/Eliminater74/atoto_firmware_downloader?style=flat-square&logo=github&color=green)](https://github.com/Eliminater74/atoto_firmware_downloader/releases/latest)
[![Total Downloads](https://img.shields.io/github/downloads/Eliminater74/atoto_firmware_downloader/total?style=flat-square&logo=github&label=Downloads&color=brightgreen)](https://github.com/Eliminater74/atoto_firmware_downloader/releases)
[![Last Commit](https://img.shields.io/github/last-commit/Eliminater74/atoto_firmware_downloader?style=flat-square)](https://github.com/Eliminater74/atoto_firmware_downloader/commits/main)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/github/license/Eliminater74/atoto_firmware_downloader?style=flat-square)](LICENSE)

A powerful, open-source utility to **find, download, and modify** firmware for ATOTO car head units — **S8, A6, F7, P8, X10**, and more.

> **v2.4.0** — Batch / multi-select downloads, DS7/Z7/F10/P7 model support, `file.myatoto.com` CDN alias support, variant filter crash fix. See [Changelog](#changelog).

---

## Features

### Smart Firmware Discovery

- **Multi-source search** — Official ATOTO API, JSON endpoints, static mirrors, and Redstone FOTA all probed in parallel
- **Collect-all JSON** — Scans every matching endpoint per model (not just the first hit), so firmware split across multiple files is always found
- **Newest-first results** — All results sorted by date so the latest firmware appears at the top
- **Retail → Platform mapping** — Translates retail SKUs (`S8EG2A74MSB`, `F7G2A7XE`, `X10G2A7E`) into their internal firmware IDs automatically
- **Deep Search** — Aggressively expands to related platform IDs and variant suffixes; available as a menu option, CLI flag, or inline during Ad-hoc search
- **MCU retry fallback** — If the API returns nothing with your MCU version set, it silently retries without it before giving up
- **Redstone FOTA** — Checks the Redstone OTA server for X10 series firmware; platform map is extensible for future models

### Model Support

| Series | Example SKUs |
| ------ | ------------ |
| S8 Gen2 | `S8EG2A74MSB`, `S8EG2A7PE`, `S8EG2B74PMB` |
| A6 Gen2 | `A6EG2A74MSB`, `A6EG2A7PE`, `A6G2A7PF`, `A6G2B74PE` |
| F7 Gen1 | `F7G1A8XE`, `F7G1A8PE`, `F7G110XE` |
| F7 Gen2 7" | `F7G2A7XE`, `F7G2A7WE`, `F7G2A7SE`, `F7G2B7PE` |
| F7 Gen2 10" | `F7G210XE-NA`, `F7G210PE-EU`, `F7G209SE` |
| F7 Gen2 11" | `F7G211XE-NA`, `F7G211WE`, `F7G211SE` |
| F7 Toyota | `F7TYC7XE-A`, `F7TYC7SE` |
| F10 Gen2 | `F10G2A7PE`, `F10G2A7` |
| P7 Gen2 | `P7G2A74MS`, `P7G2A7PE` |
| P8 Gen2 | `P8EG2A74MSB`, `P8EG2A7PE` |
| X10 Gen2 | `X10G2A7E`, `X10G2A7PE`, `X10EG2A7MSB`, `X10G2B7E`, `X10DG2B7E` |
| DS7 Gen2 | `DS7G2A7PE`, `DS7G2A74MS` |
| Z7 Gen2 | `Z7G2A7PE`, `Z7G2A74MS` |

> Don't see your model? Try entering the base name (e.g. `F7`, `S8`) with **Deep Search** enabled.

### Reliable Downloads

- **Resumable** — Uses HTTP Range requests; interrupted downloads pick up exactly where they left off
- **Auto-retry** — Up to 3 retries with exponential backoff (1 s / 2 s / 4 s) on network errors mid-stream
- **Checksum verification** — SHA256 / SHA1 / MD5 auto-detected from hash length and verified before the file is finalised
- **Disk space check** — Warns before starting if the drive doesn't have enough free space
- **File-exists prompt** — Asks before overwriting an existing download (Re-download or Skip)
- **Ctrl+C = pause** — Partial file is kept; next run resumes automatically

### Profiles & History

- **Saved profiles** — Store your model, MCU, resolution, and variant preferences; switch between devices instantly
- **Download history** — Every completed download is logged (model, version, date, file path, timestamp); viewable and clearable from Settings
- **Already-downloaded badge** — Results table shows **✓ DL** next to firmware you have already downloaded

### Results Table

- **Newest-first sorting** — Latest firmware at the top regardless of discovery source
- **Source colour-coding** — `API` (green), `JSON` (cyan), `MIRROR` (yellow), `Redstone` (magenta)
- **Resolution guard** — `✓` / `⚠` / `?` fit indicators; warns before downloading a mismatched resolution
- **Variant detection** — MS / PE / PM platform editions identified automatically

### Settings & UX

- **Full settings menu** — Verbose logging, auto-open-folder toggle, history viewer, open output/config folders, version + update status
- **Auto-update checker** — Background thread checks GitHub on startup; banner shown if a new version is available
- **Open folder after download** — Launches Explorer / Finder / Nautilus automatically (configurable)
- **Cross-platform** — Windows (arrow-key menus via `msvcrt`), Linux, macOS

### Modding Tools *(Advanced / Add-ons)*

- **Firmware Password Finder** — Scans update binaries for hardcoded 32-char hex encryption keys
- **Firmware Repacker** — Converts `system.img` → `system.new.dat.br` + `transfer.list` for custom flashable ZIPs
- **Image Extractor** — Unpacks `system.img`, `vendor.img`, etc. via 7-Zip integration
- **File Inspector** — Identifies every file type (Kernel, Bootloader, Modem, TrustZone) with colour-coded safety ratings
- **OTA Extractor** — Extracts and decompresses Android OTA partition payloads (Brotli)

---

## Installation

**Requirements:** Python 3.9+

```bash
# 1. Clone
git clone https://github.com/Eliminater74/atoto_firmware_downloader.git
cd atoto_firmware_downloader

# 2. Install dependencies
pip install requests rich brotli

# 3. Run
python atoto.py
```

Or download the latest ZIP from [Releases](https://github.com/Eliminater74/atoto_firmware_downloader/releases/latest) — no Git required.

---

## Usage

### Interactive TUI (recommended)

```bash
python atoto.py
```

Main menu options:

| Option | Description |
| ------ | ----------- |
| Quick Search | Search using your saved default profile |
| Deep Search | Same as Quick but with aggressive variant expansion |
| Ad-hoc Search | One-off search — choose model, resolution, MCU, and Deep Search inline |
| Profiles | Create / edit / delete saved device profiles |
| Manual URL Download | Paste a direct link from ATOTO support |
| Settings / Info | Toggle preferences, view history, check for updates |
| Advanced / Add-ons | Modding tools |

### CLI Mode

```bash
# Search by model
python atoto.py --model "F7G2A7XE" --res 1280x720

# Search with MCU version and Deep Search
python atoto.py --model "S8EG2A74MSB" --res 1280x720 --mcu "6315" --deep

# Download a direct URL
python atoto.py --manual "https://atoto-usa.oss-us-west-1.aliyuncs.com/.../firmware.zip"

# Print version and exit
python atoto.py --version
```

### Profile Tips

| Field | Notes |
| ----- | ----- |
| Model | Use your retail SKU (e.g. `F7G2A7XE`) — the tool maps it to internal IDs |
| MCU | Optional. If set and returns no results, the tool retries without it automatically |
| Resolution | `1280x720` for QLED / S8 / F7 PE / X10; `1024x600` for standard 7–10 inch units |
| Variants | `MS` = Mass Series, `PE` = Premium Edition, `PM` = side-key variant; leave `ANY` if unsure |

---

## Modding Guide

### Repack Custom Firmware

1. Extract an official `update.zip`
2. Decompress `system.new.dat.br` → `system.img` (`brotli` + `sdat2img`)
3. Mount and modify `system.img` on Linux (preserves file capabilities)
4. Open **Advanced / Add-ons → Firmware Repacker** — select your `.img` files
5. Replace the originals in the ZIP and flash

> Always match your exact **Model** and **Resolution** before flashing.

---

## Adding Mirror URLs

If ATOTO support sends you a direct download link, you can:

1. Use it immediately via **Manual URL Download**
2. Permanently add it to `atoto_fw/core/discovery/mirrors.py` in `KNOWN_LINKS`:

```python
{
    "match": r"^(F7G2|F7).*$",          # regex matched against your model input
    "title": "F7 Gen2 (SOC5P) — 2023-06-09",
    "url":   "https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/.../F7-SOC5P-230609.zip",
},
```

> **Note on hostnames:** `file.myatoto.com` is a CDN alias for `atoto-usa.oss-us-west-1.aliyuncs.com`.
> Both hostnames serve the same files — the tool normalizes and tries both automatically.
> If support gives you a `file.myatoto.com/…` link it works in Manual URL Download directly.

## Flashing Firmware

1. Download the update ZIP via this tool and extract it on your PC.
2. **Manually format** your USB drive or SD card using **Windows Disk Management** (right-click partition → Quick Format → NTFS or FAT32). Do not rely on the head unit to format the drive — manual prep gives the most reliable result.
3. Copy **all extracted files** to the **root** of the formatted drive (no sub-folders).
4. Insert the drive into the head unit while it is powered on.
5. An update prompt appears automatically — tap **Start**.
6. The update takes ~10 minutes; do not remove the drive or cut power.
7. When complete a confirmation banner appears; remove the drive and the unit restarts.

> **Before flashing:** Check your current build via  
> *Settings → System → About device → MCU Version* (tap MCU Version 4× to reveal the full version string).  
> Compare it to the firmware version — skip if you are already on that build.  
> **A6 Gen2 note:** Beta releases prior to `A6G2A7PF_v1.1.1` (April 2024) had a UUID handling bug causing duplicate music library entries. Always use v1.1.1 or later.

---

## Changelog

### v2.4.0

- **Batch / multi-select downloads** — type `1,3` or `1-3` at the results prompt to queue multiple packages; Windows arrow-key mode gains Space-to-mark and `a`-to-select-all
- **Redstone FOTA multi-version probing** — probes six known `swv` values per session to surface all historical X10 firmware (incremental and full); confirmed POST body from real network capture; [FULL] / [incremental] labels in results; MD5 checksum wired to hash field
- **Expanded model database** — F7 Gen1, F7 10-inch / 11-inch numeric (G209/G210/G211), X10G2B7E / X10DG2B7E (B-variant / DAB), DS7, Z7, F10, P7, A6G2A7PF (all sub-variants), A6 vehicle-fit (TYC/VW/OP), A6 Y-series, regional suffixes `-EU2`/`XED` added to expansion
- **A6G2A7PF mirror** — confirmed direct URL: `ATOTO_A6_PF_7_Inch_OS_240627_APP_240613.zip`
- `file.myatoto.com` CDN alias — same Aliyun OSS bucket; tool normalizes and tries both hostnames for every mirror URL
- Deep Search expanded — DS7, Z7, F7G1, F7G210/211, X10G2B7 added to deep-scan candidate expansion
- Variant filter `None` crash fixed
- Double `[cand]` prefix guard on JSON probe results
- Flashing guide added to README with manual SD format tip and A6 Gen2 UUID bug warning

### v2.3.0

- Download history — every completed download logged; **✓ DL** badge in results table
- Full Settings menu — verbose, auto-open-folder, history viewer, folder shortcuts
- Download retry — up to 3 automatic retries with exponential backoff on network errors
- Thread-safe update checker — module-level lock replaces fragile shared-list pattern
- `--version` and `--mcu` CLI flags
- Source colour-coding in results table (API / JSON / MIRROR / Redstone)
- Profile name validation — empty names rejected
- Open folder after download (auto or prompt); configurable in Settings
- Deep Search toggle inside Ad-hoc Search flow

### v2.2.x

- A6 Gen2, P8 Gen2, X10 Gen2 retail SKU mappings added
- F7 Gen2 GDB6P and SOC5P mirror URLs from ATOTO support
- Redstone FOTA platform map (extensible)
- MCU field in Ad-hoc Search
- Resolution preset menu in profile creation
- Disk space check before download
- Ctrl+C = pause (partial file kept for resume)
- File-exists prompt (skip or overwrite)
- Newest-first result sorting
- JSON probe collects from all endpoints (not just first hit)
- MCU retry fallback — retries API without MCU if no results found with it
- Improved "No results" message with actionable suggestions
- Resume corruption fix — detects when server ignores Range header

### v2.2.2

- Initial v2 release with Deep Search, Profiles, Redstone FOTA, OTA tools

---

## Disclaimer

- **Not affiliated** with ATOTO. Community-built and not official software.
- **Use at your own risk.** Flashing firmware can brick your device. Always match model and resolution exactly.
- **Back up** your original firmware before experimenting.

---

## Contributing

Found a bug? Know a mirror URL? Have a Redstone capture for a new model?
Open an issue or PR on [GitHub](https://github.com/Eliminater74/atoto_firmware_downloader).

**License:** MIT
