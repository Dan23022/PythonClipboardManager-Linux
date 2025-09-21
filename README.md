# 🖋️ GTK Clipboard Manager Utility (Python + GTK 3)

A lightweight, encrypted clipboard manager built using Python and GTK 3. This utility monitors your clipboard for changes and securely logs clipboard contents using Fernet symmetric encryption. The application features a clean GTK 3 interface, built with PyGObject, and runs on most Linux systems with minimal dependencies.

---

## ✨ Features

- 🔐 **Encrypted Clipboard Logging**  
  Securely stores copied clipboard text using the `cryptography` library (Fernet encryption).
  
- 🧵 **Multithreaded Design**  
  Clipboard monitoring and the GTK GUI run concurrently using Python’s `threading` module for smooth performance.

- 🖼️ **GTK 3 GUI**  
  Built with PyGObject for native GTK integration on Linux desktops.

- 📋 **Clipboard Monitoring**  
  Automatically detects clipboard changes and logs new entries.

- 📦 **Minimal & Lightweight**  
  Few dependencies, no bloat — easy to deploy and run on any Linux machine.

---

## 📦 Requirements

### ✅ Python Packages

Install via pip:

```bash
pip install -r requirements.txt
