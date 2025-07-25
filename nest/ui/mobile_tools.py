import tkinter as tk
from tkinter import ttk, messagebox
import logging


class MobileToolsModule(ttk.Frame):
    def __init__(self, parent, current_user=None, app=None):
        super().__init__(parent, padding=15, style="RepairDesk.TFrame")
        self.current_user = current_user
        self.app = app
        self.colors = {
            "primary": "#017E84",
            "secondary": "#2ecc71",
            "background": "#f9f9f9",
            "card_bg": "#ffffff",
            "text_primary": "#212121",
            "text_secondary": "#666666"
        }
        self._setup_styles()
        self.create_widgets()
    
    def _setup_styles(self):
        style = ttk.Style()
        
        style.configure("RepairDesk.TFrame", background=self.colors["background"])
        style.configure("Card.TFrame", 
                       background=self.colors["card_bg"],
                       relief="solid", 
                       borderwidth=1)
        style.configure("RepairDesk.TLabel", 
                       background=self.colors["background"],
                       foreground=self.colors["text_primary"],
                       font=("Segoe UI", 9))
        style.configure("Header.TLabel",
                       background=self.colors["background"],
                       foreground=self.colors["text_primary"],
                       font=("Segoe UI", 16, "bold"))
        style.configure("Subheader.TLabel",
                       background=self.colors["card_bg"],
                       foreground=self.colors["primary"],
                       font=("Segoe UI", 12, "bold"))
        style.configure("RepairDesk.TButton", 
                       background=self.colors["primary"], 
                       foreground="white", 
                       font=("Segoe UI", 9),
                       padding=(8, 4))
    
    def create_widgets(self):
        header_frame = ttk.Frame(self, style="RepairDesk.TFrame")
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(header_frame, text="Mobile Device Tools", 
                 style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Comprehensive mobile device diagnostics and management tools", 
                 style="RepairDesk.TLabel").pack(anchor="w", pady=(5, 0))
        
        main_container = ttk.Frame(self, style="RepairDesk.TFrame")
        main_container.pack(fill="both", expand=True)
        
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)
        
        self._create_ios_section(main_container)
        self._create_android_section(main_container)
        self._create_status_section(main_container)
    
    def _create_ios_section(self, parent):
        ios_card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        ios_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        
        ttk.Label(ios_card, text="iOS Device Tools", 
                 style="Subheader.TLabel").pack(anchor="w", pady=(0, 10))
        
        features = [
            "Device Information & Diagnostics",
            "iTunes Backup & Restore",
            "App Installation & Management", 
            "File System Access",
            "Battery Health Analysis",
            "Network Configuration",
            "Screen Recording & Screenshots"
        ]
        
        for feature in features:
            feature_frame = ttk.Frame(ios_card, style="Card.TFrame")
            feature_frame.pack(fill="x", pady=2)
            
            ttk.Label(feature_frame, text=f"• {feature}", 
                     style="RepairDesk.TLabel").pack(anchor="w", padx=10, pady=2)
        
        button_frame = ttk.Frame(ios_card, style="Card.TFrame")
        button_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(button_frame, text="Connect iOS Device", 
                  style="RepairDesk.TButton",
                  command=self._connect_ios).pack(side="left", padx=(0, 5))
        ttk.Button(button_frame, text="View iOS Tools", 
                  style="RepairDesk.TButton",
                  command=self._show_ios_tools).pack(side="left")
    
    def _create_android_section(self, parent):
        android_card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        android_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        
        ttk.Label(android_card, text="Android Device Tools", 
                 style="Subheader.TLabel").pack(anchor="w", pady=(0, 10))
        
        features = [
            "ADB Device Management",
            "APK Installation & Sideloading",
            "System Information & Logs",
            "File Transfer & Management",
            "Network & Connectivity Tools",
            "Performance Monitoring",
            "Developer Options Control"
        ]
        
        for feature in features:
            feature_frame = ttk.Frame(android_card, style="Card.TFrame")
            feature_frame.pack(fill="x", pady=2)
            
            ttk.Label(feature_frame, text=f"• {feature}", 
                     style="RepairDesk.TLabel").pack(anchor="w", padx=10, pady=2)
        
        button_frame = ttk.Frame(android_card, style="Card.TFrame")
        button_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(button_frame, text="Connect Android Device", 
                  style="RepairDesk.TButton",
                  command=self._connect_android).pack(side="left", padx=(0, 5))
        ttk.Button(button_frame, text="View Android Tools", 
                  style="RepairDesk.TButton",
                  command=self._show_android_tools).pack(side="left")
    
    def _create_status_section(self, parent):
        status_card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        status_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        ttk.Label(status_card, text="Device Connection Status", 
                 style="Subheader.TLabel").pack(anchor="w", pady=(0, 10))
        
        status_frame = ttk.Frame(status_card, style="Card.TFrame")
        status_frame.pack(fill="x")
        
        self.ios_status_var = tk.StringVar(value="No iOS device connected")
        self.android_status_var = tk.StringVar(value="No Android device connected")
        
        ttk.Label(status_frame, text="iOS Status:", 
                 style="RepairDesk.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(status_frame, textvariable=self.ios_status_var, 
                 style="RepairDesk.TLabel").grid(row=0, column=1, sticky="w")
        
        ttk.Label(status_frame, text="Android Status:", 
                 style="RepairDesk.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(5, 0))
        ttk.Label(status_frame, textvariable=self.android_status_var, 
                 style="RepairDesk.TLabel").grid(row=1, column=1, sticky="w", pady=(5, 0))
        
        refresh_frame = ttk.Frame(status_card, style="Card.TFrame")
        refresh_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(refresh_frame, text="Refresh Device Status", 
                  style="RepairDesk.TButton",
                  command=self._refresh_status).pack(side="left")
    
    def _connect_ios(self):
        messagebox.showinfo("iOS Connection", 
                           "iOS device connection will be implemented in the full iOS Tools module.\n\n"
                           "This will include:\n"
                           "• iTunes integration\n"
                           "• 3uTools support\n"
                           "• Device detection and pairing")
    
    def _show_ios_tools(self):
        messagebox.showinfo("iOS Tools", 
                           "Opening iOS Tools module...\n\n"
                           "The iOS Tools module provides comprehensive device management capabilities.")
    
    def _connect_android(self):
        messagebox.showinfo("Android Connection", 
                           "Android device connection will be implemented in the full Android Tools module.\n\n"
                           "This will include:\n"
                           "• ADB device detection\n"
                           "• USB debugging setup\n"
                           "• Wireless ADB connection")
    
    def _show_android_tools(self):
        messagebox.showinfo("Android Tools", 
                           "Opening Android Tools module...\n\n"
                           "The Android Tools module provides comprehensive ADB-based device management.")
    
    def _refresh_status(self):
        self.ios_status_var.set("Checking iOS devices...")
        self.android_status_var.set("Checking Android devices...")
        
        self.after(1000, lambda: self.ios_status_var.set("No iOS device connected"))
        self.after(1000, lambda: self.android_status_var.set("No Android device connected"))
