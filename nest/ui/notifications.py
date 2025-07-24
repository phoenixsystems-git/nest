import tkinter as tk
from tkinter import ttk


class NotificationsModule(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        ttk.Label(self, text="Notifications Module", style="Header.TLabel").pack(anchor="w", pady=5)
        ttk.Label(self, text="View system or user notifications.\n(Placeholder)").pack(pady=10)
