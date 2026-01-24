# Pro Video Trimmer 🎬

A simple and powerful tool for lightning-fast video trimming across all formats with zero quality loss (no re-encoding).

[![Latest Release](https://img.shields.io/github/v/release/olexandr-klymenko/VideoCutter?label=Download%20Latest&color=green)](https://github.com/olexandr-klymenko/VideoCutter/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features
- **Instant Trimming:** Leverages FFmpeg power to cut segments without re-rendering (Stream Copy).
- **User-Friendly UI:** Built with Python (Tkinter) for maximum performance and native feel.
- **Automatic Updates:** Automatically checks for new versions via GitHub API on startup.
- **Full Installer:** Easy Windows installation process powered by Inno Setup.

## 🚀 Download
You can always download the latest version of the installer here:
👉 **[Download Installer (.exe)](https://github.com/olexandr-klymenko/VideoCutter/releases/latest)**

---

## 🛠 Development and Build

### 1. Requirements
- Python 3.12+
- Git Bash (for running automation scripts)
- Inno Setup 6 (for creating local installers)

### 2. Installation
- git clone https://github.com/olexandr-klymenko/VideoCutter.git
- cd VideoCutter
- pip install -r requirements.txt

### 3. Release Automation (CI/CD)
The project uses a multi-stage validation process before each release:

1. Validation: The `check_configs.py` script verifies encoding and version presence in all critical files.
2. Local check (Dry Run): Run `./release.sh --dry-run`. This builds the project locally into the `Output/` folder without making any Git changes.
3. Full release: Run `./release.sh`. This automatically updates tags and publishes the code.

---

## 📂 Project Structure
- `main.py` — application logic and GUI.
- `version.txt` — single source of truth for the version used across all scripts.
- `main.spec` — PyInstaller build configuration.
- `setup_script.iss` — Inno Setup packaging script.
- `check_configs.py` — pre-build validation script.
- `release.sh` — main automation script.

## 📝 License
Distributed under the MIT License. See the LICENSE file for details.

---
Developed by Olexandr Klymenko (https://github.com/olexandr-klymenko)
