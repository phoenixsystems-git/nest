import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os
import sys
import threading
import json
import time
import platform
import logging
import shutil
import tempfile
import requests
import zipfile
import re
from pathlib import Path
import urllib.request
from urllib.parse import urljoin
import webbrowser
from nest.utils.ui_threading import ThreadSafeUIUpdater
from nest.main import FixedHeaderTreeview

# Check if running on Windows or Linux/Mac
IS_WINDOWS = platform.system().lower() == 'windows'


class AndroidToolsModule(ttk.Frame):
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.parent = parent
        self.app = app
        self.device_connected = False
        self.device_info = {}
        self.device_serial = None  # Initialize device_serial to None
        self.threads = []  # Keep track of threads
        self.log_text = None  # Initialize to None, will be created in create_widgets
        self.adb_path = None  # Initialize adb_path to None
        
        # Initialize platform_tools_installed to False by default
        # This needs to be set before create_widgets is called
        self.platform_tools_installed = False
        
        # Create UI first so logging works properly
        self.create_widgets()
        
        # Now check for platform-specific tools after UI is created
        if IS_WINDOWS:
            # Windows-specific initialization
            self.adb_path = self._find_adb_path()
            self.platform_tools_installed = self.adb_path is not None
        else:
            # Linux/Mac initialization
            self.platform_tools_installed = self._check_platform_tools()
            
        # Update UI to reflect the actual tools status
        tools_status = "✅ Installed" if self.platform_tools_installed else "❌ Not Installed"
        self.tools_label.configure(text=f"Android Platform Tools: {tools_status}")

    def create_widgets(self):
        # Create main container with canvas and scrollbar
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)
        
        # Create a canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure the canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create window in canvas for the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Main header with logo
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill="x", padx=10, pady=5)

        header_label = ttk.Label(
            header_frame, text="Android Device Management", font=("Arial", 14, "bold")
        )
        header_label.pack(side="left", pady=10)
        
        # Setup status frame for tools
        self.setup_status_frame = ttk.LabelFrame(scrollable_frame, text="Tools Status")
        self.setup_status_frame.pack(fill="x", padx=10, pady=5, expand=False)
        
        # Check Platform Tools (ADB)
        tools_status = "✅ Installed" if self.platform_tools_installed else "❌ Not Installed"
        self.tools_label = ttk.Label(
            self.setup_status_frame, text=f"Android Platform Tools: {tools_status}", font=("Arial", 10)
        )
        self.tools_label.pack(anchor="w", padx=5, pady=2)

        # Tools installation button
        if not self.platform_tools_installed:
            tools_frame = ttk.Frame(self.setup_status_frame)
            tools_frame.pack(fill="x", padx=5, pady=5)

            tools_btn = ttk.Button(
                tools_frame, text="Install Android Platform Tools", command=self.install_platform_tools,
                width=30  # Explicitly set width to ensure text fits
            )
            tools_btn.pack(side="left", padx=5, pady=5)

        # Main content area with tabs
        self.notebook = ttk.Notebook(scrollable_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Device Info Tab
        self.device_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.device_frame, text="Device Info")
        
        # Device connection frame
        connection_frame = ttk.LabelFrame(self.device_frame, text="Device Connection")
        connection_frame.pack(fill="x", padx=10, pady=10, expand=False)
        
        # Connection buttons frame
        conn_buttons_frame = ttk.Frame(connection_frame)
        conn_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        # Connect button
        self.connect_btn = ttk.Button(
            conn_buttons_frame, text="Connect Device", command=self.connect_device,
            width=20  # Explicitly set width to ensure text fits
        )
        self.connect_btn.pack(side="left", padx=5, pady=5)
        
        # Refresh button
        self.refresh_btn = ttk.Button(
            conn_buttons_frame, text="Refresh Devices", command=self.refresh_device_list,
            width=20  # Explicitly set width to ensure text fits
        )
        self.refresh_btn.pack(side="left", padx=5, pady=5)
        
        # Device list frame
        list_frame = ttk.Frame(connection_frame)
        list_frame.pack(fill="x", padx=5, pady=5)
        
        # Device list label
        list_label = ttk.Label(list_frame, text="Available Devices:")
        list_label.pack(anchor="w", padx=5, pady=2)
        
        # Device listbox with scrollbar
        list_subframe = ttk.Frame(list_frame)
        list_subframe.pack(fill="x", padx=5, pady=2)
        
        self.device_listbox = tk.Listbox(list_subframe, height=3)
        self.device_listbox.pack(side="left", fill="x", expand=True)
        
        scroll = ttk.Scrollbar(list_subframe, orient="vertical", command=self.device_listbox.yview)
        scroll.pack(side="right", fill="y")
        self.device_listbox.config(yscrollcommand=scroll.set)
        
        # Device info display
        device_info_frame = ttk.LabelFrame(self.device_frame, text="Device Information")
        device_info_frame.pack(fill="both", padx=10, pady=10, expand=True)
        
        # Device info content - simple grid layout instead of columns
        info_content = ttk.Frame(device_info_frame)
        info_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Basic device info fields (left column)
        self.info_fields = {
            "Model": tk.StringVar(value="N/A"),
            "Manufacturer": tk.StringVar(value="N/A"),
            "Android Version": tk.StringVar(value="N/A"),
            "Serial Number": tk.StringVar(value="N/A"),
            "IMEI": tk.StringVar(value="N/A"),
            "Battery Level": tk.StringVar(value="N/A"),
        }
        
        # Advanced device info fields (right column)
        self.adv_info_fields = {
            "Storage": tk.StringVar(value="N/A"),
            "RAM": tk.StringVar(value="N/A"),
            "Screen Resolution": tk.StringVar(value="N/A"),
            "CPU": tk.StringVar(value="N/A"),
            "Kernel": tk.StringVar(value="N/A"),
        }
        
        # Create a simple grid layout with 2 columns for all fields
        # Configure grid columns to have consistent width
        info_content.columnconfigure(0, minsize=150)  # Label column
        info_content.columnconfigure(1, minsize=150)  # Value column
        info_content.columnconfigure(2, minsize=150)  # Label column 2
        info_content.columnconfigure(3, minsize=150)  # Value column 2
        
        # Add a heading for basic info
        ttk.Label(
            info_content, text="Basic Information", font=("Arial", 10, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 10))
        
        # Add a heading for advanced info
        ttk.Label(
            info_content, text="Advanced Information", font=("Arial", 10, "bold")
        ).grid(row=0, column=2, columnspan=2, sticky="w", padx=5, pady=(5, 10))
        
        # Add a heading for debug info (at the bottom of the grid)
        max_rows = max(len(self.info_fields), len(self.adv_info_fields)) + 2
        ttk.Label(
            info_content, text="Debug Information", font=("Arial", 10, "bold")
        ).grid(row=max_rows, column=0, columnspan=4, sticky="w", padx=5, pady=(15, 5))
        
        # Add the debug text area
        debug_frame = ttk.Frame(info_content)
        debug_frame.grid(row=max_rows+1, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        
        # Create a text widget for debug info with scrollbar
        self.debug_text = tk.Text(debug_frame, height=5, width=80, wrap=tk.WORD)
        self.debug_text.pack(side="left", fill="both", expand=True)
        
        debug_scroll = ttk.Scrollbar(debug_frame, command=self.debug_text.yview)
        debug_scroll.pack(side="right", fill="y")
        self.debug_text.config(yscrollcommand=debug_scroll.set)
        
        # Make text read-only
        self.debug_text.config(state="disabled")
        
        # Add basic info fields - first column
        row = 1
        for label_text, var in self.info_fields.items():
            ttk.Label(
                info_content, text=f"{label_text}:", font=("Arial", 9, "bold")
            ).grid(row=row, column=0, sticky="w", padx=5, pady=5)
            
            ttk.Label(
                info_content, textvariable=var
            ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
            
            row += 1
            
        # Add advanced info fields - second column
        row = 1
        for label_text, var in self.adv_info_fields.items():
            ttk.Label(
                info_content, text=f"{label_text}:", font=("Arial", 9, "bold")
            ).grid(row=row, column=2, sticky="w", padx=5, pady=5)
            
            ttk.Label(
                info_content, textvariable=var
            ).grid(row=row, column=3, sticky="w", padx=5, pady=5)
            
            row += 1
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x", padx=10, pady=5)
        
        # Device actions frame
        actions_frame = ttk.LabelFrame(self.device_frame, text="Device Actions")
        actions_frame.pack(fill="x", padx=10, pady=(5, 10), expand=False)
        
        # Action buttons
        actions_buttons_frame = ttk.Frame(actions_frame)
        actions_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        # Row 1 of buttons
        self.screenshot_btn = ttk.Button(
            actions_buttons_frame, text="Take Screenshot", command=self.take_screenshot, state="disabled",
            width=18  # Explicitly set width to ensure text fits
        )
        self.screenshot_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.backup_btn = ttk.Button(
            actions_buttons_frame, text="Backup Device", command=self.backup_device, state="disabled",
            width=18  # Explicitly set width to ensure text fits
        )
        self.backup_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.files_btn = ttk.Button(
            actions_buttons_frame, text="Manage Files", command=self.manage_files, state="disabled",
            width=18  # Explicitly set width to ensure text fits
        )
        self.files_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Row 2 of buttons
        self.install_apk_btn = ttk.Button(
            actions_buttons_frame, text="Install APK", command=self.install_apk, state="disabled",
            width=18  # Explicitly set width to ensure text fits
        )
        self.install_apk_btn.grid(row=1, column=0, padx=5, pady=5)
        
        self.app_manager_btn = ttk.Button(
            actions_buttons_frame, text="App Manager", command=self.app_manager, state="disabled",
            width=18  # Explicitly set width to ensure text fits
        )
        self.app_manager_btn.grid(row=1, column=1, padx=5, pady=5)
        
        self.logcat_btn = ttk.Button(
            actions_buttons_frame, text="View Logcat", command=self.view_logcat, state="disabled",
            width=18  # Explicitly set width to ensure text fits
        )
        self.logcat_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # Tools Tab
        self.tools_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tools_frame, text="Android Tools")
        
        # Direct frame without scrollbars - we'll arrange categories horizontally
        tools_main_frame = ttk.Frame(self.tools_frame)
        tools_main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Main tool categories section
        categories = [
            {"name": "Device Control", "icon": "🔄"},
            {"name": "App Management", "icon": "📱"},
            {"name": "System Tools", "icon": "⚙️"},
            {"name": "Debugging", "icon": "🐞"},
            {"name": "File Operations", "icon": "📁"},
            {"name": "Security & Permissions", "icon": "🔒"},
            {"name": "Automation & Scripting", "icon": "🤖"}
        ]
        
        # Configure grid weights for the tools frame
        for i in range(5):  # 5 categories
            tools_main_frame.columnconfigure(i, weight=1, uniform='category_cols')
        
        # Create a section for each category - horizontally arranged
        for col, category in enumerate(categories):
            # Category header - use a frame with fixed height
            header_frame = ttk.Frame(tools_main_frame, height=25)  # Fixed height for header
            header_frame.grid(row=0, column=col, sticky="new", padx=2, pady=0)
            
            # Category label
            ttk.Label(
                header_frame, 
                text=f"{category['icon']} {category['name']}",
                font=('Arial', 9, 'bold')
            ).pack(side='left')
            
            # Category content frame
            category_frame = ttk.Frame(tools_main_frame, padding=2)
            category_frame.grid(row=1, column=col, sticky="nsew", padx=2, pady=0)
            
            # Inner frame for buttons with grid layout - more compact
            inner_frame = ttk.Frame(category_frame)
            inner_frame.pack(fill="both", expand=True, padx=0, pady=0)
            
            # Add tools based on category
            if category["name"] == "Device Control":
                # Device reboot options - single column layout
                ttk.Button(
                    inner_frame, text="Reboot Device", 
                    command=lambda: self._run_in_thread(self._reboot_device_normal),
                    width=18  # Reduced width for better fit
                ).grid(row=0, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Reboot Recovery", 
                    command=lambda: self._run_in_thread(self._reboot_device_recovery),
                    width=18
                ).grid(row=1, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Reboot Bootloader", 
                    command=lambda: self._run_in_thread(self._reboot_device_bootloader),
                    width=18
                ).grid(row=2, column=0, padx=1, pady=1, sticky="ew")
                
                # WiFi and airplane mode toggles - single column layout
                ttk.Button(
                    inner_frame, text="WiFi Toggle", 
                    command=lambda: self._run_in_thread(self._toggle_wifi),
                    width=18
                ).grid(row=3, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Airplane Mode", 
                    command=lambda: self._run_in_thread(self._toggle_airplane_mode),
                    width=18
                ).grid(row=4, column=0, padx=1, pady=1, sticky="ew")
                
                # Screen control
                ttk.Button(
                    inner_frame, text="Screen Toggle", 
                    command=lambda: self._run_in_thread(self._toggle_screen),
                    width=18
                ).grid(row=5, column=0, padx=1, pady=1, sticky="ew")
                
                # New device control tools
                ttk.Button(
                    inner_frame, text="Reboot EDL", 
                    command=lambda: self._run_in_thread(self._reboot_device_edl),
                    width=18
                ).grid(row=6, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Mobile Data", 
                    command=lambda: self._run_in_thread(self._toggle_mobile_data),
                    width=18
                ).grid(row=7, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Bluetooth", 
                    command=lambda: self._run_in_thread(self._toggle_bluetooth),
                    width=18
                ).grid(row=8, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Brightness", 
                    command=lambda: self._run_in_thread(self._set_brightness_dialog),
                    width=18
                ).grid(row=9, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Screen Timeout", 
                    command=lambda: self._run_in_thread(self._set_screen_timeout_dialog),
                    width=18
                ).grid(row=10, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Screenshot", 
                    command=lambda: self._run_in_thread(self.take_screenshot),
                    width=18
                ).grid(row=11, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="DND Toggle", 
                    command=lambda: self._run_in_thread(self._toggle_do_not_disturb),
                    width=18
                ).grid(row=12, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Power Button", 
                    command=lambda: self._run_in_thread(self._simulate_power_button),
                    width=18
                ).grid(row=13, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Flashlight", 
                    command=lambda: self._run_in_thread(self._toggle_flashlight),
                    width=18
                ).grid(row=14, column=0, padx=1, pady=1, sticky="ew")
                
            elif category["name"] == "App Management":
                # App installation and management - single column layout
                ttk.Button(
                    inner_frame, text="Install APK", 
                    command=self.install_apk,
                    width=18
                ).grid(row=0, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Uninstall App", 
                    command=lambda: self._run_in_thread(self._uninstall_app_dialog),
                    width=18
                ).grid(row=1, column=0, padx=2, pady=2)
                
                ttk.Button(
                    inner_frame, text="Clear App Data", 
                    command=lambda: self._run_in_thread(self._clear_app_data_dialog),
                    width=18
                ).grid(row=2, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Force Stop App", 
                    command=lambda: self._run_in_thread(self._force_stop_app_dialog),
                    width=18
                ).grid(row=3, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="List Installed Apps", 
                    command=lambda: self._run_in_thread(self._list_installed_apps),
                    width=18
                ).grid(row=4, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Open App", 
                    command=lambda: self._run_in_thread(self._open_app_dialog),
                    width=18
                ).grid(row=5, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Extract APK", 
                    command=lambda: self._run_in_thread(self._extract_apk_dialog),
                    width=18
                ).grid(row=6, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Freeze/Unfreeze", 
                    command=lambda: self._run_in_thread(self._toggle_freeze_dialog),
                    width=18
                ).grid(row=7, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="View Permissions", 
                    command=lambda: self._run_in_thread(self._view_permissions_dialog),
                    width=18
                ).grid(row=8, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="App Usage Stats", 
                    command=lambda: self._run_in_thread(self._show_app_usage_stats),
                    width=18
                ).grid(row=9, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="App Battery Usage", 
                    command=lambda: self._run_in_thread(self._show_battery_usage),
                    width=18
                ).grid(row=10, column=0, padx=1, pady=1, sticky="ew")
                
            elif category["name"] == "System Tools":
                # System tools - single column layout
                ttk.Button(
                    inner_frame, text="Device Info", 
                    command=lambda: self._run_in_thread(self._show_detailed_device_info),
                    width=18
                ).grid(row=0, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Battery Stats", 
                    command=lambda: self._run_in_thread(self._show_battery_stats),
                    width=18
                ).grid(row=1, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Running Services", 
                    command=lambda: self._run_in_thread(self._show_running_services),
                    width=18
                ).grid(row=2, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Network Stats", 
                    command=lambda: self._run_in_thread(self._show_network_stats),
                    width=18
                ).grid(row=3, column=0, padx=1, pady=1, sticky="ew")

            elif category["name"] == "Debugging":                
                ttk.Button(
                    inner_frame, text="ANR Traces", 
                    command=lambda: self._run_in_thread(self._show_anr_traces),
                    width=18
                ).grid(row=4, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Crash Dumps", 
                    command=lambda: self._run_in_thread(self._show_crash_dumps),
                    width=18
                ).grid(row=5, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Bug Report", 
                    command=lambda: self._run_in_thread(self._generate_bug_report),
                    width=18
                ).grid(row=6, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Screen Record", 
                    command=lambda: self._run_in_thread(self._start_screen_recording),
                    width=18
                ).grid(row=7, column=0, padx=1, pady=1, sticky="ew")
                
            elif category["name"] == "File Operations":
                # File operations - single column layout
                ttk.Button(
                    inner_frame, text="File Manager", 
                    command=self.manage_files,
                    width=18
                ).grid(row=0, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Pull from Device", 
                    command=lambda: self._run_in_thread(self._pull_from_device),
                    width=18
                ).grid(row=1, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Push to Device", 
                    command=lambda: self._run_in_thread(self._push_to_device),
                    width=18
                ).grid(row=2, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Backup Device", 
                    command=lambda: self._run_in_thread(self.backup_device),
                    width=18
                ).grid(row=3, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="View Storage", 
                    command=lambda: self._run_in_thread(self._show_storage_info),
                    width=18
                ).grid(row=4, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Clean Caches", 
                    command=lambda: self._run_in_thread(self._clean_app_caches),
                    width=18
                ).grid(row=5, column=0, padx=1, pady=1, sticky="ew")
                
            elif category["name"] == "Security & Permissions":
                # Security tools - single column layout
                ttk.Button(
                    inner_frame, text="Check Root Status", 
                    command=lambda: self._run_in_thread(self._check_root_status),
                    width=18
                ).grid(row=0, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Check AppOps", 
                    command=self._check_appops_dialog,
                    width=18
                ).grid(row=1, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Change AppOps Permission", 
                    command=self._change_appops_dialog,
                    width=18
                ).grid(row=2, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Check Encryption", 
                    command=lambda: self._run_in_thread(self._check_encryption_status),
                    width=18
                ).grid(row=3, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Check Lock Screen", 
                    command=lambda: self._run_in_thread(self._check_lock_screen_status),
                    width=18
                ).grid(row=4, column=0, padx=1, pady=1, sticky="ew")
                
            elif category["name"] == "Automation & Scripting":
                # Automation tools - single column layout
                ttk.Button(
                    inner_frame, text="Run Shell Script", 
                    command=lambda: self._run_in_thread(self._run_shell_script_dialog),
                    width=18
                ).grid(row=0, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Batch App Manager", 
                    command=lambda: self._run_in_thread(self._batch_app_manager_dialog),
                    width=18
                ).grid(row=1, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Scheduled Tasks", 
                    command=lambda: self._run_in_thread(self._scheduled_tasks_dialog),
                    width=18
                ).grid(row=2, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Logcat + Screencap", 
                    command=lambda: self._run_in_thread(self._logcat_screencap_dialog),
                    width=18
                ).grid(row=3, column=0, padx=1, pady=1, sticky="ew")
                
                ttk.Button(
                    inner_frame, text="Monkey Testing", 
                    command=lambda: self._run_in_thread(self._monkey_testing_dialog),
                    width=18
                ).grid(row=4, column=0, padx=1, pady=1, sticky="ew")
            
            # No need for separators in the horizontal layout anymore since categories are side by side
        
        # Add log frame
        self.log_frame = ttk.LabelFrame(self, text="Log")
        self.log_frame.pack(fill="x", padx=10, pady=5, expand=False)
        
        # Create the log text widget
        self.log_text = tk.Text(self.log_frame, height=6, width=80, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        log_scroll = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scroll.set)
        
        # Initialize log with a welcome message
        self.log_message("Android Tools module initialized")

    # Methods to implement in the next steps
    def _find_adb_path(self):
        """Find the ADB executable path on Windows"""
        try:
            # Check if ADB is in PATH
            adb_in_path = shutil.which('adb')
            if adb_in_path:
                self.log_message(f"Found ADB in PATH: {adb_in_path}")
                return adb_in_path
                
            # Check common installation locations
            common_locations = [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Android', 'Sdk', 'platform-tools', 'adb.exe'),
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Android', 'platform-tools', 'adb.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Android', 'platform-tools', 'adb.exe'),
                os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Android', 'Sdk', 'platform-tools', 'adb.exe'),
            ]
            
            for location in common_locations:
                if os.path.exists(location):
                    self.log_message(f"Found ADB at: {location}")
                    return location
                    
            # Check Android Studio installation
            try:
                if IS_WINDOWS:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Android Studio')
                    install_path = winreg.QueryValueEx(key, 'Path')[0]
                    sdk_path = os.path.join(install_path, 'sdk', 'platform-tools', 'adb.exe')
                    if os.path.exists(sdk_path):
                        self.log_message(f"Found ADB in Android Studio: {sdk_path}")
                        return sdk_path
            except Exception as e:
                self.log_message(f"Could not check Android Studio registry: {str(e)}")
                    
            self.log_message("Could not find ADB executable")
            return None
        except Exception as e:
            self.log_message(f"Error finding ADB path: {str(e)}")
            return None
        
    def _check_platform_tools(self):
        """Check if Android platform tools are installed on Linux/Mac"""
        try:
            # Check if ADB is in PATH
            result = subprocess.run(
                ['adb', 'version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0:
                self.log_message(f"ADB found: {result.stdout.strip()}")
                return True
            
            # Check common Linux/Mac installation locations
            common_locations = [
                '/usr/bin/adb',
                '/usr/local/bin/adb',
                '/opt/android-sdk/platform-tools/adb',
                os.path.expanduser('~/Android/Sdk/platform-tools/adb'),
                '/usr/lib/android-sdk/platform-tools/adb'
            ]
            
            for location in common_locations:
                if os.path.exists(location):
                    self.log_message(f"Found ADB at: {location}")
                    return True
            
            self.log_message("Could not find ADB executable")
            return False
        except Exception as e:
            self.log_message(f"Error checking platform tools: {str(e)}")
            return False
        
    def install_platform_tools(self):
        """Install Android platform tools"""
        self._run_in_thread(self._install_platform_tools_task)
        
    def _install_platform_tools_task(self):
        """Worker thread to download and install Android platform tools"""
        try:
            self.log_message("Installing Android platform tools...")
            self.update_status("Installing Android platform tools...")
            
            # Create a temp directory for downloads
            temp_dir = tempfile.mkdtemp()
            self.log_message(f"Created temporary directory: {temp_dir}")
            
            # Determine the correct download URL based on platform
            if IS_WINDOWS:
                platform_name = "windows"
                file_name = "platform-tools-latest-windows.zip"
            else:
                # For Linux/Mac
                if platform.system().lower() == "darwin":
                    platform_name = "mac"
                    file_name = "platform-tools-latest-darwin.zip"
                else:
                    platform_name = "linux"
                    file_name = "platform-tools-latest-linux.zip"
            
            download_url = f"https://dl.google.com/android/repository/{file_name}"
            zip_path = os.path.join(temp_dir, file_name)
            
            # Download the platform tools
            self.log_message(f"Downloading platform tools from {download_url}...")
            self.update_status("Downloading platform tools...")
            
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                self.log_message("Download completed successfully")
            except Exception as e:
                self.log_message(f"Download failed: {str(e)}")
                self.update_status("Installation failed")
                messagebox.showerror("Download Error", f"Failed to download Android platform tools: {str(e)}")
                return
            
            # Determine the installation directory
            if IS_WINDOWS:
                install_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Android')
            else:
                install_dir = os.path.expanduser("~/Android")
            
            # Create the directory if it doesn't exist
            os.makedirs(install_dir, exist_ok=True)
            self.log_message(f"Installing to: {install_dir}")
            
            # Extract the ZIP file
            self.log_message("Extracting platform tools...")
            self.update_status("Extracting platform tools...")
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
                self.log_message("Extraction completed successfully")
            except Exception as e:
                self.log_message(f"Extraction failed: {str(e)}")
                self.update_status("Installation failed")
                messagebox.showerror("Extraction Error", f"Failed to extract Android platform tools: {str(e)}")
                return
            
            # Set up PATH environment variable
            platform_tools_path = os.path.join(install_dir, "platform-tools")
            self.log_message(f"Platform tools installed at: {platform_tools_path}")
            
            # Add to PATH for the current session
            if platform_tools_path not in os.environ['PATH']:
                os.environ['PATH'] = platform_tools_path + os.pathsep + os.environ['PATH']
                self.log_message("Added platform-tools to PATH for current session")
            
            # Instruct user on permanent PATH setup
            if IS_WINDOWS:
                path_instructions = (
                    "To use ADB from any command prompt, you need to add it to your PATH:\n\n"
                    f"1. Add this to your PATH: {platform_tools_path}\n"
                    "2. Open System Properties > Advanced > Environment Variables\n"
                    "3. Edit the PATH variable and add the path above\n"
                    "4. Restart any open command prompts"
                )
            else:
                path_instructions = (
                    "To use ADB from any terminal, add this line to your .bashrc or .zshrc file:\n\n"
                    f"export PATH=\"$PATH:{platform_tools_path}\""
                )
            
            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
                self.log_message("Cleaned up temporary files")
            except Exception as e:
                self.log_message(f"Failed to clean up temporary files: {str(e)}")
            
            # Update UI to reflect successful installation
            ThreadSafeUIUpdater.safe_update(self, lambda: self.tools_label.configure(text="Android Platform Tools: ✅ Installed"))
            self.platform_tools_installed = True
            
            # Show success message with PATH instructions
            self.update_status("Installation completed")
            self.log_message("Android platform tools installed successfully")
            
            messagebox.showinfo(
                "Installation Complete",
                f"Android platform tools have been installed successfully.\n\n{path_instructions}"
            )
            
        except Exception as e:
            self.log_message(f"Installation error: {str(e)}")
            self.update_status("Installation failed")
            messagebox.showerror("Installation Error", f"Failed to install Android platform tools: {str(e)}")
        
    def connect_device(self):
        """Connect to an Android device"""
        # Get the current selection before starting the thread
        selected = self.device_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Device Selected", "Please select a device from the list first.")
            return
            
        self._run_in_thread(self._connect_device_task)
        
    def _connect_device_task(self):
        """Worker thread to connect to the selected Android device"""
        try:
            # Check if any device is selected
            selected = self.device_listbox.curselection()
            if not selected:
                self.log_message("No device selected. Please select a device from the list.")
                messagebox.showinfo("No Device Selected", "Please select a device from the list first.")
                return
            
            # Get the selected device details
            device_text = self.device_listbox.get(selected[0])
            
            # Extract serial number from the device text
            # Format could be either "Model (serial)" or just "serial"
            serial = device_text
            if '(' in device_text and ')' in device_text:
                serial = device_text.split('(')[1].split(')')[0]
            
            self.log_message(f"Connecting to device: {serial}")
            self.update_status(f"Connecting to {serial}...")
            
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
            
            # Check if device is still connected
            result = subprocess.run(
                [adb_cmd, 'devices'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0 or serial not in result.stdout:
                self.log_message(f"Device {serial} not found or disconnected")
                self.update_status("Device not found")
                messagebox.showerror("Connection Error", "Device not found or disconnected. Try refreshing the device list.")
                return
            
            # Get device information
            self.log_message("Retrieving device information...")
            self.update_status("Getting device info...")
            self.device_info = self._get_device_info(serial, adb_cmd)
            
            if self.device_info:
                self.device_connected = True
                ThreadSafeUIUpdater.safe_update(self, self.update_device_info)
                ThreadSafeUIUpdater.safe_update(self, self.enable_device_actions)
                self.log_message("Device connected successfully")
                self.update_status(f"Connected to {self.device_info.get('model', serial)}")
            else:
                self.device_connected = False
                self.log_message("Failed to get device information")
                self.update_status("Connection failed")
                messagebox.showerror("Connection Error", "Failed to get device information. The device may be locked or not responding.")
                
        except Exception as e:
            self.log_message(f"Error connecting to device: {str(e)}")
            self.update_status("Connection failed")
            messagebox.showerror("Connection Error", f"Failed to connect to device: {str(e)}")
    
    def _get_device_info(self, serial, adb_cmd):
        """Get device information using ADB"""
        try:
            device_info = {
                'serial': serial
            }
            
            # Get model
            model_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'getprop', 'ro.product.model'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if model_cmd.returncode == 0:
                device_info['model'] = model_cmd.stdout.strip()
            
            # Get manufacturer
            manufacturer_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'getprop', 'ro.product.manufacturer'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if manufacturer_cmd.returncode == 0:
                device_info['manufacturer'] = manufacturer_cmd.stdout.strip()
            
            # Get Android version
            version_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'getprop', 'ro.build.version.release'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if version_cmd.returncode == 0:
                device_info['android_version'] = version_cmd.stdout.strip()
            
            # Get battery level - use dumpsys battery without pipes for better compatibility
            battery_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'dumpsys', 'battery'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if battery_cmd.returncode == 0 and battery_cmd.stdout.strip():
                try:
                    # Parse the complete battery output and find the level
                    battery_output = battery_cmd.stdout.strip()
                    level = 'Unknown'
                    for line in battery_output.split('\n'):
                        # Look for the level line in the output
                        if 'level:' in line or 'level =' in line:
                            parts = line.split(':' if ':' in line else '=')
                            if len(parts) > 1:
                                level_str = parts[1].strip()
                                # Make sure it's a number
                                if level_str.isdigit():
                                    level = level_str
                                    break
                    
                    if level != 'Unknown':
                        device_info['battery'] = f"{level}%"
                    else:
                        # Fallback method for some devices
                        battery_cmd2 = subprocess.run(
                            [adb_cmd, '-s', serial, 'shell', 'cat', '/sys/class/power_supply/battery/capacity'], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=5
                        )
                        if battery_cmd2.returncode == 0:
                            level = battery_cmd2.stdout.strip()
                            if level.isdigit():
                                device_info['battery'] = f"{level}%"
                except Exception as e:
                    device_info['battery'] = 'Unknown'
            
            # Get storage info
            storage_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'df', '/storage/emulated/0'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if storage_cmd.returncode == 0:
                try:
                    # Parse df output
                    lines = storage_cmd.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        if len(parts) >= 4:
                            total = int(parts[1]) / (1024*1024)  # Convert to GB
                            used = int(parts[2]) / (1024*1024)   # Convert to GB
                            device_info['storage'] = f"{used:.1f} GB used / {total:.1f} GB total"
                except Exception:
                    device_info['storage'] = 'Unknown'
            
            # Get RAM info
            ram_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'cat', '/proc/meminfo'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if ram_cmd.returncode == 0:
                try:
                    ram_output = ram_cmd.stdout.strip()
                    # Parse the MemTotal line
                    for line in ram_output.split('\n'):
                        if 'MemTotal' in line:
                            mem_kb = int(line.split(':')[1].strip().split()[0])
                            total_ram_gb = mem_kb / (1024*1024)  # Convert KB to GB
                            device_info['ram'] = f"{total_ram_gb:.1f} GB"
                            break
                except Exception:
                    device_info['ram'] = 'Unknown'
            
            # Get CPU info
            cpu_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'getprop', 'ro.product.cpu.abi'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if cpu_cmd.returncode == 0:
                device_info['cpu'] = cpu_cmd.stdout.strip()
            
            # Get screen resolution
            screen_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'wm', 'size'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if screen_cmd.returncode == 0:
                try:
                    # Format: "Physical size: WIDTHxHEIGHT"
                    screen_output = screen_cmd.stdout.strip()
                    if 'size:' in screen_output:
                        resolution = screen_output.split('size:')[1].strip()
                        device_info['resolution'] = resolution
                except Exception:
                    device_info['resolution'] = 'Unknown'
            
            # Get kernel version
            kernel_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'uname', '-r'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if kernel_cmd.returncode == 0:
                device_info['kernel'] = kernel_cmd.stdout.strip()
                
            # Try multiple methods to get IMEI (comprehensive approach)
            try:
                # Method 1: User-suggested dialer method with OCR
                # This is a clever approach that works on most devices regardless of Android version
                self.log_message("Trying dialer code method to get IMEI...")
                
                # Create a temporary directory for the screenshot
                temp_dir = tempfile.mkdtemp()
                screenshot_path = os.path.join(temp_dir, "imei_screen.png")
                
                # Launch the dialer with *#06# code (shows IMEI on most phones)
                # First, launch the dialer app
                subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'am', 'start', '-a', 'android.intent.action.DIAL'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                # Wait 2 seconds for the dialer to fully load (helps with slow phones)
                time.sleep(2)
                
                # Now dial the IMEI code
                dial_cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'am', 'start', '-a', 'android.intent.action.DIAL', '-d', 'tel:*#06#'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if dial_cmd.returncode == 0:
                    # Wait for the IMEI info to appear
                    time.sleep(2)
                    
                    # Take a screenshot
                    screenshot_cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'exec-out', 'screencap', '-p'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10
                    )
                    
                    if screenshot_cmd.returncode == 0 and screenshot_cmd.stdout:
                        # Save the screenshot
                        with open(screenshot_path, 'wb') as f:
                            f.write(screenshot_cmd.stdout)
                        
                        # Check if tesseract is installed
                        try:
                            # Use tesseract to extract text from the screenshot
                            ocr_cmd = subprocess.run(
                                ['tesseract', screenshot_path, 'stdout'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                timeout=15
                            )
                            
                            if ocr_cmd.returncode == 0:
                                # Process the OCR output to find IMEI
                                ocr_text = ocr_cmd.stdout.strip()
                                self.log_message("OCR text extracted from dialer screen.")
                                
                                # Look for IMEI pattern in the text (15 digit number)
                                # IMEI is typically shown with "IMEI:" or similar prefix, or as a 15-digit number
                                imei = None
                                
                                # Look for lines with IMEI label
                                for line in ocr_text.split('\n'):
                                    # Try to extract IMEI from line with IMEI label
                                    if 'IMEI' in line.upper() or 'Device ID' in line:
                                        # Extract digits after IMEI label
                                        digits = ''.join(c for c in line if c.isdigit())
                                        if len(digits) >= 14:  # IMEI should be at least 14 digits
                                            imei = digits
                                            break
                                            
                                # If no labeled IMEI found, look for 15-digit number
                                if not imei:
                                    import re
                                    # Look for 14-16 digit numbers in the text
                                    imei_matches = re.findall(r'\b\d{14,16}\b', ocr_text)
                                    if imei_matches:
                                        # Use the first match that looks like an IMEI
                                        for match in imei_matches:
                                            if 14 <= len(match) <= 16:  # IMEI is typically 15 digits but allow some flexibility
                                                imei = match
                                                break
                                
                                if imei:
                                    self.log_message("IMEI found in OCR text!")
                                    device_info['imei'] = imei
                                    
                        except Exception as e:
                            self.log_message(f"OCR processing error: {str(e)}")
                        
                        # Clean up the temporary file
                        try:
                            os.remove(screenshot_path)
                            os.rmdir(temp_dir)
                        except:
                            pass  # Ignore cleanup errors
                
                # Fallback methods if OCR approach didn't work
                # Method 2: service call iphonesubinfo (reliable for older devices)
                if 'imei' not in device_info:
                    self.log_message("Trying service call method for IMEI...")
                    imei_cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'service', 'call', 'iphonesubinfo', '1'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    if imei_cmd.returncode == 0:
                        imei_output = imei_cmd.stdout.strip()
                        # Extract IMEI from service call output (complex parsing)
                        imei = ''
                        parcel_found = False
                        for line in imei_output.split('\n'):
                            if not parcel_found and 'Parcel' in line:
                                parcel_found = True
                            elif parcel_found:
                                # Extract digits from hex values in the output
                                hex_values = line.strip().split()
                                for hex_val in hex_values:
                                    if hex_val.startswith("'") and hex_val.endswith("'"):
                                        char = hex_val.strip("'")
                                        if char.isdigit():
                                            imei += char
                                    elif len(hex_val) == 2 and hex_val != '00':
                                        try:
                                            char = chr(int(hex_val, 16))
                                            if char.isdigit():
                                                imei += char
                                        except:
                                            pass
                        
                        # Clean up IMEI - some devices return garbage with the IMEI
                        if imei and len(imei) >= 14:
                            # Extract only digits from the string
                            imei = ''.join(c for c in imei if c.isdigit())
                            if len(imei) >= 14:  # IMEI should be about 15 digits
                                device_info['imei'] = imei
                
                # Method 3: dumpsys iphonesubinfo (works on some devices)
                if 'imei' not in device_info:
                    self.log_message("Trying dumpsys method for IMEI...")
                    imei_cmd2 = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'dumpsys', 'iphonesubinfo'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    if imei_cmd2.returncode == 0:
                        imei_output = imei_cmd2.stdout.strip()
                        for line in imei_output.split('\n'):
                            if 'Device ID' in line or 'IMEI' in line:
                                parts = line.split('=' if '=' in line else ':')
                                if len(parts) > 1:
                                    imei = parts[1].strip()
                                    # Check if it looks like a valid IMEI
                                    if imei and len(imei) >= 14 and imei.isdigit():
                                        device_info['imei'] = imei
                                        break
            except Exception as e:
                self.log_message(f"Error getting IMEI: {str(e)}")
                # Don't set imei here, will fall back to device_id if needed
                
            # Fallback: Try to get Android ID if IMEI is not available
            if 'imei' not in device_info:
                try:
                    android_id_cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'settings', 'get', 'secure', 'android_id'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    if android_id_cmd.returncode == 0:
                        android_id = android_id_cmd.stdout.strip()
                        if android_id and len(android_id) > 8:
                            device_info['device_id'] = android_id
                except Exception:
                    pass  # Ignore errors
            
            return device_info
            
        except Exception as e:
            self.log_message(f"Error getting device info: {str(e)}")
            return None
        
    def refresh_device_list(self):
        """Refresh the list of available Android devices"""
        self._run_in_thread(self._refresh_device_list_task)
        
    def _refresh_device_list_task(self):
        """Worker thread to refresh the device list"""
        try:
            self.update_status("Refreshing device list...")
            self.log_message("Refreshing list of connected Android devices...")
            
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Clear the device listbox
            ThreadSafeUIUpdater.safe_update(self, lambda: self.device_listbox.delete(0, tk.END))
            
            # Run ADB devices command
            result = subprocess.run(
                [adb_cmd, 'devices', '-l'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                self.log_message(f"Error getting device list: {result.stderr.strip()}")
                self.update_status("Failed to get device list")
                return
                
            # Parse the output to get device list
            lines = result.stdout.strip().split('\n')
            
            # Skip the first line (header)
            if len(lines) > 1:
                devices = []
                for line in lines[1:]:  # Skip header line
                    if line.strip():  # Skip empty lines
                        # Format: serial_number device product:model_name device:name
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            serial = parts[0]
                            status = parts[1]
                            
                            # Get additional info if available
                            device_info = {
                                'serial': serial,
                                'status': status,
                                'details': ' '.join(parts[2:]) if len(parts) > 2 else ''
                            }
                            
                            # Only add devices that are fully connected (not 'offline' or 'unauthorized')
                            if status == 'device':
                                devices.append(device_info)
                
                # Update the listbox with devices
                if devices:
                    for idx, device in enumerate(devices):
                        display_text = f"{device['serial']}"
                        if device['details']:
                            # Extract model info if available
                            model_info = ''
                            for detail in device['details'].split():
                                if detail.startswith('model:'):
                                    model_info = detail.split(':', 1)[1]
                                    break
                            
                            if model_info:
                                display_text = f"{model_info} ({device['serial']})"
                        
                        ThreadSafeUIUpdater.safe_update(self, lambda t=display_text: self.device_listbox.insert(tk.END, t))
                    
                    self.log_message(f"Found {len(devices)} connected device(s)")
                    self.update_status(f"{len(devices)} device(s) found")
                else:
                    self.log_message("No connected devices found")
                    self.update_status("No devices found")
            else:
                self.log_message("No connected devices found")
                self.update_status("No devices found")
                
        except Exception as e:
            self.log_message(f"Error refreshing device list: {str(e)}")
            self.update_status("Failed to refresh device list")
        
    def update_device_info(self):
        """Update the device info display with the connected device information"""
        if not self.device_info:
            return
            
        # Update basic info fields
        if 'model' in self.device_info:
            self.info_fields['Model'].set(self.device_info['model'])
        
        if 'manufacturer' in self.device_info:
            self.info_fields['Manufacturer'].set(self.device_info['manufacturer'])
            
        if 'android_version' in self.device_info:
            self.info_fields['Android Version'].set(self.device_info['android_version'])
            
        # Make sure we only show the serial number, not the debug info
        if 'serial' in self.device_info:
            # Get just the serial number without any extra text
            serial = str(self.device_info['serial']).strip()
            # Remove any ADB debug text that might be associated with it
            if '\n' in serial:
                serial = serial.split('\n')[0].strip()
            self.info_fields['Serial Number'].set(serial)
            
        if 'battery' in self.device_info:
            self.info_fields['Battery Level'].set(self.device_info['battery'])
            
        # Display IMEI if available
        if 'imei' in self.device_info:
            self.info_fields['IMEI'].set(self.device_info['imei'])
        # Fallback to Android ID if IMEI not available
        elif 'device_id' in self.device_info:
            self.info_fields['IMEI'].set(f"{self.device_info['device_id']} (Android ID)")
            

        
        # Update advanced info fields
        if 'storage' in self.device_info:
            self.adv_info_fields['Storage'].set(self.device_info['storage'])
            
        if 'ram' in self.device_info:
            self.adv_info_fields['RAM'].set(self.device_info['ram'])
            
        if 'resolution' in self.device_info:
            self.adv_info_fields['Screen Resolution'].set(self.device_info['resolution'])
            
        if 'cpu' in self.device_info:
            self.adv_info_fields['CPU'].set(self.device_info['cpu'])
            
        if 'kernel' in self.device_info:
            self.adv_info_fields['Kernel'].set(self.device_info['kernel'])
        
    def take_screenshot(self):
        """Take a screenshot of the connected Android device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        self._run_in_thread(self._take_screenshot_task)
        
    def _take_screenshot_task(self):
        """Worker thread to take a screenshot"""
        try:
            self.update_status("Taking screenshot...")
            self.log_message("Taking screenshot of the connected Android device...")
            
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Screenshot failed")
                return
                
            # Create a directory to store screenshots if it doesn't exist
            screenshots_dir = os.path.join(os.path.expanduser("~"), "Nest", "Screenshots", "Android")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Generate a filename based on the current time and device model
            device_model = self.device_info.get('model', 'Android').replace(' ', '_')
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_file = os.path.join(screenshots_dir, f"{device_model}_{timestamp}.png")
            
            # Take the screenshot using ADB
            self.log_message(f"Saving screenshot to: {screenshot_file}")
            
            # Use ADB to take the screenshot and save it to the device's storage
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'screencap', '-p', '/sdcard/screenshot.png'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.log_message(f"Failed to take screenshot: {result.stderr.strip()}")
                self.update_status("Screenshot failed")
                return
                
            # Pull the screenshot from the device to the local machine
            pull_result = subprocess.run(
                [adb_cmd, '-s', serial, 'pull', '/sdcard/screenshot.png', screenshot_file], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if pull_result.returncode != 0:
                self.log_message(f"Failed to transfer screenshot: {pull_result.stderr.strip()}")
                self.update_status("Screenshot transfer failed")
                return
                
            # Clean up the temporary file on the device
            subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'rm', '/sdcard/screenshot.png'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.log_message("Screenshot captured successfully")
            self.update_status("Screenshot saved")
            
            # Show the screenshot in a new window
            ThreadSafeUIUpdater.safe_update(self, lambda: self._show_screenshot(screenshot_file))
            
        except Exception as e:
            self.log_message(f"Error taking screenshot: {str(e)}")
            self.update_status("Screenshot failed")
            messagebox.showerror("Screenshot Error", f"Failed to take screenshot: {str(e)}")
            
    def _show_screenshot(self, screenshot_path):
        """Show the screenshot in a new window"""
        try:
            # Create a new top-level window
            screenshot_window = tk.Toplevel(self)
            screenshot_window.title(f"Android Screenshot - {os.path.basename(screenshot_path)}")
            
            # Load the image using tkinter's PhotoImage
            img = tk.PhotoImage(file=screenshot_path)
            
            # Calculate a reasonable window size (max 80% of screen size)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            
            max_width = int(screen_width * 0.8)
            max_height = int(screen_height * 0.8)
            
            window_width = min(img.width(), max_width)
            window_height = min(img.height(), max_height)
            
            # Set the window size and position
            screenshot_window.geometry(f"{window_width}x{window_height}")
            
            # Center the window on the screen
            x_pos = (screen_width - window_width) // 2
            y_pos = (screen_height - window_height) // 2
            screenshot_window.geometry(f"+{x_pos}+{y_pos}")
            
            # Create a canvas to display the image with scrollbars if needed
            canvas = tk.Canvas(screenshot_window, width=window_width, height=window_height)
            canvas.pack(side="left", fill="both", expand=True)
            
            # Add scrollbars if the image is larger than the window
            if img.width() > window_width or img.height() > window_height:
                h_scrollbar = tk.Scrollbar(screenshot_window, orient="horizontal", command=canvas.xview)
                h_scrollbar.pack(side="bottom", fill="x")
                
                v_scrollbar = tk.Scrollbar(screenshot_window, orient="vertical", command=canvas.yview)
                v_scrollbar.pack(side="right", fill="y")
                
                canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
            
            # Display the image on the canvas
            canvas.create_image(0, 0, anchor="nw", image=img)
            canvas.config(scrollregion=canvas.bbox("all"))
            
            # Keep a reference to the image to prevent garbage collection
            canvas.image = img
            
            # Add a button frame at the bottom
            button_frame = ttk.Frame(screenshot_window)
            button_frame.pack(side="bottom", fill="x", padx=10, pady=5)
            
            # Add buttons for common actions
            screenshots_dir = os.path.dirname(screenshot_path)
            open_btn = ttk.Button(
                button_frame, text="Open Folder",
                command=lambda: self._open_screenshots_folder(screenshots_dir)
            )
            open_btn.pack(side="left", padx=5)
            
            # Add a button to save the screenshot to another location
            save_btn = ttk.Button(
                button_frame, text="Save As",
                command=lambda: self._save_screenshot_as(screenshot_path)
            )
            save_btn.pack(side="left", padx=5)
            
            # Add a close button
            close_btn = ttk.Button(
                button_frame, text="Close",
                command=screenshot_window.destroy
            )
            close_btn.pack(side="right", padx=5)
            
        except Exception as e:
            self.log_message(f"Error displaying screenshot: {str(e)}")
            messagebox.showerror("Display Error", f"Failed to display screenshot: {str(e)}")
            
    def _open_screenshots_folder(self, folder_path):
        """Open the screenshots folder in the file explorer"""
        try:
            if IS_WINDOWS:
                os.startfile(folder_path)
            else:
                # For Linux/Mac
                if platform.system().lower() == 'darwin':  # macOS
                    subprocess.run(['open', folder_path])
                else:  # Linux
                    subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            self.log_message(f"Error opening screenshots folder: {str(e)}")
            
    def _save_screenshot_as(self, source_path):
        """Save the screenshot to another location"""
        try:
            # Ask for the save location
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                initialfile=os.path.basename(source_path)
            )
            
            if save_path:
                # Copy the file
                shutil.copy2(source_path, save_path)
                self.log_message(f"Screenshot saved to: {save_path}")
        except Exception as e:
            self.log_message(f"Error saving screenshot: {str(e)}")
            messagebox.showerror("Save Error", f"Failed to save screenshot: {str(e)}")

        
    def backup_device(self):
        """Backup the connected Android device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Ask the user where to save the backup
        backup_path = filedialog.askdirectory(
            title="Select Backup Directory"
        )
        
        if not backup_path:
            # User cancelled the directory selection
            return
            
        # Ask user for backup options
        backup_dialog = tk.Toplevel(self)
        backup_dialog.title("Backup Options")
        backup_dialog.geometry("400x450")  # Increased height to fit all content
        backup_dialog.resizable(False, False)
        
        # Center the dialog
        x_pos = (self.winfo_screenwidth() - 400) // 2
        y_pos = (self.winfo_screenheight() - 450) // 2
        backup_dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Make dialog modal
        backup_dialog.transient(self)
        backup_dialog.grab_set()
        
        # Create main frame
        main_frame = ttk.Frame(backup_dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Title label
        ttk.Label(
            main_frame, text="Android Backup Options", font=("Arial", 12, "bold")
        ).pack(pady=(0, 10))
        
        # Backup options
        options_frame = ttk.LabelFrame(main_frame, text="Backup Content", padding=10)
        options_frame.pack(fill="x", pady=5)
        
        # Checkboxes for backup options
        backup_options = {}
        
        # Apps checkbox
        backup_options['apps'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Apps and App Data",
            variable=backup_options['apps']
        ).pack(anchor="w", pady=2)
        
        # System settings checkbox
        backup_options['system'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="System Settings",
            variable=backup_options['system']
        ).pack(anchor="w", pady=2)
        
        # Media checkbox
        backup_options['media'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, text="Media (Photos, Videos, Music)",
            variable=backup_options['media']
        ).pack(anchor="w", pady=2)
        
        # Documents checkbox
        backup_options['documents'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, text="Documents and Downloads",
            variable=backup_options['documents']
        ).pack(anchor="w", pady=2)
        
        # Shared storage checkbox
        backup_options['shared'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, text="Shared Storage",
            variable=backup_options['shared']
        ).pack(anchor="w", pady=2)
        
        # Advanced options
        adv_frame = ttk.LabelFrame(main_frame, text="Advanced Options", padding=10)
        adv_frame.pack(fill="x", pady=5)
        
        # Encrypt backup checkbox
        backup_options['encrypt'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            adv_frame, text="Encrypt Backup (Password Protected)",
            variable=backup_options['encrypt']
        ).pack(anchor="w", pady=2)
        
        # Add more space before buttons
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=10)
        
        # Create a container for the buttons to ensure they're visible
        btn_container = ttk.Frame(buttons_frame)
        btn_container.pack(fill="x")
        
        # Cancel button
        cancel_btn = ttk.Button(
            btn_container, text="Cancel", width=15,
            command=backup_dialog.destroy
        )
        cancel_btn.pack(side="right", padx=5)
        
        # Start backup button
        start_btn = ttk.Button(
            btn_container, text="Start Backup", width=15,
            command=lambda: self._start_backup(backup_dialog, backup_path, backup_options)
        )
        start_btn.pack(side="right", padx=5)
        
        # Wait for the dialog to be closed
        self.wait_window(backup_dialog)
        
    def _start_backup(self, dialog, backup_path, options):
        """Start the backup process"""
        # Close the dialog
        dialog.destroy()
        
        # Start the backup in a separate thread
        self._run_in_thread(lambda: self._backup_task(backup_path, options))
        
    def _backup_task(self, backup_path, options):
        """Worker thread to perform the Android device backup"""
        try:
            self.update_status("Backing up device...")
            self.log_message("Starting Android device backup...")
            
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Backup failed")
                return
                
            # Create backup directory with timestamp
            device_model = self.device_info.get('model', 'Android').replace(' ', '_')
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(backup_path, f"{device_model}_{timestamp}_backup")
            os.makedirs(backup_folder, exist_ok=True)
            
            self.log_message(f"Saving backup to: {backup_folder}")
            
            # Build the adb backup command options
            backup_flags = []
            
            # Add options based on user selections
            if options['apps'].get():
                backup_flags.append("-apk")  # Include .apk files in the backup
                backup_flags.append("-all")  # Backup all installed applications
            
            if options['system'].get():
                backup_flags.append("-system")  # Include system applications
            
            if options['shared'].get():
                backup_flags.append("-shared")  # Include shared storage
            
            # Use Android Backup instead (full backup to PC)
            backup_file = os.path.join(backup_folder, "backup.ab")
            
            # Starting the device backup using adb backup
            # Note: Modern Android versions may limit what ADB backup can access
            cmd = [adb_cmd, '-s', serial, 'backup']
            
            # Add backup flags
            cmd.extend(backup_flags)
            
            # Add output file
            cmd.extend(["-f", backup_file])
            
            self.log_message("Starting ADB backup (you may need to confirm on your device)")
            self.update_status("Backup in progress...")
            
            # Show notification to user
            ThreadSafeUIUpdater.safe_update(self, lambda: messagebox.showinfo(
                "Backup Started",
                "The backup process has started. You may need to unlock your device and confirm the backup.\n\n"
                "Please DO NOT disconnect your device until the backup is complete."
            ))
            
            # Run the backup command
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                self.log_message(f"Backup failed: {result.stderr.strip()}")
                self.update_status("Backup failed")
                messagebox.showerror("Backup Error", f"Failed to backup device: {result.stderr.strip()}")
                return
            
            # Additionally, copy files if media or documents options selected
            if options['media'].get() or options['documents'].get():
                self._backup_files(adb_cmd, serial, backup_folder, options)
                
            # Create a backup info file
            self._create_backup_info(backup_folder, options)
            
            self.log_message("Device backup completed successfully")
            self.update_status("Backup completed")
            
            messagebox.showinfo(
                "Backup Complete",
                f"Your device has been successfully backed up to:\n{backup_folder}"
            )
            
        except subprocess.TimeoutExpired:
            self.log_message("Backup timeout - this may be normal if the backup is large")
            self.update_status("Backup in progress on device")
            messagebox.showinfo(
                "Backup In Progress",
                "The backup is being processed on your device. This may take some time.\n\n"
                "You will need to confirm the backup on your device and wait for it to complete."
            )
        except Exception as e:
            self.log_message(f"Error during backup: {str(e)}")
            self.update_status("Backup failed")
            messagebox.showerror("Backup Error", f"Failed to backup device: {str(e)}")
            
    def _backup_files(self, adb_cmd, serial, backup_folder, options):
        """Backup files from the device"""
        try:
            if options['media'].get():
                # Create media folders
                media_folder = os.path.join(backup_folder, "Media")
                os.makedirs(os.path.join(media_folder, "Pictures"), exist_ok=True)
                os.makedirs(os.path.join(media_folder, "Videos"), exist_ok=True)
                os.makedirs(os.path.join(media_folder, "Music"), exist_ok=True)
                
                # Pull media files
                self.log_message("Backing up photos...")
                self.update_status("Backing up photos...")
                
                # Pictures
                subprocess.run(
                    [adb_cmd, '-s', serial, 'pull', '/sdcard/DCIM', os.path.join(media_folder, "Pictures")],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Videos
                subprocess.run(
                    [adb_cmd, '-s', serial, 'pull', '/sdcard/Movies', os.path.join(media_folder, "Videos")],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Music
                subprocess.run(
                    [adb_cmd, '-s', serial, 'pull', '/sdcard/Music', os.path.join(media_folder, "Music")],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
            if options['documents'].get():
                # Create documents folder
                docs_folder = os.path.join(backup_folder, "Documents")
                os.makedirs(docs_folder, exist_ok=True)
                
                # Pull documents
                self.log_message("Backing up documents...")
                self.update_status("Backing up documents...")
                
                # Documents
                subprocess.run(
                    [adb_cmd, '-s', serial, 'pull', '/sdcard/Documents', docs_folder],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Downloads
                subprocess.run(
                    [adb_cmd, '-s', serial, 'pull', '/sdcard/Download', docs_folder],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
        except Exception as e:
            self.log_message(f"Error backing up files: {str(e)}")
            
    def _create_backup_info(self, backup_folder, options):
        """Create a backup info file with details about the backup"""
        try:
            # Create backup info
            backup_info = {
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'device_info': self.device_info,
                'backup_options': {k: v.get() for k, v in options.items() if hasattr(v, 'get')}
            }
            
            # Save backup info to a JSON file
            info_file = os.path.join(backup_folder, "backup_info.json")
            with open(info_file, 'w') as f:
                json.dump(backup_info, f, indent=4)
                
        except Exception as e:
            self.log_message(f"Error creating backup info: {str(e)}")
        
    def manage_files(self):
        """Manage files on the connected Android device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create a file manager window
        file_manager = tk.Toplevel(self)
        file_manager.title("Android File Manager")
        file_manager.geometry("950x600")
        file_manager.minsize(800, 500)
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 950) // 2
        y_pos = (self.winfo_screenheight() - 600) // 2
        file_manager.geometry(f"+{x_pos}+{y_pos}")
        
        # Initialize variables
        self.android_path = tk.StringVar(value="/sdcard")  # Default to external storage
        self.local_path = tk.StringVar(value=os.path.expanduser("~"))  # Default to user home
        self.fm_status = tk.StringVar(value="Ready")
        
        # Main frame
        main_frame = ttk.Frame(file_manager, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Device info bar
        device_frame = ttk.Frame(main_frame)
        device_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            device_frame, 
            text=f"Device: {self.device_info.get('model')} ({self.device_info.get('serial')})", 
            font=("Arial", 10, "bold")
        ).pack(side="left")
        
        ttk.Label(
            device_frame, 
            textvariable=self.fm_status
        ).pack(side="right")
        
        # Create paned window for split view
        paned = ttk.PanedWindow(main_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)
        
        # --------------- LOCAL FILES FRAME ---------------
        local_frame = ttk.LabelFrame(paned, text="Local Files", padding=10)
        paned.add(local_frame, weight=1)
        
        # Local path navigation frame
        local_nav = ttk.Frame(local_frame)
        local_nav.pack(fill="x", pady=(0, 5))
        
        # Local location entry
        ttk.Label(local_nav, text="Location:").pack(side="left", padx=(0, 5))
        local_path_entry = ttk.Entry(local_nav, textvariable=self.local_path, width=40)
        local_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Navigate button
        ttk.Button(
            local_nav, text="Go", width=5,
            command=lambda: self._refresh_local_files(local_files_tree)
        ).pack(side="left")
        
        # Home button
        ttk.Button(
            local_nav, text="Home", width=8,
            command=lambda: [self.local_path.set(os.path.expanduser("~")), self._refresh_local_files(local_files_tree)]
        ).pack(side="left", padx=5)
        
        # Up button
        ttk.Button(
            local_nav, text="Up", width=5,
            command=lambda: [self.local_path.set(os.path.dirname(self.local_path.get())), self._refresh_local_files(local_files_tree)]
        ).pack(side="left")
        
        # Local files tree
        local_files_frame = ttk.Frame(local_frame)
        local_files_frame.pack(fill="both", expand=True)
        
        # Add scrollbar
        local_scrollbar = ttk.Scrollbar(local_files_frame)
        local_scrollbar.pack(side="right", fill="y")
        
        # File tree
        local_files_tree = FixedHeaderTreeview(
            local_files_frame,
            columns=("size", "date"),
            yscrollcommand=local_scrollbar.set
        )
        local_files_tree.pack(side="left", fill="both", expand=True)
        
        # Set scrollbar command
        local_scrollbar.config(command=local_files_tree.yview)
        
        # Configure columns
        local_files_tree.column("#0", width=250, minwidth=150)
        local_files_tree.column("size", width=100, minwidth=80, anchor="e")
        local_files_tree.column("date", width=150, minwidth=100)
        
        # Configure headers
        local_files_tree.heading("#0", text="Name")
        local_files_tree.heading("size", text="Size")
        local_files_tree.heading("date", text="Date Modified")
        
        # Local button bar
        local_btn_frame = ttk.Frame(local_frame)
        local_btn_frame.pack(fill="x", pady=(5, 0))
        
        # Local buttons
        ttk.Button(
            local_btn_frame, text="Refresh",
            command=lambda: self._refresh_local_files(local_files_tree)
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            local_btn_frame, text="Upload to Device",
            command=lambda: self._upload_to_device(local_files_tree, android_files_tree)
        ).pack(side="left")
        
        # --------------- ANDROID FILES FRAME ---------------
        android_frame = ttk.LabelFrame(paned, text="Android Device Files", padding=10)
        paned.add(android_frame, weight=1)
        
        # Android path navigation frame
        android_nav = ttk.Frame(android_frame)
        android_nav.pack(fill="x", pady=(0, 5))
        
        # Android location entry
        ttk.Label(android_nav, text="Location:").pack(side="left", padx=(0, 5))
        android_path_entry = ttk.Entry(android_nav, textvariable=self.android_path, width=40)
        android_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Navigate button
        ttk.Button(
            android_nav, text="Go", width=5,
            command=lambda: self._refresh_android_files(android_files_tree)
        ).pack(side="left")
        
        # Standard locations dropdown
        locations = [
            "/sdcard",
            "/sdcard/DCIM",
            "/sdcard/Download",
            "/sdcard/Pictures",
            "/sdcard/Movies",
            "/sdcard/Music",
            "/sdcard/Documents"
        ]
        
        # Create variable and combobox
        location_var = tk.StringVar()
        location_dropdown = ttk.Combobox(
            android_nav, textvariable=location_var,
            values=locations, width=15, state="readonly"
        )
        location_dropdown.pack(side="left", padx=5)
        
        # Bind selection event
        location_dropdown.bind(
            "<<ComboboxSelected>>",
            lambda e: [self.android_path.set(location_var.get()), self._refresh_android_files(android_files_tree)]
        )
        
        # Up button
        ttk.Button(
            android_nav, text="Up", width=5,
            command=lambda: [
                self.android_path.set(os.path.dirname(self.android_path.get()) or "/"), 
                self._refresh_android_files(android_files_tree)
            ]
        ).pack(side="left")
        
        # Android files tree
        android_files_frame = ttk.Frame(android_frame)
        android_files_frame.pack(fill="both", expand=True)
        
        # Add scrollbar
        android_scrollbar = ttk.Scrollbar(android_files_frame)
        android_scrollbar.pack(side="right", fill="y")
        
        # File tree
        android_files_tree = FixedHeaderTreeview(
            android_files_frame,
            columns=("size", "date"),
            yscrollcommand=android_scrollbar.set
        )
        android_files_tree.pack(side="left", fill="both", expand=True)
        
        # Set scrollbar command
        android_scrollbar.config(command=android_files_tree.yview)
        
        # Configure columns
        android_files_tree.column("#0", width=250, minwidth=150)
        android_files_tree.column("size", width=100, minwidth=80, anchor="e")
        android_files_tree.column("date", width=150, minwidth=100)
        
        # Configure headers
        android_files_tree.heading("#0", text="Name")
        android_files_tree.heading("size", text="Size")
        android_files_tree.heading("date", text="Date Modified")
        
        # Android button bar
        android_btn_frame = ttk.Frame(android_frame)
        android_btn_frame.pack(fill="x", pady=(5, 0))
        
        # Android buttons
        ttk.Button(
            android_btn_frame, text="Refresh",
            command=lambda: self._refresh_android_files(android_files_tree)
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            android_btn_frame, text="Download to PC",
            command=lambda: self._download_from_device(android_files_tree, local_files_tree)
        ).pack(side="left")
        
        # Initialize file listings
        self._refresh_local_files(local_files_tree)
        self._refresh_android_files(android_files_tree)
        
        # Set up double-click to navigate directories
        local_files_tree.bind("<Double-1>", lambda e: self._on_local_double_click(e, local_files_tree))
        android_files_tree.bind("<Double-1>", lambda e: self._on_android_double_click(e, android_files_tree))
        
    def _refresh_local_files(self, tree):
        """Refresh the local files tree"""
        # Clear the tree
        for item in tree.get_children():
            tree.delete(item)
            
        # Get the current path
        current_path = self.local_path.get()
        
        # Check if the path exists
        if not os.path.exists(current_path):
            messagebox.showerror("Invalid Path", f"The path {current_path} does not exist.")
            self.local_path.set(os.path.expanduser("~"))  # Reset to home directory
            current_path = self.local_path.get()
            
        try:
            # Add parent directory entry
            tree.insert("", "end", text="..", values=("<DIR>", ""), image="", tags=("dir",))
            
            # Add directories first
            dirs = []
            files = []
            
            for item in os.listdir(current_path):
                full_path = os.path.join(current_path, item)
                
                try:
                    # Get file info
                    stats = os.stat(full_path)
                    size = stats.st_size
                    modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats.st_mtime))
                    
                    if os.path.isdir(full_path):
                        dirs.append((item, "<DIR>", modified))
                    else:
                        # Format size
                        size_str = self._format_size(size)
                        files.append((item, size_str, modified))
                except Exception:
                    # Skip files with access issues
                    pass
            
            # Sort dirs and files
            dirs.sort(key=lambda x: x[0].lower())
            files.sort(key=lambda x: x[0].lower())
            
            # Add to tree
            for name, size, date in dirs:
                tree.insert("", "end", text=name, values=(size, date), tags=("dir",))
                
            for name, size, date in files:
                tree.insert("", "end", text=name, values=(size, date), tags=("file",))
                
            # Update status
            self.fm_status.set(f"Local: {len(dirs)} dirs, {len(files)} files")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error reading directory: {str(e)}")
            
    def _refresh_android_files(self, tree):
        """Refresh the Android files tree"""
        # Clear the tree
        for item in tree.get_children():
            tree.delete(item)
            
        try:
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                return
                
            # Get the current path
            current_path = self.android_path.get()
            
            # Add parent directory entry
            tree.insert("", "end", text="..", values=("<DIR>", ""), tags=("dir",))
            
            # List directories first, then files
            dirs = []
            files = []
            
            # Execute ls -la command to get file details
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', f"ls -la {current_path}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Path might not exist or no permissions
                self.log_message(f"Error listing files: {result.stderr.strip()}")
                self.fm_status.set("Error listing files")
                return
                
            # Process the output line by line
            lines = result.stdout.strip().split("\n")
            
            # Skip the first line (total) if it exists
            if lines and lines[0].startswith("total"):
                lines = lines[1:]
                
            for line in lines:
                parts = line.split()
                if len(parts) >= 8:
                    # Parse ls -la output format
                    perms = parts[0]
                    # size = parts[4]
                    # date1, date2, date3 = parts[5:8]
                    
                    # Extract file name (can contain spaces)
                    if len(parts) > 8:
                        name = " ".join(parts[8:])
                    else:
                        name = parts[8]
                        
                    # Skip . and .. entries from device output
                    if name == "." or name == "..":
                        continue
                        
                    # Get file size
                    size = parts[4]
                    
                    # Get date: combine date parts
                    date = " ".join(parts[5:8])
                    
                    # Check if it's a directory
                    if perms.startswith("d"):
                        dirs.append((name, "<DIR>", date))
                    else:
                        # Format size
                        size_str = self._format_size(int(size))
                        files.append((name, size_str, date))
            
            # Sort and add to tree
            dirs.sort(key=lambda x: x[0].lower())
            files.sort(key=lambda x: x[0].lower())
            
            # Add to tree
            for name, size, date in dirs:
                tree.insert("", "end", text=name, values=(size, date), tags=("dir",))
                
            for name, size, date in files:
                tree.insert("", "end", text=name, values=(size, date), tags=("file",))
                
            # Update status
            self.fm_status.set(f"Android: {len(dirs)} dirs, {len(files)} files")
            
        except Exception as e:
            self.log_message(f"Error refreshing Android files: {str(e)}")
            self.fm_status.set("Error listing files")
            
    def _on_local_double_click(self, event, tree):
        """Handle double-click on local files tree"""
        # Get the selected item
        selection = tree.selection()
        if not selection:
            return
            
        # Get the clicked item's text (directory name)
        item_id = selection[0]
        item_text = tree.item(item_id, "text")
        
        # Get item type (directory or file)
        item_tags = tree.item(item_id, "tags")
        if "dir" not in item_tags:
            return  # Not a directory, nothing to do
            
        # Handle parent directory
        if item_text == "..":
            new_path = os.path.dirname(self.local_path.get())
            self.local_path.set(new_path)
        else:
            # Navigate to subdirectory
            new_path = os.path.join(self.local_path.get(), item_text)
            self.local_path.set(new_path)
            
        # Refresh the tree
        self._refresh_local_files(tree)
        
    def _on_android_double_click(self, event, tree):
        """Handle double-click on Android files tree"""
        # Get the selected item
        selection = tree.selection()
        if not selection:
            return
            
        # Get the clicked item's text (directory name)
        item_id = selection[0]
        item_text = tree.item(item_id, "text")
        
        # Get item type (directory or file)
        item_tags = tree.item(item_id, "tags")
        if "dir" not in item_tags:
            return  # Not a directory, nothing to do
            
        # Handle parent directory
        if item_text == "..":
            current_path = self.android_path.get()
            # Ensure we don't go above root
            if current_path == "/":
                return
                
            new_path = os.path.dirname(current_path)
            # Handle empty path (root directory)
            if not new_path:
                new_path = "/"
                
            self.android_path.set(new_path)
        else:
            # Navigate to subdirectory
            new_path = os.path.join(self.android_path.get(), item_text)
            self.android_path.set(new_path)
            
        # Refresh the tree
        self._refresh_android_files(tree)
        
    def _upload_to_device(self, local_tree, android_tree):
        """Upload selected file from PC to Android device"""
        # Get selected local file
        selection = local_tree.selection()
        if not selection:
            messagebox.showinfo("No File Selected", "Please select a file to upload.")
            return
            
        # Get selected items
        item_ids = local_tree.selection()
        
        # Prepare for upload
        for item_id in item_ids:
            item_text = local_tree.item(item_id, "text")
            
            # Skip parent directory
            if item_text == "..":
                continue
                
            # Get item type (directory or file)
            item_tags = local_tree.item(item_id, "tags")
            
            # Source path
            source_path = os.path.join(self.local_path.get(), item_text)
            
            # Target path on device
            target_path = self.android_path.get()
            
            # Start upload in a thread to keep UI responsive
            self._run_in_thread(lambda src=source_path, tgt=target_path, is_dir="dir" in item_tags: 
                               self._upload_file_task(src, tgt, is_dir, android_tree))
            
    def _upload_file_task(self, source_path, target_path, is_directory, tree):
        """Worker thread to upload file/directory to device"""
        try:
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                return
                
            # Get file/dir name
            name = os.path.basename(source_path)
            
            # Update status
            self.fm_status.set(f"Uploading {name}...")
            self.log_message(f"Uploading {name} to {target_path}...")
            
            # Run adb push command
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'push', source_path, target_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 minute timeout for large files
            )
            
            if result.returncode != 0:
                self.log_message(f"Upload failed: {result.stderr.strip()}")
                self.fm_status.set("Upload failed")
                messagebox.showerror("Upload Error", f"Failed to upload {name}: {result.stderr.strip()}")
                return
                
            self.log_message(f"Upload of {name} completed successfully")
            self.fm_status.set("Upload complete")
            
            # Refresh the Android files list
            ThreadSafeUIUpdater.safe_update(self, lambda: self._refresh_android_files(tree))
            
        except Exception as e:
            self.log_message(f"Error during upload: {str(e)}")
            self.fm_status.set("Upload failed")
            messagebox.showerror("Upload Error", f"Failed to upload file: {str(e)}")
            
    def _download_from_device(self, android_tree, local_tree):
        """Download selected file from Android device to PC"""
        # Get selected Android file
        selection = android_tree.selection()
        if not selection:
            messagebox.showinfo("No File Selected", "Please select a file to download.")
            return
            
        # Get selected items
        item_ids = android_tree.selection()
        
        # Prepare for download
        for item_id in item_ids:
            item_text = android_tree.item(item_id, "text")
            
            # Skip parent directory
            if item_text == "..":
                continue
                
            # Get item type (directory or file)
            item_tags = android_tree.item(item_id, "tags")
            
            # Source path on device
            source_path = os.path.join(self.android_path.get(), item_text)
            
            # Target path on PC
            target_path = self.local_path.get()
            
            # Start download in a thread to keep UI responsive
            self._run_in_thread(lambda src=source_path, tgt=target_path, is_dir="dir" in item_tags: 
                               self._download_file_task(src, tgt, is_dir, local_tree))
            
    def _download_file_task(self, source_path, target_path, is_directory, tree):
        """Worker thread to download file/directory from device"""
        try:
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                return
                
            # Get file/dir name
            name = os.path.basename(source_path)
            
            # Update status
            self.fm_status.set(f"Downloading {name}...")
            self.log_message(f"Downloading {name} to {target_path}...")
            
            # Run adb pull command
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'pull', source_path, target_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 minute timeout for large files
            )
            
            if result.returncode != 0:
                self.log_message(f"Download failed: {result.stderr.strip()}")
                self.fm_status.set("Download failed")
                messagebox.showerror("Download Error", f"Failed to download {name}: {result.stderr.strip()}")
                return
                
            self.log_message(f"Download of {name} completed successfully")
            self.fm_status.set("Download complete")
            
            # Refresh the local files list
            ThreadSafeUIUpdater.safe_update(self, lambda: self._refresh_local_files(tree))
            
        except Exception as e:
            self.log_message(f"Error during download: {str(e)}")
            self.fm_status.set("Download failed")
            messagebox.showerror("Download Error", f"Failed to download file: {str(e)}")
            
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        # Define unit prefixes
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        
        # Handle zero size
        if size_bytes == 0:
            return "0 B"
            
        # Calculate appropriate unit
        i = 0
        size = float(size_bytes)
        while size >= 1024.0 and i < len(units) - 1:
            size /= 1024.0
            i += 1
            
        # Return formatted size with unit
        return f"{size:.2f} {units[i]}"
        
    def install_apk(self):
        """Install an APK on the connected Android device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Ask for the APK file to install
        apk_path = filedialog.askopenfilename(
            title="Select APK file to install",
            filetypes=[("Android Package", "*.apk"), ("All files", "*.*")]
        )
        
        if not apk_path:
            # User cancelled the file selection
            return
            
        self._run_in_thread(lambda: self._install_apk_task(apk_path))
        
    def _install_apk_task(self, apk_path):
        """Worker thread to install an APK"""
        try:
            self.update_status(f"Installing {os.path.basename(apk_path)}...")
            self.log_message(f"Installing APK: {apk_path}")
            
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Installation failed")
                return
            
            # Install the APK using ADB
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'install', '-r', apk_path], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=60  # Installing APKs can take time
            )
            
            if result.returncode != 0 or 'Failure' in result.stdout:
                self.log_message(f"Failed to install APK: {result.stderr.strip() or result.stdout.strip()}")
                self.update_status("Installation failed")
                messagebox.showerror("Installation Error", 
                                  f"Failed to install APK:\n{result.stderr.strip() or result.stdout.strip()}")
                return
                
            self.log_message("APK installed successfully")
            self.update_status("APK installed")
            messagebox.showinfo("Installation Complete", f"{os.path.basename(apk_path)} was installed successfully.")
            
        except Exception as e:
            self.log_message(f"Error installing APK: {str(e)}")
            self.update_status("Installation failed")
            messagebox.showerror("Installation Error", f"Failed to install APK: {str(e)}")
        
    def app_manager(self):
        """Manage apps on the connected Android device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create a new top-level window for app management
        self._run_in_thread(self._app_manager_task)
        
    def _app_manager_task(self):
        """Worker thread to load app list and show app manager"""
        try:
            self.update_status("Loading app list...")
            self.log_message("Loading list of installed applications...")
            
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Failed to load app list")
                return
                
            # Get list of installed packages
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages', '-3'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=20
            )
            
            if result.returncode != 0:
                self.log_message(f"Failed to get app list: {result.stderr.strip()}")
                self.update_status("Failed to load app list")
                return
                
            # Parse the package list
            packages = []
            for line in result.stdout.strip().split('\n'):
                if line.startswith('package:'):
                    package_name = line[8:].strip()  # Remove 'package:' prefix
                    packages.append(package_name)
            
            # Sort alphabetically
            packages.sort()
            
            self.update_status(f"Found {len(packages)} apps")
            self.log_message(f"Found {len(packages)} user-installed applications")
            
            # Show the app manager window in the main thread
            self.after(0, lambda: self._show_app_manager(packages, serial, adb_cmd))
            
        except Exception as e:
            self.log_message(f"Error loading app list: {str(e)}")
            self.update_status("Failed to load app list")
            
    def _show_app_manager(self, packages, serial, adb_cmd):
        """Show the app manager window"""
        try:
            # Create a new top-level window
            app_window = tk.Toplevel(self)
            app_window.title("Android App Manager")
            app_window.geometry("500x600")
            app_window.minsize(400, 400)
            
            # Center the window
            x_pos = (self.winfo_screenwidth() - 500) // 2
            y_pos = (self.winfo_screenheight() - 600) // 2
            app_window.geometry(f"+{x_pos}+{y_pos}")
            
            # Create a main frame
            main_frame = ttk.Frame(app_window)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Add a label
            ttk.Label(
                main_frame, text=f"Installed Applications ({len(packages)})", font=("Arial", 12, "bold")
            ).pack(anchor="w", pady=(0, 10))
            
            # Create a frame for the search box
            search_frame = ttk.Frame(main_frame)
            search_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
            
            search_var = tk.StringVar()
            search_var.trace_add("write", lambda name, index, mode: self._filter_app_list(
                search_var.get(), packages, app_listbox
            ))
            
            search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
            search_entry.pack(side="left", fill="x", expand=True)
            
            # Create a frame for the app list with scrollbar
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(fill="both", expand=True, pady=(0, 10))
            
            app_listbox = tk.Listbox(list_frame, width=50, height=20)
            app_listbox.pack(side="left", fill="both", expand=True)
            
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=app_listbox.yview)
            scrollbar.pack(side="right", fill="y")
            
            app_listbox.config(yscrollcommand=scrollbar.set)
            
            # Populate the listbox
            for package in packages:
                app_listbox.insert(tk.END, package)
                
            # Create a frame for the buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x", pady=(0, 5))
            
            # Add buttons for common actions
            uninstall_btn = ttk.Button(
                button_frame, text="Uninstall App",
                command=lambda: self._uninstall_app(app_listbox, packages, serial, adb_cmd, app_window)
            )
            uninstall_btn.pack(side="left", padx=5)
            
            clear_data_btn = ttk.Button(
                button_frame, text="Clear App Data",
                command=lambda: self._clear_app_data(app_listbox, packages, serial, adb_cmd)
            )
            clear_data_btn.pack(side="left", padx=5)
            
            force_stop_btn = ttk.Button(
                button_frame, text="Force Stop",
                command=lambda: self._force_stop_app(app_listbox, packages, serial, adb_cmd)
            )
            force_stop_btn.pack(side="left", padx=5)
            
            extract_btn = ttk.Button(
                button_frame, text="Extract APK",
                command=lambda: self._extract_apk(app_listbox, packages, serial, adb_cmd)
            )
            extract_btn.pack(side="left", padx=2)
            
            freeze_btn = ttk.Button(
                button_frame, text="Freeze/Unfreeze",
                command=lambda: self._toggle_app_freeze(app_listbox, packages, serial, adb_cmd)
            )
            freeze_btn.pack(side="left", padx=2)
            
            perms_btn = ttk.Button(
                button_frame, text="View Permissions",
                command=lambda: self._view_app_permissions(app_listbox, packages, serial, adb_cmd)
            )
            perms_btn.pack(side="left", padx=2)
            
            close_btn = ttk.Button(
                button_frame, text="Close",
                command=app_window.destroy
            )
            close_btn.pack(side="right", padx=5)
            
            # Set focus to the search box
            search_entry.focus_set()
            
        except Exception as e:
            self.log_message(f"Error showing app manager: {str(e)}")
            messagebox.showerror("App Manager Error", f"Failed to show app manager: {str(e)}")
            
    def _view_app_permissions(self, listbox, packages, serial, adb_cmd):
        """View permissions for the selected app"""
        try:
            # Get the selected app
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("No App Selected", "Please select an app to view permissions.")
                return
                
            # Get the package name
            package_name = listbox.get(selected[0])
            
            # Create a new window to display permissions
            perm_window = tk.Toplevel(self)
            perm_window.title(f"Permissions - {package_name}")
            perm_window.geometry("600x500")
            
            # Add a text widget to display permissions
            text_frame = ttk.Frame(perm_window)
            text_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            text = tk.Text(text_frame, wrap="word", font=("Courier", 10))
            scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)
            
            scrollbar.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)
            
            # Add a status label
            status_var = tk.StringVar(value="Loading permissions...")
            status_bar = ttk.Label(perm_window, textvariable=status_var, relief="sunken")
            status_bar.pack(fill="x", side="bottom")
            
            # Function to load permissions in a separate thread
            def load_permissions():
                try:
                    # Get app permissions
                    result = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'dumpsys', 'package', package_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode != 0:
                        raise Exception(result.stderr.strip())
                    
                    # Parse the permissions
                    permissions = []
                    in_permissions = False
                    
                    for line in result.stdout.splitlines():
                        line = line.strip()
                        if "requested permissions:" in line:
                            in_permissions = True
                            continue
                        elif "install permissions:" in line:
                            break
                            
                        if in_permissions and line.startswith('android.permission.'):
                            permissions.append(line)
                    
                    # Update the UI in the main thread
                    perm_window.after(0, lambda: self._display_permissions(
                        text, status_var, package_name, permissions
                    ))
                    
                except Exception as e:
                    error_msg = f"Error loading permissions: {str(e)}"
                    perm_window.after(0, lambda: self._show_permission_error(status_var, error_msg))
            
            # Start the thread to load permissions
            threading.Thread(target=load_permissions, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"Error viewing app permissions: {str(e)}")
            messagebox.showerror("Error", f"Failed to view app permissions: {str(e)}")
    
    def _display_permissions(self, text_widget, status_var, package_name, permissions):
        """Display the permissions in the text widget"""
        try:
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, f"Permissions for: {package_name}\n")
            text_widget.insert(tk.END, "=" * 50 + "\n\n")
            
            if not permissions:
                text_widget.insert(tk.END, "No permissions found or couldn't retrieve permissions.")
            else:
                for perm in sorted(permissions):
                    text_widget.insert(tk.END, f"• {perm}\n")
            
            status_var.set(f"Loaded {len(permissions)} permissions")
            
        except Exception as e:
            status_var.set(f"Error displaying permissions: {str(e)}")
            raise
    
    def _show_permission_error(self, status_var, error_msg):
        """Show an error message in the status bar"""
        status_var.set(error_msg)
        messagebox.showerror("Error", error_msg)
        
    def _toggle_app_freeze(self, listbox, packages, serial, adb_cmd):
        """Freeze or unfreeze the selected app"""
        try:
            # Get the selected app
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("No App Selected", "Please select an app to freeze/unfreeze.")
                return
                
            # Get the package name
            package_name = listbox.get(selected[0])
            
            # Check if the app is currently frozen
            check_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages', '--disabled'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            is_frozen = f"package:{package_name}" in check_cmd.stdout
            
            if is_frozen:
                # Unfreeze the app
                self.log_message(f"Unfreezing {package_name}...")
                action = "enable"
                success_msg = f"{package_name} has been unfrozen and is now enabled."
                fail_msg = f"Failed to unfreeze {package_name}"
            else:
                # Freeze the app
                self.log_message(f"Freezing {package_name}...")
                action = "disable"
                success_msg = f"{package_name} has been frozen and is now disabled."
                fail_msg = f"Failed to freeze {package_name}"
                
            # Execute the freeze/unfreeze command
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', action, package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.log_message(success_msg)
                messagebox.showinfo("Success", success_msg)
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.log_message(f"{fail_msg}: {error_msg}")
                messagebox.showerror("Error", f"{fail_msg}:\n{error_msg}")
                
        except Exception as e:
            self.log_message(f"Error toggling app freeze state: {str(e)}")
            messagebox.showerror("Error", f"Failed to toggle app freeze state: {str(e)}")
            
    def _extract_apk(self, listbox, packages, serial, adb_cmd):
        """Extract APK for the selected app"""
        try:
            # Get the selected app
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("No App Selected", "Please select an app to extract APK.")
                return
                
            # Get the package name
            package_name = listbox.get(selected[0])
            
            # Ask user for save location
            save_dir = filedialog.askdirectory(
                title="Select Directory to Save APK",
                initialdir=os.path.expanduser("~/Downloads")
            )
            
            if not save_dir:
                return  # User cancelled
                
            # Show progress
            progress = ttk.Progressbar(
                listbox.master, orient="horizontal",
                length=200, mode="indeterminate"
            )
            progress.pack(pady=10)
            progress.start()
            
            # Get the APK path on the device
            self.log_message(f"Getting APK path for {package_name}...")
            
            # Get the APK path using pm path command
            path_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'path', package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if path_cmd.returncode != 0 or not path_cmd.stdout.strip():
                raise Exception(f"Failed to get APK path: {path_cmd.stderr.strip()}")
                
            # Extract the APK path from the output (format: package:/path/to/apk)
            apk_path = path_cmd.stdout.strip().split(':', 1)[1]
            
            # Pull the APK file
            self.log_message(f"Extracting APK from {apk_path}...")
            
            # Create the output filename
            output_file = os.path.join(save_dir, f"{package_name}.apk")
            
            # Pull the APK file
            pull_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'pull', apk_path, output_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            # Stop and remove progress bar
            progress.stop()
            progress.destroy()
            
            if pull_cmd.returncode != 0:
                raise Exception(f"Failed to pull APK: {pull_cmd.stderr.strip()}")
                
            self.log_message(f"APK extracted successfully to {output_file}")
            
            # Show success message with option to open the containing folder
            if messagebox.askyesno(
                "Extraction Complete",
                f"APK extracted successfully to:\n{output_file}\n\nOpen containing folder?"
            ):
                if sys.platform == 'win32':
                    os.startfile(os.path.dirname(output_file))
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', os.path.dirname(output_file)])
                else:
                    subprocess.Popen(['xdg-open', os.path.dirname(output_file)])
                    
        except Exception as e:
            if 'progress' in locals():
                progress.stop()
                progress.destroy()
            self.log_message(f"Error extracting APK: {str(e)}")
            messagebox.showerror("Extraction Error", f"Failed to extract APK: {str(e)}")
            
    def _filter_app_list(self, search_text, packages, listbox):
        """Filter the app list based on search text"""
        try:
            # Clear the listbox
            listbox.delete(0, tk.END)
            
            # Filter the packages based on the search text
            search_text = search_text.lower()
            filtered_packages = [pkg for pkg in packages if search_text in pkg.lower()]
            
            # Populate the listbox with the filtered packages
            for package in filtered_packages:
                listbox.insert(tk.END, package)
                
        except Exception as e:
            self.log_message(f"Error filtering app list: {str(e)}")
            
    def _uninstall_app(self, listbox, packages, serial, adb_cmd, parent_window):
        """Uninstall the selected app"""
        try:
            # Get the selected app
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("No App Selected", "Please select an app to uninstall.")
                return
                
            # Get the package name
            package_name = listbox.get(selected[0])
            
            # Confirm uninstallation
            if not messagebox.askyesno(
                "Confirm Uninstall", 
                f"Are you sure you want to uninstall {package_name}?\n\nThis action cannot be undone."
            ):
                return
                
            # Show a busy cursor
            parent_window.config(cursor="wait")
            parent_window.update()
            
            # Uninstall the app
            self.log_message(f"Uninstalling {package_name}...")
            
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'uninstall', package_name], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=20
            )
            
            # Reset cursor
            parent_window.config(cursor="")
            
            if result.returncode != 0 or 'Success' not in result.stdout:
                self.log_message(f"Failed to uninstall {package_name}: {result.stderr.strip() or result.stdout.strip()}")
                messagebox.showerror(
                    "Uninstall Error", 
                    f"Failed to uninstall {package_name}:\n{result.stderr.strip() or result.stdout.strip()}"
                )
                return
                
            self.log_message(f"{package_name} uninstalled successfully")
            messagebox.showinfo("Uninstall Complete", f"{package_name} was uninstalled successfully.")
            
            # Remove the app from the list and the listbox
            if package_name in packages:
                packages.remove(package_name)
            
            listbox.delete(selected[0])
            
        except Exception as e:
            if 'parent_window' in locals():
                parent_window.config(cursor="")
            self.log_message(f"Error uninstalling app: {str(e)}")
            messagebox.showerror("Uninstall Error", f"Failed to uninstall app: {str(e)}")
            
    def _clear_app_data(self, listbox, packages, serial, adb_cmd):
        """Clear data for the selected app"""
        try:
            # Get the selected app
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("No App Selected", "Please select an app to clear data for.")
                return
                
            # Get the package name
            package_name = listbox.get(selected[0])
            
            # Confirm data clearing
            if not messagebox.askyesno(
                "Confirm Clear Data", 
                f"Are you sure you want to clear all data for {package_name}?\n\nThis will remove all app data, settings, accounts, databases, etc."
            ):
                return
                
            # Clear the app data
            self.log_message(f"Clearing data for {package_name}...")
            
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'clear', package_name], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0 or 'Success' not in result.stdout:
                self.log_message(f"Failed to clear data for {package_name}: {result.stderr.strip() or result.stdout.strip()}")
                messagebox.showerror(
                    "Clear Data Error", 
                    f"Failed to clear data for {package_name}:\n{result.stderr.strip() or result.stdout.strip()}"
                )
                return
                
            self.log_message(f"Data cleared for {package_name}")
            messagebox.showinfo("Clear Data Complete", f"All data for {package_name} was cleared successfully.")
            
        except Exception as e:
            self.log_message(f"Error clearing app data: {str(e)}")
            messagebox.showerror("Clear Data Error", f"Failed to clear app data: {str(e)}")
            
    def _force_stop_app(self, listbox, packages, serial, adb_cmd):
        """Force stop the selected app"""
        try:
            # Get the selected app
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("No App Selected", "Please select an app to force stop.")
                return
                
            # Get the package name
            package_name = listbox.get(selected[0])
            
            # Force stop the app
            self.log_message(f"Force stopping {package_name}...")
            
            result = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'am', 'force-stop', package_name], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.log_message(f"Failed to force stop {package_name}: {result.stderr.strip()}")
                messagebox.showerror(
                    "Force Stop Error", 
                    f"Failed to force stop {package_name}:\n{result.stderr.strip()}"
                )
                return
                
            self.log_message(f"{package_name} force stopped")
            messagebox.showinfo("Force Stop Complete", f"{package_name} was force stopped successfully.")
        except Exception as e:
            self.log_message(f"Error force stopping app: {str(e)}")
            messagebox.showerror("Force Stop Error", f"Failed to force stop app: {str(e)}")
        
    def view_logcat(self):
        """View logcat from the connected Android device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        self._run_in_thread(self._view_logcat_task)
        
    def _view_logcat_task(self):
        """Worker thread to open a logcat viewer"""
        try:
            self.update_status("Opening logcat viewer...")
            self.log_message("Opening logcat viewer...")
            
            # Get the platform tools path
            if IS_WINDOWS:
                adb_path = self._find_adb_path()
                if not adb_path:
                    self.update_status("ADB not found")
                    return
                adb_cmd = adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Failed to open logcat")
                return
                
            # Show the logcat window in the main thread
            self.after(0, lambda: self._show_logcat_window(serial, adb_cmd))
        except Exception as e:
            self.log_message(f"Error opening logcat: {str(e)}")
            self.update_status("Failed to open logcat")
    
    def _show_logcat_window(self, serial, adb_cmd):
        """Show the logcat window"""
        try:
            # Create a new top-level window
            logcat_window = tk.Toplevel(self)
            logcat_window.title("Android Logcat Viewer")
            logcat_window.geometry("800x600")
            logcat_window.minsize(600, 400)
            
            # Center the window
            x_pos = (self.winfo_screenwidth() - 800) // 2
            y_pos = (self.winfo_screenheight() - 600) // 2
            logcat_window.geometry(f"+{x_pos}+{y_pos}")
            
            # Create a main frame
            main_frame = ttk.Frame(logcat_window)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Create filter frame
            filter_frame = ttk.Frame(main_frame)
            filter_frame.pack(fill="x", pady=(0, 10))
            
            # Add filter options
            ttk.Label(filter_frame, text="Filter:").pack(side="left", padx=(0, 5))
            
            filter_var = tk.StringVar()
            filter_entry = ttk.Entry(filter_frame, textvariable=filter_var, width=30)
            filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            # Log level filter
            ttk.Label(filter_frame, text="Log Level:").pack(side="left", padx=(10, 5))
            
            level_var = tk.StringVar(value="VERBOSE")
            level_combo = ttk.Combobox(filter_frame, textvariable=level_var, width=10)
            level_combo['values'] = ("VERBOSE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL")
            level_combo.pack(side="left", padx=(0, 10))
            
            # Clear button
            clear_btn = ttk.Button(filter_frame, text="Clear", width=8)
            clear_btn.pack(side="right", padx=5)
            
            # Apply button
            apply_btn = ttk.Button(filter_frame, text="Apply Filter", width=12)
            apply_btn.pack(side="right", padx=5)
            
            # Create a frame for the log with scrollbar
            log_frame = ttk.Frame(main_frame)
            log_frame.pack(fill="both", expand=True, pady=(0, 10))
            
            # Create a text widget for displaying logcat output
            log_text = tk.Text(log_frame, wrap=tk.NONE, width=80, height=20)
            log_text.pack(side="left", fill="both", expand=True)
            
            # Add vertical scrollbar
            v_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
            v_scrollbar.pack(side="right", fill="y")
            log_text.config(yscrollcommand=v_scrollbar.set)
            
            # Add horizontal scrollbar
            h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=log_text.xview)
            h_scrollbar.pack(side="bottom", fill="x", before=log_frame)
            log_text.config(xscrollcommand=h_scrollbar.set)
            
            # Define tag configurations for different log levels
            log_text.tag_configure("VERBOSE", foreground="gray")
            log_text.tag_configure("DEBUG", foreground="black")
            log_text.tag_configure("INFO", foreground="green")
            log_text.tag_configure("WARN", foreground="orange")
            log_text.tag_configure("ERROR", foreground="red")
            log_text.tag_configure("FATAL", foreground="purple", font=("Arial", 10, "bold"))
            
            # Add timestamp tag for timestamps
            log_text.tag_configure("timestamp", foreground="blue")
            
            # Add button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x", pady=(0, 5))
            
            # Add buttons
            save_btn = ttk.Button(
                button_frame, text="Save Log",
                command=lambda: self._save_logcat(log_text)
            )
            save_btn.pack(side="left", padx=5)
            
            close_btn = ttk.Button(
                button_frame, text="Close",
                command=lambda: self._close_logcat(logcat_window, serial, adb_cmd)
            )
            close_btn.pack(side="right", padx=5)
            
            # Set initial state
            log_text.insert(tk.END, "Loading logcat... Please wait.\n")
            log_text.config(state="disabled")
            
            # Store references in the window object for the worker thread to access
            logcat_window.log_text = log_text
            logcat_window.filter_var = filter_var
            logcat_window.level_var = level_var
            
            # Start logcat in a separate thread
            logcat_thread = threading.Thread(
                target=self._run_logcat,
                args=(serial, adb_cmd, logcat_window, log_text, filter_var, level_var)
            )
            logcat_thread.daemon = True
            logcat_window.logcat_thread = logcat_thread  # Store reference to thread
            logcat_thread.start()
            
            # Configure the buttons to actually do something
            clear_btn.config(command=lambda: self._clear_logcat(log_text))
            apply_btn.config(command=lambda: self._apply_logcat_filter(serial, adb_cmd, logcat_window))
            
            # Update the window title with device info
            model = self.device_info.get('model', 'Unknown')
            logcat_window.title(f"Android Logcat - {model} ({serial})")
            
            # Set up a handler for window close
            logcat_window.protocol("WM_DELETE_WINDOW", lambda: self._close_logcat(logcat_window, serial, adb_cmd))
            
        except Exception as e:
            self.log_message(f"Error showing logcat window: {str(e)}")
            messagebox.showerror("Logcat Error", f"Failed to show logcat window: {str(e)}")
            
    def _run_logcat(self, serial, adb_cmd, window, log_text, filter_var, level_var):
        """Run logcat in a separate thread"""
        try:
            # Store subprocess for later termination
            process = None
            
            # Initialize variables to filter logcat based on user settings
            current_filter = filter_var.get()
            current_level = level_var.get()
            
            # Map log level to ADB logcat parameters
            level_map = {
                "VERBOSE": "V",
                "DEBUG": "D",
                "INFO": "I",
                "WARN": "W",
                "ERROR": "E",
                "FATAL": "F"
            }
            
            # Build the logcat command
            cmd = [adb_cmd, '-s', serial, 'logcat', '*:' + level_map[current_level]]
            
            # Add filter if specified
            if current_filter:
                cmd.extend(["|", "grep", current_filter])
            
            # Create a simple regex to identify log levels in the output
            log_level_pattern = re.compile(r'\b([VDIWEAF])/')
            
            # Start logcat process
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                shell=True if '|' in cmd else False  # Use shell if piping
            )
            
            # Store the process in the window for later termination
            window.logcat_process = process
            
            # Clear the initial loading message
            self.after(0, lambda: self._clear_logcat(log_text))
            
            # Read and display logcat output
            for line in iter(process.stdout.readline, ''):
                # If window is destroyed, exit loop
                if not hasattr(window, 'winfo_exists') or not window.winfo_exists():
                    break
                    
                # Determine line style based on log level
                tag = "DEBUG"  # Default tag
                
                # Check if this line contains a log level marker
                match = log_level_pattern.search(line)
                if match:
                    level_char = match.group(1)
                    if level_char == 'V':
                        tag = "VERBOSE"
                    elif level_char == 'D':
                        tag = "DEBUG"
                    elif level_char == 'I':
                        tag = "INFO"
                    elif level_char == 'W':
                        tag = "WARN"
                    elif level_char == 'E':
                        tag = "ERROR"
                    elif level_char == 'F' or level_char == 'A':
                        tag = "FATAL"
                
                # Append the line to the text widget - use a thread-safe queue approach
                # Instead of trying to access the widget directly from a thread
                if hasattr(window, 'winfo_exists') and window.winfo_exists():
                    # Use the after method of the window instead of self
                    window.after(0, lambda l=line, t=tag: self._append_logcat_line(log_text, l, t))
            
            # Process completed
            if process.poll() is not None:
                # Process ended, add message to log
                status = process.poll()
                if hasattr(window, 'winfo_exists') and window.winfo_exists():
                    window.after(0, lambda: self._append_logcat_line(
                        log_text, f"\nLogcat process ended (status {status}). Please close and reopen the viewer.\n", "ERROR"
                    ))
                
        except Exception as e:
            # Log the error
            self.log_message(f"Error in logcat thread: {str(e)}")
            
            # Add error message to log_text if it still exists
            if hasattr(window, 'winfo_exists') and window.winfo_exists():
                window.after(0, lambda: self._append_logcat_line(
                    log_text, f"\nError: {str(e)}\n", "ERROR"
                ))
            
        finally:
            # Ensure process is terminated
            if process and process.poll() is None:
                try:
                    process.terminate()
                except:  # Deliberately broad exception handler
                    pass
    
    def _append_logcat_line(self, log_text, line, tag):
        """Append a line to the logcat text widget"""
        try:
            # Skip if the text widget is destroyed or no longer valid
            if not log_text.winfo_exists():
                return
                
            # Enable editing
            log_text.config(state="normal")
            
            # Insert the text with the appropriate tag
            log_text.insert(tk.END, line, tag)
            
            # Auto-scroll to the end
            log_text.see(tk.END)
            
            # Disable editing again
            log_text.config(state="disabled")
        except Exception as e:
            # This may happen if the window was closed
            self.log_message(f"Error appending to logcat: {str(e)}")
    
    def _clear_logcat(self, log_text):
        """Clear the logcat display"""
        try:
            log_text.config(state="normal")
            log_text.delete(1.0, tk.END)
            log_text.config(state="disabled")
        except Exception as e:
            self.log_message(f"Error clearing logcat: {str(e)}")
    
    def _apply_logcat_filter(self, serial, adb_cmd, window):
        """Apply a new filter to the logcat"""
        try:
            # Terminate the current logcat process
            if hasattr(window, 'logcat_process') and window.logcat_process:
                if window.logcat_process.poll() is None:  # Process is still running
                    window.logcat_process.terminate()
                    
            # Start new logcat process with updated filters
            new_thread = threading.Thread(
                target=self._run_logcat,
                args=(serial, adb_cmd, window, window.log_text, window.filter_var, window.level_var)
            )
            new_thread.daemon = True
            
            # Update thread reference
            if hasattr(window, 'logcat_thread'):
                window.logcat_thread = new_thread
                
            # Start the new thread
            new_thread.start()
        except Exception as e:
            self.log_message(f"Error applying logcat filter: {str(e)}")
    
    def _save_logcat(self, log_text):
        """Save logcat contents to a file"""
        try:
            # Get file path from user
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Logcat Output"
            )
            
            if not file_path:
                return  # User cancelled
                
            # Get the contents of the log text widget
            log_text.config(state="normal")
            contents = log_text.get(1.0, tk.END)
            log_text.config(state="disabled")
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(contents)
                
            self.log_message(f"Logcat saved to {file_path}")
            messagebox.showinfo("Save Complete", f"Logcat output saved to:\n{file_path}")
        except Exception as e:
            self.log_message(f"Error saving logcat: {str(e)}")
            messagebox.showerror("Save Error", f"Failed to save logcat: {str(e)}")
    
    def _close_logcat(self, window, serial, adb_cmd):
        """Close the logcat window and terminate the logcat process"""
        try:
            # Terminate the logcat process if it's running
            if hasattr(window, 'logcat_process') and window.logcat_process:
                if window.logcat_process.poll() is None:  # Process is still running
                    window.logcat_process.terminate()
            # Destroy the window
            window.destroy()
        except Exception as e:
            self.log_message(f"Error closing logcat: {str(e)}")
        
    def log_message(self, message):
        """Add a message to the log console"""
        # Log to console even if the UI element doesn't exist yet
        logging.info(f"[AndroidTools] {message}")
        
        # Only update the UI if the log_text widget exists
        if self.log_text is not None:
            try:
                self.log_text.configure(state="normal")
                self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
                self.log_text.see(tk.END)
                self.log_text.configure(state="disabled")
            except Exception as e:
                logging.error(f"Error updating log display: {str(e)}")
        
    def update_status(self, status_text):
        """Update the status bar text"""
        try:
            if hasattr(self, 'status_var'):
                self.status_var.set(status_text)
        except Exception as e:
            logging.error(f"Error updating status: {str(e)}")
        
    def enable_device_actions(self):
        """Enable device action buttons when a device is connected"""
        self.screenshot_btn.configure(state="normal")
        self.backup_btn.configure(state="normal")
        self.files_btn.configure(state="normal")
        self.install_apk_btn.configure(state="normal")
        self.app_manager_btn.configure(state="normal")
        self.logcat_btn.configure(state="normal")
        
    def disable_device_actions(self):
        """Disable device action buttons when no device is connected"""
        self.screenshot_btn.configure(state="disabled")
        self.backup_btn.configure(state="disabled")
        self.files_btn.configure(state="disabled")
        self.install_apk_btn.configure(state="disabled")
        self.app_manager_btn.configure(state="disabled")
        self.logcat_btn.configure(state="disabled")
        
    def _run_in_thread(self, target_function, *args, **kwargs):
        """Run a function in a separate thread with error handling"""
        def thread_wrapper():
            try:
                target_function(*args, **kwargs)
            except Exception as e:
                # Log the full traceback to the console
                import traceback
                traceback.print_exc()
                # Also log to the GUI if available
                if hasattr(self, 'log_message'):
                    self.after(0, lambda: self.log_message(f"Error in thread: {str(e)}"))
        
        thread = threading.Thread(target=thread_wrapper)
        thread.daemon = True  # Thread will close when main app closes
        self.threads.append(thread)
        thread.start()
        return thread
        
    # Device Control Functions
    def _reboot_device_normal(self):
        """Reboot device normally"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Rebooting device...")
            self.log_message("Rebooting device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Reboot failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Execute ADB reboot command
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'reboot'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if cmd.returncode == 0:
                self.log_message("Device reboot initiated.")
                self.update_status("Device rebooting")
                
                # Update device connection status
                self.device_connected = False
                self.disable_device_actions()
                
                # Show a message to the user
                messagebox.showinfo("Reboot Initiated", "The device has been instructed to reboot. Please wait for it to complete and reconnect.")
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Reboot failed: {error_msg}")
                self.update_status("Reboot failed")
                messagebox.showerror("Reboot Failed", f"Failed to reboot the device: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error during reboot: {str(e)}")
            self.update_status("Reboot error")
            messagebox.showerror("Reboot Error", f"An error occurred while trying to reboot the device: {str(e)}")
            
    def _reboot_device_recovery(self):
        """Reboot device to recovery mode"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Ask for confirmation as this is more advanced
            confirm = messagebox.askyesno(
                "Confirm Reboot to Recovery", 
                "Are you sure you want to reboot the device to recovery mode? \n\nThis is typically used for advanced operations like flashing ROMs or performing system updates."
            )
            
            if not confirm:
                return
                
            self.update_status("Rebooting to recovery...")
            self.log_message("Rebooting device to recovery mode...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Reboot failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Execute ADB reboot command
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'reboot', 'recovery'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if cmd.returncode == 0:
                self.log_message("Device reboot to recovery initiated.")
                self.update_status("Device rebooting to recovery")
                
                # Update device connection status
                self.device_connected = False
                self.disable_device_actions()
                
                # Show a message to the user
                messagebox.showinfo("Reboot Initiated", "The device has been instructed to reboot into recovery mode. Please wait for it to complete and reconnect.")
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Reboot to recovery failed: {error_msg}")
                self.update_status("Reboot failed")
                messagebox.showerror("Reboot Failed", f"Failed to reboot the device to recovery: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error during reboot to recovery: {str(e)}")
            self.update_status("Reboot error")
            messagebox.showerror("Reboot Error", f"An error occurred while trying to reboot the device to recovery: {str(e)}")
            
    def _reboot_device_edl(self):
        """Reboot device to EDL (Emergency Download) mode"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Ask for confirmation as this is an advanced operation
            confirm = messagebox.askyesno(
                "Confirm Reboot to EDL", 
                "WARNING: Rebooting to EDL mode is an advanced operation.\n\n"
                "This mode is typically used for low-level operations like firmware flashing. "
                "The device will appear as a Qualcomm HS-USB device and will not boot normally until restarted.\n\n"
                "Are you sure you want to continue?"
            )
            
            if not confirm:
                return
                
            self.update_status("Rebooting to EDL mode...")
            self.log_message("Rebooting device to EDL mode...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Reboot failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Try different methods to enter EDL mode
            # Method 1: Using reboot edl (works on some devices)
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'reboot', 'edl'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            # If the first method fails, try alternative methods
            if cmd.returncode != 0:
                # Method 2: Using reboot edl download (some Samsung devices)
                cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'reboot', 'edl download'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
            
            if cmd.returncode == 0:
                self.log_message("Device reboot to EDL mode initiated.")
                self.update_status("Device rebooting to EDL mode")
                
                # Update device connection status
                self.device_connected = False
                self.disable_device_actions()
                
                # Show a message to the user
                messagebox.showinfo(
                    "EDL Mode Initiated",
                    "The device has been instructed to reboot into EDL mode.\n\n"
                    "The device will now appear as a Qualcomm HS-USB device in Device Manager.\n"
                    "You will need to manually restart the device to boot back to Android."
                )
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Reboot to EDL failed: {error_msg}")
                self.update_status("EDL reboot failed")
                messagebox.showerror(
                    "EDL Reboot Failed",
                    f"Failed to reboot the device to EDL mode: {error_msg}\n\n"
                    "Your device may not support standard EDL mode entry.\n"
                    "Some devices require specific button combinations or hardware tools to enter EDL mode."
                )
                
        except Exception as e:
            self.log_message(f"Error during EDL reboot: {str(e)}")
            self.update_status("EDL reboot error")
            messagebox.showerror("EDL Reboot Error", f"An error occurred while trying to reboot to EDL mode: {str(e)}")

    def _reboot_device_bootloader(self):
        """Reboot device to bootloader/fastboot mode"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Ask for confirmation as this is more advanced
            confirm = messagebox.askyesno(
                "Confirm Reboot to Bootloader", 
                "Are you sure you want to reboot the device to bootloader mode? \n\nThis is used for advanced operations like unlocking the bootloader or flashing system images."
            )
            
            if not confirm:
                return
                
            self.update_status("Rebooting to bootloader...")
            self.log_message("Rebooting device to bootloader mode...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Reboot failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Execute ADB reboot command
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'reboot', 'bootloader'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if cmd.returncode == 0:
                self.log_message("Device reboot to bootloader initiated.")
                self.update_status("Device rebooting to bootloader")
                
                # Update device connection status
                self.device_connected = False
                self.disable_device_actions()
                
                # Show a message to the user
                messagebox.showinfo("Reboot Initiated", "The device has been instructed to reboot into bootloader mode. Please wait for it to complete and reconnect.")
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Reboot to bootloader failed: {error_msg}")
                self.update_status("Reboot failed")
                messagebox.showerror("Reboot Failed", f"Failed to reboot the device to bootloader: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error during reboot to bootloader: {str(e)}")
            self.update_status("Reboot error")
            messagebox.showerror("Reboot Error", f"An error occurred while trying to reboot the device to bootloader: {str(e)}")

    def _toggle_mobile_data(self):
        """Toggle mobile data on/off on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Toggling mobile data...")
            self.log_message("Toggling mobile data state on device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Mobile data toggle failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # First check current mobile data state
            get_state_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'settings', 'get', 'global', 'mobile_data'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            # Determine new state (toggle)
            current_state = get_state_cmd.stdout.strip()
            new_state = '0' if current_state == '1' else '1'
            
            # Set the new state
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'global', 'mobile_data', new_state],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if cmd.returncode == 0:
                state_text = "enabled" if new_state == '1' else "disabled"
                self.log_message(f"Mobile data {state_text}")
                self.update_status(f"Mobile data {state_text}")
                messagebox.showinfo("Success", f"Mobile data has been {state_text}.")
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to toggle mobile data: {error_msg}")
                self.update_status("Mobile data toggle failed")
                messagebox.showerror("Error", f"Failed to toggle mobile data: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error toggling mobile data: {str(e)}")
            self.update_status("Mobile data toggle error")
            messagebox.showerror("Error", f"An error occurred while toggling mobile data: {str(e)}")

    def _toggle_wifi(self):
        """Toggle WiFi on/off on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Toggling WiFi...")
            self.log_message("Toggling WiFi state on device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("WiFi toggle failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # First check current WiFi state
            get_state_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'settings', 'get', 'global', 'wifi_on'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if get_state_cmd.returncode == 0:
                # Determine if WiFi is on (1) or off (0)
                current_state = get_state_cmd.stdout.strip()
                new_state = '0' if current_state == '1' else '1'
                state_desc = "OFF" if new_state == '0' else "ON"
                
                # Toggle the WiFi state
                toggle_cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'svc', 'wifi', 'disable' if new_state == '0' else 'enable'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if toggle_cmd.returncode == 0:
                    self.log_message(f"WiFi has been toggled {state_desc}.")
                    self.update_status(f"WiFi toggled {state_desc}")
                    messagebox.showinfo("WiFi Toggled", f"WiFi has been turned {state_desc} on the device.")
                else:
                    error_msg = toggle_cmd.stderr.strip() or "Unknown error"
                    self.log_message(f"WiFi toggle failed: {error_msg}")
                    self.update_status("WiFi toggle failed")
                    messagebox.showerror("WiFi Toggle Failed", f"Failed to toggle WiFi: {error_msg}")
            else:
                error_msg = get_state_cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Getting WiFi state failed: {error_msg}")
                self.update_status("WiFi toggle failed")
                messagebox.showerror("WiFi Toggle Failed", f"Failed to get current WiFi state: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error toggling WiFi: {str(e)}")
            self.update_status("WiFi toggle error")
            messagebox.showerror("WiFi Toggle Error", f"An error occurred while trying to toggle WiFi: {str(e)}")

    def _toggle_bluetooth(self):
        """Toggle Bluetooth on/off on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Toggling Bluetooth...")
            self.log_message("Toggling Bluetooth state on device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Bluetooth toggle failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
            
            # First check current Bluetooth state
            get_state_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'settings', 'get', 'global', 'bluetooth_on'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            # Handle the case where the setting might not exist
            current_state = get_state_cmd.stdout.strip()
            if current_state == 'null' or not current_state.isdigit():
                # If we can't determine current state, default to toggling it on
                new_state = '1'
            else:
                # Toggle the current state
                new_state = '0' if current_state == '1' else '1'
            
            # Set the new state using the Bluetooth manager
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'service', 'call', 'bluetooth_manager', '8', 'i32', new_state],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            # Also update the settings for consistency
            subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'global', 'bluetooth_on', new_state],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if cmd.returncode == 0:
                state_text = "enabled" if new_state == '1' else "disabled"
                self.log_message(f"Bluetooth {state_text}")
                self.update_status(f"Bluetooth {state_text}")
                messagebox.showinfo("Success", f"Bluetooth has been {state_text}.")
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to toggle Bluetooth: {error_msg}")
                self.update_status("Bluetooth toggle failed")
                messagebox.showerror("Error", f"Failed to toggle Bluetooth: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error toggling Bluetooth: {str(e)}")
            self.update_status("Bluetooth toggle error")
            messagebox.showerror("Error", f"An error occurred while toggling Bluetooth: {str(e)}")
            
    def _set_brightness_dialog(self):
        """Show a dialog to set the screen brightness"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Create a dialog window
            dialog = tk.Toplevel()
            dialog.title("Set Screen Brightness")
            dialog.transient(self.parent)
            dialog.grab_set()
            
            # Set the dialog to be modal
            dialog.focus_set()
            
            # Get current brightness level
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                adb_cmd = 'adb'
                
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                messagebox.showerror("Error", "Could not get device information.")
                dialog.destroy()
                return
                
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
            
            # Get current brightness and max brightness
            try:
                # Get max brightness first
                max_brightness_cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'cat', '/sys/class/backlight/panel0-backlight/max_brightness'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if max_brightness_cmd.returncode != 0:
                    # Try alternative path for some devices
                    max_brightness_cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'cat', '/sys/class/leds/lcd-backlight/max_brightness'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                
                if max_brightness_cmd.returncode != 0:
                    # Default to a reasonable max if we can't determine it
                    max_brightness = 255
                else:
                    max_brightness = int(max_brightness_cmd.stdout.strip() or '255')
                
                # Get current brightness
                brightness_cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'settings', 'get', 'system', 'screen_brightness'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if brightness_cmd.returncode == 0 and brightness_cmd.stdout.strip().isdigit():
                    current_brightness = int(brightness_cmd.stdout.strip())
                    # Ensure brightness is within valid range
                    current_brightness = max(0, min(current_brightness, max_brightness))
                else:
                    # Default to 50% if we can't get current brightness
                    current_brightness = max_brightness // 2
                
            except (ValueError, subprocess.SubprocessError) as e:
                self.log_message(f"Error getting brightness: {str(e)}")
                max_brightness = 255
                current_brightness = 128
            
            # Create the brightness scale
            ttk.Label(dialog, text=f"Set Brightness (0-{max_brightness}):").pack(pady=10)
            
            brightness_var = tk.IntVar(value=current_brightness)
            scale = ttk.Scale(
                dialog, 
                from_=0, 
                to=max_brightness, 
                orient='horizontal',
                variable=brightness_var,
                length=300
            )
            scale.pack(padx=20, pady=5)
            
            # Show current brightness value
            value_label = ttk.Label(dialog, text=str(current_brightness))
            value_label.pack(pady=5)
            
            # Update label when scale changes
            def update_value(val):
                value_label.config(text=str(int(float(val))))
                
            scale.config(command=update_value)
            
            # Add buttons
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            
            def apply_brightness():
                try:
                    brightness = brightness_var.get()
                    # Set the brightness using settings
                    cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'system', 'screen_brightness', str(brightness)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    
                    # Also set the brightness directly (for immediate effect)
                    subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'su', '-c', f'echo {brightness} > /sys/class/backlight/panel0-backlight/brightness'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5
                    )
                    
                    if cmd.returncode == 0:
                        self.log_message(f"Brightness set to {brightness}")
                        self.update_status(f"Brightness set to {brightness}")
                        dialog.destroy()
                    else:
                        error_msg = cmd.stderr.strip() or "Unknown error"
                        self.log_message(f"Failed to set brightness: {error_msg}")
                        messagebox.showerror("Error", f"Failed to set brightness: {error_msg}")
                        
                except Exception as e:
                    self.log_message(f"Error setting brightness: {str(e)}")
                    messagebox.showerror("Error", f"An error occurred while setting brightness: {str(e)}")
            
            ttk.Button(button_frame, text="Apply", command=apply_brightness).pack(side='left', padx=5)
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
            
            # Center the dialog
            dialog.update_idletasks()
            width = 400
            height = 200
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            self.log_message(f"Error in brightness dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to open brightness dialog: {str(e)}")
    
    def _set_screen_timeout_dialog(self):
        """Show a dialog to set the screen timeout duration"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Create a dialog window
            dialog = tk.Toplevel()
            dialog.title("Set Screen Timeout")
            dialog.transient(self.parent)
            dialog.grab_set()
            dialog.focus_set()
            
            # Common screen timeout values in milliseconds
            timeout_options = [
                ("15 seconds", 15000),
                ("30 seconds", 30000),
                (("1 minute", 60000)),
                ("2 minutes", 120000),
                ("5 minutes", 300000),
                ("10 minutes", 600000),
                ("30 minutes", 1800000),
                ("Never (keep on)", 2147483647)  # MAX_INT
            ]
            
            # Get current timeout setting
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                adb_cmd = 'adb'
                
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                messagebox.showerror("Error", "Could not get device information.")
                dialog.destroy()
                return
                
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
            
            # Get current timeout
            try:
                timeout_cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'settings', 'get', 'system', 'screen_off_timeout'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if timeout_cmd.returncode == 0 and timeout_cmd.stdout.strip().isdigit():
                    current_timeout = int(timeout_cmd.stdout.strip())
                else:
                    current_timeout = 30000  # Default to 30 seconds if can't get current
                    
            except (ValueError, subprocess.SubprocessError) as e:
                self.log_message(f"Error getting screen timeout: {str(e)}")
                current_timeout = 30000
            
            # Create the main frame
            main_frame = ttk.Frame(dialog, padding=10)
            main_frame.pack(fill='both', expand=True)
            
            # Add title
            ttk.Label(main_frame, text="Set Screen Timeout", font=('Arial', 10, 'bold')).pack(pady=(0, 10))
            
            # Create radio buttons for timeout options
            timeout_var = tk.IntVar(value=current_timeout)
            
            for text, value in timeout_options:
                rb = ttk.Radiobutton(
                    main_frame,
                    text=text,
                    variable=timeout_var,
                    value=value
                )
                rb.pack(anchor='w', pady=2)
                
                # Select the current timeout if it matches
                if value == current_timeout:
                    rb.invoke()
            
            # Add custom timeout option
            custom_frame = ttk.Frame(main_frame)
            custom_frame.pack(fill='x', pady=5)
            
            ttk.Radiobutton(
                custom_frame,
                text="Custom:",
                variable=timeout_var,
                value=-1
            ).pack(side='left')
            
            custom_timeout = ttk.Entry(custom_frame, width=10)
            custom_timeout.pack(side='left', padx=5)
            ttk.Label(custom_frame, text="seconds").pack(side='left')
            
            # Function to handle radio button selection
            def on_timeout_select():
                if timeout_var.get() == -1:
                    custom_timeout.config(state='normal')
                    custom_timeout.focus()
                else:
                    custom_timeout.config(state='disabled')
            
            timeout_var.trace('w', lambda *args: on_timeout_select())
            
            # Initially disable custom entry if not selected
            if current_timeout not in [t[1] for t in timeout_options]:
                timeout_var.set(-1)
                custom_timeout.insert(0, str(current_timeout // 1000))
            else:
                custom_timeout.config(state='disabled')
            
            # Add buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(pady=(10, 0))
            
            def apply_timeout():
                try:
                    if timeout_var.get() == -1:
                        # Custom timeout
                        try:
                            seconds = int(custom_timeout.get())
                            if seconds < 0:
                                raise ValueError("Timeout must be positive")
                            timeout_ms = seconds * 1000
                        except ValueError:
                            messagebox.showerror("Invalid Input", "Please enter a valid number of seconds.")
                            return
                    else:
                        timeout_ms = timeout_var.get()
                    
                    # Set the screen timeout
                    cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'system', 'screen_off_timeout', str(timeout_ms)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    
                    if cmd.returncode == 0:
                        self.log_message(f"Screen timeout set to {timeout_ms}ms")
                        self.update_status(f"Screen timeout set to {timeout_ms//1000} seconds")
                        dialog.destroy()
                    else:
                        error_msg = cmd.stderr.strip() or "Unknown error"
                        self.log_message(f"Failed to set screen timeout: {error_msg}")
                        messagebox.showerror("Error", f"Failed to set screen timeout: {error_msg}")
                        
                except Exception as e:
                    self.log_message(f"Error setting screen timeout: {str(e)}")
                    messagebox.showerror("Error", f"An error occurred while setting screen timeout: {str(e)}")
            
            ttk.Button(button_frame, text="Apply", command=apply_timeout).pack(side='left', padx=5)
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
            
            # Set dialog size and position
            dialog.update_idletasks()
            width = 300
            height = 350
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'{width}x{height}+{x}+{y}')
            dialog.resizable(False, False)
            
        except Exception as e:
            self.log_message(f"Error in screen timeout dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to open screen timeout dialog: {str(e)}")
    
    def _toggle_airplane_mode(self):
        """Toggle airplane mode on/off on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Toggling airplane mode...")
            self.log_message("Toggling airplane mode on device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Airplane mode toggle failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # First check current airplane mode state
            get_state_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'settings', 'get', 'global', 'airplane_mode_on'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if get_state_cmd.returncode == 0:
                # Determine if airplane mode is on (1) or off (0)
                current_state = get_state_cmd.stdout.strip()
                new_state = '0' if current_state == '1' else '1'
                state_desc = "OFF" if new_state == '0' else "ON"
                
                # Set the new state
                set_state_cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'global', 'airplane_mode_on', new_state],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if set_state_cmd.returncode == 0:
                    # Broadcast the change so that the device updates
                    broadcast_cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', 'true' if new_state == '1' else 'false'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    
                    if broadcast_cmd.returncode == 0:
                        self.log_message(f"Airplane mode has been toggled {state_desc}.")
                        self.update_status(f"Airplane mode toggled {state_desc}")
                        messagebox.showinfo("Airplane Mode Toggled", f"Airplane mode has been turned {state_desc} on the device.")
                    else:
                        error_msg = broadcast_cmd.stderr.strip() or "Unknown error"
                        self.log_message(f"Broadcasting airplane mode change failed: {error_msg}")
                        self.update_status("Airplane mode toggle incomplete")
                        messagebox.showerror("Airplane Mode Toggle Failed", f"Failed to broadcast airplane mode change: {error_msg}")
                else:
                    error_msg = set_state_cmd.stderr.strip() or "Unknown error"
                    self.log_message(f"Setting airplane mode state failed: {error_msg}")
                    self.update_status("Airplane mode toggle failed")
                    messagebox.showerror("Airplane Mode Toggle Failed", f"Failed to set airplane mode state: {error_msg}")
            else:
                error_msg = get_state_cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Getting airplane mode state failed: {error_msg}")
                self.update_status("Airplane mode toggle failed")
                messagebox.showerror("Airplane Mode Toggle Failed", f"Failed to get current airplane mode state: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error toggling airplane mode: {str(e)}")
            self.update_status("Airplane mode toggle error")
            messagebox.showerror("Airplane Mode Toggle Error", f"An error occurred while trying to toggle airplane mode: {str(e)}")

    def _toggle_do_not_disturb(self):
        """Toggle Do Not Disturb mode on/off on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Toggling Do Not Disturb...")
            self.log_message("Toggling Do Not Disturb mode on device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Do Not Disturb toggle failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
            
            # First check current DND state
            # On Android, we can check the current policy for DND
            dnd_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'dumpsys', 'notification', 'policy'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            # Check if DND is currently enabled
            dnd_enabled = "mZenMode=0" not in dnd_cmd.stdout
            
            # Toggle DND state
            if dnd_enabled:
                # Turn DND off
                cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'global', 'zen_mode', '0'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                # Also reset any DND rules
                subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'cmd', 'notification', 'set_dnd', 'false'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                
                if cmd.returncode == 0:
                    self.log_message("Do Not Disturb disabled")
                    self.update_status("Do Not Disturb disabled")
                    messagebox.showinfo("Success", "Do Not Disturb has been disabled.")
                else:
                    error_msg = cmd.stderr.strip() or "Unknown error"
                    self.log_message(f"Failed to disable Do Not Disturb: {error_msg}")
                    self.update_status("DND disable failed")
                    messagebox.showerror("Error", f"Failed to disable Do Not Disturb: {error_msg}")
            else:
                # Turn DND on with default settings (priority only)
                cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'global', 'zen_mode', '1'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                # Set priority mode to allow only priority interruptions
                subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'settings', 'put', 'global', 'zen_mode_config_etag', '1'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                
                # Enable DND
                subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'cmd', 'notification', 'set_dnd', 'true', 'from:0', 'from:0'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                
                if cmd.returncode == 0:
                    self.log_message("Do Not Disturb enabled (priority only)")
                    self.update_status("Do Not Disturb enabled")
                    messagebox.showinfo("Success", "Do Not Disturb has been enabled (priority only).")
                else:
                    error_msg = cmd.stderr.strip() or "Unknown error"
                    self.log_message(f"Failed to enable Do Not Disturb: {error_msg}")
                    self.update_status("DND enable failed")
                    messagebox.showerror("Error", f"Failed to enable Do Not Disturb: {error_msg}")
                    
        except Exception as e:
            self.log_message(f"Error toggling Do Not Disturb: {str(e)}")
            self.update_status("DND toggle error")
            messagebox.showerror("Error", f"An error occurred while toggling Do Not Disturb: {str(e)}")
    
    def _simulate_power_button(self):
        """Simulate a power button press on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Simulating power button...")
            self.log_message("Simulating power button press on device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Power button simulation failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Method 1: Use input keyevent to simulate power button (KEYCODE_POWER = 26)
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'input', 'keyevent', '26'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if cmd.returncode == 0:
                self.log_message("Power button press simulated")
                self.update_status("Power button pressed")
                # No need to show a message box for this action as it's a simple simulation
            else:
                # Method 2: Alternative method using sendevent (for some devices)
                self.log_message("Primary power button method failed, trying alternative...")
                
                # Get the event number for the power button
                event_cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'getevent', '-p'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if event_cmd.returncode == 0 and 'KEY_POWER' in event_cmd.stdout:
                    # If we can find the power button event, try to simulate it
                    cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'sendevent', '/dev/input/eventX', '1', '116', '1'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    
                    # Send the key up event
                    subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'sendevent', '/dev/input/eventX', '1', '116', '0'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5
                    )
                    
                    if cmd.returncode == 0:
                        self.log_message("Power button press simulated (alternative method)")
                        self.update_status("Power button pressed")
                    else:
                        error_msg = cmd.stderr.strip() or "Unknown error"
                        self.log_message(f"Failed to simulate power button: {error_msg}")
                        self.update_status("Power button simulation failed")
                        messagebox.showerror("Error", f"Failed to simulate power button: {error_msg}")
                else:
                    error_msg = event_cmd.stderr.strip() or "Unknown error"
                    self.log_message(f"Failed to find power button event: {error_msg}")
                    self.update_status("Power button simulation failed")
                    messagebox.showerror("Error", "Could not simulate power button press on this device.")
                    
        except Exception as e:
            self.log_message(f"Error simulating power button: {str(e)}")
            self.update_status("Power button error")
            messagebox.showerror("Error", f"An error occurred while simulating power button: {str(e)}")
    
    def _toggle_flashlight(self):
        """Toggle the device's flashlight (camera flash) on/off"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Toggling flashlight...")
            self.log_message("Toggling flashlight on device...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Flashlight toggle failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
            
            # First check if the device has a flashlight
            has_flash_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'features'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if 'feature:android.hardware.camera.flash' not in has_flash_cmd.stdout:
                messagebox.showerror("Not Supported", "This device does not have a flashlight/camera flash.")
                self.log_message("Device does not have a flashlight")
                self.update_status("Flashlight not available")
                return
            
            # Check current flashlight state by checking if any camera app is using the flash
            # This is a bit of a hack since there's no direct way to check flashlight state
            flash_check = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'dumpsys', 'media.camera'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            # This is a heuristic - if the flash is on, there will be torch related output
            # This might need adjustment based on the device
            flash_on = 'mTorchEnabled=true' in flash_check.stdout or 'Torch' in flash_check.stdout
            
            # Toggle the flashlight state
            if flash_on:
                # Turn off flashlight
                cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'am', 'start', '-n', 'com.android.systemui/.statusbar.phone.TorchOffReceiver', '--es', 'torch', '0'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                # Alternative method if the first one doesn't work
                if cmd.returncode != 0:
                    cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'echo', '0', '>', '/sys/class/leds/led:torch_0/brightness'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5,
                        shell=True
                    )
                
                if cmd.returncode == 0:
                    self.log_message("Flashlight turned off")
                    self.update_status("Flashlight off")
                else:
                    error_msg = cmd.stderr.strip() or "Unknown error"
                    self.log_message(f"Failed to turn off flashlight: {error_msg}")
                    self.update_status("Flashlight off failed")
                    messagebox.showerror("Error", f"Failed to turn off flashlight: {error_msg}")
            else:
                # Turn on flashlight
                cmd = subprocess.run(
                    [adb_cmd, '-s', serial, 'shell', 'am', 'start', '-n', 'com.android.systemui/.statusbar.phone.TorchOffReceiver', '--es', 'torch', '1'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                # Alternative method if the first one doesn't work
                if cmd.returncode != 0:
                    cmd = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'echo', '1', '>', '/sys/class/leds/led:torch_0/brightness'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5,
                        shell=True
                    )
                
                if cmd.returncode == 0:
                    self.log_message("Flashlight turned on")
                    self.update_status("Flashlight on")
                else:
                    error_msg = cmd.stderr.strip() or "Unknown error"
                    self.log_message(f"Failed to turn on flashlight: {error_msg}")
                    self.update_status("Flashlight on failed")
                    messagebox.showerror("Error", f"Failed to turn on flashlight: {error_msg}")
                    
        except Exception as e:
            self.log_message(f"Error toggling flashlight: {str(e)}")
            self.update_status("Flashlight error")
            messagebox.showerror("Error", f"An error occurred while toggling flashlight: {str(e)}")
    
    def _toggle_screen(self):
        """Toggle device screen on/off"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Toggling screen...")
            self.log_message("Toggling device screen...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Screen toggle failed")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
            
            # Send key event for power button
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'input', 'keyevent', '26'],  # 26 is the keycode for power
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if cmd.returncode == 0:
                self.log_message("Screen toggle command sent successfully.")
                self.update_status("Screen toggled")
                messagebox.showinfo("Screen Toggled", "Screen has been toggled (on/off).")
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Screen toggle failed: {error_msg}")
                self.update_status("Screen toggle failed")
                messagebox.showerror("Screen Toggle Failed", f"Failed to toggle screen: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error toggling screen: {str(e)}")
            self.update_status("Screen toggle error")
            messagebox.showerror("Screen Toggle Error", f"An error occurred while trying to toggle the screen: {str(e)}")
            
    # App Management Functions
    def _uninstall_app_dialog(self):
        """Show dialog to select app to uninstall"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Retrieving installed apps...")
            self.log_message("Getting list of installed apps...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Failed to get installed apps")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Get list of non-system apps
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages', '-3'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            
            if cmd.returncode == 0:
                # Process the output to get package names
                packages = []
                for line in cmd.stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        package_name = line[8:].strip()  # Remove 'package:' prefix
                        packages.append(package_name)
                        
                if not packages:
                    self.log_message("No third-party apps found on the device.")
                    self.update_status("No apps to uninstall")
                    messagebox.showinfo("No Apps", "No third-party applications were found on the device.")
                    return
                    
                # Sort alphabetically for better usability
                packages.sort()
                    
                # Create a dialog to select an app
                dialog = tk.Toplevel(self)
                dialog.title("Select App to Uninstall")
                dialog.geometry("500x400")
                dialog.transient(self)  # Set to be on top of the parent window
                dialog.grab_set()  # Modal dialog
                
                # Add a label
                ttk.Label(
                    dialog, text="Select an application to uninstall:", font=("Arial", 10, "bold")
                ).pack(pady=10)
                
                # Add a listbox with scrollbar
                list_frame = ttk.Frame(dialog)
                list_frame.pack(fill="both", expand=True, padx=10, pady=5)
                
                scrollbar = ttk.Scrollbar(list_frame)
                scrollbar.pack(side="right", fill="y")
                
                app_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 9))
                app_listbox.pack(side="left", fill="both", expand=True)
                
                scrollbar.config(command=app_listbox.yview)
                
                # Insert packages into the listbox
                for package in packages:
                    app_listbox.insert(tk.END, package)
                    
                # Buttons
                button_frame = ttk.Frame(dialog)
                button_frame.pack(fill="x", padx=10, pady=10)
                
                ttk.Button(
                    button_frame, text="Uninstall", 
                    command=lambda: self._uninstall_selected_app(dialog, app_listbox, serial, adb_cmd)
                ).pack(side="left", padx=5)
                
                ttk.Button(
                    button_frame, text="Cancel", command=dialog.destroy
                ).pack(side="right", padx=5)
                
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to get app list: {error_msg}")
                self.update_status("Failed to get app list")
                messagebox.showerror("Error", f"Failed to retrieve the list of installed applications.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error preparing uninstall dialog: {str(e)}")
            self.update_status("Error preparing uninstall dialog")
            messagebox.showerror("Error", f"An error occurred while preparing the uninstall dialog: {str(e)}")
    
    def _uninstall_selected_app(self, dialog, app_listbox, serial, adb_cmd):
        """Uninstall the selected app"""
        selected = app_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select an app to uninstall.")
            return
            
        package_name = app_listbox.get(selected[0])
        
        # Confirm uninstall
        confirm = messagebox.askyesno(
            "Confirm Uninstall", 
            f"Are you sure you want to uninstall the following app?\n\n{package_name}"
        )
        
        if not confirm:
            return
            
        try:
            self.update_status(f"Uninstalling {package_name}...")
            self.log_message(f"Uninstalling app: {package_name}")
            
            # Execute uninstall command
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'uninstall', package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20
            )
            
            if cmd.returncode == 0 and 'Success' in cmd.stdout:
                self.log_message(f"Successfully uninstalled {package_name}")
                self.update_status("App uninstalled")
                messagebox.showinfo("Success", f"The app {package_name} has been successfully uninstalled.")
                dialog.destroy()
            else:
                error_msg = cmd.stderr.strip() or cmd.stdout.strip() or "Unknown error"
                self.log_message(f"Failed to uninstall app: {error_msg}")
                self.update_status("Uninstall failed")
                messagebox.showerror("Uninstall Failed", f"Failed to uninstall the app.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error during uninstall: {str(e)}")
            self.update_status("Uninstall error")
            messagebox.showerror("Uninstall Error", f"An error occurred during the uninstall process: {str(e)}")
            
    def _clear_app_data_dialog(self):
        """Show dialog to select app to clear data for"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Retrieving installed apps...")
            self.log_message("Getting list of installed apps...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Failed to get installed apps")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Get list of all apps
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages', '-3'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            
            if cmd.returncode == 0:
                # Process the output to get package names
                packages = []
                for line in cmd.stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        package_name = line[8:].strip()  # Remove 'package:' prefix
                        packages.append(package_name)
                        
                if not packages:
                    self.log_message("No third-party apps found on the device.")
                    self.update_status("No apps found")
                    messagebox.showinfo("No Apps", "No third-party applications were found on the device.")
                    return
                    
                # Sort alphabetically for better usability
                packages.sort()
                
                # Create a dialog to select an app
                dialog = tk.Toplevel(self)
                dialog.title("Select App to Clear Data")
                dialog.geometry("500x400")
                dialog.transient(self)  # Set to be on top of the parent window
                dialog.grab_set()  # Modal dialog
                
                # Add a label
                ttk.Label(
                    dialog, text="Select an application to clear data:", font=("Arial", 10, "bold")
                ).pack(pady=10)
                
                # Add a listbox with scrollbar
                list_frame = ttk.Frame(dialog)
                list_frame.pack(fill="both", expand=True, padx=10, pady=5)
                
                scrollbar = ttk.Scrollbar(list_frame)
                scrollbar.pack(side="right", fill="y")
                
                app_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 9))
                app_listbox.pack(side="left", fill="both", expand=True)
                
                scrollbar.config(command=app_listbox.yview)
                
                # Insert packages into the listbox
                for package in packages:
                    app_listbox.insert(tk.END, package)
                    
                # Buttons
                button_frame = ttk.Frame(dialog)
                button_frame.pack(fill="x", padx=10, pady=10)
                
                ttk.Button(
                    button_frame, text="Clear Data", 
                    command=lambda: self._clear_selected_app_data(dialog, app_listbox, serial, adb_cmd)
                ).pack(side="left", padx=5)
                
                ttk.Button(
                    button_frame, text="Cancel", command=dialog.destroy
                ).pack(side="right", padx=5)
                
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to get app list: {error_msg}")
                self.update_status("Failed to get app list")
                messagebox.showerror("Error", f"Failed to retrieve the list of installed applications.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error preparing clear data dialog: {str(e)}")
            self.update_status("Error preparing clear data dialog")
            messagebox.showerror("Error", f"An error occurred while preparing the clear data dialog: {str(e)}")
    
    def _clear_selected_app_data(self, dialog, app_listbox, serial, adb_cmd):
        """Clear data for the selected app"""
        selected = app_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select an app to clear data for.")
            return
            
        package_name = app_listbox.get(selected[0])
        
        # Confirm clear data
        confirm = messagebox.askyesno(
            "Confirm Clear Data", 
            f"WARNING: This will delete all data for the app.\n\n"
            f"Are you sure you want to clear data for:\n{package_name}"
        )
        
        if not confirm:
            return
            
        try:
            self.update_status(f"Clearing data for {package_name}...")
            self.log_message(f"Clearing data for app: {package_name}")
            
            # Execute clear data command
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'clear', package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20
            )
            
            if cmd.returncode == 0 and 'Success' in cmd.stdout:
                self.log_message(f"Successfully cleared data for {package_name}")
                self.update_status("App data cleared")
                messagebox.showinfo("Success", f"Successfully cleared data for {package_name}")
                dialog.destroy()
            else:
                error_msg = cmd.stderr.strip() or cmd.stdout.strip() or "Unknown error"
                self.log_message(f"Failed to clear app data: {error_msg}")
                self.update_status("Clear data failed")
                messagebox.showerror("Clear Data Failed", f"Failed to clear data for the app.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error during clear data: {str(e)}")
            self.update_status("Clear data error")
            messagebox.showerror("Clear Data Error", f"An error occurred while clearing app data: {str(e)}")
        
    def _force_stop_app_dialog(self):
        """Show dialog to select app to force stop"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Retrieving running apps...")
            self.log_message("Getting list of running apps...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Failed to get running apps")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Get list of running apps
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'ps'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            
            if cmd.returncode == 0:
                # Process the output to get package names
                packages = set()
                for line in cmd.stdout.strip().split('\n'):
                    # Look for lines containing package names (usually under the USER column)
                    parts = line.split()
                    if len(parts) >= 9:  # Make sure we have enough columns
                        pkg = parts[-1].strip()
                        # Filter out system processes and shell commands
                        if pkg and '.' in pkg and not pkg.startswith(('com.android', 'android.', 'system_', 'root', 'shell')):
                            packages.add(pkg)
                
                packages = sorted(list(packages))
                        
                if not packages:
                    self.log_message("No user apps are currently running.")
                    self.update_status("No running apps found")
                    messagebox.showinfo("No Running Apps", "No user applications are currently running.")
                    return
                    
                # Create a dialog to select an app
                dialog = tk.Toplevel(self)
                dialog.title("Select App to Force Stop")
                dialog.geometry("500x400")
                dialog.transient(self)  # Set to be on top of the parent window
                dialog.grab_set()  # Modal dialog
                
                # Add a label
                ttk.Label(
                    dialog, text="Select an application to force stop:", font=("Arial", 10, "bold")
                ).pack(pady=10)
                
                # Add a listbox with scrollbar
                list_frame = ttk.Frame(dialog)
                list_frame.pack(fill="both", expand=True, padx=10, pady=5)
                
                scrollbar = ttk.Scrollbar(list_frame)
                scrollbar.pack(side="right", fill="y")
                
                app_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 9))
                app_listbox.pack(side="left", fill="both", expand=True)
                
                scrollbar.config(command=app_listbox.yview)
                
                # Insert packages into the listbox
                for package in packages:
                    app_listbox.insert(tk.END, package)
                    
                # Buttons
                button_frame = ttk.Frame(dialog)
                button_frame.pack(fill="x", padx=10, pady=10)
                
                ttk.Button(
                    button_frame, text="Force Stop", 
                    command=lambda: self._force_stop_selected_app(dialog, app_listbox, serial, adb_cmd)
                ).pack(side="left", padx=5)
                
                ttk.Button(
                    button_frame, text="Cancel", command=dialog.destroy
                ).pack(side="right", padx=5)
                
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to get running apps: {error_msg}")
                self.update_status("Failed to get running apps")
                messagebox.showerror("Error", f"Failed to retrieve the list of running applications.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error preparing force stop dialog: {str(e)}")
            self.update_status("Error preparing force stop dialog")
            messagebox.showerror("Error", f"An error occurred while preparing the force stop dialog: {str(e)}")
    
    def _force_stop_selected_app(self, dialog, app_listbox, serial, adb_cmd):
        """Force stop the selected app"""
        selected = app_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select an app to force stop.")
            return
            
        package_name = app_listbox.get(selected[0])
        
        # Confirm force stop
        confirm = messagebox.askyesno(
            "Confirm Force Stop", 
            f"WARNING: This will immediately stop the app and may cause data loss.\n\n"
            f"Are you sure you want to force stop:\n{package_name}"
        )
        
        if not confirm:
            return
            
        try:
            self.update_status(f"Force stopping {package_name}...")
            self.log_message(f"Force stopping app: {package_name}")
            
            # Execute force stop command
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'am', 'force-stop', package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20
            )
            
            if cmd.returncode == 0:
                self.log_message(f"Successfully force stopped {package_name}")
                self.update_status("App force stopped")
                messagebox.showinfo("Success", f"Successfully force stopped {package_name}")
                dialog.destroy()
            else:
                error_msg = cmd.stderr.strip() or cmd.stdout.strip() or "Unknown error"
                self.log_message(f"Failed to force stop app: {error_msg}")
                self.update_status("Force stop failed")
                messagebox.showerror("Force Stop Failed", f"Failed to force stop the app.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error during force stop: {str(e)}")
            self.update_status("Force stop error")
            messagebox.showerror("Force Stop Error", f"An error occurred while force stopping the app: {str(e)}")
        
    def _list_installed_apps(self):
        """Show a list of all installed apps"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Retrieving installed apps...")
            self.log_message("Getting list of all installed apps...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Failed to get installed apps")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Get list of all apps (both system and user)
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages', '-f'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if cmd.returncode == 0:
                # Process the output to get package names and paths
                packages = []
                for line in cmd.stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        # Extract package path and name (format: package:/path/to/app.apk=package.name)
                        parts = line[8:].strip().split('=')
                        if len(parts) == 2:
                            apk_path = parts[0]
                            package_name = parts[1]
                            packages.append((package_name, apk_path))
                
                if not packages:
                    self.log_message("No apps found on the device.")
                    self.update_status("No apps found")
                    messagebox.showinfo("No Apps", "No applications were found on the device.")
                    return
                
                # Sort alphabetically by package name
                packages.sort(key=lambda x: x[0].lower())
                
                # Create a new window to display the list
                app_window = tk.Toplevel(self)
                app_window.title("Installed Applications")
                app_window.geometry("800x600")
                
                # Center the window
                x_pos = (self.winfo_screenwidth() - 800) // 2
                y_pos = (self.winfo_screenheight() - 600) // 2
                app_window.geometry(f"+{x_pos}+{y_pos}")
                
                # Create a frame for the search box
                search_frame = ttk.Frame(app_window)
                search_frame.pack(fill="x", padx=10, pady=10)
                
                ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
                
                search_var = tk.StringVar()
                search_entry = ttk.Entry(search_frame, textvariable=search_var, width=50)
                search_entry.pack(side="left", fill="x", expand=True)
                
                # Create a frame for the treeview and scrollbars
                tree_frame = ttk.Frame(app_window)
                tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                
                # Create a treeview with scrollbars
                tree_scroll_y = ttk.Scrollbar(tree_frame)
                tree_scroll_y.pack(side="right", fill="y")
                
                tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
                tree_scroll_x.pack(side="bottom", fill="x")
                
                columns = ("package", "path")
                tree = FixedHeaderTreeview(
                    tree_frame, 
                    columns=columns, 
                    show="headings",
                    yscrollcommand=tree_scroll_y.set,
                    xscrollcommand=tree_scroll_x.set
                )
                
                # Configure the scrollbars
                tree_scroll_y.config(command=tree.yview)
                tree_scroll_x.config(command=tree.xview)
                
                # Define columns
                tree.heading("package", text="Package Name", anchor="w")
                tree.heading("path", text="APK Path", anchor="w")
                
                # Set column widths
                tree.column("package", width=300, minwidth=200, stretch=tk.YES)
                tree.column("path", width=450, minwidth=300, stretch=tk.YES)
                
                # Add data to the treeview
                for package, path in packages:
                    tree.insert("", "end", values=(package, path))
                
                tree.pack(side="left", fill="both", expand=True)
                
                # Add a context menu
                context_menu = tk.Menu(app_window, tearoff=0)
                context_menu.add_command(label="Copy Package Name", 
                                       command=lambda: self._copy_to_clipboard(tree, "package"))
                context_menu.add_command(label="Copy APK Path", 
                                       command=lambda: self._copy_to_clipboard(tree, "path"))
                
                def show_context_menu(event):
                    item = tree.identify_row(event.y)
                    if item:
                        tree.selection_set(item)
                        context_menu.post(event.x_root, event.y_root)
                
                tree.bind("<Button-3>", show_context_menu)
                
                # Function to filter the treeview based on search text
                def filter_tree(*args):
                    search_text = search_var.get().lower()
                    for item in tree.get_children():
                        values = tree.item(item, 'values')
                        if search_text in ' '.join(values).lower():
                            tree.reattach(item, '', 'end')
                        else:
                            tree.detach(item)
                
                search_var.trace_add("write", filter_tree)
                
                # Add a status bar
                status_bar = ttk.Label(
                    app_window, 
                    text=f"Total apps: {len(packages)}",
                    relief=tk.SUNKEN, 
                    anchor=tk.W
                )
                status_bar.pack(side=tk.BOTTOM, fill=tk.X)
                
                # Set focus to search box
                search_entry.focus_set()
                
                self.update_status(f"Found {len(packages)} installed apps")
                self.log_message(f"Displaying list of {len(packages)} installed apps")
                
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to get installed apps: {error_msg}")
                self.update_status("Failed to get installed apps")
                messagebox.showerror("Error", f"Failed to retrieve the list of installed applications.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error retrieving installed apps: {str(e)}")
            self.update_status("Error retrieving installed apps")
            messagebox.showerror("Error", f"An error occurred while retrieving the list of installed applications: {str(e)}")
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            
            # Get list of system apps
            sys_cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages', '-s'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            
            if cmd.returncode == 0 and sys_cmd.returncode == 0:
                # Process the output to get package names
                all_packages = set()
                system_packages = set()
                
                for line in cmd.stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        package_name = line[8:].strip()  # Remove 'package:' prefix
                        all_packages.add(package_name)
                        
                for line in sys_cmd.stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        package_name = line[8:].strip()  # Remove 'package:' prefix
                        system_packages.add(package_name)
                
                user_packages = all_packages - system_packages
                
                # Create a dialog to show apps
                dialog = tk.Toplevel(self)
                dialog.title("Installed Applications")
                dialog.geometry("700x500")
                dialog.transient(self)  # Set to be on top of the parent window
                dialog.grab_set()  # Modal dialog
                
                # Add a notebook with tabs for app categories
                app_notebook = ttk.Notebook(dialog)
                app_notebook.pack(fill="both", expand=True, padx=10, pady=10)
                
                # User Apps Tab
                user_frame = ttk.Frame(app_notebook)
                app_notebook.add(user_frame, text="User Apps")
                
                # System Apps Tab
                system_frame = ttk.Frame(app_notebook)
                app_notebook.add(system_frame, text="System Apps")
                
                # All Apps Tab
                all_frame = ttk.Frame(app_notebook)
                app_notebook.add(all_frame, text="All Apps")
                
                # Create lists for each tab
                self._create_app_list(user_frame, sorted(user_packages))
                self._create_app_list(system_frame, sorted(system_packages))
                self._create_app_list(all_frame, sorted(all_packages))
                
                # Close button
                ttk.Button(
                    dialog, text="Close", command=dialog.destroy
                ).pack(pady=10)
                
                self.update_status("App list displayed")
                
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to get app list: {error_msg}")
                self.update_status("Failed to get app list")
                messagebox.showerror("Error", f"Failed to retrieve the list of installed applications.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error listing installed apps: {str(e)}")
            self.update_status("Error listing apps")
            messagebox.showerror("Error", f"An error occurred while getting the list of installed apps: {str(e)}")
            
    def _create_app_list(self, parent, packages):
        """Create a scrollable list of apps"""
        # Frame with scrollbar
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        # Create a text widget to display the list
        app_text = tk.Text(frame, yscrollcommand=scrollbar.set, font=("Courier", 9))
        app_text.pack(side="left", fill="both", expand=True)
        
        scrollbar.config(command=app_text.yview)
        
        # Insert packages with numbers
        app_text.config(state="normal")
        for i, package in enumerate(packages, 1):
            app_text.insert(tk.END, f"{i:3d}. {package}\n")
        app_text.config(state="disabled")
        
    def _extract_apk_dialog(self):
        """Show dialog to select an app and extract its APK"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        dialog = tk.Toplevel(self)
        dialog.title("Extract APK")
        dialog.geometry("400x500")
        
        # Center the dialog
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 500) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Select an app to extract:", font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Search box
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Listbox for apps
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        app_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        app_listbox.pack(fill="both", expand=True)
        scrollbar.config(command=app_listbox.yview)
        
        # Status bar
        status_var = tk.StringVar()
        status_bar = ttk.Label(dialog, textvariable=status_var, relief="sunken")
        status_bar.pack(fill="x", side="bottom", padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        extract_btn = ttk.Button(button_frame, text="Extract APK", 
                               command=lambda: self._extract_selected_apk(app_listbox, dialog))
        extract_btn.pack(side="left", padx=5)
        
        close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
        close_btn.pack(side="right", padx=5)
        
        # Load apps in background
        self._load_apps_for_selection(app_listbox, status_var, search_var)
        
        # Bind search
        search_var.trace_add("write", lambda *args: self._filter_app_list(app_listbox, search_var.get()))
        
    def _toggle_freeze_dialog(self):
        """Show dialog to freeze/unfreeze an app"""
        print("DEBUG: _toggle_freeze_dialog called")
        try:
            if not hasattr(self, 'device_connected') or not self.device_connected:
                error_msg = "Device not connected or device_connected attribute missing"
                print(f"ERROR: {error_msg}")
                messagebox.showinfo("Not Connected", "Please connect to a device first.")
                return
                
            print("DEBUG: Creating freeze dialog window")
            dialog = tk.Toplevel(self)
            dialog.title("Freeze/Unfreeze App")
            dialog.geometry("400x500")
            
            # Center the dialog
            try:
                x = self.winfo_x() + (self.winfo_width() - 400) // 2
                y = self.winfo_y() + (self.winfo_height() - 500) // 2
                dialog.geometry(f"+{x}+{y}")
                print(f"DEBUG: Dialog positioned at {x},{y}")
            except Exception as e:
                print(f"WARNING: Could not position dialog: {str(e)}")
                dialog.geometry("400x500+100+100")
            
            # Status variable
            status_var = tk.StringVar()
            status_var.set("Loading apps...")
            
            # App list
            print("DEBUG: Creating app list frame")
            list_frame = ttk.LabelFrame(dialog, text="Installed Apps", padding=5)
            list_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            app_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=app_listbox.yview)
            app_listbox.configure(yscrollcommand=scrollbar.set)
            
            scrollbar.pack(side="right", fill="y")
            app_listbox.pack(side="left", fill="both", expand=True)
            
            # Status label
            status_label = ttk.Label(dialog, textvariable=status_var, wraplength=380)
            status_label.pack(fill="x", padx=5, pady=5)
            
            # Buttons
            print("DEBUG: Creating button frame")
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill="x", padx=5, pady=5)
            
            toggle_btn = ttk.Button(button_frame, text="Toggle Freeze",
                                  command=lambda: self._toggle_app_freeze(app_listbox, status_var))
            toggle_btn.pack(side="left", padx=5)
            
            close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
            close_btn.pack(side="right", padx=5)
            
            # Load apps in background
            print("DEBUG: Starting background app load")
            try:
                self._load_apps_for_selection(app_listbox, status_var, None, include_frozen=True)
                print("DEBUG: Background app load started successfully")
            except Exception as e:
                error_msg = f"Failed to start app loading: {str(e)}"
                print(f"ERROR: {error_msg}")
                status_var.set(f"Error: {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error in _toggle_freeze_dialog: {str(e)}"
            print(f"CRITICAL ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", "An unexpected error occurred. Please check the console for details.")
    
    def _open_app_dialog(self):
        """Show dialog to select app to open"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            self.update_status("Retrieving launchable apps...")
            self.log_message("Getting list of launchable applications...")
            
            # Determine the ADB command based on platform
            if IS_WINDOWS and hasattr(self, 'adb_path'):
                adb_cmd = self.adb_path
            else:
                # On Linux/Mac, use command directly if it's in PATH
                adb_cmd = 'adb'
                
            # Get the serial number for the device
            serial = self.device_info.get('serial')
            if not serial:
                self.log_message("Device serial not found")
                self.update_status("Failed to get app list")
                return
                
            # Clean serial number if it contains debug info
            if isinstance(serial, str) and '\n' in serial:
                serial = serial.split('\n')[0].strip()
                
            # Get list of launchable apps using 'pm list packages -l' to get more info
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'pm', 'list', 'packages', '-l', '-3'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            
            if cmd.returncode == 0:
                # Get package names first
                package_names = []
                for line in cmd.stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        parts = line[8:].strip().split('=')
                        if len(parts) == 2:
                            package_name = parts[1].strip()
                            package_names.append(package_name)
                
                if not package_names:
                    self.log_message("No third-party apps found on the device.")
                    self.update_status("No apps found")
                    messagebox.showinfo("No Apps", "No third-party applications were found on the device.")
                    return
                
                # Get app labels using 'dumpsys package' for each package
                apps = []
                for package in package_names:
                    # Get app label and main activity
                    cmd_dump = subprocess.run(
                        [adb_cmd, '-s', serial, 'shell', 'dumpsys', 'package', package],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    
                    if cmd_dump.returncode == 0:
                        app_label = package  # Default to package name if label not found
                        main_activity = None
                        
                        # Parse the output to find app label and main activity
                        for line in cmd_dump.stdout.split('\n'):
                            line = line.strip()
                            if 'applicationInfo' in line and 'labelRes=' in line and 'nonLocalizedLabel=' in line:
                                # Extract label if available
                                if 'labelRes=0x0' not in line and 'nonLocalizedLabel=null' not in line:
                                    label_match = re.search(r'labelRes=0x[0-9a-fA-F]+', line)
                                    if label_match:
                                        app_label = f"{package} (No Label)"
                            
                            # Find main activity
                            if 'android.intent.action.MAIN' in line and 'category.LAUNCHER' in line:
                                activity_match = re.search(r'([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)', line)
                                if activity_match:
                                    main_activity = activity_match.group(1)
                        
                        # If we found a main activity, add to our apps list
                        if main_activity:
                            apps.append({
                                'package': package,
                                'label': app_label,
                                'activity': main_activity
                            })
                
                if not apps:
                    self.log_message("No launchable apps found on the device.")
                    self.update_status("No launchable apps")
                    messagebox.showinfo("No Launchable Apps", "No launchable applications were found on the device.")
                    return
                
                # Sort apps by label for better usability
                apps.sort(key=lambda x: x['label'].lower())
                
                # Create a dialog to select an app
                dialog = tk.Toplevel(self)
                dialog.title("Select App to Open")
                dialog.geometry("600x500")
                dialog.transient(self)  # Set to be on top of the parent window
                dialog.grab_set()  # Modal dialog
                
                # Add a label
                ttk.Label(
                    dialog, 
                    text="Select an application to launch:", 
                    font=("Arial", 10, "bold")
                ).pack(pady=10)
                
                # Add a search box
                search_frame = ttk.Frame(dialog)
                search_frame.pack(fill="x", padx=10, pady=5)
                
                ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
                
                search_var = tk.StringVar()
                search_entry = ttk.Entry(search_frame, textvariable=search_var, width=50)
                search_entry.pack(side="left", fill="x", expand=True)
                
                # Add a listbox with scrollbar
                list_frame = ttk.Frame(dialog)
                list_frame.pack(fill="both", expand=True, padx=10, pady=5)
                
                scrollbar = ttk.Scrollbar(list_frame)
                scrollbar.pack(side="right", fill="y")
                
                app_listbox = tk.Listbox(
                    list_frame, 
                    yscrollcommand=scrollbar.set, 
                    font=("Arial", 9),
                    selectmode=tk.SINGLE
                )
                app_listbox.pack(side="left", fill="both", expand=True)
                
                scrollbar.config(command=app_listbox.yview)
                
                # Store app data for later use
                app_listbox.apps = apps
                
                # Insert apps into the listbox with their labels
                for app in apps:
                    app_listbox.insert(tk.END, f"{app['label']} ({app['package']})")
                
                # Buttons
                button_frame = ttk.Frame(dialog)
                button_frame.pack(fill="x", padx=10, pady=10)
                
                ttk.Button(
                    button_frame, 
                    text="Open App", 
                    command=lambda: self._launch_selected_app(dialog, app_listbox, serial, adb_cmd)
                ).pack(side="left", padx=5)
                
                ttk.Button(
                    button_frame, 
                    text="Cancel", 
                    command=dialog.destroy
                ).pack(side="right", padx=5)
                
                # Function to filter the list based on search text
                def filter_list(*args):
                    search_text = search_var.get().lower()
                    app_listbox.delete(0, tk.END)
                    for app in apps:
                        if search_text in app['label'].lower() or search_text in app['package'].lower():
                            app_listbox.insert(tk.END, f"{app['label']} ({app['package']})")
                
                search_var.trace_add("write", filter_list)
                
                # Bind double-click to launch app
                def on_double_click(event):
                    self._launch_selected_app(dialog, app_listbox, serial, adb_cmd)
                
                app_listbox.bind("<Double-1>", on_double_click)
                
                # Set focus to search box
                search_entry.focus_set()
                
                self.update_status(f"Found {len(apps)} launchable apps")
                
            else:
                error_msg = cmd.stderr.strip() or "Unknown error"
                self.log_message(f"Failed to get app list: {error_msg}")
                self.update_status("Failed to get app list")
                messagebox.showerror("Error", f"Failed to retrieve the list of applications.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error preparing open app dialog: {str(e)}")
            self.update_status("Error preparing open app dialog")
    
    def _update_app_list(self, listbox, packages, status_var, search_var=None):
        """Update the listbox with the given packages and update status"""
        try:
            print(f"DEBUG: Updating app list with {len(packages)} packages")
            
            # Clear the listbox
            listbox.delete(0, tk.END)
            
            # Get current filter text if search_var is provided
            current_filter = search_var.get().lower() if search_var else ""
            
            # Filter packages based on search text
            filtered_pkgs = [pkg for pkg in packages if current_filter in pkg.lower()]
            
            # Add packages to listbox
            for pkg in sorted(filtered_pkgs):
                listbox.insert(tk.END, pkg)
                
            # Update status
            status_text = f"Loaded {len(filtered_pkgs)} of {len(packages)} apps"
            status_var.set(status_text)
            print(f"DEBUG: {status_text}")
            
        except Exception as e:
            error_msg = f"Error updating app list: {str(e)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            status_var.set(f"Error: {error_msg}")
    
    def _load_apps_for_selection(self, listbox, status_var, search_var=None, include_frozen=False):
        """Load apps into the listbox in a background thread with enhanced error logging"""
        print("DEBUG: _load_apps_for_selection called")
        
        def load_apps():
            print("DEBUG: Starting app loading in background thread")
            try:
                # Update status in UI
                self.after(0, lambda: status_var.set("Loading apps..."))
                
                # Verify ADB path and device
                if not hasattr(self, 'adb_path') or not self.adb_path:
                    raise Exception("ADB path not set")
                    
                if not hasattr(self, 'device_serial') or not self.device_serial:
                    raise Exception("Device serial not set")
                
                print(f"DEBUG: Using ADB path: {self.adb_path}")
                print(f"DEBUG: Using device: {self.device_serial}")
                
                # Get list of packages
                cmd = [self.adb_path, '-s', self.device_serial, 'shell', 'pm', 'list', 'packages', '-3']
                if include_frozen:
                    cmd.append('--show-versioncode')
                
                print(f"DEBUG: Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30
                )
                
                print(f"DEBUG: Command output: {result.stdout[:200]}...")  # First 200 chars of output
                if result.stderr:
                    print(f"DEBUG: Command error: {result.stderr}")
                
                if result.returncode != 0:
                    error_msg = f"Failed to list packages (code {result.returncode}): {result.stderr.strip()}"
                    print(f"ERROR: {error_msg}")
                    raise Exception(error_msg)
                
                # Parse package list
                packages = []
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                        
                    if include_frozen and 'versionCode=' in line:
                        pkg = line.split('=')[1].split(' ')[0]
                    else:
                        pkg = line.replace('package:', '')
                    
                    if pkg and pkg not in packages:
                        packages.append(pkg)
                
                print(f"DEBUG: Found {len(packages)} packages")
                
                # Update UI in main thread
                self.after(0, lambda: self._update_app_list(listbox, packages, status_var, search_var))
                
            except subprocess.TimeoutExpired:
                error_msg = "Timed out while loading apps"
                print(f"ERROR: {error_msg}")
                self.after(0, lambda: status_var.set(f"Error: {error_msg}"))
                
            except Exception as e:
                import traceback
                error_msg = f"Error loading apps: {str(e)}"
                print(f"ERROR: {error_msg}")
                print(f"Traceback: {traceback.format_exc()}")
                self.after(0, lambda: status_var.set(f"Error: {error_msg}"))
        
        # Start the loading thread
        try:
            thread = threading.Thread(target=load_apps, daemon=True)
            thread.start()
            print("DEBUG: Started app loading thread")
        except Exception as e:
            error_msg = f"Failed to start app loading thread: {str(e)}"
            print(f"CRITICAL ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda: status_var.set(f"Error: {error_msg}"))
    
    def _filter_app_list(self, listbox, search_text):
        """Filter the app list based on search text"""
        items = listbox.get(0, tk.END)
        listbox.delete(0, tk.END)
        
        for item in items:
            if search_text.lower() in item.lower():
                listbox.insert(tk.END, item)
    
    def _extract_selected_apk(self, listbox, dialog):
        """Extract APK for the selected app"""
        selected = listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select an app to extract.")
            return
            
        package_name = listbox.get(selected[0])
        dialog.destroy()
        self._run_in_thread(lambda: self._extract_apk(package_name))
    
    def _extract_apk(self, package_name):
        """Extract APK for the specified package"""
        try:
            # Ask user for save location
            save_dir = filedialog.askdirectory(
                title="Select Directory to Save APK",
                initialdir=os.path.expanduser("~/Downloads")
            )
            
            if not save_dir:
                return  # User cancelled
                
            self.update_status(f"Extracting {package_name}.apk...")
            
            # Get the APK path on the device
            result = subprocess.run(
                [self.adb_path, '-s', self.device_serial, 'shell', 'pm', 'path', package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                raise Exception(f"Failed to get APK path: {result.stderr.strip()}")
                
            # Extract the APK path
            apk_path = result.stdout.strip().split(':', 1)[1]
            
            # Create the output filename
            output_file = os.path.join(save_dir, f"{package_name}.apk")
            
            # Pull the APK file
            pull_cmd = subprocess.run(
                [self.adb_path, '-s', self.device_serial, 'pull', apk_path, output_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if pull_cmd.returncode != 0:
                raise Exception(f"Failed to pull APK: {pull_cmd.stderr.strip()}")
                
            self.update_status(f"APK extracted to: {output_file}")
            
            # Show success message with option to open the containing folder
            if messagebox.askyesno(
                "Extraction Complete",
                f"APK extracted successfully to:\n{output_file}\n\nOpen containing folder?"
            ):
                if sys.platform == 'win32':
                    os.startfile(os.path.dirname(output_file))
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', os.path.dirname(output_file)])
                else:
                    subprocess.Popen(['xdg-open', os.path.dirname(output_file)])
                    
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            messagebox.showerror("Extraction Error", f"Failed to extract APK: {str(e)}")
    
    def _view_permissions_dialog(self):
        """Show dialog to view app permissions"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        dialog = tk.Toplevel(self)
        dialog.title("View App Permissions")
        dialog.geometry("800x600")
        
        # Center the dialog
        x = self.winfo_x() + (self.winfo_width() - 800) // 2
        y = self.winfo_y() + (self.winfo_height() - 600) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Select an app to view permissions:", font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Search box
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Main content frame
        content_frame = ttk.Frame(dialog)
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel - App list
        list_frame = ttk.LabelFrame(content_frame, text="Installed Apps")
        list_frame.pack(side="left", fill="y", padx=(0, 5))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        app_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=40, height=25)
        app_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=app_listbox.yview)
        
        # Right panel - Permissions
        perm_frame = ttk.LabelFrame(content_frame, text="Permissions")
        perm_frame.pack(side="right", fill="both", expand=True)
        
        perm_text = tk.Text(perm_frame, wrap=tk.WORD, width=60, height=25)
        perm_text.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        
        # Add scrollbar to permissions text
        perm_scroll = ttk.Scrollbar(perm_frame, command=perm_text.yview)
        perm_scroll.pack(side="right", fill="y")
        perm_text.config(yscrollcommand=perm_scroll.set)
        
        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        view_btn = ttk.Button(button_frame, text="View Permissions",
                            command=lambda: self._show_app_permissions(app_listbox, perm_text))
        view_btn.pack(side="left", padx=5)
        
        close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
        close_btn.pack(side="right", padx=5)
        
        # Status bar
        status_var = tk.StringVar()
        status_bar = ttk.Label(dialog, textvariable=status_var, relief="sunken")
        status_bar.pack(fill="x", side="bottom", padx=5, pady=5)
        
        # Load apps in background
        def load_apps():
            try:
                status_var.set("Loading apps...")
                result = subprocess.run(
                    [self.adb_path, '-s', self.device_serial, 'shell', 'pm', 'list', 'packages', '-3'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise Exception(result.stderr.strip())
                
                packages = []
                for line in result.stdout.splitlines():
                    if line.startswith('package:'):
                        pkg = line.replace('package:', '').strip()
                        packages.append(pkg)
                
                # Update UI in main thread
                dialog.after(0, lambda: self._update_permissions_app_list(app_listbox, packages, status_var))
                
            except Exception as e:
                dialog.after(0, lambda: status_var.set(f"Error: {str(e)}"))
        
        threading.Thread(target=load_apps, daemon=True).start()
        
        # Bind search
        search_var.trace_add("write", lambda *args: self._filter_app_list(app_listbox, search_var.get()))
        
        # Bind double-click to view permissions
        app_listbox.bind("<Double-1>", lambda e: self._show_app_permissions(app_listbox, perm_text))
    
    def _update_permissions_app_list(self, listbox, packages, status_var):
        """Update the app list in permissions dialog"""
        listbox.delete(0, tk.END)
        for pkg in sorted(packages):
            listbox.insert(tk.END, pkg)
        status_var.set(f"Loaded {len(packages)} apps")
    
    def _show_app_usage_stats(self):
        """Show app usage statistics"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        dialog = tk.Toplevel(self)
        dialog.title("App Usage Statistics")
        dialog.geometry("900x700")
        
        # Center the dialog
        x = self.winfo_x() + (self.winfo_width() - 900) // 2
        y = self.winfo_y() + (self.winfo_height() - 700) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Create a text widget to display the stats
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Add buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        refresh_btn = ttk.Button(button_frame, text="Refresh",
                               command=lambda: self._load_usage_stats(text_widget))
        refresh_btn.pack(side="left", padx=5)
        
        close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
        close_btn.pack(side="right", padx=5)
        
        # Status bar
        status_var = tk.StringVar()
        status_bar = ttk.Label(dialog, textvariable=status_var, relief="sunken")
        status_bar.pack(fill="x", side="bottom", padx=5, pady=5)
        
        # Load stats in background
        def load_stats():
            try:
                status_var.set("Loading app usage statistics...")
                
                # Get app usage stats
                result = subprocess.run(
                    [self.adb_path, '-s', self.device_serial, 'shell', 'dumpsys', 'usagestats'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15
                )
                
                if result.returncode != 0:
                    raise Exception(result.stderr.strip())
                
                # Parse and format the output
                stats = self._parse_usage_stats(result.stdout)
                
                # Update UI in main thread
                dialog.after(0, lambda: self._display_usage_stats(text_widget, stats, status_var))
                
            except Exception as e:
                dialog.after(0, lambda: status_var.set(f"Error: {str(e)}"))
        
        threading.Thread(target=load_stats, daemon=True).start()
    
    def _parse_usage_stats(self, dump_output):
        """Parse the output of 'dumpsys usagestats'"""
        stats = []
        current_app = None
        
        for line in dump_output.splitlines():
            line = line.strip()
            
            # Look for app entries
            if ':' in line and '=' not in line and ' ' not in line.split(':', 1)[0]:
                current_app = line.split(':', 1)[0]
                
            # Look for time in foreground
            elif 'Time spent in' in line and current_app:
                time_spent = line.split(':', 1)[1].strip()
                stats.append((current_app, time_spent))
        
        return stats
    
    def _display_usage_stats(self, text_widget, stats, status_var):
        """Display the parsed usage statistics"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        
        text_widget.insert(tk.END, "App Usage Statistics\n")
        text_widget.insert(tk.END, "=" * 50 + "\n\n")
        
        if not stats:
            text_widget.insert(tk.END, "No usage statistics available.")
        else:
            for app, time_spent in stats:
                text_widget.insert(tk.END, f"• {app}: {time_spent}\n")
        
        text_widget.config(state=tk.DISABLED)
        status_var.set(f"Loaded {len(stats)} app usage records")
    
    def _show_battery_usage(self):
        """Show battery usage statistics"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        dialog = tk.Toplevel(self)
        dialog.title("Battery Usage")
        dialog.geometry("900x700")
        
        # Center the dialog
        x = self.winfo_x() + (self.winfo_width() - 900) // 2
        y = self.winfo_y() + (self.winfo_height() - 700) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Create a text widget to display the stats
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Add buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        refresh_btn = ttk.Button(button_frame, text="Refresh",
                               command=lambda: self._load_battery_stats(text_widget))
        refresh_btn.pack(side="left", padx=5)
        
        close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
        close_btn.pack(side="right", padx=5)
        
        # Status bar
        status_var = tk.StringVar()
        status_bar = ttk.Label(dialog, textvariable=status_var, relief="sunken")
        status_bar.pack(fill="x", side="bottom", padx=5, pady=5)
        
        # Load stats in background
        def load_stats():
            try:
                status_var.set("Loading battery statistics...")
                
                # Get battery stats
                result = subprocess.run(
                    [self.adb_path, '-s', self.device_serial, 'shell', 'dumpsys', 'batterystats', '--checkin'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15
                )
                
                if result.returncode != 0:
                    raise Exception(result.stderr.strip())
                
                # Parse and format the output
                stats = self._parse_battery_stats(result.stdout)
                
                # Update UI in main thread
                dialog.after(0, lambda: self._display_battery_stats(text_widget, stats, status_var))
                
            except Exception as e:
                dialog.after(0, lambda: status_var.set(f"Error: {str(e)}"))
        
        threading.Thread(target=load_stats, daemon=True).start()
    
    def _parse_battery_stats(self, dump_output):
        """Parse the output of 'dumpsys batterystats --checkin'"""
        stats = []
        
        for line in dump_output.splitlines():
            if not line.startswith('b,'):
                continue
                
            parts = line.split(',')
            if len(parts) < 8:  # Make sure we have enough fields
                continue
                
            uid = parts[1]
            package_name = parts[3]
            power_usage = parts[7]
            
            # Only include user apps (u0_ prefix) and skip system components
            if uid.startswith('u0_') and package_name and not package_name.startswith('android.') and not package_name.startswith('com.android.'):
                stats.append((package_name, power_usage))
        
        # Sort by power usage (descending)
        stats.sort(key=lambda x: float(x[1]) if x[1].replace('.', '').isdigit() else 0, reverse=True)
        return stats
    
    def _display_battery_stats(self, text_widget, stats, status_var):
        """Display the parsed battery statistics"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        
        text_widget.insert(tk.END, "Battery Usage by App\n")
        text_widget.insert(tk.END, "=" * 50 + "\n\n")
        
        if not stats:
            text_widget.insert(tk.END, "No battery usage statistics available.")
        else:
            text_widget.insert(tk.END, "App\t\tPower (mAh)\n")
            text_widget.insert(tk.END, "-" * 50 + "\n")
            
            for app, power in stats:
                text_widget.insert(tk.END, f"{app}\t\t{power} mAh\n")
        
        text_widget.config(state=tk.DISABLED)
        status_var.set(f"Loaded battery stats for {len(stats)} apps")
    
    def _show_app_permissions(self, listbox, text_widget):
        """Show permissions for the selected app"""
        selected = listbox.curselection()
        if not selected:
            return
            
        package_name = listbox.get(selected[0])
        
        try:
            # Get app info
            result = subprocess.run(
                [self.adb_path, '-s', self.device_serial, 'shell', 'dumpsys', 'package', package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise Exception(result.stderr.strip())
            
            # Parse permissions
            permissions = []
            in_permissions = False
            
            for line in result.stdout.splitlines():
                line = line.strip()
                
                if "requested permissions:" in line:
                    in_permissions = True
                    continue
                elif in_permissions and not line:
                    in_permissions = False
                    break
                    
                if in_permissions and line.startswith('android.permission.'):
                    permissions.append(line)
            
            # Display in text widget
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            
            text_widget.insert(tk.END, f"Permissions for: {package_name}\n")
            text_widget.insert(tk.END, "=" * 50 + "\n\n")
            
            if not permissions:
                text_widget.insert(tk.END, "No permissions found or could not be determined.")
            else:
                for perm in sorted(permissions):
                    text_widget.insert(tk.END, f"• {perm}\n")
            
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
    def _toggle_app_freeze(self, listbox, status_var):
        """Toggle freeze state for the selected app"""
        try:
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("No Selection", "Please select an app to freeze/unfreeze.")
                return
                
            package_name = listbox.get(selected[0])
            print(f"Attempting to toggle freeze state for package: {package_name}")
            
            # Check current state
            cmd = [self.adb_path, '-s', self.device_serial, 'shell', 'pm', 'list', 'packages', '--disabled']
            print(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"Failed to get app state: {result.stderr.strip()}"
                print(error_msg)
                raise Exception(error_msg)
                
            is_frozen = f"package:{package_name}" in result.stdout
            action = 'disable' if not is_frozen else 'enable'
            print(f"Current state - frozen: {is_frozen}, action: {action}")
            
            # Toggle the state
            cmd = [self.adb_path, '-s', self.device_serial, 'shell', 'pm', action, package_name]
            print(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            print(f"Toggle command output: {result.stdout}")
            print(f"Toggle command error: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"Failed to toggle app state: {result.stderr.strip()}"
                print(error_msg)
                raise Exception(error_msg)
                
            new_state = "frozen" if not is_frozen else "unfrozen"
            status_msg = f"Successfully {new_state} {package_name}"
            print(status_msg)
            status_var.set(status_msg)
            
        except subprocess.TimeoutExpired:
            error_msg = "Operation timed out while toggling app state"
            print(error_msg)
            status_var.set(f"Error: {error_msg}")
            messagebox.showerror("Error", error_msg)
            
        except Exception as e:
            import traceback
            error_msg = f"Error in _toggle_app_freeze: {str(e)}"
            print(error_msg)
            print(f"Traceback: {traceback.format_exc()}")
            status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to toggle app state: {str(e)}")
    
    def _launch_selected_app(self, dialog, app_listbox, serial, adb_cmd):
        """Launch the selected application"""
        # ... (rest of the code remains the same)
        selected = app_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select an app to launch.")
            return
            
        # Get the selected app's data
        app = app_listbox.apps[selected[0]]
        package_name = app['package']
        activity = app['activity']
        
        try:
            self.update_status(f"Launching {package_name}...")
            self.log_message(f"Launching app: {package_name} ({activity})")
            
            # Execute the launch command
            cmd = subprocess.run(
                [adb_cmd, '-s', serial, 'shell', 'am', 'start', '-n', activity],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            
            if cmd.returncode == 0:
                self.log_message(f"Successfully launched {package_name}")
                self.update_status("App launched")
                dialog.destroy()
            else:
                error_msg = cmd.stderr.strip() or cmd.stdout.strip() or "Unknown error"
                self.log_message(f"Failed to launch app: {error_msg}")
                self.update_status("Launch failed")
                messagebox.showerror("Launch Failed", f"Failed to launch the application.\n\nError: {error_msg}")
                
        except Exception as e:
            self.log_message(f"Error during app launch: {str(e)}")
            self.update_status("Launch error")
            messagebox.showerror("Launch Error", f"An error occurred while launching the application: {str(e)}")
        
    # File Management Functions
    def _pull_from_device(self):
        """Pull a file or folder from the device to the computer"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Ask user to select a file or folder on the device
        device_path = filedialog.askdirectory(
            title="Select File or Folder on Device",
            initialdir="/sdcard"
        )
        
        if not device_path:
            return  # User cancelled
            
        # Ask where to save the file/folder on the computer
        local_path = filedialog.askdirectory(
            title="Select Destination Folder on Computer"
        )
        
        if not local_path:
            return  # User cancelled
            
        # Get ADB command and serial
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        # Create a progress dialog
        progress = ttk.Progressbar(
            self, orient="horizontal", length=300, mode="indeterminate"
        )
        progress.pack(pady=10)
        progress.start()
        
        try:
            # Run ADB pull command
            cmd = [adb_cmd, "-s", serial, "pull", device_path, local_path]
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                messagebox.showinfo("Success", f"Successfully pulled to {local_path}")
            else:
                messagebox.showerror("Error", f"Failed to pull file/folder: {stderr}")
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            progress.stop()
            progress.destroy()
        
    def _push_to_device(self):
        """Push a file or folder from the computer to the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Ask user to select a file or folder on the computer
        local_path = filedialog.askopenfilename(
            title="Select File or Folder to Push",
            initialdir=os.path.expanduser("~"),
            multiple=False
        )
        
        if not local_path:
            return  # User cancelled
            
        # Ask where to save the file/folder on the device
        device_path = filedialog.askdirectory(
            title="Select Destination Folder on Device",
            initialdir="/sdcard"
        )
        
        if not device_path:
            return  # User cancelled
            
        # Get ADB command and serial
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        # Create a progress dialog
        progress = ttk.Progressbar(
            self, orient="horizontal", length=300, mode="indeterminate"
        )
        progress.pack(pady=10)
        progress.start()
        
        try:
            # Run ADB push command
            cmd = [adb_cmd, "-s", serial, "push", local_path, device_path]
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                messagebox.showinfo("Success", f"Successfully pushed to {device_path}")
            else:
                messagebox.showerror("Error", f"Failed to push file/folder: {stderr}")
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            progress.stop()
            progress.destroy()
        
    # System Tools Functions
    def _show_detailed_device_info(self):
        """Show detailed information about the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Create a new window for device info
            info_window = tk.Toplevel(self)
            info_window.title(f"Device Info - {self.device_info.get('model', 'Android Device')}")
            info_window.geometry("800x600")
            info_window.minsize(700, 500)
            info_window.transient(self)
            info_window.grab_set()
            
            # Create notebook for tabs
            notebook = ttk.Notebook(info_window)
            notebook.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Tab for device properties
            props_tab = ttk.Frame(notebook)
            notebook.add(props_tab, text="Properties")
            
            # Tab for system info
            sys_tab = ttk.Frame(notebook)
            notebook.add(sys_tab, text="System Info")
            
            # Tab for hardware info
            hw_tab = ttk.Frame(notebook)
            notebook.add(hw_tab, text="Hardware")
            
            # Get ADB command and serial
            serial = self.device_info.get("serial", "")
            adb_cmd = self.adb_path if IS_WINDOWS else "adb"
            
            # Get detailed device properties
            def get_device_properties():
                try:
                    cmd = [adb_cmd, "-s", serial, "shell", "getprop"]
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = process.communicate(timeout=10)
                    
                    if process.returncode != 0:
                        return f"Error getting device properties: {stderr}"
                        
                    return stdout
                except Exception as e:
                    return f"Error: {str(e)}"
            
            # Display properties in the properties tab
            props_text = tk.Text(props_tab, wrap="word", font=("Consolas", 10))
            props_scroll = ttk.Scrollbar(props_tab, command=props_text.yview)
            props_text.configure(yscrollcommand=props_scroll.set)
            
            props_scroll.pack(side="right", fill="y")
            props_text.pack(side="left", fill="both", expand=True)
            
            # Display system info in system tab
            def get_system_info():
                info = []
                try:
                    # Get Android version
                    cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.build.version.release"]
                    android_ver = subprocess.check_output(cmd, text=True).strip()
                    info.append(f"Android Version: {android_ver}")
                    
                    # Get security patch
                    cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.build.version.security_patch"]
                    security_patch = subprocess.check_output(cmd, text=True).strip()
                    info.append(f"Security Patch: {security_patch}")
                    
                    # Get build number
                    cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.build.display.id"]
                    build_num = subprocess.check_output(cmd, text=True).strip()
                    info.append(f"Build Number: {build_num}")
                    
                    # Get kernel version
                    cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/version"]
                    kernel = subprocess.check_output(cmd, text=True).strip()
                    info.append(f"\nKernel: {kernel}")
                    
                    return "\n".join(info)
                except Exception as e:
                    return f"Error getting system info: {str(e)}"
            
            sys_text = tk.Text(sys_tab, wrap="word", font=("Consolas", 10))
            sys_scroll = ttk.Scrollbar(sys_tab, command=sys_text.yview)
            sys_text.configure(yscrollcommand=sys_scroll.set)
            
            sys_scroll.pack(side="right", fill="y")
            sys_text.pack(side="left", fill="both", expand=True)
            
            # Get hardware info
            def get_hardware_info():
                info = []
                try:
                    # Get CPU info
                    cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/cpuinfo"]
                    cpu_info = subprocess.check_output(cmd, text=True).strip()
                    
                    # Get memory info
                    cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/meminfo"]
                    mem_info = subprocess.check_output(cmd, text=True).strip()
                    
                    # Get storage info
                    cmd = [adb_cmd, "-s", serial, "shell", "df", "-h"]
                    storage_info = subprocess.check_output(cmd, text=True).strip()
                    
                    return f"=== CPU Info ===\n{cpu_info}\n\n=== Memory Info ===\n{mem_info}\n\n=== Storage ===\n{storage_info}"
                except Exception as e:
                    return f"Error getting hardware info: {str(e)}"
            
            hw_text = tk.Text(hw_tab, wrap="word", font=("Consolas", 10))
            hw_scroll = ttk.Scrollbar(hw_tab, command=hw_text.yview)
            hw_text.configure(yscrollcommand=hw_scroll.set)
            
            hw_scroll.pack(side="right", fill="y")
            hw_text.pack(side="left", fill="both", expand=True)
            
            # Add refresh button
            refresh_btn = ttk.Button(info_window, text="Refresh All", 
                                   command=lambda: self._refresh_device_info(props_text, sys_text, hw_text, serial, adb_cmd))
            refresh_btn.pack(side="bottom", pady=5)
            
            # Initial load
            self._refresh_device_info(props_text, sys_text, hw_text, serial, adb_cmd)
            
        except Exception as e:
            logging.error(f"Error showing device info: {e}")
            messagebox.showerror("Error", f"Failed to display device information: {e}")
        
    def _refresh_device_info(self, props_widget, sys_widget, hw_widget, serial, adb_cmd):
        """Refresh all device information in the UI"""
        def get_device_properties():
            try:
                cmd = [adb_cmd, "-s", serial, "shell", "getprop"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=10)
                if process.returncode != 0:
                    return f"Error getting device properties: {stderr}"
                return stdout
            except Exception as e:
                return f"Error: {str(e)}"
        
        def get_system_info():
            info = []
            try:
                # Get Android version
                cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.build.version.release"]
                android_ver = subprocess.check_output(cmd, text=True).strip()
                info.append(f"Android Version: {android_ver}")
                
                # Get security patch
                cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.build.version.security_patch"]
                security_patch = subprocess.check_output(cmd, text=True).strip()
                info.append(f"Security Patch: {security_patch}")
                
                # Get build number
                cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.build.display.id"]
                build_num = subprocess.check_output(cmd, text=True).strip()
                info.append(f"Build Number: {build_num}")
                
                # Get kernel version
                cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/version"]
                kernel = subprocess.check_output(cmd, text=True).strip()
                info.append(f"\nKernel: {kernel}")
                
                return "\n".join(info)
            except Exception as e:
                return f"Error getting system info: {str(e)}"
        
        def get_hardware_info():
            try:
                # Get CPU info
                cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/cpuinfo"]
                cpu_info = subprocess.check_output(cmd, text=True).strip()
                
                # Get memory info
                cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/meminfo"]
                mem_info = subprocess.check_output(cmd, text=True).strip()
                
                # Get storage info
                cmd = [adb_cmd, "-s", serial, "shell", "df", "-h"]
                storage_info = subprocess.check_output(cmd, text=True).strip()
                
                return f"=== CPU Info ===\n{cpu_info}\n\n=== Memory Info ===\n{mem_info}\n\n=== Storage ===\n{storage_info}"
            except Exception as e:
                return f"Error getting hardware info: {str(e)}"
        
        # Update each widget with the latest data
        try:
            # Update properties
            props_widget.delete(1.0, tk.END)
            props_widget.insert(tk.END, get_device_properties())
            
            # Update system info
            sys_widget.delete(1.0, tk.END)
            sys_widget.insert(tk.END, get_system_info())
            
            # Update hardware info
            hw_widget.delete(1.0, tk.END)
            hw_widget.insert(tk.END, get_hardware_info())
            
        except Exception as e:
            logging.error(f"Error refreshing device info: {e}")
    
    def _show_battery_stats(self):
        """Show detailed battery statistics"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Create a new window for battery stats
            battery_window = tk.Toplevel(self)
            battery_window.title(f"Battery Stats - {self.device_info.get('model', 'Android Device')}")
            battery_window.geometry("800x600")
            battery_window.minsize(700, 500)
            battery_window.transient(self)
            battery_window.grab_set()
            
            # Create notebook for different battery info views
            notebook = ttk.Notebook(battery_window)
            notebook.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Tab for current battery status
            status_tab = ttk.Frame(notebook)
            notebook.add(status_tab, text="Status")
            
            # Tab for battery history
            history_tab = ttk.Frame(notebook)
            notebook.add(history_tab, text="History")
            
            # Tab for battery usage stats
            usage_tab = ttk.Frame(notebook)
            notebook.add(usage_tab, text="Usage")
            
            # Get ADB command and serial
            serial = self.device_info.get("serial", "")
            adb_cmd = self.adb_path if IS_WINDOWS else "adb"
            
            # Create text widgets for each tab
            status_text = tk.Text(status_tab, wrap="word", font=("Consolas", 10))
            status_scroll = ttk.Scrollbar(status_tab, command=status_text.yview)
            status_text.configure(yscrollcommand=status_scroll.set)
            status_scroll.pack(side="right", fill="y")
            status_text.pack(side="left", fill="both", expand=True)
            
            history_text = tk.Text(history_tab, wrap="word", font=("Consolas", 10))
            history_scroll = ttk.Scrollbar(history_tab, command=history_text.yview)
            history_text.configure(yscrollcommand=history_scroll.set)
            history_scroll.pack(side="right", fill="y")
            history_text.pack(side="left", fill="both", expand=True)
            
            usage_text = tk.Text(usage_tab, wrap="word", font=("Consolas", 10))
            usage_scroll = ttk.Scrollbar(usage_tab, command=usage_text.yview)
            usage_text.configure(yscrollcommand=usage_scroll.set)
            usage_scroll.pack(side="right", fill="y")
            usage_text.pack(side="left", fill="both", expand=True)
            
            # Add refresh button and auto-refresh option
            control_frame = ttk.Frame(battery_window)
            control_frame.pack(fill="x", padx=10, pady=5)
            
            refresh_btn = ttk.Button(control_frame, text="Refresh", 
                                   command=lambda: self._refresh_battery_stats(
                                       status_text, history_text, usage_text, serial, adb_cmd))
            refresh_btn.pack(side="left", padx=5)
            
            auto_refresh_var = tk.BooleanVar(value=False)
            auto_refresh_check = ttk.Checkbutton(
                control_frame, text="Auto-refresh (10s)", 
                variable=auto_refresh_var
            )
            auto_refresh_check.pack(side="left", padx=5)
            
            # Initial load
            self._refresh_battery_stats(status_text, history_text, usage_text, serial, adb_cmd)
            
            # Auto-refresh function
            def auto_refresh():
                if auto_refresh_var.get() and battery_window.winfo_exists():
                    self._refresh_battery_stats(status_text, history_text, usage_text, serial, adb_cmd)
                    battery_window.after(10000, auto_refresh)
            
            # Setup auto-refresh when checkbox changes
            def on_auto_refresh_change():
                if auto_refresh_var.get():
                    auto_refresh()
            
            auto_refresh_check.config(command=on_auto_refresh_change)
            
        except Exception as e:
            logging.error(f"Error showing battery stats: {e}")
            messagebox.showerror("Error", f"Failed to display battery statistics: {e}")
        
    def _get_package_name_from_uid(self, uid, adb_cmd, serial):
        """Get package name from UID"""
        try:
            # Try to get package name from package manager
            cmd = [adb_cmd, "-s", serial, "shell", "cmd", "package", "list", "packages", "--uid", str(uid)]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=5)
            
            if process.returncode == 0 and stdout.strip():
                # Format: package:com.example.app uid:1000
                lines = [line.strip() for line in stdout.splitlines() if line.strip()]
                if lines:
                    # Get the first package name
                    pkg_line = lines[0].split()
                    if len(pkg_line) > 0 and ':' in pkg_line[0]:
                        return pkg_line[0].split(':', 1)[1]
            
            # If not found, try to get from /data/system/packages.list
            cmd = [adb_cmd, "-s", serial, "shell", "cat", "/data/system/packages.list"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=5)
            
            if process.returncode == 0 and stdout.strip():
                # Format: com.example.app 1000 0 /data/user/0/com.example.app default:targetSdkVersion=30 3003
                for line in stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == str(uid):
                        return parts[0]
            
            return f"UID: {uid}"
            
        except Exception:
            return f"UID: {uid}"
    
    def _format_battery_usage(self, stats_text, adb_cmd, serial):
        """Format battery usage statistics into a more readable format"""
        if not stats_text.strip():
            return "No battery usage data available."
        
        # Parse the stats
        stats = {}
        for line in stats_text.splitlines():
            if not line.strip() or line.startswith('#'):
                continue
                
            parts = line.strip().split(',')
            if len(parts) < 5:
                continue
                
            # Extract UID and other relevant information
            uid = parts[1]
            stat_type = parts[2]
            value = parts[3]
            
            if uid not in stats:
                stats[uid] = {
                    'uid': uid,
                    'wakelocks': 0,
                    'cpu': 0,
                    'wifi': 0,
                    'mobile': 0,
                    'sensors': 0,
                    'camera': 0,
                    'flashlight': 0,
                    'bluetooth': 0,
                    'package_name': None
                }
            
            # Categorize the stat
            if 'wl' in stat_type:
                stats[uid]['wakelocks'] += int(value)
            elif 'cpu' in stat_type:
                stats[uid]['cpu'] += int(value)
            elif 'wifi' in stat_type:
                stats[uid]['wifi'] += int(value)
            elif 'mobile' in stat_type:
                stats[uid]['mobile'] += int(value)
            elif 'sensor' in stat_type:
                stats[uid]['sensors'] += int(value)
            elif 'camera' in stat_type:
                stats[uid]['camera'] += int(value)
            elif 'flashlight' in stat_type:
                stats[uid]['flashlight'] += int(value)
            elif 'bluetooth' in stat_type:
                stats[uid]['bluetooth'] += int(value)
        
        # Convert to list and sort by total usage
        stats_list = []
        for uid, data in stats.items():
            total = sum([v for k, v in data.items() if k not in ['uid', 'package_name']])
            if total > 0:  # Only include apps with some usage
                data['total'] = total
                stats_list.append(data)
        
        # Sort by total usage (descending)
        stats_list.sort(key=lambda x: x['total'], reverse=True)
        
        # Generate report
        report = []
        report.append("Battery Usage by Application")
        report.append("=" * 80)
        
        # Format header with consistent spacing
        header = (
            f"{'Package':<40} "
            f"{'Total':>10} "
            f"{'CPU':>10} "
            f"{'Wakelocks':>12} "
            f"{'WiFi':>10} "
            f"{'Mobile':>10} "
            f"{'Sensors':>10}"
        )
        report.append(header)
        report.append("-" * 105)  # Adjust the line to match header width
        
        # Add each stat line
        for stat in stats_list:
            # Get package name if not already cached
            if not stat['package_name']:
                stat['package_name'] = self._get_package_name_from_uid(stat['uid'], adb_cmd, serial)
            
            # Truncate package name if too long
            pkg_name = stat['package_name']
            if len(pkg_name) > 38:
                pkg_name = pkg_name[:35] + "..."
                
            # Format the line with consistent spacing
            line = (
                f"{pkg_name:<40} "
                f"{stat['total']:>10} "
                f"{stat['cpu']:>10} "
                f"{stat['wakelocks']:>12} "
                f"{stat['wifi']:>10} "
                f"{stat['mobile']:>10} "
                f"{stat['sensors']:>10}"
            )
            report.append(line)
        
        # Add summary if we have data
        if stats_list:
            report.append("-" * 105)
            total_line = (
                f"{'TOTAL:':<40} "
                f"{sum(s['total'] for s in stats_list):>10} "
                f"{sum(s['cpu'] for s in stats_list):>10} "
                f"{sum(s['wakelocks'] for s in stats_list):>12} "
                f"{sum(s['wifi'] for s in stats_list):>10} "
                f"{sum(s['mobile'] for s in stats_list):>10} "
                f"{sum(s['sensors'] for s in stats_list):>10}"
            )
            report.append(total_line)
        
        return "\n".join(report)
    
    def _highlight_battery_text(self, widget, text):
        """Apply syntax highlighting to battery stats text"""
        widget.configure(state='normal', font=('Consolas', 10, 'normal'))
        widget.delete('1.0', tk.END)
        
        # Define tag configurations
        widget.tag_configure('header', foreground='#2e7d32', font=('Segoe UI', 11, 'bold'))
        widget.tag_configure('subheader', foreground='#1976d2', font=('Segoe UI', 10, 'bold'))
        widget.tag_configure('warning', foreground='#d32f2f', font=('Segoe UI', 9, 'bold'))
        widget.tag_configure('good', foreground='#388e3c', font=('Consolas', 10, 'normal'))
        widget.tag_configure('normal', foreground='#1976d2', font=('Consolas', 10, 'normal'))
        widget.tag_configure('critical', foreground='#d32f2f', font=('Consolas', 10, 'bold'))
        widget.tag_configure('value', foreground='#1976d2', font=('Consolas', 10, 'normal'))
        widget.tag_configure('separator', foreground='#757575')
        widget.tag_configure('total', foreground='#000000', font=('Consolas', 10, 'bold'))
        
        # Process each line
        in_battery_usage = False
        
        for line in text.split('\n'):
            if not line.strip():
                widget.insert(tk.END, '\n')
                continue
                
            if 'Battery Usage by Application' in line:
                in_battery_usage = True
                widget.insert(tk.END, line + '\n', 'header')
            elif '===' in line and not in_battery_usage:
                # Main header line
                widget.insert(tk.END, line + '\n', 'header')
            elif '---' in line and not in_battery_usage:
                # Subheader line
                widget.insert(tk.END, line + '\n', 'subheader')
            elif any(x in line.lower() for x in ['error', 'failed', 'not found']):
                # Error/warning line
                widget.insert(tk.END, line + '\n', 'warning')
            elif in_battery_usage and 'TOTAL:' in line:
                # Total line in battery usage
                parts = line.split()
                if len(parts) >= 7:  # Make sure we have all columns
                    widget.insert(tk.END, f"{parts[0]:<40} ", 'total')
                    widget.insert(tk.END, f"{parts[1]:>10} ", 'total')
                    widget.insert(tk.END, f"{parts[2]:>10} ", 'total')
                    widget.insert(tk.END, f"{parts[3]:>12} ", 'total')
                    widget.insert(tk.END, f"{parts[4]:>10} ", 'total')
                    widget.insert(tk.END, f"{parts[5]:>10} ", 'total')
                    widget.insert(tk.END, f"{parts[6]:>10}\n", 'total')
            elif in_battery_usage and 'Package' not in line and '----' not in line:
                # Battery usage data line
                parts = line.split()
                if len(parts) >= 7:  # Make sure we have all columns
                    # Package name (left-aligned, truncated if needed)
                    pkg_name = ' '.join(parts[:-6])
                    if len(pkg_name) > 38:
                        pkg_name = pkg_name[:35] + '...'
                    widget.insert(tk.END, f"{pkg_name:<40} ", 'normal')
                    
                    # Numeric values (right-aligned)
                    for i, val in enumerate(parts[-6:], 1):
                        try:
                            num = int(val)
                            if num > 1000:
                                tag = 'critical'
                            elif num > 100:
                                tag = 'warning'
                            else:
                                tag = 'value'
                        except (ValueError, IndexError):
                            tag = 'value'
                            
                        # Special formatting for each column
                        if i == 1:  # Total
                            width = 10
                        elif i == 2:  # CPU
                            width = 10
                        elif i == 3:  # Wakelocks
                            width = 12
                        else:  # WiFi, Mobile, Sensors
                            width = 10
                            
                        widget.insert(tk.END, f"{val:>{width}} ", tag)
                    
                    widget.insert(tk.END, '\n')
            elif any(x in line.lower() for x in ['temperature', 'level', 'health']):
                # Important metrics
                if ':' in line:
                    key, value = line.split(':', 1)
                    widget.insert(tk.END, key + ':', 'normal')
                    
                    # Color code values based on their content
                    if 'temperature' in line.lower():
                        try:
                            temp = float(value.strip().split()[0])
                            if temp > 40:
                                widget.insert(tk.END, f' {value.strip()}\n', 'critical')
                            else:
                                widget.insert(tk.END, f' {value.strip()}\n', 'good')
                            continue
                        except (ValueError, IndexError):
                            pass
                    elif 'level' in line.lower() and '%' in value:
                        try:
                            level = float(value.split('%')[0].strip())
                            if level < 20:
                                widget.insert(tk.END, f' {value.strip()}\n', 'critical')
                            elif level < 50:
                                widget.insert(tk.END, f' {value.strip()}\n', 'warning')
                            else:
                                widget.insert(tk.END, f' {value.strip()}\n', 'good')
                            continue
                        except (ValueError, IndexError):
                            pass
                    
                    widget.insert(tk.END, f' {value.strip()}\n', 'value')
                else:
                    widget.insert(tk.END, line + '\n')
            elif line.strip() and ('---' in line or '===' in line):
                # Separator line
                widget.insert(tk.END, line + '\n', 'separator')
            else:
                # Regular line
                widget.insert(tk.END, line + '\n', 'normal')
        
        widget.configure(state='disabled')
    
    def _refresh_battery_stats(self, status_widget, history_widget, usage_widget, serial, adb_cmd):
        """Refresh battery statistics in the UI"""
        def get_battery_status():
            try:
                # Get battery status using dumpsys
                cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "battery"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=10)
                
                if process.returncode != 0:
                    return f"Error getting battery status: {stderr}"
                
                # Parse and format the battery info
                battery_info = []
                battery_info.append("=== Battery Status ===\n")
                
                # Common battery properties to display
                properties = [
                    'AC powered', 'USB powered', 'Wireless powered', 'Max charging current',
                    'Max charging voltage', 'Charge counter', 'status', 'health', 'present',
                    'level', 'scale', 'voltage', 'temperature', 'technology'
                ]
                
                for line in stdout.splitlines():
                    line = line.strip()
                    if any(prop in line.lower() for prop in [p.lower() for p in properties]):
                        # Format the line for better readability
                        if 'temperature' in line.lower() and '=' in line:
                            # Convert temperature from 10ths of a degree C to C
                            try:
                                temp = int(line.split('=')[1].strip()) / 10.0
                                battery_info.append(f"Temperature: {temp}°C")
                                continue
                            except (ValueError, IndexError):
                                pass
                        elif 'level' in line.lower() and 'scale' in line.lower() and '=' in line:
                            # Calculate battery percentage
                            try:
                                level = int(line.split('=')[1].split()[0].strip())
                                scale = int(line.split('scale=')[1].split()[0].strip())
                                if scale > 0:
                                    percent = (level / scale) * 100
                                    battery_info.append(f"Battery Level: {percent:.1f}% ({level}/{scale})")
                                    continue
                            except (ValueError, IndexError):
                                pass
                        
                        # Default formatting
                        battery_info.append(line)
                
                return "\n".join(battery_info)
                
            except Exception as e:
                return f"Error getting battery status: {str(e)}"
        
        def get_battery_history():
            try:
                # Get battery history
                cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "batteryhistory"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=15)  # May take longer
                
                if process.returncode != 0:
                    return f"Error getting battery history: {stderr}"
                
                # Extract the most relevant parts of the history
                history = []
                capture = False
                
                for line in stdout.splitlines():
                    line = line.strip()
                    
                    # Look for the history section
                    if 'Battery History ' in line:
                        capture = True
                        history.append("=== Battery History ===\n")
                        continue
                        
                    if capture:
                        if line.startswith('  Estimated power use'):
                            history.append("\n" + line)
                            break
                        if line:
                            history.append(line)
                
                return "\n".join(history) if history else "No battery history available."
                
            except Exception as e:
                return f"Error getting battery history: {str(e)}"
        
        def get_battery_stats():
            try:
                # Get battery stats
                cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "batterystats", "--checkin"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=15)  # May take longer
                
                if process.returncode != 0:
                    return f"Error getting battery stats: {stderr}"
                
                # Process and format the stats
                return self._format_battery_usage(stdout, adb_cmd, serial)
                
            except Exception as e:
                return f"Error getting battery stats: {str(e)}"
        
        # Update each widget with the latest data
        try:
            # Get all the data first
            status_text = get_battery_status()
            history_text = get_battery_history()
            usage_text = get_battery_stats()
            
            # Update status tab with highlighting
            self._highlight_battery_text(status_widget, status_text)
            
            # Update history tab with highlighting
            self._highlight_battery_text(history_widget, history_text)
            
            # Update usage stats tab with highlighting
            self._highlight_battery_text(usage_widget, usage_text)
            
        except Exception as e:
            error_msg = f"Error refreshing battery stats: {e}"
            logging.error(error_msg)
            self._highlight_battery_text(status_widget, error_msg)
            self._highlight_battery_text(history_widget, error_msg)
            self._highlight_battery_text(usage_widget, error_msg)
    
    def _show_running_services(self):
        """Show list of running services"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            # Create a new window for services
            services_window = tk.Toplevel(self)
            services_window.title(f"Running Services - {self.device_info.get('model', 'Android Device')}")
            services_window.geometry("900x600")
            services_window.minsize(800, 500)
            services_window.transient(self)
            services_window.grab_set()
            
            # Create main frame
            main_frame = ttk.Frame(services_window)
            main_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Create filter frame
            filter_frame = ttk.Frame(main_frame)
            filter_frame.pack(fill="x", pady=(0, 5))
            
            ttk.Label(filter_frame, text="Filter:").pack(side="left", padx=(0, 5))
            
            filter_var = tk.StringVar()
            filter_entry = ttk.Entry(filter_frame, textvariable=filter_var, width=40)
            filter_entry.pack(side="left", fill="x", expand=True)
            
            # Create treeview with scrollbars
            tree_frame = ttk.Frame(main_frame)
            tree_frame.pack(fill="both", expand=True)
            
            # Horizontal scrollbar
            h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal")
            h_scroll.pack(side="bottom", fill="x")
            
            # Vertical scrollbar
            v_scroll = ttk.Scrollbar(tree_frame)
            v_scroll.pack(side="right", fill="y")
            
            # Create the treeview
            columns = ("service", "package", "pid", "uid", "foreground", "started")
            tree = FixedHeaderTreeview(
                tree_frame, 
                columns=columns, 
                show="headings",
                yscrollcommand=v_scroll.set,
                xscrollcommand=h_scroll.set
            )
            
            # Configure scrollbars
            v_scroll.config(command=tree.yview)
            h_scroll.config(command=tree.xview)
            
            # Define column headings
            tree.heading("service", text="Service", anchor="w")
            tree.heading("package", text="Package", anchor="w")
            tree.heading("pid", text="PID", anchor="center")
            tree.heading("uid", text="UID", anchor="center")
            tree.heading("foreground", text="Foreground", anchor="center")
            tree.heading("started", text="Started", anchor="center")
            
            # Configure column widths
            tree.column("service", width=300, minwidth=200, stretch=tk.YES)
            tree.column("package", width=200, minwidth=150, stretch=tk.YES)
            tree.column("pid", width=80, minwidth=60, stretch=tk.NO, anchor="center")
            tree.column("uid", width=80, minwidth=60, stretch=tk.NO, anchor="center")
            tree.column("foreground", width=100, minwidth=80, stretch=tk.NO, anchor="center")
            tree.column("started", width=100, minwidth=80, stretch=tk.NO, anchor="center")
            
            tree.pack(side="left", fill="both", expand=True)
            
            # Add context menu
            context_menu = tk.Menu(services_window, tearoff=0)
            context_menu.add_command(label="Copy Service Name", 
                                   command=lambda: self._copy_to_clipboard(tree, "service"))
            context_menu.add_command(label="Copy Package Name", 
                                   command=lambda: self._copy_to_clipboard(tree, "package"))
            context_menu.add_separator()
            context_menu.add_command(label="Force Stop", 
                                   command=lambda: self._force_stop_service(tree, "package"))
            
            def show_context_menu(event):
                item = tree.identify_row(event.y)
                if item:
                    tree.selection_set(item)
                    context_menu.post(event.x_root, event.y_root)
            
            tree.bind("<Button-3>", show_context_menu)
            
            # Add control frame
            control_frame = ttk.Frame(main_frame)
            control_frame.pack(fill="x", pady=(5, 0))
            
            # Add refresh button
            refresh_btn = ttk.Button(
                control_frame, 
                text="Refresh",
                command=lambda: self._refresh_running_services(tree, filter_var.get())
            )
            refresh_btn.pack(side="left", padx=(0, 10))
            
            # Add auto-refresh option
            auto_refresh_var = tk.BooleanVar(value=False)
            auto_refresh_btn = ttk.Checkbutton(
                control_frame,
                text="Auto-refresh (5s)",
                variable=auto_refresh_var
            )
            auto_refresh_btn.pack(side="left")
            
            # Bind filter entry
            filter_var.trace("w", lambda *args: self._filter_services(tree, filter_var.get()))
            
            # Initial load
            self._refresh_running_services(tree, "")
            
            # Auto-refresh function
            def auto_refresh():
                if auto_refresh_var.get() and services_window.winfo_exists():
                    self._refresh_running_services(tree, filter_var.get())
                    services_window.after(5000, auto_refresh)
            
            # Setup auto-refresh when checkbox changes
            def on_auto_refresh_change():
                if auto_refresh_var.get():
                    auto_refresh()
            
            auto_refresh_btn.config(command=on_auto_refresh_change)
            
            # Set focus to filter entry
            filter_entry.focus_set()
            
        except Exception as e:
            logging.error(f"Error showing running services: {e}")
            messagebox.showerror("Error", f"Failed to display running services: {e}")
        
    def _refresh_running_services(self, tree_widget, filter_text=""):
        """Refresh the list of running services"""
        if not hasattr(self, 'device_info') or not self.device_connected:
            return
            
        try:
            # Clear existing items
            for item in tree_widget.get_children():
                tree_widget.delete(item)
            
            # Get ADB command and serial
            serial = self.device_info.get("serial", "")
            adb_cmd = self.adb_path if IS_WINDOWS else "adb"
            
            # Get running services using dumpsys
            cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "activity", "services"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=15)
            
            if process.returncode != 0:
                messagebox.showerror("Error", f"Failed to get running services: {stderr}")
                return
            
            # Parse the output to extract service information
            services = []
            current_service = {}
            
            for line in stdout.splitlines():
                line = line.strip()
                
                # Look for service entries
                if "ServiceRecord" in line and "pid=" in line:
                    # Save previous service if exists
                    if current_service:
                        services.append(current_service)
                    
                    # Start new service
                    current_service = {
                        "service": "",
                        "package": "",
                        "pid": "",
                        "uid": "",
                        "foreground": "No",
                        "started": "No"
                    }
                    
                    # Extract PID
                    pid_match = re.search(r'pid=([0-9]+)', line)
                    if pid_match:
                        current_service["pid"] = pid_match.group(1)
                
                # Extract service name and package
                elif "intent=" in line:
                    # Example: intent={cmp=com.example.app/.MyService}
                    intent_match = re.search(r'intent=\{(.*?)\}', line)
                    if intent_match:
                        intent_parts = intent_match.group(1).split()
                        for part in intent_parts:
                            if part.startswith("cmp="):
                                service_name = part[4:].strip('}')
                                current_service["service"] = service_name
                                # Extract package name (everything before the last '/')
                                if '/' in service_name:
                                    current_service["package"] = service_name.split('/')[0]
                
                # Extract UID
                elif "uid=" in line and "pid=" not in line:  # Avoid matching the pid= from earlier
                    uid_match = re.search(r'uid=([0-9]+)', line)
                    if uid_match:
                        current_service["uid"] = uid_match.group(1)
                
                # Check if service is in foreground
                elif "foreground" in line and "true" in line.lower():
                    current_service["foreground"] = "Yes"
                
                # Check if service is started
                elif "started" in line and "true" in line.lower():
                    current_service["started"] = "Yes"
            
            # Add the last service if exists
            if current_service:
                services.append(current_service)
            
            # Filter and add services to the treeview
            for service in services:
                if not filter_text or filter_text.lower() in service["service"].lower() or \
                   filter_text.lower() in service["package"].lower():
                    tree_widget.insert("", "end", values=(
                        service["service"],
                        service["package"],
                        service["pid"],
                        service["uid"],
                        service["foreground"],
                        service["started"]
                    ))
            
            # Sort by service name by default
            tree_widget.heading("service", command=lambda: self._sort_treeview(tree_widget, "service", False))
            
        except subprocess.TimeoutExpired:
            messagebox.showerror("Timeout", "Timed out while getting running services.")
        except Exception as e:
            logging.error(f"Error refreshing running services: {e}")
            messagebox.showerror("Error", f"Failed to refresh running services: {e}")
    
    def _filter_services(self, tree_widget, filter_text):
        """Filter services based on the filter text"""
        # Get all items
        for item in tree_widget.get_children():
            values = tree_widget.item(item, 'values')
            if (not filter_text or 
                filter_text.lower() in values[0].lower() or  # service name
                filter_text.lower() in values[1].lower()):   # package name
                tree_widget.item(item, tags=('unfiltered',))
                tree_widget.detach(item)
                tree_widget.reattach(item, '', 'end')
            else:
                tree_widget.detach(item)
    
    def _copy_to_clipboard(self, tree_widget, column):
        """Copy the selected item's column value to clipboard"""
        selected = tree_widget.selection()
        if not selected:
            return
            
        item = selected[0]
        values = tree_widget.item(item, 'values')
        
        # Get the column index
        columns = tree_widget['columns']
        try:
            col_index = columns.index(column)
            value = values[col_index]
            self.clipboard_clear()
            self.clipboard_append(value)
        except (ValueError, IndexError):
            pass  # Column not found or no value
    
    def _force_stop_service(self, tree_widget, column):
        """Force stop the selected service"""
        selected = tree_widget.selection()
        if not selected:
            return
            
        item = selected[0]
        values = tree_widget.item(item, 'values')
        
        # Get the package name
        columns = tree_widget['columns']
        try:
            col_index = columns.index(column)
            package_name = values[col_index]
            
            if not package_name:
                messagebox.showerror("Error", "No package name found for the selected service.")
                return
                
            # Confirm before force stopping
            if messagebox.askyesno(
                "Confirm Force Stop",
                f"Are you sure you want to force stop {package_name}?\n\n"
                "This may cause the app to misbehave or crash."
            ):
                # Get ADB command and serial
                serial = self.device_info.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Force stop the package
                cmd = [adb_cmd, "-s", serial, "shell", "am", "force-stop", package_name]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                _, stderr = process.communicate(timeout=10)
                
                if process.returncode == 0:
                    messagebox.showinfo("Success", f"Successfully force stopped {package_name}")
                    # Refresh the services list
                    self._refresh_running_services(tree_widget, "")
                else:
                    messagebox.showerror("Error", f"Failed to force stop {package_name}: {stderr}")
                    
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Could not determine the package name for the selected service.")
    
    def _show_memory_usage(self):
        """Show memory usage statistics"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
        
        # Get the serial number and adb command
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create a new window for memory usage display
            mem_window = tk.Toplevel(self)
            mem_window.title("Memory Usage - " + self.device_info.get("model", "Android Device"))
            mem_window.geometry("700x500")
            mem_window.minsize(600, 400)
            mem_window.transient(self)
            mem_window.grab_set()
            
            # Add refresh button and auto-refresh option
            control_frame = ttk.Frame(mem_window)
            control_frame.pack(fill="x", padx=10, pady=5)
            
            refresh_btn = ttk.Button(control_frame, text="Refresh", 
                                     command=lambda: self._refresh_memory_stats(mem_text, serial, adb_cmd))
            refresh_btn.pack(side="left", padx=5)
            
            auto_refresh_var = tk.BooleanVar(value=False)
            auto_refresh_check = ttk.Checkbutton(control_frame, text="Auto-refresh (5s)", 
                                                variable=auto_refresh_var)
            auto_refresh_check.pack(side="left", padx=5)
            
            # Create text widget with scrollbar for memory stats
            frame = ttk.Frame(mem_window)
            frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side="right", fill="y")
            
            mem_text = tk.Text(frame, wrap="word", font=("Consolas", 10), 
                              yscrollcommand=scrollbar.set)
            mem_text.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=mem_text.yview)
            
            # Initial load of memory stats
            self._refresh_memory_stats(mem_text, serial, adb_cmd)
            
            # Auto-refresh function
            def auto_refresh():
                if auto_refresh_var.get() and mem_window.winfo_exists():
                    self._refresh_memory_stats(mem_text, serial, adb_cmd)
                    mem_window.after(5000, auto_refresh)
            
            # Start auto-refresh loop if enabled
            auto_refresh_check.config(command=auto_refresh)
            
        except Exception as e:
            logging.error(f"Error showing memory usage: {e}")
            messagebox.showerror("Error", f"Failed to display memory usage: {e}")
    
    def _refresh_memory_stats(self, text_widget, serial, adb_cmd):
        """Refresh memory statistics in the text widget"""
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, "Loading memory statistics...\n\n")
        text_widget.update()
        
        try:
            # Get memory info using dumpsys meminfo
            cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "meminfo"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate(timeout=10)
            
            if process.returncode != 0:
                text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, f"Error retrieving memory information:\n{error}")
                return
            
            # Get procrank output for more detailed per-process memory info
            cmd_procrank = [adb_cmd, "-s", serial, "shell", "su -c procrank"]
            try:
                proc_process = subprocess.Popen(cmd_procrank, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                proc_output, proc_error = proc_process.communicate(timeout=5)
                
                if proc_process.returncode == 0 and proc_output:
                    # Device has root access, show procrank output too
                    output += "\n\n--- DETAILED PER-PROCESS MEMORY USAGE (ROOT) ---\n\n" + proc_output
            except:
                # procrank failed or timed out, continue without it
                pass
            
            # Display the output
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, output)
            
            # Highlight important memory values
            self._highlight_memory_text(text_widget)
            
        except subprocess.TimeoutExpired:
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "Command timed out. Device may be unresponsive.")
        except Exception as e:
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, f"Error: {str(e)}")
            logging.error(f"Error refreshing memory stats: {e}")
    
    def _highlight_memory_text(self, text_widget):
        """Highlight important memory values in the text widget"""
        # Configure tags
        text_widget.tag_configure("header", font=("Consolas", 10, "bold"))
        text_widget.tag_configure("warning", background="#ffe0e0")
        text_widget.tag_configure("good", background="#e0ffe0")
        
        # Find and highlight headers
        for pattern in ["Total RAM:", "Free RAM:", "Used RAM:", "Lost RAM:", "MEMORY USAGE BY PROCESS:"]:
            start_idx = "1.0"
            while True:
                start_idx = text_widget.search(pattern, start_idx, tk.END)
                if not start_idx:
                    break
                end_idx = f"{start_idx}+{len(pattern)}c"
                text_widget.tag_add("header", start_idx, end_idx)
                start_idx = end_idx
        
    def _show_cpu_usage(self):
        """Show CPU usage statistics"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
        
        # Get the serial number and adb command
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create a new window for CPU usage display
            cpu_window = tk.Toplevel(self)
            cpu_window.title("CPU Usage - " + self.device_info.get("model", "Android Device"))
            cpu_window.geometry("700x500")
            cpu_window.minsize(600, 400)
            cpu_window.transient(self)
            cpu_window.grab_set()
            
            # Add refresh button and auto-refresh option
            control_frame = ttk.Frame(cpu_window)
            control_frame.pack(fill="x", padx=10, pady=5)
            
            refresh_btn = ttk.Button(control_frame, text="Refresh", 
                                     command=lambda: self._refresh_cpu_stats(cpu_text, serial, adb_cmd))
            refresh_btn.pack(side="left", padx=5)
            
            auto_refresh_var = tk.BooleanVar(value=False)
            auto_refresh_check = ttk.Checkbutton(control_frame, text="Auto-refresh (3s)", 
                                                variable=auto_refresh_var)
            auto_refresh_check.pack(side="left", padx=5)
            
            # Add sort option
            sort_frame = ttk.Frame(control_frame)
            sort_frame.pack(side="left", padx=20)
            
            ttk.Label(sort_frame, text="Sort by:").pack(side="left")
            
            sort_var = tk.StringVar(value="cpu")
            sort_cpu = ttk.Radiobutton(sort_frame, text="CPU %", variable=sort_var, value="cpu")
            sort_cpu.pack(side="left", padx=5)
            
            sort_pid = ttk.Radiobutton(sort_frame, text="PID", variable=sort_var, value="pid")
            sort_pid.pack(side="left", padx=5)
            
            sort_name = ttk.Radiobutton(sort_frame, text="Name", variable=sort_var, value="name")
            sort_name.pack(side="left", padx=5)
            
            # Create text widget with scrollbar for CPU stats
            frame = ttk.Frame(cpu_window)
            frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side="right", fill="y")
            
            cpu_text = tk.Text(frame, wrap="word", font=("Consolas", 10), 
                              yscrollcommand=scrollbar.set)
            cpu_text.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=cpu_text.yview)
            
            # Initial load of CPU stats
            self._refresh_cpu_stats(cpu_text, serial, adb_cmd, sort_var.get())
            
            # Update when sort option changes
            def on_sort_change(*args):
                self._refresh_cpu_stats(cpu_text, serial, adb_cmd, sort_var.get())
            
            sort_var.trace("w", on_sort_change)
            
            # Auto-refresh function
            def auto_refresh():
                if auto_refresh_var.get() and cpu_window.winfo_exists():
                    self._refresh_cpu_stats(cpu_text, serial, adb_cmd, sort_var.get())
                    cpu_window.after(3000, auto_refresh)
            
            # Setup auto-refresh when checkbox changes
            def on_auto_refresh_change():
                if auto_refresh_var.get():
                    auto_refresh()
            
            auto_refresh_check.config(command=on_auto_refresh_change)
            
        except Exception as e:
            logging.error(f"Error showing CPU usage: {e}")
            messagebox.showerror("Error", f"Failed to display CPU usage: {e}")
    
    def _refresh_cpu_stats(self, text_widget, serial, adb_cmd, sort_by="cpu"):
        """Refresh CPU statistics in the text widget"""
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, "Loading CPU statistics...\n\n")
        text_widget.update()
        
        try:
            # Get CPU info using top command
            cmd = [adb_cmd, "-s", serial, "shell", "top", "-n", "1", "-b"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate(timeout=10)
            
            if process.returncode != 0:
                text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, f"Error retrieving CPU information:\n{error}")
                return
            
            # Get CPU cores and frequency info
            cmd_cpu_info = [adb_cmd, "-s", serial, "shell", "cat", "/proc/cpuinfo"]
            try:
                cpu_process = subprocess.Popen(cmd_cpu_info, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                cpu_output, cpu_error = cpu_process.communicate(timeout=5)
                
                if cpu_process.returncode == 0 and cpu_output:
                    # Extract processor count and details
                    processor_count = cpu_output.count("processor")
                    model_name = "Unknown"
                    for line in cpu_output.splitlines():
                        if "model name" in line or "Processor" in line:
                            model_name = line.split(":", 1)[1].strip()
                            break
                    
                    cpu_summary = f"CPU Model: {model_name}\nCores: {processor_count}\n\n"
                else:
                    cpu_summary = ""  
            except:
                cpu_summary = ""
            
            # Parse the top output
            lines = output.splitlines()
            header = ""
            processes = []
            
            for i, line in enumerate(lines):
                if "PID" in line and "CPU%" in line:
                    header = line
                    # Process subsequent lines that contain process info
                    for proc_line in lines[i+1:]:
                        if proc_line.strip() and not proc_line.startswith("Tasks:"):
                            processes.append(proc_line)
                    break
            
            # Sort processes based on user selection
            sorted_processes = []
            if processes:
                if sort_by == "cpu":
                    # Sort by CPU usage (usually 9th column)
                    for proc in processes:
                        parts = proc.split()
                        if len(parts) >= 10:
                            try:
                                cpu_val = float(parts[8].replace('%', ''))
                                sorted_processes.append((cpu_val, proc))
                            except (ValueError, IndexError):
                                sorted_processes.append((0, proc))
                    sorted_processes.sort(reverse=True, key=lambda x: x[0])
                    sorted_processes = [p[1] for p in sorted_processes]
                elif sort_by == "pid":
                    # Sort by PID (usually 1st column)
                    for proc in processes:
                        parts = proc.split()
                        if parts:
                            try:
                                pid_val = int(parts[0])
                                sorted_processes.append((pid_val, proc))
                            except (ValueError, IndexError):
                                sorted_processes.append((0, proc))
                    sorted_processes.sort(key=lambda x: x[0])
                    sorted_processes = [p[1] for p in sorted_processes]
                elif sort_by == "name":
                    # Sort by process name (usually last column)
                    for proc in processes:
                        parts = proc.split()
                        if len(parts) >= 10:
                            name = parts[-1]
                            sorted_processes.append((name, proc))
                        else:
                            sorted_processes.append(("", proc))
                    sorted_processes.sort(key=lambda x: x[0])
                    sorted_processes = [p[1] for p in sorted_processes]
                else:
                    sorted_processes = processes
            
            # Display the output with our formatting
            text_widget.delete(1.0, tk.END)
            
            # Add overall CPU summary from /proc/cpuinfo
            if cpu_summary:
                text_widget.insert(tk.END, cpu_summary)
            
            # Add header and processes
            if header:
                text_widget.insert(tk.END, f"{header}\n")
                for i, proc in enumerate(sorted_processes):
                    if i < 100:  # Limit to 100 processes to avoid performance issues
                        text_widget.insert(tk.END, f"{proc}\n")
                    else:
                        text_widget.insert(tk.END, "\n... (more processes not shown)")
                        break
            else:
                text_widget.insert(tk.END, output)
            
            # Highlight important parts
            self._highlight_cpu_text(text_widget, header)
            
        except subprocess.TimeoutExpired:
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "Command timed out. Device may be unresponsive.")
        except Exception as e:
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, f"Error: {str(e)}")
            logging.error(f"Error refreshing CPU stats: {e}")
    
    def _highlight_cpu_text(self, text_widget, header):
        """Highlight important CPU values in the text widget"""
        # Configure tags
        text_widget.tag_configure("header", font=("Consolas", 10, "bold"))
        text_widget.tag_configure("high_cpu", background="#ffe0e0")
        text_widget.tag_configure("medium_cpu", background="#ffffd0")
        text_widget.tag_configure("system_proc", foreground="#0000ff")
        
        # Highlight header
        if header:
            text_widget.tag_add("header", "1.0", "1.end")
            
            # Determine column positions for highlighting
            cpu_col_idx = header.find("CPU%")
            
            # Highlight high CPU usage processes
            if cpu_col_idx > 0:
                for i in range(2, 102):  # Check up to 100 processes (limit we set earlier)
                    try:
                        line_start = f"{i}.0"
                        line_end = f"{i}.end"
                        line_text = text_widget.get(line_start, line_end)
                        
                        # Try to extract CPU percentage
                        parts = line_text.split()
                        if len(parts) >= 9:
                            try:
                                cpu_pct = float(parts[8].replace('%', ''))
                                
                                # Highlight based on CPU usage
                                if cpu_pct > 20.0:
                                    text_widget.tag_add("high_cpu", line_start, line_end)
                                elif cpu_pct > 10.0:
                                    text_widget.tag_add("medium_cpu", line_start, line_end)
                                    
                                # Highlight system processes
                                if any(proc in line_text for proc in 
                                       ["system", "systemui", "zygote", "surfaceflinger"]):
                                    text_widget.tag_add("system_proc", line_start, line_end)
                            except (ValueError, IndexError):
                                pass
                    except tk.TclError:
                        # Line doesn't exist, we've reached the end
                        break
        
    def _show_network_stats(self):
        """Show network usage statistics"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
        
        # Get the serial number and adb command
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create a new window for network stats display
            net_window = tk.Toplevel(self)
            net_window.title("Network Statistics - " + self.device_info.get("model", "Android Device"))
            net_window.geometry("700x500")
            net_window.minsize(600, 400)
            net_window.transient(self)
            net_window.grab_set()
            
            # Add tabs for different network information
            notebook = ttk.Notebook(net_window)
            notebook.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Tab for network interfaces
            ifaces_tab = ttk.Frame(notebook)
            notebook.add(ifaces_tab, text="Interfaces")
            
            # Tab for connections
            conn_tab = ttk.Frame(notebook)
            notebook.add(conn_tab, text="Connections")
            
            # Tab for data usage
            usage_tab = ttk.Frame(notebook)
            notebook.add(usage_tab, text="Data Usage")
            
            # Setup interface tab
            ifaces_frame = ttk.Frame(ifaces_tab)
            ifaces_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            ifaces_scroll = ttk.Scrollbar(ifaces_frame)
            ifaces_scroll.pack(side="right", fill="y")
            
            ifaces_text = tk.Text(ifaces_frame, wrap="word", font=("Consolas", 10),
                               yscrollcommand=ifaces_scroll.set)
            ifaces_text.pack(side="left", fill="both", expand=True)
            ifaces_scroll.config(command=ifaces_text.yview)
            
            # Setup connections tab
            conn_frame = ttk.Frame(conn_tab)
            conn_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            conn_scroll = ttk.Scrollbar(conn_frame)
            conn_scroll.pack(side="right", fill="y")
            
            conn_text = tk.Text(conn_frame, wrap="word", font=("Consolas", 10),
                               yscrollcommand=conn_scroll.set)
            conn_text.pack(side="left", fill="both", expand=True)
            conn_scroll.config(command=conn_text.yview)
            
            # Setup data usage tab
            usage_frame = ttk.Frame(usage_tab)
            usage_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            usage_scroll = ttk.Scrollbar(usage_frame)
            usage_scroll.pack(side="right", fill="y")
            
            usage_text = tk.Text(usage_frame, wrap="word", font=("Consolas", 10),
                               yscrollcommand=usage_scroll.set)
            usage_text.pack(side="left", fill="both", expand=True)
            usage_scroll.config(command=usage_text.yview)
            
            # Add refresh button
            control_frame = ttk.Frame(net_window)
            control_frame.pack(fill="x", padx=10, pady=5)
            
            refresh_btn = ttk.Button(
                control_frame, text="Refresh", 
                command=lambda: self._refresh_network_stats(
                    ifaces_text, conn_text, usage_text, serial, adb_cmd
                )
            )
            refresh_btn.pack(side="left", padx=5)
            
            # Add auto-refresh option
            auto_refresh_var = tk.BooleanVar(value=False)
            auto_refresh_check = ttk.Checkbutton(
                control_frame, text="Auto-refresh (10s)", 
                variable=auto_refresh_var
            )
            auto_refresh_check.pack(side="left", padx=5)
            
            # Initial load of stats
            self._refresh_network_stats(ifaces_text, conn_text, usage_text, serial, adb_cmd)
            
            # Auto-refresh function
            def auto_refresh():
                if auto_refresh_var.get() and net_window.winfo_exists():
                    self._refresh_network_stats(ifaces_text, conn_text, usage_text, serial, adb_cmd)
                    net_window.after(10000, auto_refresh)
            
            # Setup auto-refresh when checkbox changes
            def on_auto_refresh_change():
                if auto_refresh_var.get():
                    auto_refresh()
            
            auto_refresh_check.config(command=on_auto_refresh_change)
            
        except Exception as e:
            logging.error(f"Error showing network stats: {e}")
            messagebox.showerror("Error", f"Failed to display network statistics: {e}")
    
    def _refresh_network_stats(self, ifaces_text, conn_text, usage_text, serial, adb_cmd):
        """Refresh network statistics"""
        # Clear all text widgets and show loading message
        for text_widget in [ifaces_text, conn_text, usage_text]:
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "Loading data...")
            text_widget.update()
        
        # Get network interface info
        try:
            cmd = [adb_cmd, "-s", serial, "shell", "ip", "addr"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate(timeout=10)
            
            if process.returncode == 0:
                ifaces_text.delete(1.0, tk.END)
                ifaces_text.insert(tk.END, output)
                
                # Highlight interface names
                self._highlight_network_text(ifaces_text)
            else:
                ifaces_text.delete(1.0, tk.END)
                ifaces_text.insert(tk.END, f"Error retrieving network interfaces:\n{error}")
        except Exception as e:
            ifaces_text.delete(1.0, tk.END)
            ifaces_text.insert(tk.END, f"Error: {str(e)}")
        
        # Get network connections
        try:
            cmd = [adb_cmd, "-s", serial, "shell", "netstat"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate(timeout=10)
            
            if process.returncode == 0:
                conn_text.delete(1.0, tk.END)
                conn_text.insert(tk.END, output)
            else:
                # Try alternative command
                cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/net/tcp"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                output, error = process.communicate(timeout=10)
                
                if process.returncode == 0:
                    conn_text.delete(1.0, tk.END)
                    conn_text.insert(tk.END, "TCP Connections:\n" + output)
                else:
                    conn_text.delete(1.0, tk.END)
                    conn_text.insert(tk.END, f"Error retrieving network connections:\n{error}")
        except Exception as e:
            conn_text.delete(1.0, tk.END)
            conn_text.insert(tk.END, f"Error: {str(e)}")
        
        # Get data usage
        try:
            cmd = [adb_cmd, "-s", serial, "shell", "cat", "/proc/net/xt_qtaguid/stats"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate(timeout=10)
            
            if process.returncode == 0:
                # Try to get app package names for UIDs
                cmd_packages = [adb_cmd, "-s", serial, "shell", "pm", "list", "packages", "-U"]
                try:
                    pkg_process = subprocess.Popen(cmd_packages, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    pkg_output, pkg_error = pkg_process.communicate(timeout=10)
                    
                    # Create a mapping of UIDs to package names
                    uid_to_pkg = {}
                    if pkg_process.returncode == 0:
                        for line in pkg_output.splitlines():
                            if ":" in line and "uid:" in line:
                                try:
                                    parts = line.split(":")
                                    if len(parts) >= 3:
                                        pkg = parts[1].strip()
                                        uid_str = parts[2].strip()
                                        if uid_str.startswith("uid:"):
                                            uid = uid_str[4:]
                                            uid_to_pkg[uid] = pkg
                                except:
                                    pass
                except:
                    uid_to_pkg = {}
                
                # Process the raw stats data
                usage_data = {}
                headers = []
                for i, line in enumerate(output.splitlines()):
                    if i == 0:
                        headers = line.split()
                        usage_text.delete(1.0, tk.END)
                        usage_text.insert(tk.END, "Data Usage by UID:\n\n")
                        usage_text.insert(tk.END, "UID\tPackage\tRx Bytes\tTx Bytes\n")
                        usage_text.insert(tk.END, "---------------------------------------------------\n")
                    else:
                        parts = line.split()
                        if len(parts) > 5:
                            try:
                                uid = parts[3]
                                rx_bytes = int(parts[5])
                                tx_bytes = int(parts[7])
                                
                                if uid not in usage_data:
                                    usage_data[uid] = {"rx": 0, "tx": 0}
                                
                                usage_data[uid]["rx"] += rx_bytes
                                usage_data[uid]["tx"] += tx_bytes
                                
                            except (ValueError, IndexError):
                                pass
                
                # Sort UIDs by total usage
                sorted_uids = sorted(
                    usage_data.items(),
                    key=lambda x: x[1]["rx"] + x[1]["tx"],
                    reverse=True
                )
                
                # Show the top users
                for uid, data in sorted_uids[:50]:  # Show top 50 to limit output
                    pkg_name = uid_to_pkg.get(uid, "Unknown")
                    usage_text.insert(tk.END, f"{uid}\t{pkg_name}\t{self._format_bytes(data['rx'])}\t{self._format_bytes(data['tx'])}\n")
                
                if len(sorted_uids) > 50:
                    usage_text.insert(tk.END, "\n... (more entries not shown)")
            else:
                # Alternative command for older Android versions
                cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "netstats"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                output, error = process.communicate(timeout=10)
                
                if process.returncode == 0:
                    usage_text.delete(1.0, tk.END)
                    usage_text.insert(tk.END, output)
                else:
                    usage_text.delete(1.0, tk.END)
                    usage_text.insert(tk.END, f"Error retrieving data usage:\n{error}")
        except Exception as e:
            usage_text.delete(1.0, tk.END)
            usage_text.insert(tk.END, f"Error: {str(e)}")
    
    def _highlight_network_text(self, text_widget):
        """Highlight important parts in the network text"""
        text_widget.tag_configure("interface", font=("Consolas", 10, "bold"), foreground="#0000ff")
        text_widget.tag_configure("ip_addr", foreground="#008800")
        text_widget.tag_configure("up", background="#e0ffe0")
        text_widget.tag_configure("down", background="#ffe0e0")
        
        # Find and tag interface names and states
        for pattern in ["eth", "wlan", "rmnet", "usb", "lo", "tun", "ip6tnl"]:
            start_idx = "1.0"
            while True:
                start_idx = text_widget.search(pattern, start_idx, tk.END)
                if not start_idx:
                    break
                line_start = start_idx.split('.')[0] + ".0"
                line_end = start_idx.split('.')[0] + ".end"
                line_text = text_widget.get(line_start, line_end)
                
                # Tag the interface name
                if ":" in line_text:
                    iface_end = line_text.find(":")
                    if iface_end > 0:
                        end_idx = f"{line_start.split('.')[0]}.{iface_end+1}"
                        text_widget.tag_add("interface", line_start, end_idx)
                
                # Tag UP/DOWN state
                if "UP" in line_text:
                    up_start = line_text.find("UP")
                    if up_start > 0:
                        up_start_idx = f"{line_start.split('.')[0]}.{up_start}"
                        up_end_idx = f"{line_start.split('.')[0]}.{up_start+2}"
                        text_widget.tag_add("up", up_start_idx, up_end_idx)
                        
                if "DOWN" in line_text:
                    down_start = line_text.find("DOWN")
                    if down_start > 0:
                        down_start_idx = f"{line_start.split('.')[0]}.{down_start}"
                        down_end_idx = f"{line_start.split('.')[0]}.{down_start+4}"
                        text_widget.tag_add("down", down_start_idx, down_end_idx)
                
                # Tag IP addresses
                ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
                import re
                for match in re.finditer(ip_pattern, line_text):
                    ip_start = match.start()
                    ip_end = match.end()
                    ip_start_idx = f"{line_start.split('.')[0]}.{ip_start}"
                    ip_end_idx = f"{line_start.split('.')[0]}.{ip_end}"
                    text_widget.tag_add("ip_addr", ip_start_idx, ip_end_idx)
                
                start_idx = line_end
    
    def _format_bytes(self, bytes_val):
        """Format bytes into human readable format"""
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val/1024:.2f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val/(1024*1024):.2f} MB"
        else:
            return f"{bytes_val/(1024*1024*1024):.2f} GB"
        
    # Debugging Functions
    def _show_system_log(self):
        """Show system log"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
        
        # Get the serial number and adb command
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create a new window for system logs
            log_window = tk.Toplevel(self)
            log_window.title("System Log - " + self.device_info.get("model", "Android Device"))
            log_window.geometry("900x600")
            log_window.minsize(700, 500)
            log_window.transient(self)
            log_window.grab_set()
            
            # Add toolbar with controls
            control_frame = ttk.Frame(log_window)
            control_frame.pack(fill="x", padx=10, pady=5)
            
            # Log types selection
            log_type_frame = ttk.LabelFrame(control_frame, text="Log Type")
            log_type_frame.pack(side="left", padx=5, pady=5)
            
            log_type_var = tk.StringVar(value="dmesg")
            
            dmesg_radio = ttk.Radiobutton(log_type_frame, text="Kernel (dmesg)", 
                                          variable=log_type_var, value="dmesg")
            dmesg_radio.pack(side="left", padx=5)
            
            logcat_radio = ttk.Radiobutton(log_type_frame, text="Logcat", 
                                           variable=log_type_var, value="logcat")
            logcat_radio.pack(side="left", padx=5)
            
            events_radio = ttk.Radiobutton(log_type_frame, text="Events", 
                                           variable=log_type_var, value="events")
            events_radio.pack(side="left", padx=5)
            
            # Filter options
            filter_frame = ttk.LabelFrame(control_frame, text="Filter")
            filter_frame.pack(side="left", padx=20, pady=5)
            
            ttk.Label(filter_frame, text="Filter:").pack(side="left")
            filter_var = tk.StringVar()
            filter_entry = ttk.Entry(filter_frame, textvariable=filter_var, width=20)
            filter_entry.pack(side="left", padx=5)
            
            # Log level for logcat
            level_frame = ttk.Frame(control_frame)
            level_frame.pack(side="left", padx=5)
            
            ttk.Label(level_frame, text="Level:").pack(side="left")
            level_var = tk.StringVar(value="V")
            level_combo = ttk.Combobox(level_frame, textvariable=level_var, 
                                      values=["V", "D", "I", "W", "E"], width=5)
            level_combo.pack(side="left", padx=5)
            
            # Action buttons
            btn_frame = ttk.Frame(control_frame)
            btn_frame.pack(side="left", padx=10)
            
            refresh_btn = ttk.Button(btn_frame, text="Refresh", 
                                     command=lambda: self._refresh_system_log(
                                         log_text, serial, adb_cmd, log_type_var.get(), filter_var.get(), level_var.get()
                                     ))
            refresh_btn.pack(side="left", padx=5)
            
            clear_btn = ttk.Button(btn_frame, text="Clear", 
                                   command=lambda: log_text.delete(1.0, tk.END))
            clear_btn.pack(side="left")
            
            save_btn = ttk.Button(btn_frame, text="Save Log", 
                                  command=lambda: self._save_log_to_file(log_text.get(1.0, tk.END)))
            save_btn.pack(side="left", padx=5)
            
            # Create text widget with scrollbar for logs
            log_frame = ttk.Frame(log_window)
            log_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            scrollbar = ttk.Scrollbar(log_frame)
            scrollbar.pack(side="right", fill="y")
            
            log_text = tk.Text(log_frame, wrap="word", font=("Consolas", 10), 
                              yscrollcommand=scrollbar.set, background="#f8f8f8")
            log_text.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=log_text.yview)
            
            # Status bar
            status_frame = ttk.Frame(log_window)
            status_frame.pack(fill="x", padx=10, pady=2)
            status_var = tk.StringVar(value="Ready")
            status_label = ttk.Label(status_frame, textvariable=status_var, anchor="w")
            status_label.pack(side="left")
            
            # Set up line counting and monitoring
            line_count_var = tk.StringVar(value="Lines: 0")
            line_count_label = ttk.Label(status_frame, textvariable=line_count_var)
            line_count_label.pack(side="right")
            
            # Auto refresh checkbox
            auto_refresh_var = tk.BooleanVar(value=False)
            auto_refresh_check = ttk.Checkbutton(control_frame, text="Auto-refresh", 
                                                variable=auto_refresh_var)
            auto_refresh_check.pack(side="right", padx=10)
            
            # Set up tag configurations for colorizing logs
            log_text.tag_configure("debug", foreground="#0000FF")
            log_text.tag_configure("info", foreground="#000000")
            log_text.tag_configure("warning", foreground="#FF8800")
            log_text.tag_configure("error", foreground="#FF0000")
            log_text.tag_configure("timestamp", foreground="#008800")
            log_text.tag_configure("process", foreground="#880088")
            
            # Initial load of system log
            self._refresh_system_log(log_text, serial, adb_cmd, log_type_var.get(), 
                                    filter_var.get(), level_var.get(), status_var, line_count_var)
            
            # Update when log type or filter changes
            def on_log_type_change():
                self._refresh_system_log(log_text, serial, adb_cmd, log_type_var.get(), 
                                        filter_var.get(), level_var.get(), status_var, line_count_var)
            
            # Bind changes to refresh
            log_type_var.trace("w", lambda *args: on_log_type_change())
            level_var.trace("w", lambda *args: on_log_type_change())
            
            # Filter on Enter key
            filter_entry.bind("<Return>", 
                            lambda event: self._refresh_system_log(
                                log_text, serial, adb_cmd, log_type_var.get(), 
                                filter_var.get(), level_var.get(), status_var, line_count_var
                            ))
            
            # Auto-refresh function
            def auto_refresh():
                if auto_refresh_var.get() and log_window.winfo_exists():
                    self._refresh_system_log(
                        log_text, serial, adb_cmd, log_type_var.get(), 
                        filter_var.get(), level_var.get(), status_var, line_count_var, append_mode=True
                    )
                    log_window.after(3000, auto_refresh)
            
            # Setup auto-refresh when checkbox changes
            auto_refresh_check.config(command=lambda: auto_refresh() if auto_refresh_var.get() else None)
            
        except Exception as e:
            logging.error(f"Error showing system log: {e}")
            messagebox.showerror("Error", f"Failed to display system log: {e}")
    
    def _refresh_system_log(self, text_widget, serial, adb_cmd, log_type="dmesg", 
                           filter_text="", log_level="V", status_var=None, line_count_var=None, 
                           append_mode=False):
        """Refresh system log in the text widget"""
        if not append_mode:
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, f"Loading {log_type} logs...\n\n")
            text_widget.update()
        
        try:
            # Prepare the command based on log type
            if log_type == "dmesg":
                cmd = [adb_cmd, "-s", serial, "shell", "dmesg"]
                if filter_text:
                    cmd.extend(["|", "grep", filter_text])
            elif log_type == "logcat":
                cmd = [adb_cmd, "-s", serial, "shell", "logcat", "-d", "-v", "threadtime", "*:" + log_level]
                if filter_text:
                    cmd.extend(["|", "grep", filter_text])
            elif log_type == "events":
                cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "events"]
                if filter_text:
                    cmd.extend(["|", "grep", filter_text])
            else:
                if status_var:
                    status_var.set(f"Unknown log type: {log_type}")
                return
            
            # Execute the command
            if IS_WINDOWS:
                # For Windows, we need to use shell=True and join the command
                cmd_str = " ".join(cmd)
                process = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                          shell=True, text=True)
            else:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
            output, error = process.communicate(timeout=15)
            
            if process.returncode != 0:
                if not append_mode:
                    text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, f"Error retrieving logs:\n{error}")
                if status_var:
                    status_var.set("Error retrieving logs")
                return
            
            # Process output
            if not append_mode:
                text_widget.delete(1.0, tk.END)
                
            if output:
                # Check if we're appending and need to add a separator
                if append_mode and text_widget.get(1.0, tk.END).strip():
                    text_widget.insert(tk.END, "\n--- Updated at " + 
                                     time.strftime("%Y-%m-%d %H:%M:%S") + " ---\n")
                
                # Insert logs and apply colorization
                self._insert_colorized_logs(text_widget, output, log_type)
                
                # Update line count
                if line_count_var:
                    lines = text_widget.get(1.0, tk.END).count('\n')
                    line_count_var.set(f"Lines: {lines}")
                    
                # Scroll to end for append mode
                if append_mode:
                    text_widget.see(tk.END)
                    
                # Update status
                if status_var:
                    status_var.set(f"Loaded {log_type} logs at " + time.strftime("%H:%M:%S"))
            else:
                text_widget.insert(tk.END, "No log entries found.")
                if status_var:
                    status_var.set("No log entries found")
                
        except subprocess.TimeoutExpired:
            if not append_mode:
                text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "Command timed out. Device may be unresponsive.")
            if status_var:
                status_var.set("Command timed out")
        except Exception as e:
            if not append_mode:
                text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, f"Error: {str(e)}")
            if status_var:
                status_var.set(f"Error: {str(e)}")
            logging.error(f"Error refreshing system log: {e}")
    
    def _insert_colorized_logs(self, text_widget, log_output, log_type):
        """Insert logs with proper colorization based on log type"""
        lines = log_output.splitlines()
        
        for line in lines:
            if not line.strip():
                continue
                
            if log_type == "logcat":
                # Logcat format: date time PID-TID level tag: message
                parts = line.split(None, 5) if len(line.split()) > 5 else []
                
                if len(parts) >= 6:
                    # Extract components
                    date_time = parts[0] + " " + parts[1]
                    pid_tid = parts[2]
                    level = parts[4]
                    message = parts[5]
                    
                    # Insert with tags
                    text_widget.insert(tk.END, date_time + " ", "timestamp")
                    text_widget.insert(tk.END, pid_tid + " ", "process")
                    
                    # Apply tag based on log level
                    if level == "D":
                        text_widget.insert(tk.END, message + "\n", "debug")
                    elif level == "I":
                        text_widget.insert(tk.END, message + "\n", "info")
                    elif level == "W":
                        text_widget.insert(tk.END, message + "\n", "warning")
                    elif level == "E" or level == "F":
                        text_widget.insert(tk.END, message + "\n", "error")
                    else:
                        text_widget.insert(tk.END, message + "\n")
                else:
                    text_widget.insert(tk.END, line + "\n")
                    
            elif log_type == "dmesg":
                # Simple colorization for dmesg
                lower_line = line.lower()
                if "error" in lower_line or "fail" in lower_line:
                    text_widget.insert(tk.END, line + "\n", "error")
                elif "warn" in lower_line:
                    text_widget.insert(tk.END, line + "\n", "warning")
                elif "info" in lower_line:
                    text_widget.insert(tk.END, line + "\n", "info")
                elif "debug" in lower_line:
                    text_widget.insert(tk.END, line + "\n", "debug")
                else:
                    # Try to highlight timestamp if present with brackets
                    if "[" in line and "]" in line:
                        timestamp_end = line.find("]")+1
                        text_widget.insert(tk.END, line[:timestamp_end], "timestamp")
                        text_widget.insert(tk.END, line[timestamp_end:] + "\n")
                    else:
                        text_widget.insert(tk.END, line + "\n")
            else:
                # Default case for other log types
                text_widget.insert(tk.END, line + "\n")
                
    def _save_log_to_file(self, log_content):
        """Save log content to a file"""
        if not log_content.strip():
            messagebox.showinfo("Empty Log", "There is no log content to save.")
            return
            
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Log As"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            messagebox.showinfo("Success", f"Log saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save log: {e}")
            logging.error(f"Error saving log to file: {e}")

    
    def _show_anr_traces(self):
        """Show application not responding traces"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create a new window for ANR traces
            anr_window = tk.Toplevel(self)
            anr_window.title("ANR Traces")
            anr_window.geometry("900x600")
            anr_window.transient(self)
            anr_window.grab_set()
            
            # Add header
            header_frame = ttk.Frame(anr_window)
            header_frame.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(
                header_frame, 
                text="ANR (Application Not Responding) Traces", 
                font=("Arial", 12, "bold")
            ).pack(side="left")
            
            # Add refresh button
            refresh_btn = ttk.Button(
                header_frame, 
                text="Refresh",
                command=lambda: self._refresh_anr_traces(anr_text, serial, adb_cmd)
            )
            refresh_btn.pack(side="right", padx=5)
            
            # Add text widget for ANR traces
            text_frame = ttk.Frame(anr_window)
            text_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side="right", fill="y")
            
            anr_text = tk.Text(
                text_frame, 
                wrap=tk.WORD, 
                yscrollcommand=scrollbar.set,
                font=("Courier", 10),
                padx=10,
                pady=10
            )
            anr_text.pack(fill="both", expand=True)
            scrollbar.config(command=anr_text.yview)
            
            # Add status bar
            status_var = tk.StringVar(value="Loading ANR traces...")
            status_bar = ttk.Label(anr_window, textvariable=status_var, relief="sunken")
            status_bar.pack(fill="x", side="bottom", pady=(5, 0))
            
            # Load ANR traces
            self._refresh_anr_traces(anr_text, serial, adb_cmd, status_var)
            
            # Add right-click context menu
            context_menu = tk.Menu(anr_window, tearoff=0)
            context_menu.add_command(
                label="Copy", 
                command=lambda: anr_text.event_generate("<<Copy>>"),
                accelerator="Ctrl+C"
            )
            
            def show_context_menu(event):
                try:
                    context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    context_menu.grab_release()
            
            anr_text.bind("<Button-3>", show_context_menu)
            
        except Exception as e:
            logging.error(f"Error showing ANR traces: {e}")
            messagebox.showerror("Error", f"Failed to show ANR traces: {e}")
        
    def _refresh_anr_traces(self, text_widget, serial, adb_cmd, status_var=None):
        """Refresh the ANR traces in the text widget"""
        try:
            if status_var:
                status_var.set("Fetching ANR traces...")
                
            text_widget.delete(1.0, tk.END)
            
            # Get ANR traces from device
            cmd = [adb_cmd, "-s", serial, "shell", "cat", "/data/anr/traces.txt"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            
            if process.returncode == 0 and output.strip():
                text_widget.insert(tk.END, output)
                if status_var:
                    status_var.set(f"ANR traces loaded ({len(output.splitlines())} lines)")
            else:
                text_widget.insert(tk.END, "No ANR traces found or access denied.\n\n")
                text_widget.insert(tk.END, f"Error: {error}" if error else "No error information available.")
                if status_var:
                    status_var.set("No ANR traces found")
                    
            # Apply syntax highlighting
            self._highlight_anr_text(text_widget)
            
        except Exception as e:
            error_msg = f"Error refreshing ANR traces: {e}"
            logging.error(error_msg)
            if status_var:
                status_var.set("Error loading ANR traces")
            text_widget.insert(tk.END, f"Error: {error_msg}")
    
    def _highlight_anr_text(self, text_widget):
        """Apply syntax highlighting to ANR traces"""
        # Configure tags for different parts of the ANR trace
        text_widget.tag_configure("timestamp", foreground="blue")
        text_widget.tag_configure("process_name", foreground="darkgreen", font=("Courier", 10, "bold"))
        text_widget.tag_configure("pid_tid", foreground="purple")
        text_widget.tag_configure("error", foreground="red")
        text_widget.tag_configure("warning", foreground="orange")
        
        # Get all text content
        content = text_widget.get("1.0", tk.END)
        
        # Clear existing tags
        for tag in text_widget.tag_names():
            text_widget.tag_remove(tag, "1.0", tk.END)
        
        # Apply highlighting line by line
        for i, line in enumerate(content.splitlines(), 1):
            line_start = f"{i}.0"
            line_end = f"{i}.end"
            
            # Highlight timestamps (e.g., "2023-01-01 12:34:56.789")
            if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+', line):
                text_widget.tag_add("timestamp", line_start, line_end)
            # Highlight process names (e.g., "Process: com.example.app")
            elif line.strip().startswith("Process:"):
                text_widget.tag_add("process_name", line_start, line_end)
            # Highlight PIDs and TIDs (e.g., "PID: 1234" or "TID: 1")
            elif re.match(r'^\s*(PID|TID|sysTid|callTid):\s*\d+', line):
                text_widget.tag_add("pid_tid", line_start, line_end)
            # Highlight errors and warnings
            elif any(word in line.lower() for word in ["error", "exception", "crash"]):
                text_widget.tag_add("error", line_start, line_end)
            elif any(word in line.lower() for word in ["warn", "warning"]):
                text_widget.tag_add("warning", line_start, line_end)
    
    def _show_crash_dumps(self):
        """Show crash dumps"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create a new window for crash dumps
            crash_window = tk.Toplevel(self)
            crash_window.title("Crash Dumps")
            crash_window.geometry("1000x700")
            crash_window.transient(self)
            crash_window.grab_set()
            
            # Main container
            main_frame = ttk.Frame(crash_window)
            main_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Left panel for crash list
            list_frame = ttk.LabelFrame(main_frame, text="Crash Logs")
            list_frame.pack(side="left", fill="y", padx=(0, 5), pady=5)
            
            # Add search box
            search_frame = ttk.Frame(list_frame)
            search_frame.pack(fill="x", padx=5, pady=5)
            
            search_var = tk.StringVar()
            search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
            search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            
            search_btn = ttk.Button(
                search_frame, 
                text="Search",
                command=lambda: self._filter_crash_list(crash_list, search_var.get())
            )
            search_btn.pack(side="left")
            
            # Add listbox for crash logs
            crash_list = tk.Listbox(
                list_frame,
                width=40,
                selectmode="browse",
                font=("Courier", 9)
            )
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=crash_list.yview)
            crash_list.configure(yscrollcommand=scrollbar.set)
            
            scrollbar.pack(side="right", fill="y")
            crash_list.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            
            # Right panel for crash details
            detail_frame = ttk.LabelFrame(main_frame, text="Crash Details")
            detail_frame.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=5)
            
            # Add text widget for crash details
            detail_text = tk.Text(
                detail_frame,
                wrap=tk.WORD,
                font=("Courier", 9),
                padx=10,
                pady=10
            )
            scrollbar_detail = ttk.Scrollbar(detail_frame, command=detail_text.yview)
            detail_text.configure(yscrollcommand=scrollbar_detail.set)
            
            scrollbar_detail.pack(side="right", fill="y")
            detail_text.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Add status bar
            status_var = tk.StringVar(value="Loading crash dumps...")
            status_bar = ttk.Label(crash_window, textvariable=status_var, relief="sunken")
            status_bar.pack(fill="x", side="bottom", pady=(5, 0))
            
            # Add buttons frame
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(side="left", fill="y", padx=5)
            
            refresh_btn = ttk.Button(
                btn_frame,
                text="Refresh",
                command=lambda: self._populate_crash_list(crash_list, detail_text, serial, adb_cmd, status_var)
            )
            refresh_btn.pack(pady=5, fill="x")
            
            # Initial population of crash list
            self._populate_crash_list(crash_list, detail_text, serial, adb_cmd, status_var)
            
            # Bind selection event
            crash_list.bind(
                "<<ListboxSelect>>",
                lambda e: self._show_crash_details(
                    crash_list, detail_text, serial, adb_cmd, status_var
                )
            )
            
        except Exception as e:
            logging.error(f"Error showing crash dumps: {e}")
            messagebox.showerror("Error", f"Failed to show crash dumps: {e}")
        
    def _populate_crash_list(self, listbox, detail_widget, serial, adb_cmd, status_var):
        """Populate the crash list with crash logs from the device"""
        try:
            status_var.set("Fetching crash logs...")
            listbox.delete(0, tk.END)
            detail_widget.delete(1.0, tk.END)
            
            # Find all crash log files
            cmd = [adb_cmd, "-s", serial, "shell", "ls", "-t", "/data/tombstones/"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            
            crash_files = []
            
            if process.returncode == 0 and output.strip():
                # Add tombstone files
                crash_files.extend([f"/data/tombstones/{f.strip()}" for f in output.splitlines() if f.strip()])
            
            # Also check for ANR traces
            cmd = [adb_cmd, "-s", serial, "shell", "ls", "-t", "/data/anr/"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, _ = process.communicate()
            
            if process.returncode == 0 and output.strip():
                # Add ANR files
                crash_files.extend([f"/data/anr/{f.strip()}" for f in output.splitlines() 
                                 if f.strip() and f.lower().endswith(('.txt', '.log', '.traces'))])
            
            if crash_files:
                for i, crash_file in enumerate(crash_files[:100]):  # Limit to 100 most recent
                    listbox.insert(tk.END, os.path.basename(crash_file))
                    listbox.itemconfig(i, {'bg': '#f0f0f0' if i % 2 == 0 else 'white'})
                
                status_var.set(f"Found {len(crash_files)} crash logs")
                # Select first item by default
                if crash_files:
                    listbox.selection_set(0)
                    listbox.event_generate("<<ListboxSelect>>")
            else:
                status_var.set("No crash logs found")
                detail_widget.insert(tk.END, "No crash logs found on the device.")
                
        except Exception as e:
            error_msg = f"Error populating crash list: {e}"
            logging.error(error_msg)
            status_var.set("Error loading crash logs")
            detail_widget.insert(tk.END, f"Error: {error_msg}")
    
    def _show_crash_details(self, listbox, text_widget, serial, adb_cmd, status_var):
        """Show details of the selected crash log"""
        try:
            selection = listbox.curselection()
            if not selection:
                return
                
            crash_file = listbox.get(selection[0])
            status_var.set(f"Loading {crash_file}...")
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, f"Loading {crash_file}...")
            
            # Get the full path of the crash file
            full_path = f"/data/tombstones/{crash_file}" if crash_file.startswith("tombstone_") else f"/data/anr/{crash_file}"
            
            # Pull the crash file content
            cmd = [adb_cmd, "-s", serial, "shell", "cat", full_path]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            
            if process.returncode == 0 and output.strip():
                text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, output)
                status_var.set(f"Loaded {crash_file}")
                self._highlight_crash_text(text_widget)
            else:
                text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, f"Failed to load {crash_file}\n\n")
                text_widget.insert(tk.END, f"Error: {error}" if error else "No error information available.")
                status_var.set(f"Error loading {crash_file}")
                
        except Exception as e:
            error_msg = f"Error showing crash details: {e}"
            logging.error(error_msg)
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, f"Error: {error_msg}")
            status_var.set("Error loading crash details")
    
    def _highlight_crash_text(self, text_widget):
        """Apply syntax highlighting to crash logs"""
        # Configure tags
        text_widget.tag_configure("error", foreground="red")
        text_widget.tag_configure("warning", foreground="orange")
        text_widget.tag_configure("pid_tid", foreground="purple")
        text_widget.tag_configure("address", foreground="blue")
        text_widget.tag_configure("timestamp", foreground="green")
        
        # Get all text content
        content = text_widget.get("1.0", tk.END)
        
        # Clear existing tags
        for tag in text_widget.tag_names():
            text_widget.tag_remove(tag, "1.0", tk.END)
        
        # Apply highlighting line by line
        for i, line in enumerate(content.splitlines(), 1):
            line_start = f"{i}.0"
            line_end = f"{i}.end"
            
            # Highlight error patterns
            if any(word in line.lower() for word in ["error", "fatal", "crash", "abort"]):
                text_widget.tag_add("error", line_start, line_end)
            # Highlight warning patterns
            elif any(word in line.lower() for word in ["warn", "warning", "notice"]):
                text_widget.tag_add("warning", line_start, line_end)
            # Highlight PIDs and TIDs
            elif re.match(r'^\s*(pid|tid|process|thread):?\s*\d+', line.lower()):
                text_widget.tag_add("pid_tid", line_start, line_end)
            # Highlight memory addresses
            elif re.search(r'0x[0-9a-fA-F]{8,}', line):
                for match in re.finditer(r'0x[0-9a-fA-F]{8,}', line):
                    start = f"{i}.{match.start()}"
                    end = f"{i}.{match.end()}"
                    text_widget.tag_add("address", start, end)

    
    def _filter_crash_list(self, listbox, search_text):
        """Filter the crash list based on search text"""
        if not search_text:
            # Reset filter
            for i in range(listbox.size()):
                listbox.itemconfig(i, {'fg': 'black'})
            return
            
        search_text = search_text.lower()
        for i in range(listbox.size()):
            item = listbox.get(i).lower()
            if search_text in item:
                listbox.itemconfig(i, {'fg': 'blue', 'font': ('Courier', 9, 'bold')})
            else:
                listbox.itemconfig(i, {'fg': 'gray', 'font': ('Courier', 9)})
    
    def _generate_bug_report(self):
        """Generate a bug report"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create a new window for bug report options
            bug_report_window = tk.Toplevel(self)
            bug_report_window.title("Generate Bug Report")
            bug_report_window.geometry("600x400")
            bug_report_window.transient(self)
            bug_report_window.grab_set()
            
            # Main container
            main_frame = ttk.Frame(bug_report_window, padding="10")
            main_frame.pack(fill="both", expand=True)
            
            # Bug report options
            ttk.Label(
                main_frame,
                text="Bug Report Options",
                font=("Arial", 12, "bold")
            ).pack(pady=(0, 15))
            
            # Options frame
            options_frame = ttk.LabelFrame(main_frame, text="Report Options", padding="10")
            options_frame.pack(fill="x", pady=5)
            
            # Include system logs
            include_logs = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                options_frame,
                text="Include system logs",
                variable=include_logs
            ).pack(anchor="w", pady=2)
            
            # Include dumpsys
            include_dumpsys = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                options_frame,
                text="Include system dumpsys information",
                variable=include_dumpsys
            ).pack(anchor="w", pady=2)
            
            # Include ANR traces
            include_anr = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                options_frame,
                text="Include ANR traces",
                variable=include_anr
            ).pack(anchor="w", pady=2)
            
            # Include crash dumps
            include_crashes = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                options_frame,
                text="Include crash dumps",
                variable=include_crashes
            ).pack(anchor="w", pady=2)
            
            # Include bug report
            include_bugreport = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                options_frame,
                text="Include full bug report (may take longer)",
                variable=include_bugreport
            ).pack(anchor="w", pady=2)
            
            # Output directory
            output_frame = ttk.Frame(main_frame)
            output_frame.pack(fill="x", pady=10)
            
            ttk.Label(
                output_frame,
                text="Output Directory:"
            ).pack(anchor="w")
            
            output_dir = tk.StringVar(value=os.path.expanduser("~/bugreports"))
            
            dir_frame = ttk.Frame(output_frame)
            dir_frame.pack(fill="x", pady=5)
            
            ttk.Entry(
                dir_frame,
                textvariable=output_dir,
                width=50
            ).pack(side="left", fill="x", expand=True)
            
            def browse_directory():
                dir_path = filedialog.askdirectory()
                if dir_path:
                    output_dir.set(dir_path)
            
            ttk.Button(
                dir_frame,
                text="Browse...",
                command=browse_directory
            ).pack(side="left", padx=5)
            
            # Status frame
            status_frame = ttk.Frame(main_frame)
            status_frame.pack(fill="x", pady=10)
            
            status_var = tk.StringVar(value="Ready to generate bug report")
            status_label = ttk.Label(
                status_frame,
                textvariable=status_var,
                foreground="blue"
            )
            status_label.pack(side="left")
            
            # Progress bar
            progress_var = tk.DoubleVar()
            progress = ttk.Progressbar(
                main_frame,
                variable=progress_var,
                maximum=100,
                mode="determinate"
            )
            progress.pack(fill="x", pady=5)
            
            # Buttons frame
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill="x", pady=10)
            
            def generate_report():
                """Generate the bug report with selected options"""
                try:
                    # Create output directory if it doesn't exist
                    output_path = output_dir.get()
                    os.makedirs(output_path, exist_ok=True)
                    
                    # Generate timestamp for the report
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_dir = os.path.join(output_path, f"bugreport_{timestamp}")
                    os.makedirs(report_dir, exist_ok=True)
                    
                    status_var.set("Generating bug report...")
                    progress_var.set(10)
                    self.update()
                    
                    # Collect system information
                    with open(os.path.join(report_dir, "device_info.txt"), "w") as f:
                        f.write(f"Bug Report - {timestamp}\n")
                        f.write(f"Device: {self.device_info.get('model', 'Unknown')} "
                               f"({self.device_info.get('serial', 'Unknown')})\n")
                        f.write(f"Android Version: {self.device_info.get('version', 'Unknown')}\n")
                        f.write(f"SDK Version: {self.device_info.get('sdk', 'Unknown')}\n")
                    
                    progress_var.set(20)
                    
                    # Collect logs if selected
                    if include_logs.get():
                        status_var.set("Collecting system logs...")
                        self.update()
                        
                        logcat_file = os.path.join(report_dir, "logcat.txt")
                        cmd = [adb_cmd, "-s", serial, "logcat", "-d", "-v", "threadtime"]
                        with open(logcat_file, "w") as f:
                            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                    
                    progress_var.set(40)
                    
                    # Collect dumpsys if selected
                    if include_dumpsys.get():
                        status_var.set("Collecting system information...")
                        self.update()
                        
                        dumpsys_file = os.path.join(report_dir, "dumpsys.txt")
                        cmd = [adb_cmd, "-s", serial, "shell", "dumpsys"]
                        with open(dumpsys_file, "w") as f:
                            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                    
                    progress_var.set(60)
                    
                    # Collect ANR traces if selected
                    if include_anr.get():
                        status_var.set("Collecting ANR traces...")
                        self.update()
                        
                        anr_dir = os.path.join(report_dir, "anr")
                        os.makedirs(anr_dir, exist_ok=True)
                        
                        # Get ANR traces
                        cmd = [adb_cmd, "-s", serial, "shell", "ls", "/data/anr/"]
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        output, _ = process.communicate()
                        
                        if process.returncode == 0 and output.strip():
                            anr_files = [f.strip() for f in output.splitlines() if f.strip() and 
                                       f.lower().endswith(('.txt', '.log', '.traces'))]
                            
                            for anr_file in anr_files:
                                cmd = [adb_cmd, "-s", serial, "shell", "cat", f"/data/anr/{anr_file}"]
                                with open(os.path.join(anr_dir, anr_file), "w") as f:
                                    subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                    
                    progress_var.set(80)
                    
                    # Collect crash dumps if selected
                    if include_crashes.get():
                        status_var.set("Collecting crash dumps...")
                        self.update()
                        
                        crash_dir = os.path.join(report_dir, "crashes")
                        os.makedirs(crash_dir, exist_ok=True)
                        
                        # Get tombstone files
                        cmd = [adb_cmd, "-s", serial, "shell", "ls", "/data/tombstones/"]
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        output, _ = process.communicate()
                        
                        if process.returncode == 0 and output.strip():
                            crash_files = [f.strip() for f in output.splitlines() if f.strip()]
                            
                            for crash_file in crash_files:
                                cmd = [adb_cmd, "-s", serial, "shell", "cat", f"/data/tombstones/{crash_file}"]
                                with open(os.path.join(crash_dir, crash_file), "w") as f:
                                    subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                    
                    progress_var.set(95)
                    
                    # Generate full bug report if selected (may take a while)
                    if include_bugreport.get():
                        status_var.set("Generating full bug report (this may take a while)...")
                        self.update()
                        
                        bugreport_file = os.path.join(report_dir, "full_bugreport.txt")
                        cmd = [adb_cmd, "-s", serial, "bugreport"]
                        with open(bugreport_file, "w") as f:
                            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                    
                    progress_var.set(100)
                    status_var.set(f"Bug report generated at: {report_dir}")
                    
                    # Open the report directory
                    if os.name == 'nt':  # Windows
                        os.startfile(report_dir)
                    elif os.name == 'posix':  # macOS and Linux
                        subprocess.Popen(['xdg-open', report_dir])
                    
                    messagebox.showinfo("Success", f"Bug report generated successfully at:\n{report_dir}")
                    bug_report_window.destroy()
                    
                except Exception as e:
                    error_msg = f"Error generating bug report: {e}"
                    logging.error(error_msg)
                    status_var.set("Error generating bug report")
                    messagebox.showerror("Error", error_msg)
            
            # Generate button
            ttk.Button(
                btn_frame,
                text="Generate Bug Report",
                command=generate_report,
                style="Accent.TButton"
            ).pack(side="right", padx=5)
            
            # Cancel button
            ttk.Button(
                btn_frame,
                text="Cancel",
                command=bug_report_window.destroy
            ).pack(side="right", padx=5)
            
            # Apply some styling
            style = ttk.Style()
            style.configure("Accent.TButton", font=('Arial', 10, 'bold'))
            
        except Exception as e:
            logging.error(f"Error showing bug report dialog: {e}")
            messagebox.showerror("Error", f"Failed to initialize bug report dialog: {e}")
        
    def _start_screen_recording(self):
        """Start screen recording"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
        
        # Get the serial number and adb command
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Create recording configuration dialog
            record_dialog = tk.Toplevel(self)
            record_dialog.title("Screen Recording")
            record_dialog.geometry("400x800")  # Increased height to show all controls
            record_dialog.transient(self)
            record_dialog.grab_set()
            record_dialog.resizable(False, False)
            
            # Add header
            header_label = ttk.Label(
                record_dialog, text="Android Screen Recording", 
                font=("Arial", 14, "bold")
            )
            header_label.pack(pady=10)
            
            # Main configuration frame
            config_frame = ttk.LabelFrame(record_dialog, text="Recording Settings")
            config_frame.pack(fill="x", padx=20, pady=10)
            
            # Destination folder
            folder_frame = ttk.Frame(config_frame)
            folder_frame.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(folder_frame, text="Save to folder:").pack(side="left", padx=5)
            
            # Create screenshots directory if it doesn't exist
            screenshots_dir = os.path.join(os.path.expanduser("~"), "AndroidScreenRecordings")
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
            
            folder_var = tk.StringVar(value=screenshots_dir)
            folder_entry = ttk.Entry(folder_frame, textvariable=folder_var, width=25)
            folder_entry.pack(side="left", padx=5, fill="x", expand=True)
            
            browse_btn = ttk.Button(
                folder_frame, text="Browse", 
                command=lambda: folder_var.set(filedialog.askdirectory() or folder_var.get())
            )
            browse_btn.pack(side="left", padx=5)
            
            # Filename
            filename_frame = ttk.Frame(config_frame)
            filename_frame.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(filename_frame, text="Filename:").pack(side="left", padx=5)
            
            default_filename = f"recording_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
            filename_var = tk.StringVar(value=default_filename)
            filename_entry = ttk.Entry(filename_frame, textvariable=filename_var, width=30)
            filename_entry.pack(side="left", padx=5, fill="x", expand=True)
            
            # Time limit
            time_frame = ttk.Frame(config_frame)
            time_frame.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(time_frame, text="Time limit:").pack(side="left", padx=5)
            
            time_var = tk.StringVar(value="30")
            time_entry = ttk.Spinbox(time_frame, from_=1, to=180, textvariable=time_var, width=5)
            time_entry.pack(side="left", padx=5)
            ttk.Label(time_frame, text="seconds").pack(side="left")
            
            # Resolution options
            res_frame = ttk.Frame(config_frame)
            res_frame.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(res_frame, text="Resolution:").pack(side="left", padx=5)
            
            # Default to device resolution
            res_var = tk.StringVar(value="Default")
            res_combo = ttk.Combobox(res_frame, textvariable=res_var, width=15)
            res_combo['values'] = ("Default", "1920x1080", "1280x720", "800x600")
            res_combo.pack(side="left", padx=5)
            
            # Bitrate options
            bitrate_frame = ttk.Frame(config_frame)
            bitrate_frame.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(bitrate_frame, text="Bitrate:").pack(side="left", padx=5)
            
            bitrate_var = tk.StringVar(value="6Mbps")
            bitrate_combo = ttk.Combobox(bitrate_frame, textvariable=bitrate_var, width=10)
            bitrate_combo['values'] = ("2Mbps", "4Mbps", "6Mbps", "8Mbps", "12Mbps")
            bitrate_combo.pack(side="left", padx=5)
            
            # Additional options
            options_frame = ttk.LabelFrame(record_dialog, text="Options")
            options_frame.pack(fill="x", padx=20, pady=10)
            
            # Audio recording (if supported)
            audio_var = tk.BooleanVar(value=False)
            audio_check = ttk.Checkbutton(
                options_frame, text="Record audio (if supported by device)", 
                variable=audio_var
            )
            audio_check.pack(anchor="w", padx=10, pady=5)
            
            # No display touch indicators
            touch_var = tk.BooleanVar(value=True)
            touch_check = ttk.Checkbutton(
                options_frame, text="Show touch indicators", 
                variable=touch_var
            )
            touch_check.pack(anchor="w", padx=10, pady=5)
            
            # Show recording progress
            progress_var = tk.BooleanVar(value=True)
            progress_check = ttk.Checkbutton(
                options_frame, text="Show progress indicator", 
                variable=progress_var
            )
            progress_check.pack(anchor="w", padx=10, pady=5)
            
            # Open after recording
            open_var = tk.BooleanVar(value=True)
            open_check = ttk.Checkbutton(
                options_frame, text="Open after recording", 
                variable=open_var
            )
            open_check.pack(anchor="w", padx=10, pady=5)
            
            # Action buttons
            btn_frame = ttk.Frame(record_dialog)
            btn_frame.pack(fill="x", padx=20, pady=15)
            
            cancel_btn = ttk.Button(
                btn_frame, text="Cancel", 
                command=record_dialog.destroy
            )
            cancel_btn.pack(side="left", padx=5)
            
            start_btn = ttk.Button(
                btn_frame, text="Start Recording", 
                command=lambda: self._do_screen_recording(
                    record_dialog,
                    serial,
                    adb_cmd,
                    os.path.join(folder_var.get(), filename_var.get()),
                    int(time_var.get()),
                    res_var.get(),
                    bitrate_var.get(),
                    audio_var.get(),
                    touch_var.get(),
                    progress_var.get(),
                    open_var.get()
                )
            )
            start_btn.pack(side="right", padx=5)
            
        except Exception as e:
            logging.error(f"Error setting up screen recording: {e}")
            messagebox.showerror("Error", f"Failed to setup screen recording: {e}")
    
    def _do_screen_recording(self, dialog, serial, adb_cmd, output_path, time_limit, 
                            resolution, bitrate, record_audio, show_touches, 
                            show_progress, open_after):
        """Start the actual screen recording process"""
        try:
            # Close the configuration dialog
            dialog.destroy()
            
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Prepare the command with selected options
            cmd = [adb_cmd, "-s", serial, "shell", "screenrecord"]
            
            # Add options
            if resolution != "Default":
                cmd.extend(["--size", resolution])
                
            # Parse bitrate (e.g., "6Mbps" to "6000000")
            if bitrate:
                bitrate_value = bitrate.lower().replace("mbps", "").strip()
                try:
                    # Convert Mbps to bps (1 Mbps = 1,000,000 bps)
                    bitrate_bps = int(float(bitrate_value) * 1000000)
                    cmd.extend(["--bit-rate", str(bitrate_bps)])
                except ValueError:
                    pass
            
            # Time limit in seconds
            cmd.extend(["--time-limit", str(time_limit)])
            
            # Audio recording
            if record_audio:
                # Only available on Android 11+
                cmd.append("--mic")
            
            # Show touches
            if show_touches:
                cmd.append("--show-touch")
                
            # Set temporary path on device
            device_path = "/sdcard/screen_recording_temp.mp4"
            cmd.append(device_path)
            
            # Create progress dialog
            if show_progress:
                progress_dialog = tk.Toplevel(self)
                progress_dialog.title("Screen Recording")
                progress_dialog.geometry("300x150")
                progress_dialog.transient(self)
                progress_dialog.resizable(False, False)
                
                ttk.Label(
                    progress_dialog, 
                    text="Recording in progress...", 
                    font=("Arial", 12)
                ).pack(pady=10)
                
                progress = ttk.Progressbar(
                    progress_dialog, orient="horizontal", 
                    length=250, mode="determinate"
                )
                progress.pack(padx=20, pady=10)
                progress["maximum"] = time_limit
                progress["value"] = 0
                
                time_var = tk.StringVar(value=f"Time remaining: {time_limit} seconds")
                time_label = ttk.Label(progress_dialog, textvariable=time_var)
                time_label.pack(pady=5)
                
                # Stop button
                stop_btn = ttk.Button(
                    progress_dialog, text="Stop Recording", 
                    command=lambda: self._stop_recording(serial, adb_cmd, device_path, output_path, open_after)
                )
                stop_btn.pack(pady=10)
                
                # Update progress
                def update_progress(current_time):
                    if current_time <= time_limit and progress_dialog.winfo_exists():
                        progress["value"] = current_time
                        time_var.set(f"Time remaining: {time_limit - current_time} seconds")
                        
                        if current_time < time_limit:
                            progress_dialog.after(1000, update_progress, current_time + 1)
                        else:
                            self._finish_recording(
                                serial, adb_cmd, device_path, output_path, 
                                open_after, progress_dialog
                            )
                
                # Start the recording in a separate thread
                threading.Thread(
                    target=self._recording_thread, 
                    args=(cmd, serial, adb_cmd, device_path, output_path, open_after, progress_dialog),
                    daemon=True
                ).start()
                
                # Start progress update
                progress_dialog.after(1000, update_progress, 1)
            else:
                # Start the recording in a separate thread without progress dialog
                threading.Thread(
                    target=self._recording_thread, 
                    args=(cmd, serial, adb_cmd, device_path, output_path, open_after, None),
                    daemon=True
                ).start()
                
                messagebox.showinfo(
                    "Recording Started", 
                    f"Screen recording started for {time_limit} seconds. Please wait..."
                )
                
        except Exception as e:
            logging.error(f"Error starting screen recording: {e}")
            messagebox.showerror("Error", f"Failed to start screen recording: {e}")
            
    def _recording_thread(self, cmd, serial, adb_cmd, device_path, output_path, open_after, progress_dialog):
        """Thread for screen recording process"""
        try:
            # Start the recording
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, error = process.communicate()
            
            # Check if the recording was successful
            if process.returncode == 0:
                # Pull the file from the device
                self._finish_recording(serial, adb_cmd, device_path, output_path, open_after, progress_dialog)
            else:
                if progress_dialog and progress_dialog.winfo_exists():
                    progress_dialog.destroy()
                messagebox.showerror("Error", f"Screen recording failed: {error}")
        except Exception as e:
            if progress_dialog and progress_dialog.winfo_exists():
                progress_dialog.destroy()
            logging.error(f"Error in recording thread: {e}")
            messagebox.showerror("Error", f"Recording error: {e}")
    
    def _stop_recording(self, serial, adb_cmd, device_path, output_path, open_after, progress_dialog=None):
        """Stop the ongoing screen recording"""
        try:
            # Send Ctrl+C to stop the recording process
            subprocess.run([adb_cmd, "-s", serial, "shell", "killall", "-SIGINT", "screenrecord"])
            
            # Wait a moment to ensure the file is properly saved
            time.sleep(1)
            
            # Finish the recording process
            self._finish_recording(serial, adb_cmd, device_path, output_path, open_after, progress_dialog)
        except Exception as e:
            logging.error(f"Error stopping recording: {e}")
            messagebox.showerror("Error", f"Failed to stop recording: {e}")
    
    def _finish_recording(self, serial, adb_cmd, device_path, output_path, open_after, progress_dialog=None):
        """Finish the recording by pulling the file and cleaning up"""
        try:
            # Close the progress dialog if it exists
            if progress_dialog and progress_dialog.winfo_exists():
                progress_dialog.destroy()
                
            # Pull the recording file from the device
            pull_cmd = [adb_cmd, "-s", serial, "pull", device_path, output_path]
            process = subprocess.Popen(pull_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, error = process.communicate()
            
            if process.returncode == 0:
                # Remove temporary file from device
                subprocess.run([adb_cmd, "-s", serial, "shell", "rm", device_path])
                
                # Show success message
                messagebox.showinfo(
                    "Recording Complete", 
                    f"Screen recording saved to:\n{output_path}"
                )
                
                # Open file if requested
                if open_after:
                    if IS_WINDOWS:
                        os.startfile(output_path)
                    else:
                        subprocess.run(["xdg-open", output_path])
                        
            else:
                messagebox.showerror("Error", f"Failed to save recording: {error}")
        except Exception as e:
            logging.error(f"Error finishing recording: {e}")
            messagebox.showerror("Error", f"Failed to finish recording: {e}")

        
    def _show_storage_info(self):
        """Show storage information"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Get ADB command and serial
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        # Create a new window for storage info
        storage_window = tk.Toplevel(self)
        storage_window.title("Device Storage Information")
        storage_window.geometry("800x600")
        storage_window.minsize(700, 500)
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 800) // 2
        y_pos = (self.winfo_screenheight() - 600) // 2
        storage_window.geometry(f"+{x_pos}+{y_pos}")
        
        # Create a text widget with scrollbar
        text_frame = ttk.Frame(storage_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        text_widget = tk.Text(
            text_frame, 
            wrap="word", 
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Add a refresh button
        button_frame = ttk.Frame(storage_window)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="Refresh", 
            command=lambda: self._refresh_storage_info(text_widget, serial, adb_cmd)
        ).pack(side="left")
        
        # Initial load of storage info
        self._refresh_storage_info(text_widget, serial, adb_cmd)
    
    def _refresh_storage_info(self, text_widget, serial, adb_cmd):
        """Refresh the storage information in the text widget"""
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, "Loading storage information...\n\n")
        text_widget.update()
        
        try:
            # Get overall disk usage
            cmd = [adb_cmd, "-s", serial, "shell", "df", "-h"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Failed to get storage info: {stderr}")
                
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "=== Storage Overview ===\n\n")
            text_widget.insert(tk.END, stdout)
            
            # Get package-specific storage usage
            text_widget.insert(tk.END, "\n\n=== App Storage Usage ===\n\n")
            
            # For Android 8.0+ we can use the newer storage stats command
            cmd = [adb_cmd, "-s", serial, "shell", "dumpsys", "package", "--show-uid-size"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout.strip():
                text_widget.insert(tk.END, stdout)
            else:
                # Fallback to older method if the above fails
                cmd = [adb_cmd, "-s", serial, "shell", "du", "-h", "/data/app/", "2>/dev/null"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                
                if process.returncode == 0 and stdout.strip():
                    text_widget.insert(tk.END, "App storage usage (size on disk):\n")
                    text_widget.insert(tk.END, stdout)
                else:
                    text_widget.insert(tk.END, "Could not retrieve detailed app storage info\n")
            
            # Get cache sizes
            text_widget.insert(tk.END, "\n\n=== Cache Information ===\n\n")
            
            # Get cache size for /cache partition
            cmd = [adb_cmd, "-s", serial, "shell", "du", "-sh", "/cache/"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout.strip():
                text_widget.insert(tk.END, f"System cache: {stdout}")
            
            # Get cache size for /data/local/tmp
            cmd = [adb_cmd, "-s", serial, "shell", "du", "-sh", "/data/local/tmp/"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout.strip():
                text_widget.insert(tk.END, f"Temporary files: {stdout}")
            
            # Get app cache info
            cmd = [adb_cmd, "-s", serial, "shell", "du", "-sh", "/data/data/*/cache/"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout.strip():
                text_widget.insert(tk.END, "\nApp caches (top 20 largest):\n")
                # Sort by size (largest first) and get top 20
                lines = [line for line in stdout.split('\n') if line.strip()]
                sorted_lines = sorted(
                    lines,
                    key=lambda x: float(x.split('\t')[0].replace('M', '').replace('K', '').replace('G', '')),
                    reverse=True
                )
                text_widget.insert(tk.END, '\n'.join(sorted_lines[:20]))
            
        except Exception as e:
            text_widget.insert(tk.END, f"\nError: {str(e)}\n")
        
        # Make the text read-only
        text_widget.config(state="disabled")
        
    def _clean_app_caches(self):
        """Clean application caches"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Get ADB command and serial
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        # Ask for confirmation
        if not messagebox.askyesno(
            "Confirm Clear Cache",
            "This will clear all app caches. This may take some time.\n\n"
            "Do you want to continue?"
        ):
            return
            
        # Create a progress dialog
        progress_window = tk.Toplevel(self)
        progress_window.title("Clearing Caches")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 400) // 2
        y_pos = (self.winfo_screenheight() - 150) // 2
        progress_window.geometry(f"+{x_pos}+{y_pos}")
        
        # Add a label
        label = ttk.Label(progress_window, text="Clearing app caches, please wait...")
        label.pack(pady=20)
        
        # Add a progress bar
        progress = ttk.Progressbar(
            progress_window, 
            orient="horizontal", 
            length=300, 
            mode="indeterminate"
        )
        progress.pack(pady=10)
        progress.start()
        
        # Add a status label
        status = ttk.Label(progress_window, text="")
        status.pack(pady=5)
        
        # Make the window modal
        progress_window.transient(self)
        progress_window.grab_set()
        progress_window.focus_force()
        
        # Function to run in a separate thread
        def clear_caches():
            try:
                # First, get the list of all packages with caches
                status.config(text="Finding apps with caches...")
                progress_window.update()
                
                # Get all packages
                cmd = [adb_cmd, "-s", serial, "shell", "pm", "list", "packages", "-3"]
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise Exception(f"Failed to list packages: {stderr}")
                
                # Extract package names
                packages = [line.split(':', 1)[1].strip() for line in stdout.split('\n') if line.strip()]
                
                # Now clear caches for each package
                status.config(text=f"Clearing caches for {len(packages)} apps...")
                progress_window.update()
                
                cleared = 0
                errors = []
                
                for i, package in enumerate(packages, 1):
                    try:
                        # Update status
                        status.config(text=f"Clearing cache for {package} ({i}/{len(packages)})")
                        progress_window.update()
                        
                        # Clear app cache
                        cmd = [adb_cmd, "-s", serial, "shell", "pm", "clear", package]
                        process = subprocess.Popen(
                            cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        stdout, stderr = process.communicate()
                        
                        if process.returncode == 0 and "Success" in stdout:
                            cleared += 1
                        else:
                            errors.append(f"{package}: {stderr or stdout}")
                            
                    except Exception as e:
                        errors.append(f"{package}: {str(e)}")
                
                # Also clear system caches
                try:
                    status.config(text="Clearing system caches...")
                    progress_window.update()
                    
                    # Clear dalvik cache (requires root)
                    cmd = [adb_cmd, "-s", serial, "shell", "su", "-c", "rm -rf /data/dalvik-cache/*"]
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
                    
                    # Clear cache partition (requires root)
                    cmd = [adb_cmd, "-s", serial, "shell", "su", "-c", "rm -rf /cache/*"]
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
                    
                except Exception as e:
                    errors.append(f"System cache: {str(e)}")
                
                # Show results
                progress_window.after(0, lambda: show_results(cleared, errors))
                
            except Exception as e:
                progress_window.after(0, lambda: show_error(str(e)))
        
        # Function to show results
        def show_results(cleared, errors):
            progress.stop()
            progress_window.destroy()
            
            msg = f"Successfully cleared caches for {cleared} apps."
            if errors:
                msg += f"\n\nEncountered {len(errors)} errors:\n" + "\n".join(f"• {e}" for e in errors[:10])
                if len(errors) > 10:
                    msg += f"\n... and {len(errors) - 10} more"
            
            messagebox.showinfo("Cache Clear Complete", msg)
        
        # Function to show error
        def show_error(error):
            progress.stop()
            progress_window.destroy()
            messagebox.showerror("Error", f"Failed to clear caches: {error}")
        
        # Start the cache clearing in a separate thread
        import threading
        threading.Thread(target=clear_caches, daemon=True).start()

    def _change_appops_dialog(self):
        """Show dialog to change AppOps permissions for a package"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Change AppOps Permission")
        dialog.geometry("600x500")
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 600) // 2
        y_pos = (self.winfo_screenheight() - 500) // 2
        dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Package name entry
        ttk.Label(dialog, text="Package Name:").pack(pady=(10, 5), padx=10, anchor="w")
        pkg_entry = ttk.Entry(dialog)
        pkg_entry.pack(fill="x", padx=10, pady=5)
        
        # Permission entry
        ttk.Label(dialog, text="Permission (e.g., WAKE_LOCK, GPS, etc.):").pack(pady=(10, 5), padx=10, anchor="w")
        perm_entry = ttk.Entry(dialog)
        perm_entry.pack(fill="x", padx=10, pady=5)
        
        # Mode selection
        ttk.Label(dialog, text="Mode:").pack(pady=(10, 5), padx=10, anchor="w")
        mode_var = tk.StringVar(value="allow")
        mode_frame = ttk.Frame(dialog)
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        modes = [
            ("Allow", "allow"),
            ("Deny", "deny"),
            ("Ignore", "ignore"),
            ("Default", "default")
        ]
        
        for text, mode in modes:
            rb = ttk.Radiobutton(mode_frame, text=text, variable=mode_var, value=mode)
            rb.pack(side="left", padx=5)
        
        # Output area
        ttk.Label(dialog, text="Command Output:").pack(pady=(10, 5), padx=10, anchor="w")
        output_text = tk.Text(dialog, height=10)
        output_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        def change_permission():
            pkg = pkg_entry.get().strip()
            perm = perm_entry.get().strip()
            mode = mode_var.get()
            
            if not pkg or not perm:
                messagebox.showerror("Error", "Please enter both package name and permission")
                return
                
            serial = self.device_info.get("serial", "")
            adb_cmd = self.adb_path if IS_WINDOWS else "adb"
            
            try:
                # Build the command
                cmd = [adb_cmd, "-s", serial, "shell", "appops", "set", pkg, perm, mode]
                
                # Show the command being executed
                output_text.delete(1.0, tk.END)
                output_text.insert(tk.END, f"Executing: {' '.join(cmd)}\n\n")
                
                # Run the command
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                # Show the output
                if process.returncode == 0:
                    output_text.insert(tk.END, f"Successfully set {perm} to {mode} for {pkg}")
                else:
                    output_text.insert(tk.END, f"Error: {process.stderr or process.stdout}")
                
            except Exception as e:
                output_text.insert(tk.END, f"Error: {str(e)}")
        
        ttk.Button(btn_frame, text="Change Permission", command=change_permission).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        # Focus on package entry
        pkg_entry.focus_set()

    def _logcat_screencap_dialog(self):
        """Show dialog for logcat and screencap functionality"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Logcat & Screenshot")
        dialog.geometry("1000x700")
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 1000) // 2
        y_pos = (self.winfo_screenheight() - 700) // 2
        dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tab 1: Logcat
        logcat_tab = ttk.Frame(notebook)
        notebook.add(logcat_tab, text="Logcat")
        
        # Tab 2: Screenshot
        screenshot_tab = ttk.Frame(notebook)
        notebook.add(screenshot_tab, text="Screenshot")
        
        # Tab 3: Screen Recording
        recording_tab = ttk.Frame(notebook)
        notebook.add(recording_tab, text="Screen Recording")
        
        # ===== Logcat Tab =====
        logcat_frame = ttk.LabelFrame(logcat_tab, text="Device Logs", padding=10)
        logcat_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Log level filter
        filter_frame = ttk.Frame(logcat_frame)
        filter_frame.pack(fill="x", pady=5)
        
        ttk.Label(filter_frame, text="Log Level:").pack(side="left", padx=5)
        log_level = ttk.Combobox(filter_frame, values=["VERBOSE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL", "SILENT"], width=10, state="readonly")
        log_level.set("INFO")
        log_level.pack(side="left", padx=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side="left", padx=5)
        log_filter = ttk.Entry(filter_frame)
        log_filter.pack(side="left", fill="x", expand=True, padx=5)
        log_filter.bind("<Return>", lambda e: start_logcat())
        
        # Logcat output
        log_text = tk.Text(logcat_frame, wrap="none", font=("Courier", 10), state="disabled")
        log_scroll_y = ttk.Scrollbar(logcat_frame, orient="vertical", command=log_text.yview)
        log_scroll_x = ttk.Scrollbar(logcat_frame, orient="horizontal", command=log_text.xview)
        log_text.configure(yscrollcommand=log_scroll_y.set, xscrollcommand=log_scroll_x.set)
        
        log_text.grid(row=1, column=0, sticky="nsew")
        log_scroll_y.grid(row=1, column=1, sticky="ns")
        log_scroll_x.grid(row=2, column=0, sticky="ew")
        
        logcat_frame.grid_rowconfigure(1, weight=1)
        logcat_frame.grid_columnconfigure(0, weight=1)
        
        # Logcat controls
        ctrl_frame = ttk.Frame(logcat_frame)
        ctrl_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        
        logcat_process = None
        logcat_running = False
        logcat_buffer = ""
        
        def update_logcat_display():
            nonlocal logcat_buffer
            if logcat_buffer:
                log_text.config(state="normal")
                log_text.insert("end", logcat_buffer)
                log_text.see("end")
                log_text.config(state="disabled")
                logcat_buffer = ""
            
            if logcat_running:
                dialog.after(100, update_logcat_display)
        
        def read_logcat_output(stream):
            nonlocal logcat_buffer
            while logcat_running:
                line = stream.readline()
                if not line:
                    break
                logcat_buffer += line
        
        def start_logcat():
            nonlocal logcat_process, logcat_running
            
            if logcat_running:
                stop_logcat()
                return
                
            log_text.config(state="normal")
            log_text.delete(1.0, "end")
            log_text.config(state="disabled")
            
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Build logcat command
                cmd = [adb_cmd, "-s", serial, "logcat", "-v", "threadtime"]
                
                # Add log level filter
                level = log_level.get()
                if level != "VERBOSE":
                    cmd.extend(["*:", level[0]])
                
                # Add text filter
                text_filter = log_filter.get().strip()
                if text_filter:
                    cmd.extend(["|", "grep", "-i", f"\"{text_filter}\""])
                
                logcat_process = subprocess.Popen(
                    " ".join(cmd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    shell=True
                )
                
                logcat_running = True
                start_btn.config(text="Stop Logcat")
                clear_btn.config(state="disabled")
                
                # Start reading output in a separate thread
                threading.Thread(target=read_logcat_output, args=(logcat_process.stdout,), daemon=True).start()
                
                # Start updating the display
                update_logcat_display()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start logcat: {str(e)}")
                logcat_running = False
        
        def stop_logcat():
            nonlocal logcat_process, logcat_running
            
            if logcat_process:
                try:
                    logcat_process.terminate()
                    logcat_process.wait(timeout=5)
                except:
                    try:
                        logcat_process.kill()
                    except:
                        pass
                
            logcat_running = False
            start_btn.config(text="Start Logcat")
            clear_btn.config(state="normal")
        
        def clear_logcat():
            log_text.config(state="normal")
            log_text.delete(1.0, "end")
            log_text.config(state="disabled")
            
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                subprocess.run([adb_cmd, "-s", serial, "logcat", "-c"], check=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear logcat: {str(e)}")
        
        def save_logcat():
            if not log_text.get(1.0, "end-1c"):
                messagebox.showwarning("Warning", "No log data to save")
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log Files", "*.log"), ("Text Files", "*.txt"), ("All Files", "*.*")],
                title="Save Logcat As"
            )
            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(log_text.get(1.0, "end-1c"))
                    messagebox.showinfo("Success", f"Log saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save log: {str(e)}")
        
        start_btn = ttk.Button(ctrl_frame, text="Start Logcat", command=start_logcat)
        start_btn.pack(side="left", padx=5)
        
        clear_btn = ttk.Button(ctrl_frame, text="Clear Log", command=clear_logcat)
        clear_btn.pack(side="left", padx=5)
        
        save_btn = ttk.Button(ctrl_frame, text="Save Log", command=save_logcat)
        save_btn.pack(side="left", padx=5)
        
        # Handle window close
        def on_closing():
            stop_logcat()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_closing)
        
        # ===== Screenshot Tab =====
        screenshot_frame = ttk.LabelFrame(screenshot_tab, text="Screenshot", padding=10)
        screenshot_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Image display
        img_label = ttk.Label(screenshot_frame)
        img_label.pack(expand=True, pady=10)
        
        # Controls
        btn_frame = ttk.Frame(screenshot_frame)
        btn_frame.pack(fill="x", pady=5)
        
        current_image = None
        
        def capture_screenshot():
            nonlocal current_image
            
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Create temp directory if it doesn't exist
                temp_dir = os.path.join(os.path.expanduser("~"), ".nest", "screenshots")
                os.makedirs(temp_dir, exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                device_temp = f"/sdcard/screencap_{timestamp}.png"
                local_temp = os.path.join(temp_dir, f"screencap_{timestamp}.png")
                
                # Take screenshot
                subprocess.run(
                    [adb_cmd, "-s", serial, "shell", "screencap", "-p", device_temp],
                    check=True
                )
                
                # Pull the file
                subprocess.run(
                    [adb_cmd, "-s", serial, "pull", device_temp, local_temp],
                    check=True
                )
                
                # Clean up on device
                subprocess.run(
                    [adb_cmd, "-s", serial, "shell", "rm", device_temp],
                    check=True
                )
                
                # Display the image
                img = Image.open(local_temp)
                
                # Calculate new size to fit in the dialog while maintaining aspect ratio
                dialog_width = 900
                dialog_height = 500
                
                img_ratio = img.width / img.height
                frame_ratio = dialog_width / dialog_height
                
                if img_ratio > frame_ratio:
                    # Image is wider than frame
                    new_width = dialog_width - 50
                    new_height = int(new_width / img_ratio)
                else:
                    # Image is taller than frame
                    new_height = dialog_height - 50
                    new_width = int(new_height * img_ratio)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                current_image = ImageTk.PhotoImage(img)
                
                img_label.config(image=current_image)
                img_label.image = current_image  # Keep a reference
                
                # Enable save button
                save_ss_btn.config(state="normal")
                
                return local_temp
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture screenshot: {str(e)}")
                return None
        
        def save_screenshot():
            if not hasattr(img_label, 'image') or not img_label.image:
                messagebox.showwarning("Warning", "No screenshot to save")
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Files", "*.png"), ("JPEG Files", "*.jpg"), ("All Files", "*.*")],
                title="Save Screenshot As"
            )
            
            if file_path:
                try:
                    # The image is already saved in the temp directory, just copy it
                    src_path = img_label.image_path
                    shutil.copy2(src_path, file_path)
                    messagebox.showinfo("Success", f"Screenshot saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save screenshot: {str(e)}")
        
        capture_btn = ttk.Button(btn_frame, text="Capture Screenshot", command=capture_screenshot)
        capture_btn.pack(side="left", padx=5)
        
        save_ss_btn = ttk.Button(btn_frame, text="Save As...", state="disabled", command=save_screenshot)
        save_ss_btn.pack(side="left", padx=5)
        
        # ===== Screen Recording Tab =====
        recording_frame = ttk.LabelFrame(recording_tab, text="Screen Recording", padding=10)
        recording_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Recording controls
        ctrl_frame = ttk.Frame(recording_frame)
        ctrl_frame.pack(pady=10)
        
        # Recording duration
        ttk.Label(ctrl_frame, text="Duration (seconds):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        duration_var = tk.StringVar(value="60")
        duration_spin = ttk.Spinbox(ctrl_frame, from_=1, to=180, textvariable=duration_var, width=5)
        duration_spin.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Bitrate
        ttk.Label(ctrl_frame, text="Bitrate (Mbps):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        bitrate_var = tk.StringVar(value="4")
        bitrate_spin = ttk.Spinbox(ctrl_frame, from_=1, to=50, textvariable=bitrate_var, width=5)
        bitrate_spin.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # Resolution
        ttk.Label(ctrl_frame, text="Resolution:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        res_var = tk.StringVar()
        res_combo = ttk.Combobox(ctrl_frame, textvariable=res_var, 
                               values=["Native", "1280x720", "1920x1080"], 
                               state="readonly", width=15)
        res_combo.set("Native")
        res_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w", columnspan=3)
        
        # Status and buttons
        status_var = tk.StringVar(value="Ready to record")
        status_label = ttk.Label(recording_frame, textvariable=status_var, font=("Arial", 10, "bold"))
        status_label.pack(pady=5)
        
        btn_frame = ttk.Frame(recording_frame)
        btn_frame.pack(pady=10)
        
        record_btn = ttk.Button(btn_frame, text="Start Recording", width=15)
        record_btn.pack(side="left", padx=5)
        
        # Recording state
        recording_process = None
        is_recording = False
        output_file = ""
        
        def update_status(message, color="black"):
            status_var.set(message)
            status_label.config(foreground=color)
        
        def start_recording():
            nonlocal recording_process, is_recording, output_file
            
            if is_recording:
                stop_recording()
                return
                
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Get recording parameters
                duration = int(duration_var.get())
                bitrate = int(bitrate_var.get()) * 1000000  # Convert to bps
                resolution = res_var.get()
                
                # Create output directory if it doesn't exist
                output_dir = os.path.join(os.path.expanduser("~"), "Videos", "Nest_Recordings")
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate output filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = os.path.join(output_dir, f"recording_{timestamp}.mp4")
                
                # Build the screenrecord command
                cmd = [adb_cmd, "-s", serial, "shell", "screenrecord", "--verbose"]
                
                # Add parameters if specified
                cmd.extend(["--time-limit", str(duration)])
                cmd.extend(["--bit-rate", str(bitrate)])
                
                if resolution != "Native":
                    cmd.extend(["--size", resolution])
                
                # Add output file on device
                device_temp = "/sdcard/recording.mp4"
                cmd.append(device_temp)
                
                # Start the recording process
                recording_process = subprocess.Popen(
                    " ".join(cmd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True
                )
                
                is_recording = True
                record_btn.config(text="Stop Recording")
                update_status(f"Recording... (0/{duration}s)", "red")
                
                # Start a thread to monitor the recording progress
                def monitor_recording():
                    start_time = time.time()
                    while is_recording and time.time() - start_time < duration + 2:  # Add 2s buffer
                        elapsed = int(time.time() - start_time)
                        if elapsed <= duration:
                            update_status(f"Recording... ({elapsed}/{duration}s)", "red")
                        time.sleep(1)
                    
                    # If still recording after duration + buffer, stop it
                    if is_recording:
                        stop_recording()
                
                threading.Thread(target=monitor_recording, daemon=True).start()
                
                # Start a thread to pull the recording when done
                def pull_recording():
                    nonlocal is_recording
                    
                    # Wait for recording to finish
                    recording_process.wait()
                    
                    if not is_recording:
                        return  # Recording was stopped manually
                    
                    try:
                        # Pull the recording
                        pull_cmd = [adb_cmd, "-s", serial, "pull", device_temp, output_file]
                        result = subprocess.run(
                            pull_cmd,
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode == 0:
                            update_status(f"Recording saved to {output_file}", "green")
                        else:
                            update_status(f"Failed to save recording: {result.stderr}", "red")
                            
                    except Exception as e:
                        update_status(f"Error pulling recording: {str(e)}", "red")
                    finally:
                        # Clean up on device
                        try:
                            subprocess.run(
                                [adb_cmd, "-s", serial, "shell", "rm", device_temp],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                        except:
                            pass
                        
                        is_recording = False
                        record_btn.config(text="Start Recording")
                
                threading.Thread(target=pull_recording, daemon=True).start()
                
            except Exception as e:
                update_status(f"Failed to start recording: {str(e)}", "red")
                is_recording = False
                record_btn.config(text="Start Recording")
        
        def stop_recording():
            nonlocal recording_process, is_recording
            
            if not is_recording:
                return
                
            is_recording = False
            update_status("Stopping recording...", "orange")
            
            if recording_process and recording_process.poll() is None:
                try:
                    # Send Ctrl+C to stop the recording gracefully
                    if IS_WINDOWS:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(recording_process.pid)])
                    else:
                        import signal
                        os.killpg(os.getpgid(recording_process.pid), signal.SIGTERM)
                except Exception as e:
                    update_status(f"Error stopping recording: {str(e)}", "red")
        
        def open_output_folder():
            if output_file and os.path.exists(os.path.dirname(output_file)):
                if IS_WINDOWS:
                    os.startfile(os.path.dirname(output_file))
                else:
                    subprocess.Popen(["xdg-open", os.path.dirname(output_file)])
            else:
                messagebox.showinfo("Info", "No recording has been saved yet.")
        
        # Configure button commands
        record_btn.config(command=start_recording)
        
        # Add open folder button
        open_btn = ttk.Button(btn_frame, text="Open Folder", command=open_output_folder)
        open_btn.pack(side="left", padx=5)
        
        # Close button
        close_btn = ttk.Button(dialog, text="Close", command=on_closing)
        close_btn.pack(pady=10)
        
        # Set focus on the dialog
        dialog.focus_set()

    def _scheduled_tasks_dialog(self):
        """Show dialog to manage scheduled tasks on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Scheduled Tasks")
        dialog.geometry("1000x800")
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 1000) // 2
        y_pos = (self.winfo_screenheight() - 800) // 2
        dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tab 1: View Scheduled Tasks
        view_tab = ttk.Frame(notebook)
        notebook.add(view_tab, text="View Tasks")
        
        # Tab 2: Create New Task
        create_tab = ttk.Frame(notebook)
        notebook.add(create_tab, text="Create Task")
        
        # Tab 3: Task History
        history_tab = ttk.Frame(notebook)
        notebook.add(history_tab, text="Task History")
        
        # ===== View Tasks Tab =====
        view_frame = ttk.LabelFrame(view_tab, text="Scheduled Tasks", padding=10)
        view_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Task list treeview
        columns = ("id", "name", "type", "schedule", "next_run", "last_run", "status")
        tree = FixedHeaderTreeview(view_frame, columns=columns, show="headings", selectmode="browse")
        
        # Define column headings
        tree.heading("id", text="ID")
        tree.heading("name", text="Task Name")
        tree.heading("type", text="Type")
        tree.heading("schedule", text="Schedule")
        tree.heading("next_run", text="Next Run")
        tree.heading("last_run", text="Last Run")
        tree.heading("status", text="Status")
        
        # Set column widths
        tree.column("id", width=50, anchor="center")
        tree.column("name", width=150)
        tree.column("type", width=100, anchor="center")
        tree.column("schedule", width=150, anchor="center")
        tree.column("next_run", width=150, anchor="center")
        tree.column("last_run", width=150, anchor="center")
        tree.column("status", width=100, anchor="center")
        
        # Add scrollbars
        v_scroll = ttk.Scrollbar(view_frame, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(view_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        view_frame.grid_rowconfigure(0, weight=1)
        view_frame.grid_columnconfigure(0, weight=1)
        
        # Action buttons
        btn_frame = ttk.Frame(view_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        
        def refresh_tasks():
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)
            
            try:
                # Get scheduled jobs using adb shell dumpsys jobscheduler
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Get jobs from JobScheduler
                cmd = [adb_cmd, "-s", serial, "shell", "dumpsys jobscheduler"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    raise Exception(f"Failed to get scheduled jobs: {result.stderr}")
                
                # Parse the output to extract job information
                jobs = []
                current_job = {}
                
                for line in result.stdout.splitlines():
                    line = line.strip()
                    
                    # Start of a new job
                    if "JOB" in line and "u0a" in line:
                        if current_job:
                            jobs.append(current_job)
                        
                        # Extract job ID and package
                        parts = line.split()
                        job_id = parts[1].replace(":", "")
                        package = parts[3].split("/")[0]
                        
                        current_job = {
                            "id": job_id,
                            "package": package,
                            "constraints": [],
                            "extras": {}
                        }
                    
                    # Job details
                    elif "Service: " in line:
                        service = line.split("Service: ")[1].strip()
                        current_job["service"] = service
                    
                    elif "Source: " in line:
                        source = line.split("Source: ")[1].strip()
                        current_job["source"] = source
                    
                    elif "Required constraints: " in line:
                        constraints = line.split("Required constraints: ")[1].strip()
                        current_job["constraints"] = [c.strip() for c in constraints.split(",") if c.strip()]
                    
                    elif "Periodic: " in line:
                        period = line.split("Periodic: ")[1].split(" ")[0]
                        current_job["period"] = period
                    
                    elif "Extras: " in line:
                        extras = line.split("Extras: ")[1].strip()
                        current_job["extras"] = extras
                    
                    elif "Enqueue time: " in line:
                        enqueue_time = line.split("Enqueue time: ")[1].strip()
                        current_job["enqueue_time"] = enqueue_time
                    
                    elif "Run time: " in line and "elapsed=" in line:
                        run_time = line.split("Run time: ")[1].split(" ")[0]
                        current_job["run_time"] = run_time
                
                # Add the last job
                if current_job:
                    jobs.append(current_job)
                
                # Add jobs to the treeview
                for idx, job in enumerate(jobs, 1):
                    tree.insert("", "end", values=(
                        job.get("id", ""),
                        job.get("package", ""),
                        job.get("service", "").split(".")[-1],
                        job.get("period", "One-time"),
                        job.get("run_time", "N/A"),
                        job.get("enqueue_time", "N/A"),
                        "Active"
                    ))
                
                # Also check for AlarmManager alarms
                cmd = [adb_cmd, "-s", serial, "shell", "dumpsys alarm"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    alarm_jobs = []
                    current_alarm = {}
                    
                    for line in result.stdout.splitlines():
                        line = line.strip()
                        
                        # Alarm batch
                        if "Batch " in line and "alarm" in line.lower():
                            if current_alarm:
                                alarm_jobs.append(current_alarm)
                            current_alarm = {"type": "Alarm", "details": []}
                        
                        # Intent or operation
                        elif line.startswith("Intent {") or line.startswith("operation={"):
                            current_alarm["intent"] = line
                        
                        # When the alarm is scheduled
                        elif line.startswith("when="):
                            when = line.split("=", 1)[1].split(" ", 1)[0]
                            current_alarm["when"] = when
                        
                        # Repeat interval
                        elif line.startswith("repeatInterval="):
                            interval = line.split("=")[1].split(" ")[0]
                            current_alarm["interval"] = interval
                        
                        # Package name
                        elif line.startswith("package='"):
                            pkg = line.split("'")[1]
                            current_alarm["package"] = pkg
                    
                    # Add the last alarm
                    if current_alarm:
                        alarm_jobs.append(current_alarm)
                    
                    # Add alarms to the treeview
                    for idx, alarm in enumerate(alarm_jobs, 1):
                        if "package" in alarm and "when" in alarm:
                            tree.insert("", "end", values=(
                                f"ALM-{idx}",
                                alarm.get("package", ""),
                                "Alarm",
                                alarm.get("interval", "One-time"),
                                alarm.get("when", "N/A"),
                                "N/A",
                                "Active"
                            ))
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load scheduled tasks: {str(e)}")
        
        def cancel_selected_task():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select a task to cancel")
                return
                
            task_id = tree.item(selected[0], "values")[0]
            task_type = tree.item(selected[0], "values")[2]
            
            if not messagebox.askyesno("Confirm Cancellation", f"Cancel the selected {task_type} task?"):
                return
                
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                if task_type == "Alarm":
                    # For alarms, we need to find the specific alarm by its ID and cancel it
                    # This is a simplified approach - in a real app, you'd need to match the exact alarm
                    messagebox.showinfo("Info", "Alarm cancellation requires root access and is not fully implemented in this demo.")
                else:
                    # For JobScheduler jobs
                    job_id = task_id
                    cmd = [adb_cmd, "-s", serial, "shell", "cmd jobscheduler cancel", job_id]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        messagebox.showinfo("Success", f"Successfully cancelled task {task_id}")
                        refresh_tasks()
                    else:
                        messagebox.showerror("Error", f"Failed to cancel task: {result.stderr}")
                        
            except Exception as e:
                messagebox.showerror("Error", f"Failed to cancel task: {str(e)}")
        
        ttk.Button(btn_frame, text="Refresh", command=refresh_tasks).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel Task", command=cancel_selected_task).pack(side="left", padx=5)
        
        # ===== Create Task Tab =====
        create_frame = ttk.LabelFrame(create_tab, text="Create New Task", padding=10)
        create_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Task details
        ttk.Label(create_frame, text="Task Type:").grid(row=0, column=0, sticky="w", pady=5)
        task_type = ttk.Combobox(create_frame, values=["Shell Command", "Broadcast Intent", "Start Service", "Start Activity"], state="readonly")
        task_type.set("Shell Command")
        task_type.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        
        # Task name
        ttk.Label(create_frame, text="Task Name:").grid(row=1, column=0, sticky="w", pady=5)
        task_name = ttk.Entry(create_frame)
        task_name.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        
        # Command/Intent
        ttk.Label(create_frame, text="Command/Intent:").grid(row=2, column=0, sticky="nw", pady=5)
        command_text = tk.Text(create_frame, height=5, width=50)
        command_text.grid(row=2, column=1, sticky="nsew", pady=5, padx=5)
        
        # Schedule options
        ttk.Label(create_frame, text="Schedule:").grid(row=3, column=0, sticky="w", pady=5)
        
        schedule_frame = ttk.Frame(create_frame)
        schedule_frame.grid(row=3, column=1, sticky="ew", pady=5, padx=5)
        
        schedule_type = tk.StringVar(value="once")
        ttk.Radiobutton(schedule_frame, text="Run Once", variable=schedule_type, value="once").pack(side="left", padx=5)
        ttk.Radiobutton(schedule_frame, text="Repeat Every", variable=schedule_type, value="interval").pack(side="left", padx=5)
        
        interval_frame = ttk.Frame(schedule_frame)
        interval_frame.pack(side="left", fill="x", expand=True)
        
        interval_value = ttk.Spinbox(interval_frame, from_=1, to=999, width=5)
        interval_value.pack(side="left", padx=5)
        interval_value.set("5")
        
        interval_unit = ttk.Combobox(interval_frame, values=["Minutes", "Hours", "Days"], width=8, state="readonly")
        interval_unit.set("Minutes")
        interval_unit.pack(side="left", padx=5)
        
        # Start time
        ttk.Label(create_frame, text="Start Time:").grid(row=4, column=0, sticky="w", pady=5)
        
        time_frame = ttk.Frame(create_frame)
        time_frame.grid(row=4, column=1, sticky="w", pady=5, padx=5)
        
        # Current date and time as default
        now = datetime.now()
        
        # Date picker
        date_picker = ttk.Entry(time_frame, width=12)
        date_picker.insert(0, now.strftime("%Y-%m-%d"))
        date_picker.pack(side="left", padx=5)
        
        # Time picker
        time_picker = ttk.Entry(time_frame, width=8)
        time_picker.insert(0, now.strftime("%H:%M"))
        time_picker.pack(side="left", padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(create_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        def create_task():
            # Validate inputs
            name = task_name.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Please enter a task name")
                return
                
            cmd = command_text.get("1.0", tk.END).strip()
            if not cmd:
                messagebox.showwarning("Validation", "Please enter a command or intent")
                return
                
            # Parse schedule
            try:
                # Parse date and time
                scheduled_time = datetime.strptime(
                    f"{date_picker.get()} {time_picker.get()}", 
                    "%Y-%m-%d %H:%M"
                )
                
                if scheduled_time < datetime.now() and schedule_type.get() == "once":
                    messagebox.showwarning("Validation", "Scheduled time must be in the future")
                    return
                    
                # Calculate delay in seconds
                delay = (scheduled_time - datetime.now()).total_seconds()
                if delay < 0:
                    delay = 0
                
                # For repeating tasks, get interval in seconds
                interval_sec = 0
                if schedule_type.get() == "interval":
                    value = int(interval_value.get())
                    unit = interval_unit.get().lower()
                    
                    if unit == "minutes":
                        interval_sec = value * 60
                    elif unit == "hours":
                        interval_sec = value * 3600
                    elif unit == "days":
                        interval_sec = value * 86400
                    
                    if interval_sec < 60:  # Minimum 1 minute for repeating tasks
                        messagebox.showwarning("Validation", "Minimum interval is 1 minute")
                        return
                
                # Here you would typically schedule the task using Android's JobScheduler or AlarmManager
                # For this demo, we'll just show a success message
                
                task_info = f"""Task Created Successfully!
                
Name: {name}
Type: {task_type.get()}
Scheduled: {scheduled_time.strftime('%Y-%m-%d %H:%M')}
"""
                
                if schedule_type.get() == "interval":
                    task_info += f"Repeats every: {interval_value.get()} {interval_unit.get()}\n"
                
                task_info += f"\nCommand/Intent:\n{cmd}"
                
                messagebox.showinfo("Task Created", task_info)
                
                # Switch to View tab and refresh
                notebook.select(view_tab)
                refresh_tasks()
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid date/time format: {str(e)}")
        
        ttk.Button(btn_frame, text="Create Task", command=create_task).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=lambda: [
            task_name.delete(0, tk.END),
            command_text.delete("1.0", tk.END),
            schedule_type.set("once"),
            date_picker.delete(0, tk.END),
            date_picker.insert(0, datetime.now().strftime("%Y-%m-%d")),
            time_picker.delete(0, tk.END),
            time_picker.insert(0, (datetime.now() + timedelta(minutes=5)).strftime("%H:%M")),
            interval_value.set("5"),
            interval_unit.set("Minutes")
        ]).pack(side="left", padx=5)
        
        # ===== Task History Tab =====
        history_frame = ttk.LabelFrame(history_tab, text="Task Execution History", padding=10)
        history_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # History treeview
        history_columns = ("timestamp", "task_name", "task_type", "status", "details")
        history_tree = FixedHeaderTreeview(history_frame, columns=history_columns, show="headings", selectmode="browse")
        
        # Define column headings
        history_tree.heading("timestamp", text="Timestamp")
        history_tree.heading("task_name", text="Task Name")
        history_tree.heading("task_type", text="Type")
        history_tree.heading("status", text="Status")
        history_tree.heading("details", text="Details")
        
        # Set column widths
        history_tree.column("timestamp", width=150, anchor="center")
        history_tree.column("task_name", width=150)
        history_tree.column("task_type", width=100, anchor="center")
        history_tree.column("status", width=100, anchor="center")
        history_tree.column("details", width=300)
        
        # Add scrollbars
        v_scroll = ttk.Scrollbar(history_frame, orient="vertical", command=history_tree.yview)
        h_scroll = ttk.Scrollbar(history_frame, orient="horizontal", command=history_tree.xview)
        history_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Grid layout
        history_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        history_frame.grid_rowconfigure(0, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)
        
        # Add some sample history (in a real app, this would come from a log file or database)
        sample_history = [
            ("2023-06-15 14:30:22", "Backup Apps", "Shell Command", "Completed", "Backed up 12 apps"),
            ("2023-06-15 14:15:10", "Clean Cache", "Shell Command", "Failed", "Permission denied"),
            ("2023-06-15 10:05:45", "Sync Data", "Start Service", "Completed", "Synced 24 items"),
            ("2023-06-15 08:30:00", "Daily Backup", "Shell Command", "Completed", "Backup successful"),
        ]
        
        for item in sample_history:
            history_tree.insert("", "end", values=item)
        
        # Buttons
        history_btn_frame = ttk.Frame(history_frame)
        history_btn_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        
        def refresh_history():
            # In a real app, this would reload history from storage
            pass  # For now, we're just using static sample data
            
        def clear_history():
            if messagebox.askyesno("Confirm", "Clear all history?"):
                for item in history_tree.get_children():
                    history_tree.delete(item)
        
        ttk.Button(history_btn_frame, text="Refresh", command=refresh_history).pack(side="left", padx=5)
        ttk.Button(history_btn_frame, text="Clear History", command=clear_history).pack(side="left", padx=5)
        
        # Close button
        close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(pady=10)
        
        # Load tasks initially
        refresh_tasks()
        
        # Set focus on the dialog
        dialog.focus_set()

    def _batch_app_manager_dialog(self):
        """Show dialog for batch app management (install/uninstall)"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Batch App Manager")
        dialog.geometry("900x700")
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 900) // 2
        y_pos = (self.winfo_screenheight() - 700) // 2
        dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tab 1: Batch Install
        install_tab = ttk.Frame(notebook)
        notebook.add(install_tab, text="Batch Install")
        
        # Tab 2: Batch Uninstall
        uninstall_tab = ttk.Frame(notebook)
        notebook.add(uninstall_tab, text="Batch Uninstall")
        
        # Tab 3: Batch Disable/Enable
        toggle_tab = ttk.Frame(notebook)
        notebook.add(toggle_tab, text="Toggle Apps")
        
        # Tab 4: Backup/Restore
        backup_tab = ttk.Frame(notebook)
        notebook.add(backup_tab, text="Backup/Restore")
        
        # ===== Install Tab =====
        install_frame = ttk.LabelFrame(install_tab, text="Batch Install APKs", padding=10)
        install_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # APK list
        apk_list_frame = ttk.Frame(install_frame)
        apk_list_frame.pack(fill="both", expand=True, pady=5)
        
        apk_list = tk.Listbox(apk_list_frame, selectmode=tk.EXTENDED, height=15)
        apk_scroll = ttk.Scrollbar(apk_list_frame, orient="vertical", command=apk_list.yview)
        apk_list.config(yscrollcommand=apk_scroll.set)
        apk_list.pack(side="left", fill="both", expand=True)
        apk_scroll.pack(side="right", fill="y")
        
        # Buttons for APK management
        apk_btn_frame = ttk.Frame(install_frame)
        apk_btn_frame.pack(fill="x", pady=5)
        
        def add_apks():
            files = filedialog.askopenfilenames(
                title="Select APK Files",
                filetypes=[("APK Files", "*.apk"), ("All Files", "*.*")]
            )
            for file in files:
                if file not in apk_list.get(0, tk.END):
                    apk_list.insert(tk.END, file)
        
        def remove_apks():
            selected = apk_list.curselection()
            for idx in reversed(selected):
                apk_list.delete(idx)
        
        def clear_apks():
            if messagebox.askyesno("Confirm", "Remove all APKs from the list?"):
                apk_list.delete(0, tk.END)
        
        ttk.Button(apk_btn_frame, text="Add APKs...", command=add_apks).pack(side="left", padx=2)
        ttk.Button(apk_btn_frame, text="Remove Selected", command=remove_apks).pack(side="left", padx=2)
        ttk.Button(apk_btn_frame, text="Clear All", command=clear_apks).pack(side="left", padx=2)
        
        # Install options
        options_frame = ttk.LabelFrame(install_frame, text="Installation Options", padding=10)
        options_frame.pack(fill="x", pady=5)
        
        replace_var = tk.BooleanVar(value=True)
        test_var = tk.BooleanVar()
        downgrade_var = tk.BooleanVar()
        grant_perm_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Replace existing app", variable=replace_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(options_frame, text="Test only (no install)", variable=test_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(options_frame, text="Allow downgrade", variable=downgrade_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(options_frame, text="Grant all permissions", variable=grant_perm_var).pack(anchor="w", pady=2)
        
        # Output area
        output_frame = ttk.LabelFrame(install_frame, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, pady=5)
        
        output_text = tk.Text(output_frame, height=10, state="disabled")
        output_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=output_text.yview)
        output_text.config(yscrollcommand=output_scroll.set)
        output_text.pack(side="left", fill="both", expand=True)
        output_scroll.pack(side="right", fill="y")
        
        # Install button
        def install_apks():
            apks = apk_list.get(0, tk.END)
            if not apks:
                messagebox.showwarning("No APKs", "Please add APK files to install")
                return
                
            # Build install command
            cmd = ["install"]
            if replace_var.get():
                cmd.append("-r")
            if test_var.get():
                cmd.append("-t")
            if downgrade_var.get():
                cmd.append("-d")
            if grant_perm_var.get():
                cmd.append("-g")
                
            # Add APK files
            cmd.extend(apks)
            
            # Run installation in a separate thread
            def run_installation():
                install_btn.config(state="disabled")
                output_text.config(state="normal")
                output_text.delete(1.0, tk.END)
                output_text.config(state="disabled")
                
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                success = 0
                failed = 0
                
                for apk in apks:
                    try:
                        # Push APK to device
                        device_path = f"/data/local/tmp/{os.path.basename(apk)}"
                        push_cmd = [adb_cmd, "-s", serial, "push", apk, device_path]
                        push_result = subprocess.run(push_cmd, capture_output=True, text=True)
                        
                        if push_result.returncode != 0:
                            raise Exception(f"Failed to push APK: {push_result.stderr}")
                        
                        # Install APK
                        install_cmd = [adb_cmd, "-s", serial, "install"]
                        if replace_var.get():
                            install_cmd.append("-r")
                        if test_var.get():
                            install_cmd.append("-t")
                        if downgrade_var.get():
                            install_cmd.append("-d")
                        if grant_perm_var.get():
                            install_cmd.append("-g")
                        install_cmd.append(device_path)
                        
                        install_result = subprocess.run(install_cmd, capture_output=True, text=True)
                        
                        # Update output
                        output_text.config(state="normal")
                        output_text.insert(tk.END, f"Installing {os.path.basename(apk)}...\n")
                        output_text.insert(tk.END, install_result.stdout)
                        if install_result.stderr:
                            output_text.insert(tk.END, f"Error: {install_result.stderr}\n")
                        output_text.insert(tk.END, "-"*50 + "\n")
                        output_text.see(tk.END)
                        output_text.config(state="disabled")
                        
                        if install_result.returncode == 0:
                            success += 1
                        else:
                            failed += 1
                            
                    except Exception as e:
                        output_text.config(state="normal")
                        output_text.insert(tk.END, f"Error installing {os.path.basename(apk)}: {str(e)}\n")
                        output_text.see(tk.END)
                        output_text.config(state="disabled")
                        failed += 1
                    
                    # Small delay between installations
                    time.sleep(1)
                
                # Show summary
                output_text.config(state="normal")
                output_text.insert(tk.END, f"\nInstallation complete. Success: {success}, Failed: {failed}\n")
                output_text.see(tk.END)
                output_text.config(state="disabled")
                
                # Re-enable install button
                install_btn.config(state="normal")
                
                # Show notification
                if failed == 0:
                    messagebox.showinfo("Success", f"Successfully installed {success} app(s)")
                else:
                    messagebox.showwarning("Completed", f"Installation completed with {failed} failure(s) out of {success + failed} app(s)")
            
            # Start installation in a separate thread
            threading.Thread(target=run_installation, daemon=True).start()
        
        install_btn = ttk.Button(install_frame, text="Install APKs", command=install_apks)
        install_btn.pack(pady=10)
        
        # ===== Uninstall Tab =====
        uninstall_frame = ttk.LabelFrame(uninstall_tab, text="Batch Uninstall Apps", padding=10)
        uninstall_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Package list
        pkg_list_frame = ttk.Frame(uninstall_frame)
        pkg_list_frame.pack(fill="both", expand=True, pady=5)
        
        pkg_list = tk.Listbox(pkg_list_frame, selectmode=tk.EXTENDED, height=15)
        pkg_scroll = ttk.Scrollbar(pkg_list_frame, orient="vertical", command=pkg_list.yview)
        pkg_list.config(yscrollcommand=pkg_scroll.set)
        pkg_list.pack(side="left", fill="both", expand=True)
        pkg_scroll.pack(side="right", fill="y")
        
        # Load installed packages
        def load_installed_packages():
            pkg_list.delete(0, tk.END)
            serial = self.device_connected.get("serial", "")
            adb_cmd = self.adb_path if IS_WINDOWS else "adb"
            
            try:
                # Get list of installed packages
                cmd = [adb_cmd, "-s", serial, "shell", "pm", "list", "packages", "-3"]  # Only user apps
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    packages = [line.replace("package:", "").strip() for line in result.stdout.splitlines() if line.strip()]
                    for pkg in sorted(packages):
                        pkg_list.insert(tk.END, pkg)
                else:
                    messagebox.showerror("Error", f"Failed to get installed packages: {result.stderr}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load packages: {str(e)}")
        
        # Buttons for package management
        pkg_btn_frame = ttk.Frame(uninstall_frame)
        pkg_btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(pkg_btn_frame, text="Refresh List", command=load_installed_packages).pack(side="left", padx=2)
        
        # Uninstall button
        def uninstall_packages():
            selected = pkg_list.curselection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select packages to uninstall")
                return
                
            packages = [pkg_list.get(i) for i in selected]
            if not messagebox.askyesno("Confirm Uninstall", f"Uninstall {len(packages)} selected apps?"):
                return
                
            # Run uninstallation in a separate thread
            def run_uninstallation():
                uninstall_btn.config(state="disabled")
                output_text.config(state="normal")
                output_text.delete(1.0, tk.END)
                output_text.config(state="disabled")
                
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                success = 0
                failed = 0
                
                for pkg in packages:
                    try:
                        cmd = [adb_cmd, "-s", serial, "uninstall", pkg]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        # Update output
                        output_text.config(state="normal")
                        output_text.insert(tk.END, f"Uninstalling {pkg}...\n{result.stdout}")
                        if result.stderr:
                            output_text.insert(tk.END, f"Error: {result.stderr}\n")
                        output_text.insert(tk.END, "-"*50 + "\n")
                        output_text.see(tk.END)
                        output_text.config(state="disabled")
                        
                        if "Success" in result.stdout:
                            success += 1
                        else:
                            failed += 1
                            
                    except Exception as e:
                        output_text.config(state="normal")
                        output_text.insert(tk.END, f"Error uninstalling {pkg}: {str(e)}\n")
                        output_text.see(tk.END)
                        output_text.config(state="disabled")
                        failed += 1
                
                # Show summary
                output_text.config(state="normal")
                output_text.insert(tk.END, f"\nUninstallation complete. Success: {success}, Failed: {failed}\n")
                output_text.see(tk.END)
                output_text.config(state="disabled")
                
                # Re-enable uninstall button and refresh package list
                uninstall_btn.config(state="normal")
                load_installed_packages()
                
                # Show notification
                if failed == 0:
                    messagebox.showinfo("Success", f"Successfully uninstalled {success} app(s)")
                else:
                    messagebox.showwarning("Completed", f"Uninstallation completed with {failed} failure(s) out of {success + failed} app(s)")
            
            # Start uninstallation in a separate thread
            threading.Thread(target=run_uninstallation, daemon=True).start()
        
        uninstall_btn = ttk.Button(pkg_btn_frame, text="Uninstall Selected", command=uninstall_packages)
        uninstall_btn.pack(side="left", padx=2)
        
        # Output area for uninstall tab
        uninstall_output_frame = ttk.LabelFrame(uninstall_frame, text="Output", padding=10)
        uninstall_output_frame.pack(fill="both", expand=True, pady=5)
        
        uninstall_output_text = tk.Text(uninstall_output_frame, height=10, state="disabled")
        uninstall_output_scroll = ttk.Scrollbar(uninstall_output_frame, orient="vertical", command=uninstall_output_text.yview)
        uninstall_output_text.config(yscrollcommand=uninstall_output_scroll.set)
        uninstall_output_text.pack(side="left", fill="both", expand=True)
        uninstall_output_scroll.pack(side="right", fill="y")
        
        # Load packages when tab is selected
        def on_tab_selected(event):
            if notebook.select() == uninstall_tab._w:
                load_installed_packages()
        
        notebook.bind("<<NotebookTabChanged>>", on_tab_selected)
        
        # ===== Toggle Tab =====
        # (Implementation for enabling/disabling apps would go here)
        
        # ===== Backup/Restore Tab =====
        # (Implementation for backing up and restoring apps would go here)
        
        # Close button
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        # Load packages initially
        load_installed_packages()

    def _run_shell_script_dialog(self):
        """Show dialog to run a shell script on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Run Shell Script")
        dialog.geometry("700x600")
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 700) // 2
        y_pos = (self.winfo_screenheight() - 600) // 2
        dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Script selection
        script_frame = ttk.LabelFrame(dialog, text="Shell Script", padding=10)
        script_frame.pack(fill="x", padx=10, pady=5)
        
        # Script path entry
        path_frame = ttk.Frame(script_frame)
        path_frame.pack(fill="x", pady=5)
        
        ttk.Label(path_frame, text="Script Path:").pack(side="left", padx=(0, 5))
        script_path = tk.StringVar()
        script_entry = ttk.Entry(path_frame, textvariable=script_path)
        script_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        def browse_script():
            file_path = filedialog.askopenfilename(
                title="Select Shell Script",
                filetypes=[("Shell Scripts", "*.sh"), ("All Files", "*.*")]
            )
            if file_path:
                script_path.set(file_path)
                # Load script content if file exists
                try:
                    with open(file_path, 'r') as f:
                        script_editor.delete('1.0', tk.END)
                        script_editor.insert(tk.END, f.read())
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load script: {e}")
        
        ttk.Button(path_frame, text="Browse...", command=browse_script).pack(side="left")
        
        # Script editor
        script_editor = tk.Text(script_frame, height=10, font=("Courier", 10))
        script_editor.pack(fill="both", expand=True, pady=5)
        
        # Arguments
        ttk.Label(script_frame, text="Arguments (space-separated):").pack(anchor="w", pady=(5, 0))
        args_entry = ttk.Entry(script_frame)
        args_entry.pack(fill="x", pady=(0, 5))
        
        # Options
        options_frame = ttk.Frame(script_frame)
        options_frame.pack(fill="x", pady=5)
        
        run_as_root = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Run as root", variable=run_as_root).pack(side="left", padx=5)
        
        save_to_device = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Save to device", variable=save_to_device).pack(side="left", padx=5)
        
        # Output area
        output_frame = ttk.LabelFrame(dialog, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        output_text = tk.Text(output_frame, height=10, state="disabled", font=("Courier", 10))
        output_text.pack(fill="both", expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        def run_script():
            script = script_editor.get('1.0', tk.END).strip()
            if not script:
                messagebox.showerror("Error", "Please enter or load a script")
                return
                
            args = args_entry.get().strip()
            use_root = run_as_root.get()
            save_script = save_to_device.get()
            
            # Disable buttons during execution
            run_btn.config(state="disabled")
            save_btn.config(state="disabled")
            clear_btn.config(state="disabled")
            
            # Clear previous output
            output_text.config(state="normal")
            output_text.delete('1.0', tk.END)
            output_text.config(state="disabled")
            
            # Run in a separate thread to prevent UI freeze
            def execute_script():
                try:
                    serial = self.device_info.get("serial", "")
                    adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                    
                    # Save script to a temporary file
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp:
                        tmp.write(script)
                        tmp_path = tmp.name
                    
                    try:
                        # Push script to device
                        device_script_path = f"/data/local/tmp/{os.path.basename(tmp_path)}"
                        cmd = [adb_cmd, "-s", serial, "push", tmp_path, device_script_path]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if result.returncode != 0:
                            raise Exception(f"Failed to push script: {result.stderr}")
                        
                        # Make script executable
                        cmd = [adb_cmd, "-s", serial, "shell", "chmod", "755", device_script_path]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if result.returncode != 0:
                            raise Exception(f"Failed to make script executable: {result.stderr}")
                        
                        # Build the command to execute
                        shell_cmd = f"sh {device_script_path}"
                        if args:
                            shell_cmd += f" {args}"
                            
                        if use_root:
                            shell_cmd = f"su -c '{shell_cmd}'"
                        
                        # Execute the script
                        cmd = [adb_cmd, "-s", serial, "shell", shell_cmd]
                        
                        # Show the command being executed
                        output_text.config(state="normal")
                        output_text.insert(tk.END, f"$ {' '.join(cmd)}\n\n")
                        output_text.config(state="disabled")
                        output_text.see(tk.END)
                        
                        # Run the command and capture output in real-time
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        # Read output in real-time
                        for line in process.stdout:
                            output_text.config(state="normal")
                            output_text.insert(tk.END, line)
                            output_text.see(tk.END)
                            output_text.config(state="disabled")
                            output_text.update()
                        
                        # Wait for the process to complete
                        process.wait()
                        
                        # Clean up if not saving
                        if not save_script:
                            cmd = [adb_cmd, "-s", serial, "shell", "rm", device_script_path]
                            subprocess.run(cmd, capture_output=True)
                        
                    finally:
                        # Clean up local temp file
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                        
                except Exception as e:
                    output_text.config(state="normal")
                    output_text.insert(tk.END, f"\nError: {str(e)}\n")
                    output_text.see(tk.END)
                    output_text.config(state="disabled")
                
                # Re-enable buttons
                dialog.after(100, lambda: [
                    run_btn.config(state="normal"),
                    save_btn.config(state="normal"),
                    clear_btn.config(state="normal")
                ])
            
            # Start the execution in a separate thread
            threading.Thread(target=execute_script, daemon=True).start()
        
        def save_script():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".sh",
                filetypes=[("Shell Scripts", "*.sh"), ("All Files", "*.*")]
            )
            if file_path:
                try:
                    with open(file_path, 'w') as f:
                        f.write(script_editor.get('1.0', tk.END))
                    messagebox.showinfo("Success", f"Script saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save script: {e}")
        
        def clear_script():
            if messagebox.askyesno("Confirm", "Clear the script editor?"):
                script_editor.delete('1.0', tk.END)
        
        run_btn = ttk.Button(btn_frame, text="Run Script", command=run_script)
        run_btn.pack(side="left", padx=5)
        
        save_btn = ttk.Button(btn_frame, text="Save Script", command=save_script)
        save_btn.pack(side="left", padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear", command=clear_script)
        clear_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        # Focus on script editor
        script_editor.focus_set()

    def _check_lock_screen_status(self):
        """Check the lock screen status and security settings"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Check if lock screen is enabled
            cmd = [adb_cmd, "-s", serial, "shell", "locksettings", "get-disabled"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                messagebox.showerror("Error", f"Failed to get lock screen status: {result.stderr}")
                return
                
            is_disabled = "true" in result.stdout.lower()
            
            if is_disabled:
                messagebox.showinfo("Lock Screen Status", "Lock screen is DISABLED (no security)")
                return
                
            # Lock screen is enabled, get more details
            msg = "Lock screen is ENABLED\n\n"
            
            # Get lock screen type
            cmd = [adb_cmd, "-s", serial, "shell", "locksettings", "get-keyguard-secure"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and "true" in result.stdout.lower():
                msg += "Security Type: Secure (PIN/Pattern/Password)\n"
                
                # Try to get the type of security
                cmd = [adb_cmd, "-s", serial, "shell", "locksettings", "get-locktype"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    lock_type = result.stdout.strip()
                    if lock_type:
                        msg += f"Lock Type: {lock_type.upper()}\n"
                        
                # Get password complexity requirements
                cmd = [adb_cmd, "-s", serial, "shell", "settings", "get", "secure", "lock_pattern_visible_pattern"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and "1" in result.stdout:
                    msg += "Visible Pattern: ENABLED (less secure)\n"
                    
                # Check if Smart Lock is enabled
                cmd = [adb_cmd, "-s", serial, "shell", "settings", "secure", "get", "lock_screen_owner_info_enabled"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and "1" in result.stdout:
                    msg += "Owner Info on Lock Screen: ENABLED\n"
                    
                # Check if lock after timeout is set
                cmd = [adb_cmd, "-s", serial, "shell", "settings", "secure", "get", "lock_screen_lock_after_timeout"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip().isdigit():
                    timeout_ms = int(result.stdout.strip())
                    if timeout_ms > 0:
                        msg += f"Auto-lock after: {timeout_ms/1000} seconds\n"
                    
            else:
                msg += "Security Type: Swipe (no security)\n"
                
            # Check if device is encrypted
            cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.crypto.state"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and "encrypted" in result.stdout.lower():
                msg += "\nDevice is ENCRYPTED"
            else:
                msg += "\nDevice is NOT encrypted (less secure)"
                
            messagebox.showinfo("Lock Screen Status", msg)
            
        except Exception as e:
            logging.error(f"Error checking lock screen status: {e}")
            messagebox.showerror("Error", f"Failed to check lock screen status: {e}")

    def _check_encryption_status(self):
        """Check the encryption status of the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        serial = self.device_info.get("serial", "")
        adb_cmd = self.adb_path if IS_WINDOWS else "adb"
        
        try:
            # Check if device is encrypted
            cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.crypto.state"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                messagebox.showerror("Error", f"Failed to get encryption status: {result.stderr}")
                return
                
            crypto_state = result.stdout.strip().lower()
            
            # Get encryption type if encrypted
            if crypto_state == "encrypted":
                cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.crypto.type"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                crypto_type = result.stdout.strip() if result.returncode == 0 else "unknown"
                
                # Check if file-based encryption is used
                cmd = [adb_cmd, "-s", serial, "shell", "getprop", "ro.crypto.fde_required"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                fde_required = result.stdout.strip() if result.returncode == 0 else ""
                
                # Build the message
                msg = "Device is ENCRYPTED\n"
                msg += f"Encryption type: {crypto_type.upper()}\n"
                
                if fde_required:
                    msg += f"File-based encryption required: {fde_required}\n"
                    
                # Check if the device is secure (lock screen set)
                cmd = [adb_cmd, "-s", serial, "shell", "locksettings", "get-disabled"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and "false" in result.stdout.lower():
                    msg += "Device is secured with a lock screen\n"
                else:
                    msg += "Warning: Device is not secured with a lock screen\n"
                    
                messagebox.showinfo("Encryption Status", msg)
            else:
                messagebox.showinfo("Encryption Status", "Device is NOT encrypted")
                
        except Exception as e:
            logging.error(f"Error checking encryption status: {e}")
            messagebox.showerror("Error", f"Failed to check encryption status: {e}")

    def _monkey_testing_dialog(self):
        """Show dialog for running Monkey tests on the device"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Monkey Testing")
        dialog.geometry("700x650")
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 700) // 2
        y_pos = (self.winfo_screenheight() - 650) // 2
        dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()
        
        # Main container
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Test configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Test Configuration", padding=10)
        config_frame.pack(fill="x", pady=5)
        
        # Package selection
        ttk.Label(config_frame, text="Target Package:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        pkg_var = tk.StringVar()
        pkg_combo = ttk.Combobox(config_frame, textvariable=pkg_var, state="readonly")
        pkg_combo.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        
        # Event count
        ttk.Label(config_frame, text="Event Count:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        event_var = tk.StringVar(value="1000")
        ttk.Spinbox(config_frame, from_=100, to=100000, increment=100, textvariable=event_var, width=10).grid(
            row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Throttle (ms)
        ttk.Label(config_frame, text="Throttle (ms):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        throttle_var = tk.StringVar(value="400")
        ttk.Spinbox(config_frame, from_=0, to=5000, increment=100, textvariable=throttle_var, width=10).grid(
            row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Seed value
        ttk.Label(config_frame, text="Seed (0=random):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        seed_var = tk.StringVar(value="0")
        ttk.Spinbox(config_frame, from_=0, to=999999, textvariable=seed_var, width=10).grid(
            row=3, column=1, sticky="w", padx=5, pady=5)
        
        # Categories frame
        cat_frame = ttk.LabelFrame(main_frame, text="Categories", padding=10)
        cat_frame.pack(fill="x", pady=5)
        
        # Category checkboxes
        categories = [
            ("MAIN", "android.intent.category.LAUNCHER"),
            ("HOME", "android.intent.category.HOME"),
            ("DEFAULT", "android.intent.category.DEFAULT"),
            ("BROWSABLE", "android.intent.category.BROWSABLE"),
            ("MONKEY", "android.intent.category.MONKEY")
        ]
        
        cat_vars = {}
        for i, (name, pkg) in enumerate(categories):
            var = tk.BooleanVar()
            cat_vars[pkg] = var
            ttk.Checkbutton(cat_frame, text=name, variable=var).grid(
                row=i//3, column=i%3, sticky="w", padx=5, pady=2)
        
        # Events frame
        event_frame = ttk.LabelFrame(main_frame, text="Events", padding=10)
        event_frame.pack(fill="x", pady=5)
        
        # Event percentages
        events = [
            ("Touch Events (%)", "touch", 15, 0, 100),
            ("Motion Events (%)", "motion", 0, 0, 100),
            ("Trackball Events (%)", "trackball", 0, 0, 100),
            ("Nav Events (%)", "nav", 25, 0, 100),
            ("Major Nav Events (%)", "majornav", 15, 0, 100),
            ("System Keys (%)", "syskeys", 0, 0, 100),
            ("App Switch Events (%)", "appswitch", 2, 0, 100),
            ("Any Events (%)", "anyevent", 13, 0, 100)
        ]
        
        event_vars = {}
        for i, (label, name, default, min_val, max_val) in enumerate(events):
            ttk.Label(event_frame, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=2)
            var = tk.StringVar(value=str(default))
            event_vars[name] = var
            ttk.Spinbox(event_frame, from_=min_val, to=max_val, textvariable=var, width=5).grid(
                row=i, column=1, sticky="w", padx=5, pady=2)
        
        # Options frame
        opt_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
        opt_frame.pack(fill="x", pady=5)
        
        # Option checkboxes
        opt_vars = {
            "ignore_crashes": tk.BooleanVar(value=True),
            "ignore_timeouts": tk.BooleanVar(value=True),
            "ignore_security_exceptions": tk.BooleanVar(value=True),
            "kill_process_after_error": tk.BooleanVar(value=True),
            "hprof": tk.BooleanVar(),
            "ignore_native_crashes": tk.BooleanVar(),
            "monitor_native_crashes": tk.BooleanVar(),
            "pct_rotation": tk.BooleanVar()
        }
        
        options = [
            ("Ignore Crashes", "ignore_crashes"),
            ("Ignore Timeouts", "ignore_timeouts"),
            ("Ignore Security Exceptions", "ignore_security_exceptions"),
            ("Kill Process After Error", "kill_process_after_error"),
            ("Generate HPROF File", "hprof"),
            ("Ignore Native Crashes", "ignore_native_crashes"),
            ("Monitor Native Crashes", "monitor_native_crashes"),
            ("Allow Rotation", "pct_rotation")
        ]
        
        for i, (label, name) in enumerate(options):
            ttk.Checkbutton(opt_frame, text=label, variable=opt_vars[name]).grid(
                row=i//2, column=i%2, sticky="w", padx=5, pady=2)
        
        # Output frame
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, pady=5)
        
        # Output text area
        output_text = tk.Text(output_frame, wrap="word", height=10)
        output_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=output_text.yview)
        output_text.config(yscrollcommand=output_scroll.set)
        
        output_text.pack(side="left", fill="both", expand=True)
        output_scroll.pack(side="right", fill="y")
        
        # Button frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        # Load installed packages
        def load_packages():
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Get list of installed packages
                result = subprocess.run(
                    [adb_cmd, "-s", serial, "shell", "pm list packages -3"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                packages = [line.split(":")[1].strip() for line in result.stdout.splitlines() if line.startswith("package:")]
                pkg_combo["values"] = packages
                
                if packages:
                    pkg_combo.current(0)
                
                output_text.insert("end", f"Loaded {len(packages)} user-installed packages.\n")
                output_text.see("end")
                
            except subprocess.CalledProcessError as e:
                output_text.insert("end", f"Error loading packages: {e.stderr}\n")
                output_text.see("end")
            except Exception as e:
                output_text.insert("end", f"Error: {str(e)}\n")
                output_text.see("end")
        
        # Run monkey test
        def run_test():
            if not pkg_var.get():
                messagebox.showerror("Error", "Please select a package to test.")
                return
                
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Build the monkey command
                cmd = [adb_cmd, "-s", serial, "shell", "monkey", "-p", pkg_var.get()]
                
                # Add event percentages
                for name, var in event_vars.items():
                    try:
                        val = int(var.get())
                        if val > 0:
                            cmd.extend(["--pct-{}".format(name), str(val)])
                    except ValueError:
                        pass
                
                # Add categories
                categories = [pkg for pkg, var in cat_vars.items() if var.get()]
                if categories:
                    cmd.extend(["-c"] + [",".join(categories)])
                
                # Add options
                if opt_vars["ignore_crashes"].get():
                    cmd.append("--ignore-crashes")
                if opt_vars["ignore_timeouts"].get():
                    cmd.append("--ignore-timeouts")
                if opt_vars["ignore_security_exceptions"].get():
                    cmd.append("--ignore-security-exceptions")
                if opt_vars["kill_process_after_error"].get():
                    cmd.append("--kill-process-after-error")
                if opt_vars["hprof"].get():
                    cmd.append("--hprof")
                if opt_vars["ignore_native_crashes"].get():
                    cmd.append("--ignore-native-crashes")
                if opt_vars["monitor_native_crashes"].get():
                    cmd.append("--monitor-native-crashes")
                if opt_vars["pct_rotation"].get():
                    cmd.extend(["--pct-rotation", "10"])
                
                # Add throttle and seed
                try:
                    throttle = int(throttle_var.get())
                    if throttle > 0:
                        cmd.extend(["--throttle", str(throttle)])
                except ValueError:
                    pass
                
                try:
                    seed = int(seed_var.get())
                    if seed > 0:
                        cmd.extend(["-s", str(seed)])
                except ValueError:
                    pass
                
                # Add event count (required)
                try:
                    events = int(event_var.get())
                    cmd.append(str(events))
                except ValueError:
                    messagebox.showerror("Error", "Invalid event count.")
                    return
                
                # Add verbose output
                cmd.append("-v")
                
                # Display the command
                output_text.insert("end", "Running command: " + " ".join(cmd) + "\n")
                output_text.see("end")
                
                # Run the command in a separate thread
                def run_monkey():
                    try:
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        # Read output in real-time
                        for line in process.stdout:
                            output_text.insert("end", line)
                            output_text.see("end")
                            output_text.update_idletasks()
                        
                        process.wait()
                        output_text.insert("end", "\nMonkey test completed.\n")
                        output_text.see("end")
                        
                    except Exception as e:
                        output_text.insert("end", f"Error: {str(e)}\n")
                        output_text.see("end")
                    
                    run_btn.config(state="normal")
                    stop_btn.config(state="disabled")
                
                # Disable run button and enable stop button
                run_btn.config(state="disabled")
                stop_btn.config(state="normal")
                
                # Clear previous output
                output_text.delete(1.0, "end")
                
                # Start monkey in a separate thread
                import threading
                thread = threading.Thread(target=run_monkey, daemon=True)
                thread.start()
                
            except Exception as e:
                output_text.insert("end", f"Error: {str(e)}\n")
                output_text.see("end")
        
        # Stop monkey test
        def stop_test():
            try:
                serial = self.device_connected.get("serial", "")
                adb_cmd = self.adb_path if IS_WINDOWS else "adb"
                
                # Kill any running monkey process
                subprocess.run(
                    [adb_cmd, "-s", serial, "shell", "pkill -l 9 com.android.commands.monkey"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                output_text.insert("end", "\nMonkey test stopped by user.\n")
                output_text.see("end")
                
            except Exception as e:
                output_text.insert("end", f"Error stopping monkey: {str(e)}\n")
                output_text.see("end")
            finally:
                run_btn.config(state="normal")
                stop_btn.config(state="disabled")
        
        # Buttons
        ttk.Button(btn_frame, text="Load Packages", command=load_packages).pack(side="left", padx=5)
        run_btn = ttk.Button(btn_frame, text="Run Test", command=run_test)
        run_btn.pack(side="left", padx=5)
        stop_btn = ttk.Button(btn_frame, text="Stop Test", command=stop_test, state="disabled")
        stop_btn.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Output", command=lambda: output_text.delete(1.0, "end")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        # Load packages on dialog open
        dialog.after(100, load_packages)
        
        # Set focus on dialog
        dialog.focus_set()
    
    def _check_root_status(self):
        """Check if the device is rooted"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        try:
            serial = self.device_connected.get("serial", "")
            adb_cmd = self.adb_path if IS_WINDOWS else "adb"
            
            # Check for su binary
            result = subprocess.run(
                [adb_cmd, "-s", serial, "shell", "which su"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and "/su" in result.stdout:
                messagebox.showinfo("Root Status", "Device is rooted!")
            else:
                # Try another method to check for root
                result = subprocess.run(
                    [adb_cmd, "-s", serial, "shell", "su -c 'echo Root check'", "2>&1"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if "not found" in result.stderr or "permission denied" in result.stderr:
                    messagebox.showinfo("Root Status", "Device is not rooted or root access is not properly configured.")
                else:
                    messagebox.showinfo("Root Status", "Device is rooted!")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check root status: {str(e)}")
            messagebox.showerror("Error", f"Failed to check root status: {e}")

    def _check_appops_dialog(self):
        """Show dialog to check AppOps for a package"""
        if not self.device_connected:
            messagebox.showinfo("Not Connected", "Please connect to a device first.")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Check AppOps")
        dialog.geometry("600x400")
        
        # Center the window
        x_pos = (self.winfo_screenwidth() - 600) // 2
        y_pos = (self.winfo_screenheight() - 400) // 2
        dialog.geometry(f"+{x_pos}+{y_pos}")
        
        # Package name entry
        ttk.Label(dialog, text="Package Name:").pack(pady=(10, 5), padx=10, anchor="w")
        pkg_entry = ttk.Entry(dialog)
        pkg_entry.pack(fill="x", padx=10, pady=5)
        
        # Output area
        ttk.Label(dialog, text="AppOps Status:").pack(pady=(10, 5), padx=10, anchor="w")
        output_text = tk.Text(dialog, height=15)
        output_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        def check_appops():
            pkg = pkg_entry.get().strip()
            if not pkg:
                messagebox.showerror("Error", "Please enter a package name")
                return
                
            serial = self.device_info.get("serial", "")
            adb_cmd = self.adb_path if IS_WINDOWS else "adb"
            
            try:
                cmd = [adb_cmd, "-s", serial, "shell", "appops", "get", pkg]
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                output_text.delete(1.0, tk.END)
                if process.returncode == 0:
                    output_text.insert(tk.END, f"AppOps for {pkg}:\n")
                    output_text.insert(tk.END, process.stdout)
                else:
                    output_text.insert(tk.END, f"Error: {process.stderr}")
            except Exception as e:
                output_text.insert(tk.END, f"Error: {str(e)}")
        
        ttk.Button(btn_frame, text="Check", command=check_appops).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        # Focus on package entry
        pkg_entry.focus_set()


# For testing the module independently
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Android Tools Module Test")
    root.geometry("700x800")

    app = AndroidToolsModule(root)
    app.pack(expand=True, fill="both")

    root.mainloop()
