````markdown
# ⚡ ATOTO Firmware Downloader

A modern, streamlined tool to fetch **ATOTO head-unit firmware** directly from ATOTO’s infrastructure — without fighting the website.

This downloader queries **multiple official sources** (API + JSON indexes) and also checks **known public mirrors**. Everything is merged into a single table with source labels so you can pick and download in one step.

> Works for **most ATOTO models** (S8, A6, F7, P8, etc.) **as long as ATOTO has published firmware** for that model line. If ATOTO doesn’t expose your unit’s firmware online (or it’s gated behind a private/signed link), use **Manual URL** mode.

---

## ✅ Highlights

- **Multi-source discovery:** Official API ➝ JSON index fallbacks ➝ known mirrors (Aliyun “atoto-usa” bucket).
- **Model normalization & mapping:** Retail/device names like `S8EG2A74MSB` or `ATL-S8-HU` are translated to canonical firmware keys (e.g. `S8G2A74MS-S01/-S10`) to improve hits.
- **Shows everything (no filtering):** You see **API / JSON / MIRROR** results together with no duplicates.
- **Resolution awareness:** Adds **Res** (guessed from file/URL) and **Fit** (✓ = likely match, ⚠ = mismatch, ? = unknown). Nothing is hidden; it’s just a heads-up.
- **Resumable downloads:** Can continue after interruption.
- **Optional checksum verification:** If a package publishes a hash.
- **Manual URL mode:** Paste a direct `file.myatoto.com` link (e.g., from ATOTO support).

---

## 🧭 Compatibility

This tool is **not tied to a single SKU**. It will try:
- Retail box codes (e.g., `S8EG2A74MSB`, `S8EG2B74PMB`)
- Canonical models (e.g., `S8G2A74MS-S01`, `S8G2B74PM`)
- Device names shown in About (e.g., `ATL-S8-HU`)
- Family shorthand (e.g., `S8G2A7`, `S8G2B7`)

If ATOTO has published firmware for your model/family and it’s reachable from their API/JSON or mirrors, this script will surface it. If your firmware is only available as a **private signed URL**, use **Manual URL** mode.

---

## 📦 Requirements

- Python **3.9+**
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  # or:
  pip install requests rich
````

**requirements.txt** (suggested):

```txt
requests>=2.31
rich>=13.7
```

---

## 🚀 Quick Start (Interactive)

```bash
python atoto_firmware_downloader.py
```

You’ll be asked for:

* **Product model / device name** (e.g., `S8EG2A74MSB`, `S8G2A7`, `ATL-S8-HU`)
* **MCU version** (optional but can improve API matches)
* **Screen resolution** (defaults to `1280x720`; set `1024x600` if your unit is 600p)

The tool:

1. Normalizes your input into several likely firmware keys.
2. Queries the **official API**, then JSON fallbacks, then **known mirrors**.
3. Merges results into one table (with `Source=API/JSON/MIRROR`, `Res`, `Fit`).
4. Lets you pick a package to download (resumable, optional checksum).

---

## ⚙️ CLI Flags (Convenience)

```bash
# Non-interactive-ish run with your details:
python atoto_firmware_downloader.py --model "S8EG2A74MSB" --mcu "YFEN_53_L6315" --res 1280x720

# Choose output folder:
python atoto_firmware_downloader.py --model "ATL-S8-HU" --out "./downloads"

# Manual URL mode: opens a prompt to paste a direct link (e.g., from ATOTO support)
python atoto_firmware_downloader.py --manual
```

**Available flags**

* `--model`  Retail/device/canonical model string.
* `--mcu`    Optional MCU string (from **About → MCU Version**).
* `--res`    Your screen res for Fit warning (`1280x720` or `1024x600`).
* `--out`    Output directory (default: `ATOTO_Firmware`).
* `--manual` Open Manual URL downloader (paste a direct link).

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
Select # (1):
```

> The **Fit** column never hides results — it just warns (✓/⚠/?) so you don’t flash the wrong resolution by mistake.

---

## 🔭 Where it looks

1. **Official API**
   `https://resources.myatoto.com/atoto-product-ibook/ibMobile/getIbookList`

2. **Official JSON endpoints**
   Several patterns under `…/ibMobile/…` are probed automatically.

3. **Known mirrors** (only listed if reachable; easy to extend)

   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2025/FILE_UPLOAD_URL_2/85129692/6315-SYSTEM20250401-APP20250514.zip`
   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1024x600_system231110_app_231120.zip`
   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1280x720_system231110_app_231120.zip`

Have another working mirror? Add it in `KNOWN_LINKS` (pattern + URL) and it will show up as `Source=MIRROR`.

---

## 📥 Download location

Files are saved to:

```
ATOTO_Firmware/<best-match-model>/<model>_<version>_<original-filename>.zip
```

* Downloads **resume** if interrupted.
* If a **checksum** is provided by ATOTO, it’s verified after download.

---

## 🧰 Updating on the unit (general guidance)

Many ATOTO units accept an **offline USB update**:

1. Format a USB drive **FAT32**; place the **ZIP** at the root (do **not** unzip).
2. Plug into the recommended USB port (often **USB1**).
3. Enter **Factory/Service menu** (varies by model; common code is **3368**).
4. Choose **Update** (e.g., “DVD Update” / “System Update”) and select the ZIP.
5. Keep stable power (engine running or proper 12 V). **Do not** power off mid-update.

> Exact steps differ by model/firmware. Always follow ATOTO’s instructions for your unit.

---

## ⚠️ Safety Notes

* **Match your model & resolution.** Flashing the wrong package can brick your device.
* Keep a **stable 12 V** supply during updates.
* `file.myatoto.com` links may be **time-limited**; use **Manual URL** for those.
* This tool **does not modify** firmware. It just fetches the official packages.

---

## 🛣️ Roadmap

* Extra mirror discovery helpers
* Auto-unpack & USB prep
* Local cache of discovered packages

---

## 🤝 Contributing

PRs welcome!

* Add models to `RETAIL_TO_CANONICAL` to improve normalization.
* Share additional public mirrors that are known-good.

---

## 📜 License

**MIT** — free to use, modify, and share.

```
By: Eliminater74
```
