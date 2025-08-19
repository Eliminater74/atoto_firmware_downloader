# ⚡ ATOTO Firmware Downloader

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Eliminater74/atoto_firmware_downloader.svg?style=social)](https://github.com/Eliminater74/atoto_firmware_downloader/stargazers)
![Repo visits (simple)](https://visitor-badge.laobi.icu/badge?page_id=Eliminater74.atoto_firmware_downloader)
![Daily views](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Eliminater74/atoto_firmware_downloader/main/.github/badges/daily.json)
![Total views](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Eliminater74/atoto_firmware_downloader/main/.github/badges/total.json)

A modern, streamlined tool to fetch **ATOTO head-unit firmware** directly from ATOTO’s infrastructure — without fighting the website.

The downloader queries **multiple official sources** (API + JSON indexes) and also checks **known public mirrors**. Everything is merged into a single table with source labels so you can pick and download in one step.

> ✅ Works for **most ATOTO models** (S8, A6, F7, P8, etc.) **as long as ATOTO has published firmware online** for that model line.  
> 🔗 If your unit’s firmware is only available via a **private/signed link**, use **Manual URL** mode.

---

## ✨ Highlights

- **Multi-source discovery** → Official API ➝ JSON index fallbacks ➝ known mirrors (Aliyun *atoto-usa* bucket).
- **Model normalization & mapping** → Retail/device names like `S8EG2A74MSB` or `ATL-S8-HU` are translated to canonical keys (e.g., `S8G2A74MS-S01/-S10`) to improve hits.
- **Shows everything (no filtering)** → One table with `Source=API / JSON / MIRROR`, de-duplicated.
- **Resolution awareness** → Adds **Res** (guessed from file/URL) and **Fit** (✓ likely match, ⚠ mismatch, ? unknown). Nothing is hidden—just a heads-up.
- **Resumable downloads** + optional **checksum verification**.
- **Manual URL mode** → Paste a direct `file.myatoto.com` link (e.g., from ATOTO support).

---

## 🧭 Compatibility

Enter **any** of the following—the tool will try the right firmware keys:

- Retail box codes (e.g., `S8EG2A74MSB`, `S8EG2B74PMB`)
- Canonical models (e.g., `S8G2A74MS-S01`, `S8G2B74PM`)
- Device names shown in *About* (e.g., `ATL-S8-HU`)
- Family shorthand (e.g., `S8G2A7`, `S8G2B7`)

If ATOTO exposes firmware for your model/family via their API/JSON or public mirrors, the script will surface it. If your package is **only** a private signed URL, use **Manual URL**.

---

## 📦 Requirements

- Python **3.9+**
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  # or:
  pip install requests rich

**requirements.txt**

```txt
requests>=2.31
rich>=13.7
```

---

## 🚀 Quick Start (interactive)

```bash
python atoto_firmware_downloader.py
```

You’ll be asked for:

* **Product model / device name** (e.g., `S8EG2A74MSB`, `S8G2A7`, `ATL-S8-HU`)
* **MCU version** (optional but can improve API matches)
* **Screen resolution** (defaults to `1280x720`; use `1024x600` if your unit is 600p)

The tool:

1. Normalizes your input into several likely firmware keys.
2. Queries the **official API**, then JSON fallbacks, then **known mirrors**.
3. Merges results into one table (`Source`, `Res`, `Fit`).
4. Lets you pick a package to download (resumable; optional checksum).

---

## ⚙️ CLI flags (convenience)

```bash
# Typical run
python atoto_firmware_downloader.py --model "S8EG2A74MSB" --mcu "YFEN_53_L6315" --res 1280x720

# Choose output folder
python atoto_firmware_downloader.py --model "ATL-S8-HU" --out "./downloads"

# Manual URL mode (paste a direct link)
python atoto_firmware_downloader.py --manual
```

**Flags**

* `--model`  Model string (retail/device/canonical).
* `--mcu`    Optional MCU string (from **About → MCU Version**).
* `--res`    Screen resolution for Fit check (`1280x720` or `1024x600`).
* `--out`    Output directory (default: `ATOTO_Firmware`).
* `--manual` Open Manual URL downloader.

---

## 🖥️ Example (table view)

```
Available Packages
──────────────────────────────────────────────────────────────────────────────────────────────
#  Source  Title                                                Version   Res      Fit  URL
1  API     [S8G2A74MS-S01] 6315-SYSTEM20250401-APP20250514.zip  6315…     1280x720 ✓    …
2  JSON    [S8G2A74MS] system_20231110_app_20231120.zip         6315…     1024x600 ⚠    …
3  MIRROR  [mirror] S8 Gen2 (UIS7862 6315) — 2025-04/05         6315…     1280x720 ✓    …
4  MIRROR  [mirror] S8 Gen2 (1024×600) — 2023-11/20             6315…     1024x600 ⚠    …
──────────────────────────────────────────────────────────────────────────────────────────────
```

> **Fit** is advisory (✓/⚠/?) so you don’t flash the wrong resolution.

---

## 🔭 Where it looks

1. **Official API**
   `https://resources.myatoto.com/atoto-product-ibook/ibMobile/getIbookList`
2. **Official JSON endpoints**
   Several patterns under `…/ibMobile/…` are probed automatically.
3. **Known mirrors** *(listed only if reachable; easy to extend)*

   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2025/FILE_UPLOAD_URL_2/85129692/6315-SYSTEM20250401-APP20250514.zip`
   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1024x600_system231110_app_231120.zip`
   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1280x720_system231110_app_231120.zip`

Have another working mirror? Add it in `KNOWN_LINKS` (pattern + URL) and it’ll show up as `Source=MIRROR`.

---

## 📥 Download location

Files are saved to:

```
ATOTO_Firmware/<best-match-model>/<model>_<version>_<original-filename>.zip
```

* Downloads **resume** if interrupted.
* If ATOTO publishes a **checksum**, it’s verified after download.

---

## 🧰 Updating on the unit (general guidance)

Many ATOTO units accept an **offline USB update**:

1. Format a USB drive **FAT32**; place the **ZIP** at the root (do **not** unzip).
2. Plug into the recommended USB port (often **USB1**, the Android Auto/data port).
3. Enter the **Factory/Service menu** (varies by model; common code is **3368**).
4. Choose **Update** (e.g., “DVD/System Update”) and select the ZIP.
5. Keep stable power (engine running / proper 12 V). **Do not** power off mid-update.

> Follow ATOTO’s instructions for your specific model/firmware.

---

## ⚠️ Safety notes

* **Match your exact model & resolution.** Flashing the wrong package can brick your device.
* Keep a **stable 12 V** during updates.
* `file.myatoto.com` links are often **time-limited**; use **Manual URL** when ATOTO support sends one.
* This tool **does not modify** firmware; it only downloads official packages.

---


## 🤝 Contributing

PRs welcome!

* Add models to `RETAIL_TO_CANONICAL` to improve normalization.
* Share additional public mirrors that are known-good.
* Bug reports with your model + MCU + resolution help everyone.

---

## 📜 License

**MIT** — free to use, modify, and share.

---

**Repo:** [https://github.com/Eliminater74/atoto\_firmware\_downloader](https://github.com/Eliminater74/atoto_firmware_downloader)
By: **Eliminater74**

```
::contentReference[oaicite:0]{index=0}
```
