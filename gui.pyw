"""One-button GUI: START shrinks the screen and launches CS2, STOP (or quitting CS2) restores it."""
import argparse
import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

import cs2_24inch as core
import displaycfg as dc
import layout

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(HERE, "settings.json")
DEFAULTS = {"size": 24.0, "res": "1280x960", "panel": None, "launch": True, "auto_off": True}
RESOLUTIONS = ["1280x960", "1280x1024", "1440x1080", "1024x768", "1600x1200"]

BG, FG, MUTED = "#16181d", "#e8e8ea", "#8a8f98"
ON_COLOR, OFF_COLOR, STOP_COLOR = "#2fb36b", "#3a3f4a", "#d9534f"


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    if not s["panel"]:
        try:
            paths, _ = dc.query()
            detected = core.edid_diagonal_inches(paths[layout.find_path(paths)])
            s["panel"] = round(detected * 2) / 2 if detected else 27.0
        except (OSError, RuntimeError):
            s["panel"] = 27.0
    return s


class App:
    def __init__(self, root):
        self.root = root
        self.session = None
        s = load_settings()

        root.title("CS2 24-inch")
        root.configure(bg=BG, padx=20, pady=16)
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("TCheckbutton", background=BG, foreground=FG)
        style.map("TCheckbutton", background=[("active", BG)])

        self.status = tk.Label(root, text="OFF", font=("Segoe UI", 22, "bold"), bg=BG, fg=MUTED)
        self.status.grid(row=0, column=0, columnspan=2, pady=(0, 2))
        self.detail = ttk.Label(root, text="Normal screen", style="Muted.TLabel")
        self.detail.grid(row=1, column=0, columnspan=2, pady=(0, 12))

        self.button = tk.Button(root, text="START", font=("Segoe UI", 16, "bold"), width=16, height=2,
                                bg=ON_COLOR, fg="white", activebackground=ON_COLOR,
                                activeforeground="white", relief="flat", cursor="hand2",
                                command=self.toggle)
        self.button.grid(row=2, column=0, columnspan=2, pady=(0, 14))

        self.size = tk.StringVar(value=f"{s['size']:g}")
        self.res = tk.StringVar(value=s["res"])
        self.panel = tk.StringVar(value=f"{s['panel']:g}")
        self.launch = tk.BooleanVar(value=s["launch"])
        self.auto_off = tk.BooleanVar(value=s["auto_off"])

        self.inputs = []
        for row, (label, widget) in enumerate([
            ("Play size (inches)", ttk.Spinbox(root, from_=15, to=40, increment=0.5,
                                               textvariable=self.size, width=10)),
            ("Stretched resolution", ttk.Combobox(root, values=RESOLUTIONS,
                                                  textvariable=self.res, width=10)),
            ("Your monitor (inches)", ttk.Entry(root, textvariable=self.panel, width=12)),
        ], start=3):
            ttk.Label(root, text=label).grid(row=row, column=0, sticky="w", pady=3)
            widget.grid(row=row, column=1, sticky="e", pady=3)
            self.inputs.append(widget)
        for row, (text, var) in enumerate([("Launch CS2 on START", self.launch),
                                           ("Turn off when CS2 closes", self.auto_off)], start=6):
            cb = ttk.Checkbutton(root, text=text, variable=var)
            cb.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
            self.inputs.append(cb)

        reset = tk.Label(root, text="Screen stuck? Restore normal screen", bg=BG, fg=MUTED,
                         font=("Segoe UI", 8, "underline"), cursor="hand2")
        reset.grid(row=8, column=0, columnspan=2, pady=(12, 0))
        reset.bind("<Button-1>", lambda e: self.force_off())

        self.cs2_label = ttk.Label(root, text="", style="Muted.TLabel")
        self.cs2_label.grid(row=9, column=0, columnspan=2, pady=(4, 0))
        self.poll()

    def args(self):
        try:
            size, panel = float(self.size.get()), float(self.panel.get())
            core.parse_res(self.res.get())
        except ValueError:
            raise ValueError("Check the sizes and resolution (e.g. 24, 26.5, 1280x960).")
        return argparse.Namespace(size=size, res=self.res.get().strip(), panel=panel, monitor=None,
                                  launch_timeout=180, exit_grace=15)

    def save_settings(self, a):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"size": a.size, "res": a.res, "panel": a.panel,
                           "launch": self.launch.get(), "auto_off": self.auto_off.get()}, f, indent=2)
        except OSError:
            pass

    def toggle(self):
        if self.session:
            self.stop()
        else:
            self.start()

    def start(self):
        try:
            a = self.args()
            self.save_settings(a)
            session = core.Session(a, launch=self.launch.get())
            session.start()
        except (ValueError, OSError, RuntimeError) as e:
            messagebox.showerror("CS2 24-inch", str(e))
            return
        self.session = session
        w, h = core.parse_res(a.res)
        self.set_ui(True, f"{w}x{h} stretched on a {a.size:g}\" area")

    def stop(self, reason=None):
        if self.session:
            self.session.stop()
            self.session = None
        self.set_ui(False, reason or "Normal screen")

    def force_off(self):
        if self.session:
            self.stop()
        else:
            core.restore()
            self.set_ui(False, "Normal screen restored")

    def set_ui(self, on, detail):
        self.status.config(text="ON" if on else "OFF", fg=ON_COLOR if on else MUTED)
        self.detail.config(text=detail)
        self.button.config(text="STOP" if on else "START",
                           bg=STOP_COLOR if on else ON_COLOR,
                           activebackground=STOP_COLOR if on else ON_COLOR)
        for w in self.inputs:
            w.state(["disabled"] if on else ["!disabled"])

    def poll(self):
        running = core.cs2_running()
        self.cs2_label.config(text="CS2 is running" if running else "CS2 is not running")
        if self.session:
            try:
                event = self.session.tick()
            except (OSError, RuntimeError) as e:
                core.log(f"Watch error: {e}")
                event = None
            if event == "closed" and self.auto_off.get():
                self.stop("CS2 closed - normal screen restored")
            elif event == "timeout":
                self.stop("CS2 did not start - normal screen restored")
            elif event == "closed":
                # Keep the layout; watch for the next CS2 start.
                self.session.cs2_seen = False
                self.session.gone_since = None
            elif self.session.gave_up:
                self.detail.config(text="CS2 keeps resetting it - use Fullscreen Windowed")
        self.root.after(1000, self.poll)

    def on_close(self):
        if self.session:
            self.session.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
