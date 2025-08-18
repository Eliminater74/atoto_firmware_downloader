# ⚡ ATOTO Firmware Downloader

A modern, streamlined tool for downloading **ATOTO CarPlay/Android Auto firmware** directly from ATOTO’s servers — without fighting their clunky website.

This script automatically **probes ATOTO’s API and JSON endpoints** for your head unit’s model, lists available firmware packages in a clean interactive table, and lets you download with a single keypress.

---

## ✨ Features

✅ **API + JSON probing** – Finds firmware even if one method fails
✅ **Interactive console UI** – Rich tables, ASCII logo, and color-coded output
✅ **Direct download links** – No more endless clicking through ATOTO’s site
✅ **Model-based detection** – Enter your unit’s model and get matching firmware
✅ **Error handling** – Falls back gracefully if packages aren’t found
✅ **Windows + Linux + macOS support** – Works anywhere Python runs

---

## 📦 Requirements

* Python **3.9+**
* `pip install -r requirements.txt`

The script uses:

* [`requests`](https://pypi.org/project/requests/) – for HTTP requests
* [`rich`](https://pypi.org/project/rich/) – for the pretty console UI

---

## 🚀 Usage

1. Clone this repo:

```bash
git clone https://github.com/Eliminater74/atoto_firmware_downloader.git
cd atoto_firmware_downloader
```

2. (Optional) Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the script:

```bash
python atoto_firmware_downloader.py
```

---

## 🖥️ Example Run

```text
╔════════════════════════════════════╗
║              ATOTO                 ║
╚════════════════════════════════════╝
Available Packages (API)
─────────────────────────────────────
 #   Title        Version  Date   Size   URL
─────────────────────────────────────
 1   S8G2103M...  20       None   None   https://file.myatoto.com/...
─────────────────────────────────────
Select # (1):
```

---

## ⚠️ Notes

* If no packages are found, double-check your unit’s **About → Model Number**.
* Some ATOTO models have firmware hosted only under certain “Gen” lines.
* This script does **not modify** firmware files — it only fetches official packages.

---

## 🛠️ Roadmap

* [ ] Add checksum verification after download
* [ ] Auto-extract `.zip` updates
* [ ] Cache probed results for offline reference

---

## 🤝 Contributing

Pull requests welcome! If you’ve tested this script with different ATOTO models, please share results.

---

## 📜 License

MIT — free to use, modify, and share.
