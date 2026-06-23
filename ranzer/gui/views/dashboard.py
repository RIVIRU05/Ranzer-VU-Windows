"""RANZER GUI — Dashboard View"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from ranzer.gui import theme as T


class DashboardView(tk.Frame):
    def __init__(self, parent, main_win):
        super().__init__(parent, bg=T.BG)
        self._main = main_win
        self._apply_styles()
        self._build()
        self.after(500, self._refresh)

    def _apply_styles(self):
        s = ttk.Style()
        s.configure("Dash.Treeview",
                    background=T.CARD, foreground=T.TEXT,
                    fieldbackground=T.CARD, rowheight=30,
                    font=T.FONT_BODY)
        s.configure("Dash.Treeview.Heading",
                    background=T.CARD2, foreground=T.TEXT_MUTED,
                    font=(T.FONT_FAMILY, 9, "bold"))
        s.map("Dash.Treeview", background=[("selected", T.BLUE_GLOW)])
        s.layout("Dash.Treeview", [("Dash.Treeview.treearea", {"sticky": "nswe"})])

    def _build(self):
        # Title bar
        top = tk.Frame(self, bg=T.BG, padx=24, pady=18)
        top.pack(fill="x")
        tk.Label(top, text="Monitoring Dashboard",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 15, "bold")).pack(side="left")
        self._status_badge = tk.Label(top, text="● Active",
                                      bg=T.BG, fg=T.GREEN,
                                      font=(T.FONT_FAMILY, 10, "bold"))
        self._status_badge.pack(side="right")

        # Stat cards
        cards_row = tk.Frame(self, bg=T.BG, padx=24)
        cards_row.pack(fill="x", pady=(0, 20))
        self._card_critical = self._stat_card(cards_row, "Critical Alerts", "0", T.SEV_CRITICAL)
        self._card_total    = self._stat_card(cards_row, "Total Alerts",    "0", T.TEXT)
        self._card_status   = self._stat_card(cards_row, "Status",      "Active", T.GREEN)

        # Last 5 alerts table
        mid = tk.Frame(self, bg=T.BG, padx=24)
        mid.pack(fill="both", expand=True)

        hdr = tk.Frame(mid, bg=T.BG)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="Last 5 Alert Events",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 11, "bold")).pack(side="left")
        view_all = tk.Label(hdr, text="View All →",
                            bg=T.BG, fg=T.BLUE,
                            font=T.FONT_BODY, cursor="hand2")
        view_all.pack(side="right")
        view_all.bind("<Button-1>", lambda e: self._main.navigate("alerts"))

        cols = ("Severity", "Type", "Process", "Description", "Time")
        self._tree = ttk.Treeview(mid, columns=cols, show="headings",
                                  style="Dash.Treeview", height=5)
        widths = {"Severity": 90, "Type": 80, "Process": 120,
                  "Description": 280, "Time": 90}
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=widths[c], anchor="w",
                              stretch=(c == "Description"))
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("CRITICAL", foreground=T.SEV_CRITICAL)
        self._tree.tag_configure("HIGH",     foreground=T.SEV_HIGH)
        self._tree.tag_configure("MEDIUM",   foreground=T.SEV_MEDIUM)
        self._tree.tag_configure("LOW",      foreground=T.SEV_LOW)

        # Buttons
        btn_row = tk.Frame(self, bg=T.BG, padx=24, pady=16)
        btn_row.pack(fill="x")

        self._stop_btn = tk.Button(
            btn_row, text="Stop Monitoring",
            bg=T.RED_BTN, fg=T.WHITE, relief="flat",
            font=(T.FONT_FAMILY, 10, "bold"), cursor="hand2",
            padx=18, pady=8,
            activebackground="#B91C1C", activeforeground=T.WHITE,
            command=self._toggle_monitoring)
        self._stop_btn.pack(side="left", padx=(0, 12))

        tk.Button(btn_row, text="View All Alerts",
                  bg=T.BLUE, fg=T.WHITE, relief="flat",
                  font=(T.FONT_FAMILY, 10, "bold"), cursor="hand2",
                  padx=18, pady=8,
                  activebackground=T.BLUE_DARK, activeforeground=T.WHITE,
                  command=lambda: self._main.navigate("alerts")).pack(side="left")

    def _stat_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg=T.CARD,
                        highlightbackground=T.BORDER, highlightthickness=1,
                        padx=20, pady=16)
        card.pack(side="left", fill="both", expand=True, padx=(0, 14))
        tk.Label(card, text=label, bg=T.CARD, fg=T.TEXT_MUTED,
                 font=T.FONT_SMALL).pack(anchor="w")
        val_lbl = tk.Label(card, text=value, bg=T.CARD, fg=color,
                           font=(T.FONT_FAMILY, 24, "bold"))
        val_lbl.pack(anchor="w", pady=(4, 0))
        return val_lbl

    def _refresh(self):
        try:
            engine  = self._main.engine
            status  = engine.get_status()
            counts  = status.get("alert_counts", {})
            running = status.get("running", False)

            self._card_critical.configure(text=str(counts.get("CRITICAL", 0)))
            self._card_total.configure(text=str(counts.get("total", 0)))

            if running:
                self._card_status.configure(text="Active", fg=T.GREEN)
                self._status_badge.configure(text="● Active", fg=T.GREEN)
                self._stop_btn.configure(text="Stop Monitoring", bg=T.RED_BTN)
            else:
                self._card_status.configure(text="Stopped", fg=T.SEV_CRITICAL)
                self._status_badge.configure(text="● Stopped", fg=T.SEV_CRITICAL)
                self._stop_btn.configure(text="Start Monitoring", bg=T.GREEN)

            alerts = engine.alert_handler.get_alerts(limit=5)
            for row in self._tree.get_children():
                self._tree.delete(row)
            for a in reversed(alerts):
                sev  = a.get("severity", "LOW")
                t    = a.get("time_str", "")
                if t and len(t) > 10:
                    t = t[11:19]
                pid  = a.get("process_pid") or a.get("pid") or ""
                proc = a.get("process_name") or (f"PID {pid}" if pid else "–")
                desc = a.get("description", "")[:60]
                self._tree.insert("", "end",
                                  values=(sev, a.get("type", "–"), proc, desc, t),
                                  tags=(sev,))
        except Exception:
            pass
        self.after(500, self._refresh)

    def _toggle_monitoring(self):
        engine = self._main.engine
        if engine.is_running:
            self._main.stop_engine()
        else:
            engine.start()

    def on_show(self):
        pass

    def on_event(self, kind, event):
        pass
