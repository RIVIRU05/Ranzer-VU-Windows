"""RANZER GUI - System Actions View"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from ranzer.gui import theme as T

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class ActionsView(tk.Frame):
    def __init__(self, parent, main_win):
        super().__init__(parent, bg=T.BG)
        self._main           = main_win
        self._process_events = []
        self._apply_styles()
        self._build()
        self.after(1000, self._refresh)

    def _apply_styles(self):
        s = ttk.Style()
        s.configure("Act.Treeview",
                    background=T.CARD, foreground=T.TEXT,
                    fieldbackground=T.CARD, rowheight=30,
                    font=T.FONT_BODY)
        s.configure("Act.Treeview.Heading",
                    background=T.CARD2, foreground=T.TEXT_MUTED,
                    font=(T.FONT_FAMILY, 9, "bold"))
        s.map("Act.Treeview", background=[("selected", T.BLUE_GLOW)])

    def _build(self):
        hdr = tk.Frame(self, bg=T.BG, padx=24, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="System Actions",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 15, "bold")).pack(side="left")

        sub = tk.Frame(self, bg=T.BG, padx=24)
        sub.pack(fill="x", pady=(0, 10))
        tk.Label(sub, text="Detected Malicious Processes",
                 bg=T.BG, fg=T.TEXT_MUTED, font=(T.FONT_FAMILY, 10)).pack(side="left")

        pills = tk.Frame(self, bg=T.BG, padx=24)
        pills.pack(fill="x", pady=(0, 12))
        self._proc_count_lbl = self._pill(pills, "Processes", "0")
        self._file_count_lbl = self._pill(pills, "Files",     "0")

        cols = ("ID", "Name", "PID", "Status", "Risk %", "CPU %", "Start Time", "Reason")
        tbl_frame = tk.Frame(self, bg=T.BG, padx=24)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 12))

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        self._tree = ttk.Treeview(tbl_frame, columns=cols, show="headings",
                                  style="Act.Treeview",
                                  yscrollcommand=vsb.set,
                                  selectmode="browse")
        vsb.config(command=self._tree.yview)

        widths = {"ID": 50, "Name": 130, "PID": 65, "Status": 75,
                  "Risk %": 65, "CPU %": 65, "Start Time": 100, "Reason": 160}
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=widths[c], anchor="w",
                              stretch=(c == "Reason"))
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("HIGH_RISK",   foreground=T.SEV_CRITICAL, background=T.ROW_CRITICAL_BG)
        self._tree.tag_configure("MED_RISK",    foreground=T.SEV_HIGH,     background=T.ROW_HIGH_BG)
        self._tree.tag_configure("LOW_RISK",    foreground=T.SEV_LOW,      background=T.ROW_LOW_BG)
        self._tree.tag_configure("ENDED",       foreground=T.TEXT_MUTED,   background=T.ROW_ENDED_BG)
        self._tree.tag_configure("TERMINATED",  foreground=T.SEV_MEDIUM,   background=T.ROW_TERMINATED_BG)

        self._tree.bind("<Double-1>", self._on_double_click)

        btn_row = tk.Frame(self, bg=T.BG, padx=24, pady=12)
        btn_row.pack(fill="x")

        tk.Button(btn_row, text="Terminate Selected",
                  bg=T.RED_BTN, fg=T.WHITE, relief="flat",
                  font=(T.FONT_FAMILY, 10, "bold"), cursor="hand2",
                  padx=16, pady=8,
                  activebackground="#B91C1C", activeforeground=T.WHITE,
                  command=self._terminate_selected).pack(side="left", padx=(0, 10))

        tk.Button(btn_row, text="Details",
                  bg=T.BLUE, fg=T.WHITE, relief="flat",
                  font=(T.FONT_FAMILY, 10, "bold"), cursor="hand2",
                  padx=16, pady=8,
                  activebackground=T.BLUE_DARK, activeforeground=T.WHITE,
                  command=self._show_details).pack(side="left")

        tk.Button(btn_row, text="Refresh",
                  bg=T.CARD, fg=T.TEXT, relief="flat",
                  font=T.FONT_BODY, cursor="hand2",
                  padx=12, pady=8,
                  activebackground=T.CARD2, activeforeground=T.TEXT,
                  highlightbackground=T.BORDER, highlightthickness=1,
                  command=self._do_refresh).pack(side="right")

    def _pill(self, parent, label, value):
        f = tk.Frame(parent, bg=T.CARD,
                     highlightbackground=T.BORDER, highlightthickness=1,
                     padx=16, pady=8)
        f.pack(side="left", padx=(0, 10))
        tk.Label(f, text=label, bg=T.CARD, fg=T.TEXT_MUTED,
                 font=T.FONT_SMALL).pack()
        val = tk.Label(f, text=value, bg=T.CARD, fg=T.TEXT,
                       font=(T.FONT_FAMILY, 17, "bold"))
        val.pack()
        return val

    def _refresh(self):
        self._do_refresh()
        self.after(1000, self._refresh)

    def _do_refresh(self):
        try:
            events = self._main.engine.process_tracker.get_recent_events(limit=50)
            self._process_events = events
            self._proc_count_lbl.configure(text=str(len(events)))
            self._file_count_lbl.configure(
                text=str(sum(len(e.flagged_files) for e in events)))
            self._populate_table(events)
        except Exception:
            pass

    def _populate_table(self, events):
        # Remember selection so refresh doesn't lose it
        prev_sel = self._tree.selection()
        prev_iid = prev_sel[0] if prev_sel else None

        for row in self._tree.get_children():
            self._tree.delete(row)

        tracker = self._main.engine.process_tracker
        for idx, ev in enumerate(reversed(events), start=1):
            terminated = tracker.is_quarantined(ev.pid)
            alive      = (not terminated) and self._pid_alive(ev.pid)
            risk       = self._risk_score(ev)
            cpu        = self._get_cpu(ev.pid) if alive else "–"
            start_t    = datetime.fromtimestamp(ev.timestamp).strftime("%H:%M:%S")
            if terminated:
                status = "Terminated"
                tag    = "TERMINATED"
            elif alive:
                status = "Active"
                tag    = "HIGH_RISK" if risk >= 80 else ("MED_RISK" if risk >= 40 else "LOW_RISK")
            else:
                status = "Ended"
                tag    = "ENDED"
            self._tree.insert("", "end",
                              iid=f"{ev.pid}_{idx}",
                              values=(idx, ev.process_name, ev.pid,
                                      status, f"{risk}%", cpu,
                                      start_t, ev.event_reason),
                              tags=(tag,))

        # Restore selection after repopulation
        if prev_iid and self._tree.exists(prev_iid):
            self._tree.selection_set(prev_iid)
            self._tree.see(prev_iid)

    @staticmethod
    def _risk_score(ev) -> int:
        return {"CRITICAL": 95, "HIGH": 70, "MEDIUM": 45, "LOW": 20}.get(ev.severity, 20)

    @staticmethod
    def _get_cpu(pid) -> str:
        if not _PSUTIL:
            return "–"
        try:
            return f"{psutil.Process(pid).cpu_percent(interval=None):.1f}%"
        except Exception:
            return "–"

    @staticmethod
    def _pid_alive(pid) -> bool:
        if not _PSUTIL:
            return False
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False

    def _selected_event(self):
        sel = self._tree.selection()
        if not sel:
            return None
        pid_str = sel[0].split("_")[0]
        for ev in self._process_events:
            if str(ev.pid) == pid_str:
                return ev
        return None

    def _terminate_selected(self):
        ev = self._selected_event()
        if not ev:
            messagebox.showwarning("No Selection",
                                   "Select a process row first.", parent=self)
            return
        if not self._pid_alive(ev.pid):
            messagebox.showinfo("Already Ended",
                                f"PID {ev.pid} ({ev.process_name}) has already ended.",
                                parent=self)
            return

        if not messagebox.askyesno(
                "Confirm Terminate",
                f"Terminate '{ev.process_name}' (PID {ev.pid})?\n\nThis will forcefully end the process.",
                parent=self):
            return

        tracker = self._main.engine.process_tracker
        killed  = tracker.terminate_process(ev.pid)
        if not killed:
            killed = tracker.kill_process(ev.pid)

        if killed:
            messagebox.showinfo("Done",
                                f"PID {ev.pid} ({ev.process_name}) terminated.",
                                parent=self)
        else:
            messagebox.showerror("Failed",
                                 f"Could not terminate PID {ev.pid}.\n"
                                 "The process may require higher privileges.",
                                 parent=self)
        self._do_refresh()

    def _show_details(self):
        ev = self._selected_event()
        if not ev:
            messagebox.showwarning("No Selection",
                                   "Select a process row first.", parent=self)
            return
        tracker    = self._main.engine.process_tracker
        terminated = tracker.is_quarantined(ev.pid)
        alive      = (not terminated) and self._pid_alive(ev.pid)
        info       = tracker.get_process_info(ev.pid) if alive else None
        if terminated:
            status_str = "Terminated by RANZER"
        elif alive:
            status_str = "Active"
        else:
            status_str = "Ended"
        lines = [
            f"Process Name : {ev.process_name}",
            f"PID          : {ev.pid}",
            f"Status       : {status_str}",
            f"Exe Path     : {ev.exe_path or '–'}",
            f"Event Reason : {ev.event_reason}",
            f"Severity     : {ev.severity}",
            f"Files Open   : {ev.open_file_count}",
            f"Access Rate  : {ev.file_access_rate:.2f} files/s",
            f"Write Rate   : {ev.write_bytes_per_sec / 1024:.1f} KB/s",
        ]
        if info:
            lines += [
                "",
                f"Live Status  : {info.get('status', '–')}",
                f"CPU %        : {info.get('cpu_percent', '–')}",
                f"Memory       : {info.get('memory_mb', '–')} MB",
                f"Open Files   : {info.get('open_files', '–')}",
            ]
        if ev.flagged_files:
            lines.append("\nFlagged Files:")
            for f in ev.flagged_files[:8]:
                lines.append(f"  {f}")
        messagebox.showinfo(f"Process Detail - PID {ev.pid}",
                            "\n".join(lines), parent=self)

    def _on_double_click(self, event):
        self._show_details()

    def on_show(self):
        self._do_refresh()

    def on_event(self, kind, event):
        if kind == "process":
            self._process_events.append(event)
            self._do_refresh()
