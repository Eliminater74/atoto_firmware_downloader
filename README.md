# ATOTO Firmware Downloader Extravaganza

Behold, weary internet traveler, the ultimate tool to conquer the depths of ATOTO's [CarPlay](https://en.wikipedia.org/wiki/CarPlay) firmware downloads! Born out of sheer frustration with ATOTO's attempt at a website for firmware downloads (no offense, ATOTO, we still love your gadgets), this Python script is your shining armor in the dark.

Seriously, this was the state of affairs:
![atoto firmware download website screenshot](./docs/atoto-website-screenshot.png)

Fear no more! With our ATOTO Firmware Downloader, you'll be downloading firmware like a pro, bypassing the labyrinth that is the ATOTO download site with the grace of a gazelle.

## Getting This Show on the Road

Dare to embark on this quest? Here's how to wield this mighty script:

### 1. Conjure Up a Virtual Environment

First, clone this repository to your local mage tower. Then, cast the following incantation in the terminal within the project's sacred grounds:

```bash
virtualenv .venv
source .venv/bin/activate  # On macOS and Linux
.venv\Scripts\activate  # On Windows
```

### 2. Install the Arcane Scrolls (`requirements.txt`)

With your environment shielded from the chaos of dependency conflicts, install the required artifacts:

```bash
pip install -r requirements.txt
```

### 3. Unleash the Power

With the preparations complete, you may now unleash the magic:

```bash
python atoto_firmware_downloader.py
```

A mystical interface shall appear, guiding you through the sacred selection of firmware. Choose wisely.
