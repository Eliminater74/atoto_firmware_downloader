````markdown
# ⚡ ATOTO Firmware Downloader

A modern, streamlined tool for downloading **ATOTO firmware** straight from ATOTO’s infrastructure—without fighting their website.

The downloader **queries multiple official sources** (API + JSON endpoints) and also checks a set of **known public mirrors**. Results are merged into one clean table so you can download with a single keypress.

---

## ✨ What’s new

- **Multi-source discovery:** Queries ATOTO’s API *and* JSON indexes, then falls back to **known mirrors** (Aliyun / atoto-usa bucket).
- **Model normalization & mapping:** Retail names like `S8EG2A74MSB` or device names like `ATL-S8-HU` are auto-translated to canonical firmware models (e.g., `S8G2A74MS-S01 / -S10`).
- **“Did you mean…?” suggestions:** One-key retry with near matches.
- **Manual URL mode:** Paste a direct (signed) `file.myatoto.com` link from support and download it.
- **Resumable downloads:** Interrupted? Re-run and it continues.
- **Optional checksum verify:** If a hash is published, it’s verified after download.
- **De-dupe + Source labels:** One table showing `Source=API / JSON / MIRROR`, without duplicates.

---

## 📦 Requirements

- Python **3.9+**
- Install deps:

```bash
pip install -r requirements.txt
# (or) pip install requests rich
````

---

## 🚀 Usage

### Quick start (interactive)

```bash
python atoto_firmware_downloader.py
```

You’ll be asked for:

* **Product model / device name** (e.g., `S8EG2A74MSB`, `S8G2A7`, `S8G2B7`, or `ATL-S8-HU`)
* **MCU version** (optional, improves API matching)

### CLI flags (non-interactive convenience)

```bash
# Provide a model and (optionally) an MCU string from About → MCU Version
python atoto_firmware_downloader.py --model "S8EG2A74MSB" --mcu "YFEN_53_L6315"

# Paste a direct signed link (e.g., from support)
python atoto_firmware_downloader.py --manual "https://file.myatoto.com/…/package.zip"

# Show the normalized candidates the tool will try
python atoto_firmware_downloader.py --model "ATL-S8-HU" --list-candidates
```

> Tip: On many S8 Gen2 UIS7862 units the About page shows something like
> `MCU Version: … YFEN_53_L6315 …` — the tool uses that to pick the right track.

---

## 🖥️ Example run

```
╔════════════════════════════════════╗
║               ATOTO                ║
╚════════════════════════════════════╝

Available Packages
────────────────────────────────────────────────────────────────────────────
#  Source  Title                                               Version  URL
1  API     [S8G2A74MS-S01] 6315-SYSTEM20250401-APP20250514.zip 6315-    …
2  JSON    [S8G2A74MS]      system_20231110_app_20231120.zip   6315_…   …
3  MIRROR  [mirror] S8 Gen2 (UIS7862 6315) — 2025-04/05       6315-    …
4  MIRROR  [mirror] S8 Gen2 (1024×600) — 2023-11/20           6315_1024 …
────────────────────────────────────────────────────────────────────────────
Select # (1):
```

---

## 🔭 Sources the tool checks

1. **Official API**

   * `https://resources.myatoto.com/atoto-product-ibook/ibMobile/getIbookList`
2. **Official JSON endpoints** (several patterns under `…/ibMobile/...`)
3. **Known mirrors** (HEAD-checked before listing):

   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2025/FILE_UPLOAD_URL_2/85129692/6315-SYSTEM20250401-APP20250514.zip`
   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1024x600_system231110_app_231120.zip`
   * `https://atoto-usa.oss-us-west-1.aliyuncs.com/2023/FILE_UPLOAD_URL_2/03850677/6315_1280x720_system231110_app_231120.zip`

> Have another working link? Add it to `KNOWN_LINKS` in the script and it’ll appear under `Source=MIRROR`.

---

## 🧭 Model input tips

You can enter **any** of these and the tool will try the right firmware keys:

* Retail box codes (e.g., `S8EG2A74MSB`, `S8EG2B74PMB`)
* Canonical models (e.g., `S8G2A74MS-S01`, `S8G2B74PM`)
* Device names shown in About (e.g., `ATL-S8-HU`)
* Family shorthand (`S8G2A7`, `S8G2B7`)

It expands variants like `-S01 / -S10 / -S01W / -S10W` automatically and tries them all.

---

## 📥 Where the file goes

Downloads are saved under:

```
ATOTO_Firmware/<best-match-model>/<model>_<version>_<original-filename>.zip
```

Downloads resume if interrupted. If a checksum is published by ATOTO, it’s verified afterward.

---

## ⚠️ Safety notes

* **Always match your exact model.** Flashing the wrong package can brick your unit.
* **Keep the engine running / stable 12 V** during updates; do **not** power-cycle mid-flash.
* **file.myatoto.com** links are often **signed** and can expire—use **Manual URL** mode if support sends you one.
* This tool **does not modify** firmware. It just fetches official packages.

---

## 🛠️ Roadmap

* [ ] Extra mirror discovery helpers
* [ ] Auto-unpack & USB prep
* [ ] Local cache of discovered packages

---

## 🤝 Contributing

PRs welcome! Share models you’ve confirmed and any additional public mirrors.
If you spot a model that normalizes poorly, add it to `RETAIL_TO_CANONICAL`.

---

## 📜 License

MIT — free to use, modify, and share.

```

