"""
EntryBox Quick Drop — a small native window for dropping entries fast.

Click the shortcut (quickdrop.bat) and a compact window opens: pick a project,
type a title, hit Enter. Drop as many as you like; Esc or the close button
shuts the window. Click the shortcut again to reopen.

Native Tkinter (no browser engine, no GPU) so it stays responsive over Remote
Desktop. Stdlib only — no pip dependencies. Talks to the running EntryBox
server over its REST API.

Run it:  quickdrop.bat
"""
import os
import json
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

import tkinter as tk
from tkinter import ttk

HERE = Path(__file__).resolve().parent
HOST = os.environ.get("ENTRYBOX_BIND", "127.0.0.1").replace("0.0.0.0", "127.0.0.1")
PORT = os.environ.get("ENTRYBOX_PORT", "3859")
BASE_URL = f"http://{HOST}:{PORT}"
STATE_FILE = HERE / ".quickdrop_state.json"
TYPES = ["idea", "fix", "improve", "docs", "roadmap"]

# Palette (matches EntryBox dark theme).
BG = "#0f1117"
SURFACE = "#1e222b"
BORDER = "#2a2f3a"
ACCENT = "#3b9eff"
ACCENT_FG = "#06121f"
TEXT = "#e6e8ec"
TEXT2 = "#8b93a1"
ERR = "#ff6b6b"
OK = "#6bcb77"


# ── REST helpers (stdlib only) ────────────────────────────────────────────────
def _request(method, path, body=None, timeout=5):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode() or "{}")


def server_up(timeout=1.5):
    try:
        status, _ = _request("GET", "/health", timeout=timeout)
        return status == 200
    except Exception:
        return False


def fetch_projects():
    _, data = _request("GET", "/api/projects")
    return [p for p in data.get("projects", []) if p.get("status") != "unreachable"]


def create_entry(project_id, title, body, type_):
    return _request("POST", f"/api/projects/{project_id}/entries",
                    {"title": title, "body": body, "type": type_})


# ── small state file (remember last project) ──────────────────────────────────
def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def save_state(d):
    try:
        STATE_FILE.write_text(json.dumps(d))
    except Exception:
        pass


class QuickDrop:
    def __init__(self):
        self.projects = []
        self.root = tk.Tk()
        self.root.title("EntryBox · Quick Drop")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self._center(440, 430)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self._build_styles()
        self._build_ui()

        self.root.after(50, self.refresh_projects)

    # layout helpers --------------------------------------------------------
    def _center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 3
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("EB.TCombobox",
                        fieldbackground=SURFACE, background=SURFACE,
                        foreground=TEXT, arrowcolor=TEXT2, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, relief="flat",
                        padding=5)
        style.map("EB.TCombobox",
                  fieldbackground=[("readonly", SURFACE)],
                  selectbackground=[("readonly", SURFACE)],
                  selectforeground=[("readonly", TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", SURFACE)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", ACCENT_FG)

    def _label(self, parent, text):
        return tk.Label(parent, text=text, bg=BG, fg=TEXT2,
                        font=("Segoe UI", 8, "bold"), anchor="w")

    # build UI --------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 16}

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", pady=(14, 10), **pad)
        tk.Label(header, text="●", bg=BG, fg=ACCENT, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(header, text="  Quick Drop", bg=BG, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(header, text="Enter to send · Esc to close", bg=BG, fg=TEXT2,
                 font=("Segoe UI", 8)).pack(side="right")

        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", **pad)
        # project
        pcol = tk.Frame(row, bg=BG)
        pcol.pack(side="left", fill="x", expand=True)
        self._label(pcol, "PROJECT").pack(fill="x")
        self.project_var = tk.StringVar()
        self.project_cb = ttk.Combobox(pcol, textvariable=self.project_var,
                                       state="readonly", style="EB.TCombobox",
                                       font=("Segoe UI", 10))
        self.project_cb.pack(fill="x", pady=(4, 0))
        # type
        tcol = tk.Frame(row, bg=BG, width=120)
        tcol.pack(side="left", padx=(10, 0))
        self._label(tcol, "TYPE").pack(fill="x")
        self.type_var = tk.StringVar(value="idea")
        self.type_cb = ttk.Combobox(tcol, textvariable=self.type_var, values=TYPES,
                                    state="readonly", style="EB.TCombobox",
                                    width=10, font=("Segoe UI", 10))
        self.type_cb.pack(fill="x", pady=(4, 0))

        tframe = tk.Frame(self.root, bg=BG)
        tframe.pack(fill="x", pady=(12, 0), **pad)
        self._label(tframe, "TITLE").pack(fill="x")
        self.title_entry = tk.Entry(tframe, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                                    relief="flat", font=("Segoe UI", 11),
                                    highlightthickness=1, highlightbackground=BORDER,
                                    highlightcolor=ACCENT)
        self.title_entry.pack(fill="x", ipady=6, pady=(4, 0))
        self.title_entry.bind("<Return>", lambda e: self.submit())

        bframe = tk.Frame(self.root, bg=BG)
        bframe.pack(fill="both", expand=True, pady=(12, 0), **pad)
        self._label(bframe, "NOTE (OPTIONAL)").pack(fill="x")
        self.body_text = tk.Text(bframe, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                                 relief="flat", font=("Segoe UI", 10), height=4,
                                 highlightthickness=1, highlightbackground=BORDER,
                                 highlightcolor=ACCENT, wrap="word", padx=8, pady=6)
        self.body_text.pack(fill="both", expand=True, pady=(4, 0))
        self.body_text.bind("<Control-Return>", lambda e: self.submit())

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", pady=14, **pad)
        self.status = tk.Label(footer, text="", bg=BG, fg=TEXT2, font=("Segoe UI", 9))
        self.status.pack(side="left")
        self.submit_btn = tk.Button(footer, text="Drop it", command=self.submit,
                                    bg=ACCENT, fg=ACCENT_FG, relief="flat",
                                    font=("Segoe UI", 10, "bold"), padx=18, pady=6,
                                    activebackground=ACCENT, activeforeground=ACCENT_FG,
                                    cursor="hand2", bd=0)
        self.submit_btn.pack(side="right")
        self.start_btn = tk.Button(footer, text="Start server", command=self.start_server,
                                   bg=ACCENT, fg=ACCENT_FG, relief="flat",
                                   font=("Segoe UI", 10, "bold"), padx=18, pady=6,
                                   activebackground=ACCENT, activeforeground=ACCENT_FG,
                                   cursor="hand2", bd=0)
        # start_btn shown only when server is down (see _set_offline)

    # status helpers --------------------------------------------------------
    def set_status(self, text, color=TEXT2):
        self.status.config(text=text, fg=color)

    def _set_offline(self, offline):
        if offline:
            self.submit_btn.pack_forget()
            self.start_btn.pack(side="right")
            self.project_cb.config(values=[])
            self.project_var.set("Server not running")
            self.set_status("EntryBox server is down", ERR)
        else:
            self.start_btn.pack_forget()
            self.submit_btn.pack(side="right")

    # threading helper ------------------------------------------------------
    def _bg(self, fn, on_done):
        def run():
            try:
                res, err = fn(), None
            except Exception as e:
                res, err = None, e
            self.root.after(0, lambda: on_done(res, err))
        threading.Thread(target=run, daemon=True).start()

    # actions ---------------------------------------------------------------
    def refresh_projects(self):
        self.set_status("Connecting…")
        self._bg(fetch_projects, self._on_projects)

    def _on_projects(self, projects, err):
        if err is not None:
            self._set_offline(True)
            return
        self._set_offline(False)
        self.projects = projects
        if not projects:
            self.project_cb.config(values=[])
            self.project_var.set("No projects — register one in EntryBox")
            self.submit_btn.config(state="disabled")
            self.set_status("No registered projects", TEXT2)
            return
        self.submit_btn.config(state="normal")
        labels = [f"{p['name']} · {p['prefix']}" for p in projects]
        self.project_cb.config(values=labels)
        last = load_state().get("last_project")
        idx = next((i for i, p in enumerate(projects) if p["id"] == last), 0)
        self.project_cb.current(idx)
        self.set_status("")
        self.title_entry.focus_set()

    def start_server(self):
        try:
            subprocess.Popen('start "EntryBox Server" cmd /k run.bat',
                             cwd=str(HERE), shell=True)
        except Exception as e:
            self.set_status(f"Launch failed: {e}", ERR)
            return
        self.start_btn.config(state="disabled")
        self.set_status("Starting server…")
        self._poll_for_server(40)

    def _poll_for_server(self, tries_left):
        def check():
            return server_up()
        def done(up, err):
            if up:
                self.start_btn.config(state="normal")
                self.refresh_projects()
            elif tries_left > 0:
                self.root.after(1000, lambda: self._poll_for_server(tries_left - 1))
            else:
                self.start_btn.config(state="normal")
                self.set_status("Server didn't start — check the console", ERR)
        self._bg(check, done)

    def _selected_project(self):
        i = self.project_cb.current()
        if 0 <= i < len(self.projects):
            return self.projects[i]
        return None

    def submit(self):
        project = self._selected_project()
        title = self.title_entry.get().strip()
        if not project:
            self.set_status("No project selected", ERR)
            return
        if not title:
            self.set_status("Title required", ERR)
            self.title_entry.focus_set()
            return
        body = self.body_text.get("1.0", "end").strip()
        type_ = self.type_var.get()
        self.submit_btn.config(state="disabled")
        self.set_status("Saving…")

        def post():
            return create_entry(project["id"], title, body, type_)

        def done(res, err):
            self.submit_btn.config(state="normal")
            if err is not None:
                msg = getattr(err, "reason", None) or str(err)
                self.set_status(f"Failed: {msg}", ERR)
                return
            status, data = res
            if status >= 400 or data.get("error"):
                self.set_status(f"Failed: {data.get('error', status)}", ERR)
                return
            save_state({"last_project": project["id"]})
            self.set_status(f"{data.get('id', 'entry')} dropped ✓", OK)
            self.title_entry.delete(0, "end")
            self.body_text.delete("1.0", "end")
            self.title_entry.focus_set()

        self._bg(post, done)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    QuickDrop().run()
