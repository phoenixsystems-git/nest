import tkinter as tk
from tkinter import ttk


class TechniciansModule(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        ttk.Label(self, text="Technicians Module", style="Header.TLabel").pack(anchor="w", pady=5)
        ttk.Label(self, text="Manage or view technician details.\n(Placeholder)").pack(pady=10)
