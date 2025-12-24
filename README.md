# ⚡ ATOTO Firmware Downloader & Modding Toolkit (v2)

![Visitor Count](https://hits.sh/github.com/Eliminater74/atoto_firmware_downloader.svg?style=flat-square&label=Views&extraCount=2000)


A powerful, open-source utility to **find, download, and modify** firmware for ATOTO head units (S8, A6, F7, P8, etc.).

> **🚀 v2 Released!**: Complete rewrite with Deep Search, Password Cracker, and Firmware Repacker.

---

## 🔥 Features

### 1. Firmware Discovery
*   **Deep Search**: Probes the official ATOTO API, JSON endpoints, and curated public mirrors (including the US Aliyun bucket).
*   **Smart Matching**: Automatically handles model variations (e.g., `S8EG2A74MSB` vs `S8G2A7`) and MCU versions.
*   **Resolution Safety**: Clearly marks packages as **Universal** or **Res-Specific** (1024x600 vs 1280x720) to prevent bricking.
*   **Live Status**: Real-time spinner showing exactly what sources are being probed.

### 2. Modding Tools (New!)
Located in the **Advanced / Add-ons** menu:
*   **Firmware Repacker**:
    *   Converts `system.img` (Ext4) → `system.new.dat.br` (Brotli).
    *   Generates the correct `transfer.list` and `patch.dat`.
    *   *Auto-updates* dynamic partition metadata.
    *   **Goal**: Create custom flashable `update.zip` packages.
*   **Image Extractor**:
    *   Deep integration with **7-Zip**.
    *   Extracts contents of `system.img`, `vendor.img`, etc. to a folder.
    *   Great for inspecting APKs, configs, or drivers.
    *   *Note: On Windows, use for inspection only (permissions are not preserved).*
*   **File Inspector**:
    *   "X-Ray" vision for firmware folders.
    *   Identifies every file type: **Kernel**, **Bootloader** (Dangerous), **Modem**, **TrustZone**, **Partition Data**.
    *   Color-coded safety guide (Red = Raw Hardware Binary, Blue = Repackable Partition).
*   **Firmware Password Finder**:
    *   **Automated Cracking**: Scans update binaries (e.g., `lsec6315update`) for hardcoded encryption keys.
    *   **Targeted Unlocking**: Automatically attempts to unlock encrypted archives like `AllAppUpdate.bin`.
    *   **Smart Heuristics**: Detects 32-character hex keys used in ATOTO's update process.
    *   **Outcome**: Successfully recovers hidden APKs and libs from password-protected firmware containers.

### 3. Cross-Platform
*   **Windows**: Native support (uses `msvcrt` for menus, bundled/system 7-Zip).
*   **Linux**: Native support (uses `xdg-open` for folders, `7z`/`p7zip` for extraction).
*   **macOS**: Native support.

---

## 📦 Installation

**Requirements**: Python 3.9+

```bash
# 1. Clone the repository (and checkout beta)
git clone https://github.com/Eliminater74/atoto_firmware_downloader.git
cd atoto_firmware_downloader
git checkout beta

# 2. Install dependencies
pip install requests rich brotli

# 3. Run the tool
python atoto.py
```

---

## 🖥️ Usage

### Interactive Mode (Recommended)
Just run `python atoto.py` to enter the TUI (Text User Interface).

*   **Quick Search**: Uses your saved profile to find updates instantly.
*   **Profiles**: Save your Head Unit details (Model: `S8G2A74MS`, MCU: `YFEN_53...`, Res: `1280x720`).
*   **Manual URL**: Paste a direct `file.myatoto.com` link (useful if Support sends you a private link).
*   **Advanced / Add-ons**: Access the **Repacker**, **Extractor**, and **Inspector**.

### CLI Mode (Automation)
You can also run search commands directly:

```bash
# Search for S8 Gen 2 firmware
python atoto.py --model "S8EG2A74MSB" --res 1280x720

# Download from a specific URL
python atoto.py --manual "https://file.myatoto.com/..."
```

---

## 🛠️ Modding Guide

### How to Repack Firmware
1.  **Extract** an official `update.zip`.
2.  **Unpack** `system.new.dat.br` to `system.img` (using existing tools like `brotli` + `sdat2img`).
3.  **Mount & Modify** `system.img` (Add Apps, Root, Debloat).
    *   *Crucial*: Perform this on **Linux** to preserve file capabilities/permissions.
4.  **Repack**:
    *   Open `atoto.py` -> **Advanced / Add-ons** -> **Firmware Repacker**.
    *   Select your modified `.img` files.
    *   The tool will generate fresh `.new.dat.br`, `.transfer.list`, and update the partition map.
5.  **Zip & Flash**: Replace the files in the original zip and flash!

### Warning on Windows
Windows filesystems (NTFS) do not support Linux permissions (chmod/chown/capabilities).
*   **Safe**: Extracting images to *look* at files.
*   **Unsafe**: Modifying and repacking images on Windows to flash back to the device. (Result: Bootloop).
*   **Solution**: Use WSL (Windows Subsystem for Linux) or a Linux VM for the actual modification step.

---

## ⚠️ Disclaimer

*   **Not Affiliated**: This project is community-built and not official ATOTO software.
*   **Use at Your Own Risk**: Flashing firmware (especially custom/repacked ones) carries the risk of bricking your device. Always match your exact **Model** and **Resolution**.
*   **Backup**: Save your original firmware before experimenting.

---

## 🤝 Contributing

Found a bug? Know a new mirror?
Open an issue or PR on [GitHub](https://github.com/Eliminater74/atoto_firmware_downloader).

**License**: MIT
