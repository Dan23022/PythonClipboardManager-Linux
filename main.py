import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango
import cairo

import subprocess
import threading
import time
from pynput import keyboard
import os
import json
from cryptography.fernet import Fernet

# ========== Encryption Setup ==========

KEY_FILE = os.path.expanduser("~/.clipboard_manager_key")
DATA_FILE = os.path.expanduser("~/.clipboard_manager_data")


def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def load_key():
    if not os.path.exists(KEY_FILE):
        return generate_key()
    with open(KEY_FILE, "rb") as f:
        return f.read()


def encrypt_data(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode())


def decrypt_data(token, key):
    f = Fernet(key)
    return f.decrypt(token).decode()


# ========== Clipboard Storage ==========

MAX_HISTORY = 30
# clipboard_history stores dicts: {'text': str, 'pinned': bool}
clipboard_history = []
last_clipboard = ""

key = load_key()


def save_history():
    try:
        data = json.dumps(clipboard_history)
        encrypted = encrypt_data(data, key)
        with open(DATA_FILE, "wb") as f:
            f.write(encrypted)
    except Exception as e:
        print("Error saving clipboard history:", e)


def load_history():
    global clipboard_history
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "rb") as f:
                encrypted = f.read()
            decrypted = decrypt_data(encrypted, key)
            clipboard_history = json.loads(decrypted)

            # Fix any entries that are plain strings (old format)
            clipboard_history = [
                entry if isinstance(entry, dict) else {'text': entry, 'pinned': False}
                for entry in clipboard_history
            ]

            print("Loaded clipboard history:", clipboard_history)
        except Exception as e:
            print("Error loading clipboard history:", e)
            clipboard_history = []


# ========== Clipboard Handling ==========

def get_clipboard():
    try:
        return subprocess.run(['xclip', '-selection', 'clipboard', '-o'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              text=True).stdout.strip()
    except Exception:
        return ""


def set_clipboard(text):
    subprocess.run(['xclip', '-selection', 'clipboard'], input=text, text=True)


def clipboard_monitor():
    global last_clipboard
    while True:
        current = get_clipboard()
        if current and current != last_clipboard:
            if not any(entry['text'] == current for entry in clipboard_history if isinstance(entry, dict)):
                clipboard_history.append({'text': current, 'pinned': False})
                # Remove oldest unpinned if over max
                while len(clipboard_history) > MAX_HISTORY:
                    # Remove the oldest unpinned
                    for i, entry in enumerate(clipboard_history):
                        if not entry['pinned']:
                            clipboard_history.pop(i)
                            break
                    else:
                        # All pinned, stop removing
                        break
                save_history()
            last_clipboard = current
        time.sleep(0.5)


# ========== GUI ==========

class ClipboardWindow(Gtk.Window):
    def __init__(self, history):
        Gtk.Window.__init__(self, title="Clipboard Manager")

        # Remove window decorations (title bar, borders)
        self.set_decorated(True)

        # Enable transparency and rounded corners
        self.set_app_paintable(True)
        screen = self.get_screen()
        rgba_visual = screen.get_rgba_visual()
        if rgba_visual is not None and screen.is_composited():
            self.set_visual(rgba_visual)

        self.connect("draw", self.on_draw)

        self.set_size_request(300, 500)

        geometry = Gdk.Geometry()
        geometry.min_width = 300
        geometry.max_width = 300
        geometry.min_height = 500
        geometry.max_height = 500

        self.set_geometry_hints(
            None,
            geometry,
            Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE
        )

        self.set_resizable(False)

        # Connect map event to move window after it's shown
        self.connect("map", self.on_map)

        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)

        self.apply_css()

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Fix scrolled window size
        scrolled.set_min_content_width(125)
        scrolled.set_min_content_height(500)
        scrolled.set_size_request(125, 500)

        scrolled.add(self.vbox)
        self.add(scrolled)

        # Fix vbox width, let height expand naturally
        self.vbox.set_size_request(125, -1)

        self.history = history
        self.buttons = []  # to keep refs for later update

        self.menu_open = False  # Track if context menu is open

        self.populate_buttons()

        self.connect("delete-event", self.on_close)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("key-press-event", self.on_key_press)

        self.set_opacity(0)  # Start fully transparent
        self.fade_in()

    def on_draw(self, widget, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        radius = 12

        # Clear everything (fully transparent)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Draw rounded rectangle path
        def rounded_rect(cr, x, y, w, h, r):
            cr.new_sub_path()
            cr.arc(x + w - r, y + r, r, -90 * (3.14159 / 180), 0)
            cr.arc(x + w - r, y + h - r, r, 0, 90 * (3.14159 / 180))
            cr.arc(x + r, y + h - r, r, 90 * (3.14159 / 180), 180 * (3.14159 / 180))
            cr.arc(x + r, y + r, r, 180 * (3.14159 / 180), 270 * (3.14159 / 180))
            cr.close_path()

        rounded_rect(cr, 0, 0, width, height, radius)

        # Fill with background color and fully opaque alpha
        cr.set_source_rgba(0.1176, 0.1176, 0.1843, 1)  # #1e1e2f
        cr.fill_preserve()

        # Optional: add a border if you want
        # cr.set_source_rgba(0.3, 0.3, 0.5, 0.8)
        # cr.set_line_width(2)
        # cr.stroke()

        return False

    def on_map(self, widget):
        self.move_to_bottom_right()

    def populate_buttons(self):
        # Clear existing buttons
        for btn in self.buttons:
            self.vbox.remove(btn)
        self.buttons.clear()

        # Sort pinned first, then unpinned, latest at top
        sorted_history = sorted(self.history, key=lambda e: (not e['pinned'], self.history.index(e)), reverse=True)

        for entry in sorted_history:
            text = entry['text']
            display_text = text[:80] + ("..." if len(text) > 80 else "")
            button = Gtk.Button()
            label = Gtk.Label(label=display_text)
            label.set_line_wrap(True)  # enable wrapping
            label.set_max_width_chars(15)  # approx 15 chars width, adjust as needed
            label.set_ellipsize(Pango.EllipsizeMode.END)  # optionally add ellipsis
            label.set_xalign(0)  # left align
            label.set_hexpand(True)  # expand label horizontally inside button

            button.add(label)
            button.set_halign(Gtk.Align.FILL)
            button.set_valign(Gtk.Align.CENTER)
            button.set_hexpand(False)  # prevent button from stretching horizontally

            button.set_halign(Gtk.Align.FILL)
            button.set_valign(Gtk.Align.CENTER)
            button.set_hexpand(True)
            button.get_style_context().add_class("clipboard-button")
            if entry['pinned']:
                button.get_style_context().add_class("pinned")
            button.connect("clicked", self.on_item_clicked, entry)

            # Right-click menu setup
            button.connect("button-press-event", self.on_right_click, entry)

            self.vbox.pack_start(button, False, False, 0)
            self.buttons.append(button)

        self.show_all()

    def on_item_clicked(self, button, entry):
        set_clipboard(entry['text'])
        self.hide()

    def on_right_click(self, widget, event, entry):
        if event.button == 3:  # Right click
            menu = Gtk.Menu()

            pin_label = "Unpin" if entry['pinned'] else "Pin"
            pin_item = Gtk.MenuItem(label=pin_label)
            pin_item.connect("activate", self.toggle_pin, entry)
            menu.append(pin_item)

            remove_item = Gtk.MenuItem(label="Remove")
            remove_item.connect("activate", self.remove_entry, entry)
            menu.append(remove_item)

            menu.show_all()

            self.menu_open = True  # mark menu open

            def on_menu_done(menu):
                self.menu_open = False  # reset flag when menu closes

            menu.connect("selection-done", on_menu_done)

            menu.popup_at_pointer(event)
            return True  # stop propagation
        return False

    def toggle_pin(self, menuitem, entry):
        entry['pinned'] = not entry['pinned']
        save_history()
        self.populate_buttons()

    def remove_entry(self, menuitem, entry):
        if entry in self.history:
            self.history.remove(entry)
            save_history()
            self.populate_buttons()

    def move_to_bottom_right(self):
        screen = self.get_screen()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_workarea(monitor)

        width, height = self.get_size()
        x = geometry.x + geometry.width - width - 20  # 20 px margin from right
        y = geometry.y + geometry.height - height - 50  # 50 px margin from bottom
        self.move(x, y)

    def apply_css(self):

        css = b"""
        window {
            background-color: #1e1e2f;
            color: #ffffff;
            border-radius: 12px;
        }
        .clipboard-button {
            background-color: #2e2e3e;
            color: #ffffff;
            font: 14px 'Sans';
            padding: 10px;
            border-radius: 8px;
            margin: 4px 0;
        }
        .clipboard-button:hover {
            background-color: #3e3e5e;
        }
        .clipboard-button.pinned {
            background-color: #5a5a7a;
            font-weight: bold;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_close(self, *args):
        self.hide()
        return True

    def on_focus_out(self, widget, event):
        if not self.menu_open:
            self.hide()
        return False

    def on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == "Escape":
            self.hide()
            return True
        return False

    def fade_in(self):
        self.opacity = 0

        def increase_opacity():
            self.opacity += 0.05
            if self.opacity >= 1:
                self.set_opacity(1)
                return False
            self.set_opacity(self.opacity)
            return True

        GLib.timeout_add(30, increase_opacity)  # ~30ms steps


# ========== Hotkey Listener ==========

gui_window = None  # global window reference


def show_clipboard_gui():
    global gui_window
    if gui_window and Gtk.Widget.get_visible(gui_window):
        GLib.idle_add(gui_window.present)
    else:
        def create_and_show():
            global gui_window
            gui_window = ClipboardWindow(clipboard_history)
            gui_window.show_all()

        GLib.idle_add(create_and_show)


def start_hotkey_listener():
    COMBO = {keyboard.Key.cmd, keyboard.KeyCode.from_char('v')}
    current_keys = set()

    def on_press(key):
        current_keys.add(key)
        if COMBO.issubset(current_keys):
            threading.Thread(target=show_clipboard_gui).start()

    def on_release(key):
        if key in current_keys:
            current_keys.remove(key)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


# ========== Main ==========

if __name__ == "__main__":
    print("📋 Clipboard Manager started. Press Super + V to open.")

    load_history()

    threading.Thread(target=clipboard_monitor, daemon=True).start()

    threading.Thread(target=Gtk.main, daemon=True).start()

    start_hotkey_listener()