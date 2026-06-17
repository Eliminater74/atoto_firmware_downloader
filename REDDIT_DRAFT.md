# 🚗 I built an open-source tool to unlock, download, and mod ATOTO head unit firmware (v2.4.0)

Hey everyone,

I've been frustrated with the lack of transparency around ATOTO firmware (S8, A6, F7, X10, P8, etc.), so I built a tool to help the community take back control. Whether you're hunting for the right update file or want to peek inside those cryptic `AllAppUpdate.bin` packages, this should help.

**GitHub:** https://github.com/Eliminater74/atoto_firmware_downloader

---

## ⚡ What does it do?

### 1. Multi-Source Firmware Discovery
Official methods only show the single "latest" firmware version for your exact model. This tool aggregates:
- **Dynamic Open Directory Scraper:** Live crawls ATOTO’s central update server directories (like `hcn2000.com`), instantly retrieving firmware files and CAN bus database packages the second they are uploaded.
- **Redstone FOTA Prober:** Queries the Redstone OTA API using smart version sentinels to pull older/historical releases, distinguishing between full factory firmware and incremental packages.
- **Official MyAtoto API & JSON endpoints:** Performs deep scanning in parallel to pull down unlisted, beta, and region-specific builds.

### 2. Massive Model Database (v2.4.0 Update)
We’ve expanded SKU mapping to cover almost the entire ATOTO lineup:
- **S8 & A6 Gen2** (Premium, Mass Series, Y-series, and vehicle-specific fits)
- **X10 Gen2** (Qualcomm SM6225/680 models, including DAB/B-variants)
- **A7 / HN7 / MQ001** (Autochips G36 / MT6765)
- **F7 Gen1 & Gen2** (7", 9", 10", 11" models, and Toyota fitments)
- **DS7, Z7, F10, P7, P8**

### 3. Automated Password Cracker
Ever hit a password prompt when trying to extract `AllAppUpdate.bin`?
- **The Fix:** The tool includes a heuristic scanner that locates the hidden 32-character hex encryption keys buried inside the update binaries (like `lsec6315update`). It finds the key and extracts the files automatically—no guesswork required.

### 4. Repacker & Inspector (For Modders)
- **Firmware Repacker:** Unpack `system.img`, make your changes (root access, debloat, custom layouts), then repack it into a flashable update zip.
- **X-Ray Inspector:** Scans and highlights partition images, letting you know which components are safe to customize and which are critical bootloaders.
- **Batch Downloader:** Queue multiple downloads simultaneously (using range syntax like `1-3` or `1,3`).
- **Legacy Terminal Support:** TUI rewritten to run perfectly on classic Windows Command Prompt/PowerShell without CP1252 encoding crashes.

---

## 🖥️ Getting Started

Works on Windows, Linux, and macOS (requires Python 3.9+).

```
# Clone the repository
git clone https://github.com/Eliminater74/atoto_firmware_downloader.git
cd atoto_firmware_downloader

# Install dependencies
pip install requests rich brotli

# Run the interactive menu
python atoto.py
```

---

## ⚠️ Important Warning
- **Proceed at your own risk.** Flashing custom firmware can brick your device. Always match your model and screen resolution exactly before flashing.
- **Always backup** your current firmware before making changes.
- This is an independent community project and is not affiliated with or endorsed by ATOTO.

I'm actively maintaining this tool. If you discover a new mirror URL, a password pattern, or an unlisted OTA channel, please open an issue on GitHub or drop a comment below.

Happy hacking! 🔧🚗💨
