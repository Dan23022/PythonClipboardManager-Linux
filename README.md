# GTK Keylogger Utility (Python + GTK 3)

A lightweight keylogger utility built using Python and GTK 3, with support for encryption using Fernet (symmetric encryption). This tool leverages native Linux GUI components (via PyGObject) and captures keyboard input at the system level.

---

## ✨ Features

- 🔐 **Encrypted Keylogging**: Securely stores logged keystrokes using the `cryptography` library (Fernet symmetric encryption).
- 🧵 **Multithreaded Design**: Logging and GUI components run concurrently using Python's `threading`.
- 🎛️ **GTK 3 GUI**: Built with the GTK 3 framework via `PyGObject`, allowing a native-feeling GUI on Linux desktops.
- ⌨️ **System-wide Key Capture**: Uses `pynput` to capture all keyboard activity across applications.
- 📦 **Lightweight & Minimal**: Only a few dependencies, focused on simplicity and clarity.

---

## 📦 Requirements

### Python Packages (can be installed via pip):

```bash
pip install -r requirements.txt
