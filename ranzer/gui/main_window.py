"""RANZER GUI — Main Window"""

import os
import queue
import tkinter as tk
from datetime import datetime
from ranzer.gui import theme as T

_TEMP = os.environ.get("TEMP", os.environ.get("TMP", os.path.expanduser("~")))
_STATE_FILE = os.path.join(_TEMP, "ranzer_state.json")
_PID_FILE   = os.path.join(_TEMP, "ranzer.pid")
from ranzer.gui.views.home import HomeView
from ranzer.gui.views.dashboard import DashboardView
from ranzer.gui.views.alerts import AlertsView
from ranzer.gui.views.actions import ActionsView


class MainWindow(tk.Toplevel):
    def __init__(self, root, engine, on_back=None):
        super().__init__(root)
        self._root      = root
        self.engine     = engine
        self._on_back   = on_back
        self._event_queue = queue.Queue()
        self._active_nav  = None

        self.title("RANZER – Ransomware Detection")
        self.configure(bg=T.BG)
        self._center(980, 640)
        self.minsize(860, 560)
        self.protocol("WM_DELETE_WINDOW", self._quit)

        self._register_callbacks()
        self._build()
        self._show_view("dashboard")
        self._tick_clock()
        self._poll()

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Engine callbacks ──────────────────────────────────────────────────────
    def _register_callbacks(self):
        _orig_entropy    = self.engine.entropy_monitor.alert_callback
        _orig_honey      = self.engine.honey_file_engine.alert_callback
        _orig_process    = self.engine.process_tracker.alert_callback
        _orig_assessment = self.engine.correlator.auto_action_callback

        def _entropy(e):
            if _orig_entropy:    _orig_entropy(e)
            self._event_queue.put(("entropy", e))

        def _honey(e):
            if _orig_honey:      _orig_honey(e)
            self._event_queue.put(("honey", e))

        def _process(e):
            if _orig_process:    _orig_process(e)
            self._event_queue.put(("process", e))

        def _assessment(a):
            if _orig_assessment: _orig_assessment(a)
            self._event_queue.put(("assessment", a))

        self.engine.entropy_monitor.alert_callback   = _entropy
        self.engine.honey_file_engine.alert_callback = _honey
        self.engine.process_tracker.alert_callback   = _process
        self.engine.correlator.auto_action_callback  = _assessment

        # Escalation popup: HIGH/CRITICAL fires a GUI popup (thread-safe via after)
        self.engine.alert_handler.escalation_callback = (
            lambda sev, msg: self.after(0, self._show_threat_popup, sev, msg)
        )
        # Reset notification state so each new monitoring session starts fresh
        self.engine.alert_handler.reset_notification_state()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        header = tk.Frame(self, bg=T.BLUE, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo_img = T.load_logo(26, 26, T.BLUE)
        if logo_img:
            lbl = tk.Label(header, image=logo_img, bg=T.BLUE)
            lbl.image = logo_img
            lbl.pack(side="left", padx=(16, 8), pady=11)

        tk.Label(header, text="RANZER  –  Ransomware Detection",
                 bg=T.BLUE, fg=T.WHITE,
                 font=(T.FONT_FAMILY, 12, "bold")).pack(side="left", pady=14)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_content(body)
        self._build_statusbar()

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=T.SIDEBAR, width=190)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # Logo in sidebar
        logo_img = T.load_logo(38, 38, T.SIDEBAR)
        if logo_img:
            lbl = tk.Label(sb, image=logo_img, bg=T.SIDEBAR)
            lbl.image = logo_img
            lbl.pack(pady=(18, 4))
        tk.Label(sb, text="RANZER", bg=T.SIDEBAR, fg=T.WHITE,
                 font=(T.FONT_FAMILY, 10, "bold")).pack(pady=(0, 4))
        tk.Frame(sb, bg="#334155", height=1).pack(fill="x", padx=14, pady=(0, 10))

        self._nav_buttons = {}

        def section(label):
            tk.Label(sb, text=label, bg=T.SIDEBAR,
                     fg="#475569", font=(T.FONT_FAMILY, 8, "bold")).pack(
                         anchor="w", padx=16, pady=(10, 4))

        def nav_item(label, key):
            btn = tk.Label(sb, text=f"   {label}", bg=T.SIDEBAR,
                           fg="#94A3B8", font=T.FONT_BODY,
                           cursor="hand2", anchor="w")
            btn.pack(fill="x", ipady=9)
            btn.bind("<Button-1>", lambda e, k=key: self._show_view(k))
            btn.bind("<Enter>", lambda e, b=btn, k=key:
                     b.configure(bg=T.SIDEBAR_ACT if self._active_nav != k else T.SIDEBAR_ACT,
                                 fg=T.WHITE))
            btn.bind("<Leave>", lambda e, b=btn, k=key:
                     b.configure(bg=T.SIDEBAR_ACT if self._active_nav == k else T.SIDEBAR,
                                 fg=T.WHITE if self._active_nav == k else "#94A3B8"))
            self._nav_buttons[key] = btn

        section("MONITORING")
        nav_item("Dashboard",      "dashboard")
        nav_item("Alerts",         "alerts")
        section("ACTIONS")
        nav_item("System Actions", "actions")

        tk.Frame(sb, bg=T.SIDEBAR).pack(fill="both", expand=True)
        tk.Frame(sb, bg="#334155", height=1).pack(fill="x", padx=14, pady=(0, 4))

        quit_lbl = tk.Label(sb, text="   ✕  Stop & Exit",
                            bg=T.SIDEBAR, fg="#475569",
                            font=T.FONT_SMALL, cursor="hand2", anchor="w")
        quit_lbl.pack(fill="x", ipady=9, pady=(0, 8))
        quit_lbl.bind("<Button-1>", lambda e: self._quit())
        quit_lbl.bind("<Enter>", lambda e: quit_lbl.configure(fg="#EF4444"))
        quit_lbl.bind("<Leave>", lambda e: quit_lbl.configure(fg="#475569"))

    def _build_content(self, parent):
        self._content = tk.Frame(parent, bg=T.BG)
        self._content.pack(side="left", fill="both", expand=True)
        self._views = {
            "home":      HomeView(self._content, self),
            "dashboard": DashboardView(self._content, self),
            "alerts":    AlertsView(self._content, self),
            "actions":   ActionsView(self._content, self),
        }
        for v in self._views.values():
            v.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _build_statusbar(self):
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x")
        bar = tk.Frame(self, bg=T.CARD, height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self._status_lbl = tk.Label(bar, text="Ready",
                                    bg=T.CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL)
        self._status_lbl.pack(side="left", padx=14)
        self._clock_lbl = tk.Label(bar, text="",
                                   bg=T.CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL)
        self._clock_lbl.pack(side="right", padx=14)

    # ── Navigation ────────────────────────────────────────────────────────────
    def _show_view(self, key):
        if self._active_nav and self._active_nav in self._nav_buttons:
            self._nav_buttons[self._active_nav].configure(bg=T.SIDEBAR, fg="#94A3B8")
        self._active_nav = key
        if key in self._nav_buttons:
            self._nav_buttons[key].configure(bg=T.SIDEBAR_ACT, fg=T.WHITE)
        target = self._views.get(key) or self._views["dashboard"]
        target.tkraise()
        target.on_show()

    def navigate(self, key):
        self._show_view(key)

    def _tick_clock(self):
        self._clock_lbl.configure(
            text=datetime.now().strftime("%-m/%-d/%Y  %-I:%M:%S %p"))
        self.after(1000, self._tick_clock)

    def update_status(self, text):
        self._status_lbl.configure(text=text)

    def _poll(self):
        try:
            while True:
                kind, event = self._event_queue.get_nowait()
                for v in self._views.values():
                    if hasattr(v, "on_event"):
                        v.on_event(kind, event)
                if kind in ("entropy", "honey", "process"):
                    sev = getattr(event, "severity", "")
                    self._status_lbl.configure(
                        text=f"● {sev} alert detected",
                        fg=T.severity_color(sev))
        except queue.Empty:
            pass
        self.after(400, self._poll)

    def _show_threat_popup(self, severity: str, message: str):
        """Non-blocking threat escalation popup."""
        if severity == "MEDIUM":
            # For MEDIUM just flash the status bar — no intrusive popup
            self._status_lbl.configure(
                text="⚠  Medium threat detected — check Alerts panel",
                fg=T.SEV_MEDIUM)
            return

        is_critical = severity == "CRITICAL"
        bg_color  = "#EF4444" if is_critical else "#F97316"
        body_bg   = "#FEF2F2" if is_critical else "#FFF7ED"
        title_txt = "CRITICAL — TAKE IMMEDIATE ACTION" if is_critical else "HIGH THREAT DETECTED"
        icon_txt  = "🚨" if is_critical else "⚠"

        pop = tk.Toplevel(self)
        pop.title("RANZER Alert")
        pop.configure(bg=body_bg)
        pop.resizable(False, False)
        pop.attributes("-topmost", True)

        w, h = (420, 200) if is_critical else (380, 180)

        # Position: center for CRITICAL, bottom-right for HIGH
        self.update_idletasks()
        sw = pop.winfo_screenwidth()
        sh = pop.winfo_screenheight()
        if is_critical:
            x = (sw - w) // 2
            y = (sh - h) // 2
        else:
            x = sw - w - 24
            y = sh - h - 64
        pop.geometry(f"{w}x{h}+{x}+{y}")

        # Header bar
        hdr = tk.Frame(pop, bg=bg_color, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"  {icon_txt}  {title_txt}",
                 bg=bg_color, fg="#FFFFFF",
                 font=(T.FONT_FAMILY, 11, "bold")).pack(side="left", padx=10, pady=10)

        # Body
        body = tk.Frame(pop, bg=body_bg, padx=18, pady=12)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=message,
                 bg=body_bg, fg="#1E293B",
                 font=(T.FONT_FAMILY, 10),
                 wraplength=340, justify="left").pack(anchor="w")

        # Buttons
        tk.Frame(pop, bg=T.BORDER, height=1).pack(fill="x")
        btn_row = tk.Frame(pop, bg=body_bg, padx=14, pady=10)
        btn_row.pack(fill="x")

        tk.Button(btn_row, text="View Alerts",
                  bg=bg_color, fg="#FFFFFF", relief="flat",
                  font=(T.FONT_FAMILY, 9, "bold"), cursor="hand2",
                  padx=14, pady=5,
                  command=lambda: [self.navigate("alerts"), pop.destroy()]
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="Dismiss",
                  bg=T.CARD, fg=T.TEXT_MUTED, relief="flat",
                  font=(T.FONT_FAMILY, 9), cursor="hand2",
                  padx=14, pady=5,
                  highlightbackground=T.BORDER, highlightthickness=1,
                  command=pop.destroy
                  ).pack(side="left")

        if not is_critical:
            # AUTO-DISMISS after 12 s for HIGH
            countdown_lbl = tk.Label(btn_row, text="(12s)",
                                     bg=body_bg, fg=T.TEXT_MUTED,
                                     font=(T.FONT_FAMILY, 9))
            countdown_lbl.pack(side="right")

            def _countdown(n):
                if not pop.winfo_exists():
                    return
                if n <= 0:
                    pop.destroy()
                    return
                countdown_lbl.configure(text=f"({n}s)")
                pop.after(1000, _countdown, n - 1)

            pop.after(1000, _countdown, 11)

    def stop_engine(self):
        if self.engine.is_running:
            self.engine.stop()
        self.engine.alert_handler.reset_notification_state()
        self._status_lbl.configure(text="Stopped", fg=T.TEXT_MUTED)
        for path in (_STATE_FILE, _PID_FILE):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def _quit(self):
        self.stop_engine()
        if self._on_back:
            self._on_back()
        self.destroy()
