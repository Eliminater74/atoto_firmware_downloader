# ⚡ ATOTO Firmware Downloader

Fetch official **ATOTO head-unit firmware** from ATOTO’s infrastructure without fighting the website.
The tool probes **multiple official sources** (API + JSON indexes) and curated **public mirrors**, merges everything, and lets you download with resume & optional checksum verify.

> ✅ Works for most ATOTO families (S8, A6, F7, P8, …) **provided ATOTO has published the firmware online**.
> 🔗 If support sends you a private time-limited link, use **Manual URL** mode.

---

## Branches at a glance

| Branch                   | Purpose                                                                                                           | Stability                | Who should use it?                                                             |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------ |
| **main** (a.k.a. master) | Stable, single-file style app focused on download + simple discovery                                              | Highest                  | Regular users who just want to grab firmware reliably                          |
| **beta**                 | Actively developed, **modular** CLI with **profiles, menu UI**, progress status, variant awareness, and packaging | Fast-moving (but tested) | Power users and contributors; anyone who wants the best UX and newest features |

### What’s different in **beta**?

* **Modular package layout** (`atoto_fw/…`), so we can grow (e.g., extractors/add-ons) without turning one file into a hairball.
* **Profiles + Menu UI (Rich TUI)**
  Save multiple head-units with **model**, **MCU**, **resolution**, **variant prefs (MS/PE/PM)**, and **“prefer universal”** toggle. Pick a default and run **Quick Search** in one keystroke.
* **Clear “Universal vs Res-specific” labeling**
  We infer **Res** from filenames/URLs and show **Fit** (✓ likely match, ⚠ mismatch, ? unknown). We also mark “Universal” packages and **prefer them** when you ask us to.
* **Variant awareness & merging**
  If a URL serves the **same package** across **MS/PE/PM**, the table shows combined variants (e.g., `MS,PE`) so users see sharing across model codes (like your `S8G2A7PE` ↔ **MS** case).
* **Live status while searching**
  No more “dead air”: a spinner updates with **API probe → JSON probe N → mirrors**, so you always see progress.
* **Known mirrors included**
  Curated Aliyun `atoto-usa` mirror links (when reachable) appear as `Source=MIRROR`. Easy to extend.
* **Packaging / console entry point**
  Optional `pyproject.toml` with `console_scripts` so users can run `atoto-fw` from anywhere after `pip install -e .`.
* **Verbose logging** (toggle from the Settings panel or with `-v`): helpful for diagnostics.
* **Config separation**
  Config (profiles, defaults, verbosity) is stored in a standard path:

  * Windows: `%APPDATA%\ATOTO_Firmware\config.json`
  * Linux: `~/.config/atoto_fw/config.json`

---

## ✨ Features (beta)

* **Multi-source discovery**

  1. Official API
  2. Official JSON index fallbacks (multiple likely layouts)
  3. **Known mirrors** (only shown if reachable)
* **Model normalization & mapping**
  Retail/device names like `S8EG2A74MSB`, `ATL-S8-HU`, `S8G2A7PE` are expanded to canonical candidates (e.g., `S8G2A74MS-S01/-S10`) to maximize API/JSON hits.
* **Everything visible (no silent filtering)**
  One de-duplicated table with **Source**, **Res**, **Fit**, **Variants**, **Scope (Universal/Res-specific)**.
* **Resumable downloads** with progress bar + **optional checksum verification** (sha256/sha1/md5).
* **Manual URL mode** for private/time-limited ATOTO links.

---

## 📦 Install

> Python **3.9+** recommended.

### Option A — Local, editable install (recommended for beta)

```bash
# from repo root (beta branch)
pip install -e .
```

Now you can run:

```bash
atoto-fw          # console entry
# or
python -m atoto_fw.cli
```

### Option B — Just run the script (no install)

```bash
# classic one-off run
python atoto_firmware_downloader.py
```

### Requirements

```txt
requests>=2.31
rich>=13.7
```

---

## 🚀 Quick start

```bash
atoto-fw
# or
python -m atoto_fw.cli
```

* Create/select a **Profile** (`Model`, optional **MCU**, **Res**, **Variants**, “Prefer Universal”).
* Choose **Quick Search** to probe API → JSON → mirrors with live status.
* Pick a package and download (resume supported).

**Tip:** your model can be any of:

* Retail box code (e.g., `S8EG2A74MSB`, `S8EG2B74PMB`)
* Canonical model (e.g., `S8G2A74MS-S01`, `S8G2B74PM`)
* Device name (`ATL-S8-HU`)
* Family shorthand (`S8G2A7`, `S8G2B7`)

---

## 🧭 CLI flags

```bash
# Typical run
atoto-fw --model "S8EG2A74MSB" --mcu "YFEN_53_L6315" --res 1280x720

# Choose output folder
atoto-fw --model "ATL-S8-HU" --out "./downloads"

# Manual URL mode (paste a direct link)
atoto-fw --manual

# Verbose logs (beta)
atoto-fw -v
```

**Flags**

* `--model`  Model string (retail/device/canonical).
* `--mcu`    Optional MCU string (from **About → MCU Version**).
* `--res`    Screen resolution for Fit check (`1280x720` or `1024x600`).
* `--out`    Output directory (default: `ATOTO_Firmware`).
* `--manual` Open Manual URL downloader.
* `-v/--verbose` Enable debug logging (beta).

---

## 🖥️ What you’ll see

```
Available Packages
────────────────────────────────────────────────────────────────────────────────────────────────────────
#  Src     Title                                       Ver     Date     Size   Res      Scope       Variants  Fit  URL
1  MIRROR  S8 Gen2 (UIS7862 6315) — 2025-04/05         6315…   …        …      1280x720 Universal   MS,PE     ✓    …
2  JSON    [S8G2A74MS] system_20231110_app_20231120…   6315…   …        …      1024x600 Res-specific PM        ⚠    …
…
```

* **Res** and **Fit** help you avoid flashing the wrong screen resolution.
* **Variants** shows MS/PE/PM sharing when a single URL applies to multiple model codes.
* **Scope** highlights **Universal** (not tied to 600p/720p) vs **Res-specific** packages.

---

## 🔭 Sources we probe

1. **Official API**
   `https://resources.myatoto.com/atoto-product-ibook/ibMobile/getIbookList`

2. **Official JSON endpoints**
   Multiple predictable layouts under `…/ibMobile/…` (beta probes a list of candidates and picks the first that responds).

3. **Curated mirrors** *(Aliyun atoto-usa)*
   Shown only when reachable; easily extend `KNOWN_LINKS` to add more.

---

## 📥 Where downloads go

```
ATOTO_Firmware/<best-match-model>/<model>_<version>_<original-filename>.zip
```

* Downloads **resume** if interrupted.
* If a checksum is provided, we verify it after download.

---

## 🧰 Updating on your unit (general guidance)

Most ATOTO units accept **offline USB update**:

1. Format USB **FAT32**, copy the **ZIP** to the root (do **not** unzip).
2. Use the recommended port (commonly **USB1**, the Android Auto/data port).
3. Enter the **Factory/Service menu** (code often **3368**).
4. Choose **Update** and select the ZIP.
5. Ensure **stable power** (engine running / proper 12 V). Don’t power off mid-update.

> Always follow ATOTO’s official instructions for your exact model.

---

## ⚠️ Safety

* **Match your exact model & resolution.** Flashing the wrong one can brick the unit.
* Keep **stable 12 V** during updates.
* `file.myatoto.com` links are often **time-limited** → use **Manual URL** when ATOTO support sends one.
* This tool **does not modify** firmware — it only downloads official packages.

---

## 🗂️ Project layout (beta)

```
atoto_fw/
  cli.py                 # tiny entry wrapper
  ui.py                  # Rich TUI (profiles, menus, tables, progress)
  core/
    __init__.py          # facade re-exports (UI depends on these only)
    assemble.py          # orchestrates discovery & merging
    config.py            # config paths + load/save helpers
    grouping.py          # tag_rows (Res/Scope/Variants/Fit), group_by_url
    http.py              # resilient HTTP session + retries
    utils.py             # helpers: sizes, hashing, url_leaf_name…
    discovery/
      api.py             # official API client
      json_probe.py      # JSON endpoints probing
      mirrors.py         # curated mirror links
      normalize.py       # model normalization & mapping (MS/PE/PM, S01/S10…)
  addons/                # future: extractors, tools (e.g., OTA → .img)
```

> **Why this structure?** It keeps the **UI thin** and the **core reusable**, so we can add features like **firmware extraction** later without destabilizing the downloader.

---

## 🧪 Dev tips

* Toggle logs with `-v` or from the **Settings** menu.
* If packaging for yourself:

  * `pip install -e .` (editable)
  * Console entry becomes `atoto-fw`.
* Nice `.gitignore` adds:

  ```
  ATOTO_Firmware/
  **/__pycache__/
  *.part
  dist/
  build/
  .pytest_cache/
  ```

---

## 🛣️ Roadmap

* Add-on: **OTA extractor** (e.g., `.new.dat.br` ➝ `.img`), with a simple menu.
* Mirror list management (enable/disable, add custom).
* Export results to JSON/CSV for support tickets.
* Smarter “same-family” hints when MS/PE/PM share firmware.

---

## 🤝 Contributing

PRs and issues welcome!

* Add more retail→canonical mappings in `normalize.py`.
* Share known-good public mirrors.
* Bug reports that include **model, MCU, resolution**, and whether the package is **Universal/Res-specific** help a ton.

---

## 📜 License

**MIT** — do what you like, be kind, share improvements.

---

**Repo:** [https://github.com/Eliminater74/atoto\_firmware\_downloader](https://github.com/Eliminater74/atoto_firmware_downloader)
**This file:** for the **beta** branch (the **main** branch README is simpler for stable users).
