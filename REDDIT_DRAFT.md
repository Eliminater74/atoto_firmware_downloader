# ⚡ The Ultimate ATOTO Firmware Toolkit (v2 Beta) is here!

Hey everyone,

I've been working hard on a powerful open-source tool to help the community take control of their ATOTO head units (S8, A6, F7, P8, etc.). If you've ever struggled to find the right update file or wanted to see what's actually inside those mysterious `AllAppUpdate.bin` files, this is for you.

**GitHub Link:** [https://github.com/Eliminater74/atoto_firmware_downloader](https://github.com/Eliminater74/atoto_firmware_downloader)

---

## 🔥 What's New in v2?

We just pushed a massive update to **v2** with some game-changing features:

### 🕵️‍♂️ 1. Deep Search Mode
The "Quick Search" finds official releases, but **Deep Search** goes further.
*   **Finds Hidden Firmware:** It actively probes ATOTO's servers for unlisted versions.
*   **Beta & Debug Support:** Automatically checks for `_BETA`, `-TEST`, and `-DEBUG` variants. If there's a test build for your unit potentially fixing that one annoying bug, this tool tries to find it.
*   **Smart Probing:** Uses intelligent heuristics to scan Aliyun mirrors directly.

### 🔓 2. Automated Password Cracker
Ever tried to unzip `AllAppUpdate.bin` only to find it password protected?
*   **The Fix:** I've built a heuristic scanning engine that finds the hidden 32-character hex keys used by the update binary (`lsec6315update`).
*   **One-Click Unlock:** It automatically finds the key and extracts the files for you. No more guessing.

### 📦 3. Repacker & Inspector
For the modders out there:
*   **Firmware Repacker:** Unpack `system.img`, make your mods (root, debloat), and repack it into a flashable `update.zip`.
*   **X-Ray Inspector:** Instantly see which files are safe to touch and which are dangerous bootloaders.

---

## 🖥️ How to Use It

It's a Python tool that runs on **Windows**, **Linux**, and **macOS**.

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/Eliminater74/atoto_firmware_downloader.git
    cd atoto_firmware_downloader
    ```
2.  **Run it:**
    ```bash
    python atoto.py
    ```
3.  **Enjoy:** use the interactive menu to search, download, and mod.

---

## ⚠️ Disclaimer
*   **Use at your own risk.** Flashing custom firmware can brick your device.
*   **Always backup** your current firmware if possible.
*   This is a community tool, not official ATOTO software.

---

Let me know what you find! I'm actively adding new mirrors and features. If you find a new password or a weird firmware location, drop a comment or open an issue on GitHub.

Happy Hacking! 🚗💨
