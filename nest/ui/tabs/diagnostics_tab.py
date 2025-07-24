import tkinter as tk
from tkinter import ttk, messagebox
import threading
import psutil
import platform
import subprocess
from datetime import datetime
from nest.utils.diagnostics_util import upload_diagnostics


class DiagnosticsTab(ttk.Frame):
    def __init__(self, parent, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.diag_text = tk.Text(self)
        self.diag_text.pack(fill="both", expand=True)
        self.diag_status_var = tk.StringVar(value="Ready")
        self.diag_ticket_entry = ttk.Entry(self)
        self.diag_ticket_entry.pack()

        # Example button
        ttk.Button(self, text="Check Memory", command=self.check_memory_health).pack()
        ttk.Button(self, text="Upload", command=self.upload_diagnostic_result).pack()

    def _update_diag(self, message):
        self.diag_text.config(state="normal")
        self.diag_text.insert(tk.END, message + "\n")
        self.diag_text.see(tk.END)
        self.diag_text.config(state="disabled")

    def check_memory_health(self):
        self.diag_status_var.set("Running memory check...")
        threading.Thread(target=self._check_memory_health_thread, daemon=True).start()

    def _check_memory_health_thread(self):
        try:
            mem = psutil.virtual_memory()
            self._update_diag(f"Total RAM: {mem.total / (1024**3):.2f} GB")
            self.diag_status_var.set("Memory check complete")
            self.current_diagnostic_result = self.diag_text.get(1.0, tk.END)
            self.current_diagnostic_title = "Memory Health Check"
        except Exception as e:
            self._update_diag(f"Error: {str(e)}")

    def upload_diagnostic_result(self):
        ticket = self.diag_ticket_entry.get().strip()
        if not ticket:
            messagebox.showwarning("Missing Ticket", "Enter a ticket number.")
            return
        result = self.diag_text.get(1.0, tk.END)
        if not result.strip():
            messagebox.showinfo("Empty", "No diagnostics to upload.")
            return
        upload_diagnostics(ticket, "Tech", diagnostic_text=result)
        messagebox.showinfo("Uploaded", "Diagnostic uploaded to RepairDesk.")
