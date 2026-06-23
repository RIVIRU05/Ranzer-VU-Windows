"""RANZER GUI — Setup Window"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from ranzer.gui import theme as T


class SetupWindow(tk.Toplevel):
    def __init__(self, root, advanced=False, prefill_dirs=None, on_back=None):
        super().__init__(root)
        self._root       = root
        self._advanced   = advanced
        self._on_back    = on_back
        self._checked_dirs  = set(prefill_dirs or [])
        self._honey_var     = tk.BooleanVar(value=True)
        self._threshold_var = tk.DoubleVar(value=7.5)
        self._auto_term_var = tk.BooleanVar(value=True)

        self.title("RANZER – Setup")
        self.configure(bg=T.BG)
        self._center(840, 580)
        self.protocol("WM_DELETE_WINDOW", self._back)
        self._apply_styles()
        self._build()
        if prefill_dirs:
            self._refresh_status()

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _apply_styles(self):
        s = ttk.Style()
        s.configure("Setup.Treeview",
                    background=T.CARD, foreground=T.TEXT,
                    fieldbackground=T.CARD, rowheight=24, font=T.FONT_BODY)
        s.configure("Setup.Treeview.Heading",
                    background=T.CARD2, foreground=T.TEXT_MUTED,
                    font=(T.FONT_FAMILY, 9, "bold"))
        s.map("Setup.Treeview", background=[("selected", T.BLUE)])

    def _build(self):
        header = tk.Frame(self, bg=T.BLUE, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo_img = T.load_logo(28, 28, T.BLUE)
        if logo_img:
            lbl = tk.Label(header, image=logo_img, bg=T.BLUE)
            lbl.image = logo_img
            lbl.pack(side="left", padx=(16, 8), pady=12)

        tk.Label(header, text="RANZER  –  Setup",
                 bg=T.BLUE, fg=T.WHITE,
                 font=(T.FONT_FAMILY, 12, "bold")).pack(side="left", pady=15)

        pane = tk.Frame(self, bg=T.BG)
        pane.pack(fill="both", expand=True)
        self._build_left(pane)
        self._build_right(pane)

        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x")
        bottom = tk.Frame(self, bg=T.CARD, padx=16, pady=10)
        bottom.pack(fill="x")

        tk.Button(bottom, text="← Back",
                  bg=T.CARD, fg=T.TEXT_MUTED, relief="flat",
                  font=T.FONT_BODY, cursor="hand2",
                  activebackground=T.CARD2, activeforeground=T.TEXT,
                  command=self._back).pack(side="left")

        self._start_btn = tk.Button(
            bottom, text="Start Monitoring  (0 directories)",
            bg=T.BLUE, fg=T.WHITE, relief="flat",
            font=(T.FONT_FAMILY, 10, "bold"), cursor="hand2",
            padx=18, pady=7,
            activebackground=T.BLUE_DARK, activeforeground=T.WHITE,
            command=self._launch)
        self._start_btn.pack(side="right")
        self._refresh_status()

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=T.CARD, width=268,
                        highlightbackground=T.BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(12, 0), pady=12)
        left.pack_propagate(False)

        tk.Label(left, text="Directory Monitoring",
                 bg=T.CARD, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 11, "bold")).pack(anchor="w", padx=14, pady=(14, 4))

        tk.Checkbutton(left, text="Enable Honey Files",
                       variable=self._honey_var,
                       bg=T.CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL,
                       activebackground=T.CARD, selectcolor=T.CARD).pack(
                           anchor="w", padx=14, pady=(0, 2))
        tk.Checkbutton(left, text="Auto-Terminate threats",
                       variable=self._auto_term_var,
                       bg=T.CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL,
                       activebackground=T.CARD, selectcolor=T.CARD).pack(
                           anchor="w", padx=14, pady=(0, 8))

        tk.Frame(left, bg=T.BORDER, height=1).pack(fill="x", padx=8)

        tree_frame = tk.Frame(left, bg=T.CARD)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        self._tree = ttk.Treeview(tree_frame, yscrollcommand=vsb.set,
                                  selectmode="none", show="tree",
                                  style="Setup.Treeview")
        self._tree.pack(fill="both", expand=True)
        vsb.config(command=self._tree.yview)

        self._tree.tag_configure("checked",   foreground=T.BLUE)
        self._tree.tag_configure("unchecked", foreground=T.TEXT)
        self._tree.bind("<Button-1>", self._on_tree_click)
        self._tree.tag_bind("unchecked", "<<TreeviewOpen>>", self._on_expand)
        self._tree.tag_bind("checked",   "<<TreeviewOpen>>", self._on_expand)
        self._populate_tree()

        if self._advanced:
            adv = tk.Frame(left, bg=T.CARD2, padx=14, pady=10)
            adv.pack(fill="x")
            tk.Frame(adv, bg=T.BORDER, height=1).pack(fill="x", pady=(0, 8))
            tk.Label(adv, text="Entropy Threshold",
                     bg=T.CARD2, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(anchor="w")
            tk.Scale(adv, variable=self._threshold_var, from_=6.0, to=8.0,
                     resolution=0.1, orient="horizontal",
                     bg=T.CARD2, fg=T.TEXT, highlightthickness=0,
                     troughcolor=T.BORDER, sliderrelief="flat",
                     activebackground=T.BLUE).pack(fill="x")

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=T.BG)
        right.pack(side="left", fill="both", expand=True, padx=20, pady=12)

        centre = tk.Frame(right, bg=T.BG)
        centre.place(relx=0.5, rely=0.44, anchor="center")

        logo_img = T.load_logo(84, 84, T.BG)
        if logo_img:
            lbl = tk.Label(centre, image=logo_img, bg=T.BG)
            lbl.image = logo_img
            lbl.pack(pady=(0, 14))
        else:
            canvas = tk.Canvas(centre, width=70, height=70,
                               bg=T.BG, highlightthickness=0)
            canvas.pack(pady=(0, 14))
            canvas.create_oval(2, 2, 68, 68, fill=T.BLUE, outline="")
            canvas.create_text(35, 35, text="R", fill=T.WHITE,
                               font=(T.FONT_FAMILY, 26, "bold"))

        tk.Label(centre, text="RANZER",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 20, "bold")).pack()
        tk.Label(centre, text="Endpoint Defense System",
                 bg=T.BG, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(pady=(2, 20))

        tk.Label(centre, text="Ready to Monitor",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 13, "bold")).pack()
        tk.Label(centre,
                 text="Select directories from the left panel\nand click Start to begin monitoring",
                 bg=T.BG, fg=T.TEXT_MUTED, font=T.FONT_BODY,
                 justify="center").pack(pady=(6, 24))

        tk.Button(centre, text="▶  Start Monitoring",
                  bg=T.BLUE, fg=T.WHITE, relief="flat",
                  font=(T.FONT_FAMILY, 11, "bold"), cursor="hand2",
                  padx=32, pady=11,
                  activebackground=T.BLUE_DARK, activeforeground=T.WHITE,
                  command=self._launch).pack(fill="x")

        tk.Label(centre,
                 text="Tip: Enable honey files to deploy decoys\nthat detect unauthorised access attempts",
                 bg=T.BG, fg=T.TEXT_MUTED, font=T.FONT_SMALL,
                 justify="center").pack(pady=(16, 0))

    # ── Tree ──────────────────────────────────────────────────────────────────
    def _populate_tree(self):
        home = os.path.expanduser("~")
        self._insert_dir("", home, label=f"~ (Home)  {home}")
        for d in ["/tmp", "/var/tmp"]:
            if os.path.isdir(d):
                self._insert_dir("", d)

    def _insert_dir(self, parent, path, label=None):
        tag    = "checked" if path in self._checked_dirs else "unchecked"
        prefix = "☑  " if path in self._checked_dirs else "☐  "
        iid = self._tree.insert(parent, "end",
                                text=prefix + (label or os.path.basename(path) or path),
                                values=[path], tags=(tag,), open=False)
        try:
            children = [
                os.path.join(path, d)
                for d in sorted(os.listdir(path))
                if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")
            ][:30]
            if children:
                self._tree.insert(iid, "end", text="…", values=["__placeholder__"])
        except PermissionError:
            pass
        return iid

    def _on_expand(self, event):
        iid = self._tree.focus()
        if not iid:
            return
        children = self._tree.get_children(iid)
        if len(children) == 1 and self._tree.item(children[0], "values") == ("__placeholder__",):
            self._tree.delete(children[0])
            path = self._tree.item(iid, "values")[0]
            try:
                for d in sorted(os.listdir(path)):
                    full = os.path.join(path, d)
                    if os.path.isdir(full) and not d.startswith("."):
                        self._insert_dir(iid, full)
            except PermissionError:
                pass

    def _on_tree_click(self, event):
        # Skip only when the expand/collapse arrow itself was clicked
        if "indicator" in self._tree.identify_element(event.x, event.y):
            return
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        vals = self._tree.item(iid, "values")
        if not vals or vals[0] == "__placeholder__":
            return
        path = vals[0]
        if path in self._checked_dirs:
            self._checked_dirs.discard(path)
            self._tree.item(iid, text="☐  " + (os.path.basename(path) or path),
                            tags=("unchecked",))
        else:
            self._checked_dirs.add(path)
            self._tree.item(iid, text="☑  " + (os.path.basename(path) or path),
                            tags=("checked",))
        self._refresh_status()

    def _refresh_status(self):
        n = len(self._checked_dirs)
        self._start_btn.configure(
            text=f"Start Monitoring  ({n} {'directory' if n == 1 else 'directories'})")

    # ── Launch ────────────────────────────────────────────────────────────────
    def _launch(self):
        dirs = [d for d in self._checked_dirs if os.path.isdir(d)]
        if not dirs:
            messagebox.showwarning("No Directories",
                                   "Please select at least one directory to monitor.",
                                   parent=self)
            return
        from ranzer.core import RanzerEngine, RanzerConfig
        from ranzer.gui.main_window import MainWindow
        config = RanzerConfig(
            monitored_dirs=dirs,
            entropy_threshold=self._threshold_var.get(),
            enable_honey_files=self._honey_var.get(),
            enable_auto_terminate=self._auto_term_var.get(),
            enable_desktop_alerts=False,
        )
        engine = RanzerEngine(config)
        self.withdraw()
        MainWindow(self._root, engine=engine, on_back=self._show)
        engine.start()
        self._write_state(dirs, engine.config)

    @staticmethod
    def _write_state(dirs: list, config):
        import json
        from datetime import datetime
        state = {
            "pid": os.getpid(),
            "mode": "gui",
            "start_time": datetime.now().isoformat(),
            "dirs": dirs,
            "entropy_threshold": config.entropy_threshold,
            "honey_files": config.enable_honey_files,
            "auto_terminate": config.enable_auto_terminate,
            "log_dir": config.log_dir,   # engine resolves this to absolute on init
        }
        try:
            with open("/tmp/ranzer_state.json", "w") as f:
                json.dump(state, f)
        except OSError:
            pass

    def _show(self):
        self.deiconify()

    def _back(self):
        if self._on_back:
            self._on_back()
        self.destroy()
