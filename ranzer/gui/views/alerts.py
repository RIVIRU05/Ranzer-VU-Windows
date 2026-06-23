"""RANZER GUI — Alerts View"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ranzer.gui import theme as T

try:
    import psutil as _psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class AlertsView(tk.Frame):
    def __init__(self, parent, main_win):
        super().__init__(parent, bg=T.BG)
        self._main        = main_win
        self._filter_sev  = tk.StringVar(value="ALL")
        self._search_var  = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        self._all_alerts  = []
        self._apply_styles()
        self._build()
        self.after(1000, self._refresh)

    def _apply_styles(self):
        s = ttk.Style()
        s.configure("Alerts.Treeview",
                    background=T.CARD, foreground=T.TEXT,
                    fieldbackground=T.CARD, rowheight=28,
                    font=T.FONT_BODY)
        s.configure("Alerts.Treeview.Heading",
                    background=T.CARD2, foreground=T.TEXT_MUTED,
                    font=(T.FONT_FAMILY, 9, "bold"))
        s.map("Alerts.Treeview", background=[("selected", T.BLUE_GLOW)])
        s.configure("TCombobox",
                    fieldbackground=T.CARD2, background=T.CARD2,
                    foreground=T.TEXT, selectbackground=T.BLUE,
                    selectforeground=T.WHITE)

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=T.BG, padx=24, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Alerts Panel",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 15, "bold")).pack(side="left")
        tk.Button(hdr, text="Export ↓",
                  bg=T.BLUE, fg=T.WHITE, relief="flat",
                  font=T.FONT_SMALL, cursor="hand2",
                  padx=14, pady=5,
                  activebackground=T.BLUE_DARK, activeforeground=T.WHITE,
                  command=self._export).pack(side="right")

        # Stat pills
        pills = tk.Frame(self, bg=T.BG, padx=24)
        pills.pack(fill="x", pady=(0, 12))
        self._pill_total    = self._pill(pills, "Total",    "0", T.TEXT)
        self._pill_critical = self._pill(pills, "Critical", "0", T.SEV_CRITICAL)
        self._pill_high     = self._pill(pills, "High",     "0", T.SEV_HIGH)
        self._pill_medium   = self._pill(pills, "Medium",   "0", T.SEV_MEDIUM)
        self._pill_low      = self._pill(pills, "Low",      "0", T.SEV_LOW)

        # Search + filter
        bar = tk.Frame(self, bg=T.BG, padx=24)
        bar.pack(fill="x", pady=(0, 10))
        tk.Label(bar, text="Search:", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.FONT_SMALL).pack(side="left", padx=(0, 6))
        tk.Entry(bar, textvariable=self._search_var,
                 font=T.FONT_BODY, width=24,
                 relief="flat", bd=1,
                 bg=T.CARD2, fg=T.TEXT,
                 insertbackground=T.TEXT,
                 highlightbackground=T.BORDER, highlightthickness=1).pack(
                     side="left", ipady=4, padx=(0, 16))
        tk.Label(bar, text="Severity:", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.FONT_SMALL).pack(side="left", padx=(0, 6))
        sev_cb = ttk.Combobox(bar, textvariable=self._filter_sev, width=10,
                               values=["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
                               state="readonly", font=T.FONT_BODY)
        sev_cb.pack(side="left")
        sev_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        # Table
        cols = ("ID", "Time", "Severity", "Process", "PID", "Description", "Status")
        tbl_frame = tk.Frame(self, bg=T.BG, padx=24)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 16))

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        self._tree = ttk.Treeview(tbl_frame, columns=cols, show="headings",
                                  style="Alerts.Treeview",
                                  yscrollcommand=vsb.set)
        vsb.config(command=self._tree.yview)

        widths = {"ID": 90, "Time": 90, "Severity": 80, "Process": 110,
                  "PID": 60, "Description": 260, "Status": 70}
        for c in cols:
            self._tree.heading(c, text=c,
                               command=lambda col=c: self._sort(col))
            self._tree.column(c, width=widths[c], anchor="w",
                              stretch=(c == "Description"))
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("CRITICAL", foreground=T.SEV_CRITICAL)
        self._tree.tag_configure("HIGH",     foreground=T.SEV_HIGH)
        self._tree.tag_configure("MEDIUM",   foreground=T.SEV_MEDIUM)
        self._tree.tag_configure("LOW",      foreground=T.SEV_LOW)
        self._tree.bind("<Double-1>", self._on_double_click)

    def _pill(self, parent, label, value, color):
        f = tk.Frame(parent, bg=T.CARD,
                     highlightbackground=T.BORDER, highlightthickness=1,
                     padx=14, pady=8)
        f.pack(side="left", padx=(0, 10))
        tk.Label(f, text=label, bg=T.CARD, fg=T.TEXT_MUTED,
                 font=T.FONT_SMALL).pack()
        val = tk.Label(f, text=value, bg=T.CARD, fg=color,
                       font=(T.FONT_FAMILY, 17, "bold"))
        val.pack()
        return val

    def _refresh(self):
        try:
            alerts = self._main.engine.alert_handler.get_alerts(limit=200)
            self._all_alerts = alerts
            counts = self._main.engine.alert_handler.get_alert_counts()
            self._pill_total.configure(text=str(counts.get("total",    0)))
            self._pill_critical.configure(text=str(counts.get("CRITICAL", 0)))
            self._pill_high.configure(text=str(counts.get("HIGH",     0)))
            self._pill_medium.configure(text=str(counts.get("MEDIUM",   0)))
            self._pill_low.configure(text=str(counts.get("LOW",      0)))
            self._apply_filter()
        except Exception:
            pass
        self.after(1000, self._refresh)

    def _pid_status(self, pid_str: str) -> str:
        if not pid_str:
            return "–"
        try:
            pid = int(pid_str)
            if self._main.engine.process_tracker.is_quarantined(pid):
                return "Terminated"
            if _PSUTIL and _psutil.pid_exists(pid):
                return "Active"
            return "Ended"
        except Exception:
            return "–"

    def _apply_filter(self):
        sev_filter = self._filter_sev.get()
        search     = self._search_var.get().lower()
        for row in self._tree.get_children():
            self._tree.delete(row)
        for a in reversed(self._all_alerts):
            sev = a.get("severity", "LOW")
            if sev_filter != "ALL" and sev != sev_filter:
                continue
            pid  = str(a.get("process_pid") or a.get("pid") or "")
            proc = a.get("process_name") or (f"PID {pid}" if pid else "–")
            desc = a.get("description", "")
            if search and search not in proc.lower() \
                    and search not in desc.lower() \
                    and search not in sev.lower():
                continue
            t = a.get("time_str", "")
            if t and len(t) > 10:
                t = t[11:19]
            status = self._pid_status(pid)
            self._tree.insert("", "end",
                              values=(a.get("id", "–")[:12], t, sev, proc, pid,
                                      desc[:55], status),
                              tags=(sev,))

    def _sort(self, col):
        pass

    def _on_double_click(self, event):
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        vals = self._tree.item(iid, "values")
        if not vals:
            return
        self._show_detail_dialog(vals)

    def _show_detail_dialog(self, vals):
        # Look up full record from alert handler (treeview values are truncated)
        full_id = vals[0] if vals else ""
        record = {}
        try:
            for a in self._main.engine.alert_handler.get_alerts(limit=500):
                if a.get("id", "") == full_id:
                    record = a
                    break
        except Exception:
            pass

        sev       = record.get("severity") or (vals[2] if len(vals) > 2 else "LOW")
        sev_color = T.severity_color(sev)
        pid_val   = str(record.get("process_pid") or record.get("pid") or
                        (vals[4] if len(vals) > 4 else "–") or "–")
        proc_val  = record.get("process_name") or (vals[3] if len(vals) > 3 else "–") or "–"
        desc_val  = record.get("description") or (vals[5] if len(vals) > 5 else "–") or "–"
        time_val  = record.get("time_str") or (vals[1] if len(vals) > 1 else "–") or "–"

        # Use the root window as parent so Toplevel renders correctly on all WMs
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title("Alert Detail")
        dlg.configure(bg=T.BG)
        dlg.resizable(False, False)

        # Center on screen
        w, h = 440, 370
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # Header
        hdr = tk.Frame(dlg, bg=T.BLUE, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Alert Detail",
                 bg=T.BLUE, fg=T.WHITE,
                 font=(T.FONT_FAMILY, 11, "bold")).pack(side="left", padx=16, pady=12)
        tk.Label(hdr, text=f"  {sev}  ",
                 bg=sev_color, fg=T.WHITE,
                 font=(T.FONT_FAMILY, 9, "bold")).pack(side="right", padx=16, pady=12)

        # Body
        body = tk.Frame(dlg, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        fields = [
            ("ID",          full_id  or "–"),
            ("Time",        time_val),
            ("Severity",    sev),
            ("Process",     proc_val),
            ("PID",         pid_val),
            ("Status",      vals[6] if len(vals) > 6 else "Active"),
        ]

        card = tk.Frame(body, bg=T.CARD,
                        highlightbackground=T.BORDER, highlightthickness=1)
        card.pack(fill="x")

        for i, (label, value) in enumerate(fields):
            bg = T.CARD if i % 2 == 0 else T.CARD2
            row = tk.Frame(card, bg=bg)
            row.pack(fill="x")
            tk.Label(row, text=label, width=10, anchor="w",
                     bg=bg, fg=T.TEXT_MUTED,
                     font=(T.FONT_FAMILY, 9, "bold")).pack(side="left", padx=(14, 4), pady=5)
            fg = sev_color if label == "Severity" else T.TEXT
            tk.Label(row, text=str(value), anchor="w",
                     bg=bg, fg=fg,
                     font=T.FONT_BODY).pack(side="left", padx=(0, 14), pady=5)

        # Description (full, wrapped)
        desc_bg = T.CARD2 if len(fields) % 2 == 0 else T.CARD
        desc_row = tk.Frame(card, bg=desc_bg)
        desc_row.pack(fill="x")
        tk.Label(desc_row, text="Description", width=10, anchor="nw",
                 bg=desc_bg, fg=T.TEXT_MUTED,
                 font=(T.FONT_FAMILY, 9, "bold")).pack(side="left", padx=(14, 4), pady=(6, 8))
        tk.Label(desc_row, text=desc_val, anchor="nw",
                 bg=desc_bg, fg=T.TEXT, font=T.FONT_BODY,
                 wraplength=290, justify="left").pack(side="left", padx=(0, 14), pady=(6, 8))

        # Footer
        tk.Frame(dlg, bg=T.BORDER, height=1).pack(fill="x", padx=0, pady=(8, 0))
        btn_row = tk.Frame(dlg, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=10)
        tk.Button(btn_row, text="Close",
                  bg=T.BLUE, fg=T.WHITE, relief="flat",
                  font=(T.FONT_FAMILY, 10, "bold"), cursor="hand2",
                  padx=24, pady=6,
                  activebackground=T.BLUE_DARK, activeforeground=T.WHITE,
                  command=dlg.destroy).pack(side="right")

        dlg.grab_set()
        dlg.lift()
        dlg.focus_force()

    def _export(self):
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv"), ("Text", "*.txt")])
        if not path:
            return
        fmt = "csv" if path.endswith(".csv") else "txt" if path.endswith(".txt") else "json"
        try:
            self._main.engine.export_alerts(path, fmt)
            messagebox.showinfo("Exported", f"Alerts saved to:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Failed", str(e), parent=self)

    def on_show(self):
        try:
            self._all_alerts = self._main.engine.alert_handler.get_alerts(limit=200)
            self._apply_filter()
        except Exception:
            pass

    def on_event(self, kind, event):
        pass
