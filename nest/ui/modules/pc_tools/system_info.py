#!/usr/bin/env python3
"""
System Info Tab for PC Tools

Provides comprehensive system information gathering and display capabilities,
with RepairDesk ticket integration for reporting.
"""

import os
import sys
import logging
import threading
import datetime
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional

# Import utilities
from nest.utils.system_utils import get_system_info, register_info_callback, unregister_info_callback
from nest.utils.snapshot_logger import SnapshotLogger
from nest.utils.ticket_context import TicketContext

class SystemInfoTab(ttk.Frame):
    """System Information tab for PC Tools module."""
    
    def __init__(self, parent, shared_state):
        """Initialize the System Info tab.
        
        Args:
            parent: Parent widget
            shared_state: Shared state dictionary
        """
        super().__init__(parent)
        self.parent = parent
        self.shared_state = shared_state
        
        # Initialize state variables
        self.system_info = {}
        self.drives_list = []
        self.health_indicators = {}
        self.last_refresh_time = None
        self.callback_registered = False
        
        # Initialize colors
        self.colors = self.get_colors_from_shared_state()
        
        # Initialize ticket context for RepairDesk integration
        # Get API key from shared state if available
        api_key = None
        store_slug = None

        # Detect BIOS information
        self.bios_info = self.detect_bios_info()

        if 'repairdesk' in self.shared_state:
            api_key = self.shared_state['repairdesk'].get('api_key')
            store_slug = self.shared_state['repairdesk'].get('store_slug')
        
        # Initialize the ticket context, which will load from config if no API key provided
        self.ticket_context = TicketContext(api_key, store_slug)
        
        # Ensure that the client is initialized
        if not self.ticket_context.client:
            self.ticket_context.init_client()  # Will attempt to load from config
        
        # Initialize snapshot logger
        self.snapshot_logger = SnapshotLogger()
        
        # Create UI components
        self.create_widgets()
        
        # Bind destroy event to clean up callbacks
        self.bind("<Destroy>", self._on_destroy)
        
        # Load system information on startup
        self.load_system_info()
    
    def detect_bios_info(self) -> Dict[str, str]:
        """Detect BIOS information using multiple methods.

        Returns:
            Dict containing BIOS details like vendor, version, release date, etc.
        """
        bios_info = {
            'vendor': 'Unknown',
            'version': 'Unknown',
            'release_date': 'Unknown',
            'mode': 'Unknown'
        }

        # List of methods to try for BIOS detection
        detection_methods = [
            self._detect_bios_dmidecode,
            self._detect_bios_sysfs,
            self._detect_bios_proc
        ]

        for method in detection_methods:
            try:
                result = method()
                if any(result.values()):
                    bios_info.update(result)
                    break
            except Exception as e:
                logging.warning(f'BIOS detection method failed: {method.__name__}, Error: {e}')

        return bios_info

    def _detect_bios_dmidecode(self) -> Dict[str, str]:
        """Detect BIOS info using dmidecode."""
        import subprocess
        
        bios_info = {
            'vendor': 'Unknown',
            'version': 'Unknown',
            'release_date': 'Unknown',
            'mode': 'Unknown'
        }

        try:
            # Try without sudo first
            result = subprocess.run(
                ['dmidecode', '-t', 'bios'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Vendor:' in line:
                        bios_info['vendor'] = line.split(':')[1].strip()
                    elif 'Version:' in line:
                        bios_info['version'] = line.split(':')[1].strip()
                    elif 'Release Date:' in line:
                        bios_info['release_date'] = line.split(':')[1].strip()
                    elif 'UEFI is supported' in line:
                        bios_info['mode'] = 'UEFI'
                    elif 'Legacy is supported' in line:
                        bios_info['mode'] = 'Legacy BIOS'

        except Exception:
            pass

        return bios_info

    def _detect_bios_sysfs(self) -> Dict[str, str]:
        """Detect BIOS info from sysfs."""
        bios_info = {
            'vendor': 'Unknown',
            'version': 'Unknown',
            'release_date': 'Unknown',
            'mode': 'Unknown'
        }

        try:
            # Check BIOS vendor
            with open('/sys/class/dmi/id/bios_vendor', 'r') as f:
                bios_info['vendor'] = f.read().strip()

            # Check BIOS version
            with open('/sys/class/dmi/id/bios_version', 'r') as f:
                bios_info['version'] = f.read().strip()

            # Check BIOS date
            with open('/sys/class/dmi/id/bios_date', 'r') as f:
                bios_info['release_date'] = f.read().strip()

        except Exception:
            pass

        return bios_info

    def _detect_bios_proc(self) -> Dict[str, str]:
        """Detect BIOS info from /proc."""
        bios_info = {
            'vendor': 'Unknown',
            'version': 'Unknown',
            'release_date': 'Unknown',
            'mode': 'Unknown'
        }

        try:
            # Check BIOS mode from kernel cmdline
            with open('/proc/cmdline', 'r') as f:
                cmdline = f.read()
                if 'efi' in cmdline.lower():
                    bios_info['mode'] = 'UEFI'
                else:
                    bios_info['mode'] = 'Legacy BIOS'

        except Exception:
            pass

        return bios_info

    def get_colors_from_shared_state(self):
        """Get colors from shared state or use defaults."""
        if hasattr(self.parent, "master") and hasattr(self.parent.master, "colors"):
            return self.parent.master.colors
        elif "colors" in self.shared_state:
            return self.shared_state["colors"]
        else:
            return {
                "primary": "#017E84",  # RepairDesk teal
                "secondary": "#4CAF50",
                "warning": "#F44336",
                "background": "#FAFAFA",
                "card_bg": "#FFFFFF",
                "text_primary": "#212121",
                "text_secondary": "#757575",
            }
    
    def create_widgets(self):
        """Create the UI components for the System Info tab."""
        # Create top frame for RepairDesk ticket entry
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        # RepairDesk ticket input
        ticket_frame = ttk.Frame(top_frame)
        ticket_frame.pack(side="left", fill="x", expand=True)
        
        ttk.Label(ticket_frame, text="RepairDesk Ticket:").pack(side="left", padx=(0, 5))
        self.ticket_entry = ttk.Entry(ticket_frame, width=15)
        self.ticket_entry.pack(side="left", padx=5)
        
        # Pre-fill ticket if available in shared state
        if self.shared_state.get("current_ticket"):
            self.ticket_entry.insert(0, self.shared_state["current_ticket"])
        
        # Upload button
        ttk.Button(
            ticket_frame, 
            text="Upload System Info", 
            command=self.upload_system_info_to_repairdesk,
            width=24  # Increased width to prevent text cut-off
        ).pack(side="left", padx=5)
        
        # Refresh button directly in top frame
        ttk.Button(
            top_frame, 
            text="Refresh System Information", 
            command=self.load_system_info,
            width=26  # Increased width to prevent text cut-off
        ).pack(side="right", padx=5)
        
        # Add data source indication label
        data_source_frame = ttk.Frame(top_frame)
        data_source_frame.pack(side="right", padx=20)
        
        self.data_source_var = tk.StringVar(value="Data Source: Local System")
        ttk.Label(
            data_source_frame, 
            textvariable=self.data_source_var,
            foreground=self.colors["text_secondary"],
            font=("Segoe UI", 8)
        ).pack(side="right")
        
        # Create main content frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create a horizontal layout for system info and health
        h_layout_frame = ttk.Frame(main_frame)
        h_layout_frame.pack(fill="both", expand=True, pady=5)
        
        # Left column for system overview
        left_column = ttk.Frame(h_layout_frame)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Right column for health indicators
        right_column = ttk.Frame(h_layout_frame)
        right_column.pack(side="right", fill="y", padx=(5, 0), pady=5, ipadx=10, ipady=5)
        
        # Create the system overview section in left column
        self.create_system_overview(left_column)
        
        # Create health section in right column
        self.create_health_section(right_column)
        
        # Create scrollable frame for storage below the horizontal layout
        storage_frame = ttk.Frame(main_frame)
        storage_frame.pack(fill="both", expand=True, pady=10)
        
        # Create storage section
        self.create_storage_section(storage_frame)
    
    def on_canvas_configure(self, event):
        """Handle canvas resize events."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def create_system_overview(self, parent):
        """Create the system overview section.
        
        Args:
            parent: Parent widget
        """
        overview_frame = ttk.LabelFrame(parent, text="System Overview")
        overview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # System info grid
        self.system_info_vars = {}
        self.system_info_labels = {}
        
        info_fields = [
            ("Operating System", "os"),
            ("Kernel Version", "kernel"),
            ("System Model", "model"),
            ("Serial Number", "serial_number"),
            ("Processor", "cpu"),
            ("Memory", "memory_details"),
            ("Graphics", "graphics"),
            ("BIOS Details", "bios_details"),
            ("Battery", "battery_details"),
            ("Available Updates", "updates_available"),
            ("IP Address", "ip_address"),
            ("Hostname", "hostname"),
            ("Boot Info", "boot_info"),
        ]
        
        # Add a frame for the grid to ensure proper layout
        grid_frame = ttk.Frame(overview_frame)
        grid_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Configure grid column weights
        grid_frame.columnconfigure(0, weight=1)  # Label column
        grid_frame.columnconfigure(1, weight=4)  # Value column
        
        for i, (label_text, key) in enumerate(info_fields):
            label = ttk.Label(grid_frame, text=f"{label_text}:", style="Card.TLabel")
            label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
            
            self.system_info_vars[key] = tk.StringVar(value="Loading...")
            value_label = ttk.Label(grid_frame, textvariable=self.system_info_vars[key], style="Card.TLabel")
            value_label.grid(row=i, column=1, sticky="w", padx=5, pady=2)
            
            self.system_info_labels[key] = (label, value_label)
    
    def create_storage_section(self, parent):
        """Create the storage devices section.
        
        Args:
            parent: Parent widget
        """
        # Create a very tall frame for the Storage Devices section
        storage_frame = ttk.Frame(parent)
        storage_frame.pack(fill="both", padx=5, pady=10)
        
        # Add the label separately
        label = ttk.Label(storage_frame, text="Storage Devices", font=("Arial", 12, "bold"))
        label.pack(anchor="w", padx=5, pady=(0, 10))
        
        # Create a large fixed-height frame for the table
        table_frame = ttk.Frame(storage_frame, height=200, relief="groove", borderwidth=1)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        table_frame.pack_propagate(False)  # Critical to maintain the fixed height
        
        # Create a frame for the header row
        header_frame = ttk.Frame(table_frame, height=40)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)  # Fixed-height header
        
        # Define column structure
        columns = [
            {"name": "Model", "display": "Drive Model", "width": 250, "anchor": "w"},
            {"name": "Size", "display": "Size (GB)", "width": 100, "anchor": "center"},
            {"name": "Type", "display": "Type", "width": 100, "anchor": "center"},
            {"name": "Used", "display": "Used %", "width": 100, "anchor": "center"},
            {"name": "Status", "display": "Health", "width": 150, "anchor": "center"}
        ]
        
        # Add header labels
        for i, col in enumerate(columns):
            header = ttk.Label(header_frame, text=col["display"], 
                            background="#4a6984", foreground="white",
                            font=("Arial", 11, "bold"),
                            anchor="center", relief="raised", borderwidth=1)
            header.place(x=sum([c["width"] for c in columns[:i]]), y=0, 
                     width=col["width"], height=40)
        
        # Create a scrollable frame for data rows
        data_container = ttk.Frame(table_frame)
        data_container.pack(fill="both", expand=True)
        
        # Add scrollbar
        y_scrollbar = ttk.Scrollbar(data_container, orient="vertical")
        y_scrollbar.pack(side="right", fill="y")
        
        # Create canvas for scrolling
        canvas = tk.Canvas(data_container, yscrollcommand=y_scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        y_scrollbar.config(command=canvas.yview)
        
        # Create frame for data
        self.data_frame = ttk.Frame(canvas)
        data_window = canvas.create_window((0, 0), window=self.data_frame, anchor="nw")
        
        # Configure canvas scrolling
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_canvas_configure(event):
            canvas.itemconfig(data_window, width=event.width)
        
        self.data_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Store column config for later use
        self.storage_columns = columns
        self.current_row = 0
        
        # No need for column headings - already defined above
        
        # Column widths are defined in the columns list above
        
        # No need for additional treeview styling as we're using our own custom table implementation
        
        # No need for additional containers - the treeview handles everything

    def create_health_section(self, parent):
        """Create the system health section.
        
        Args:
            parent: Parent widget
        """
        health_frame = ttk.LabelFrame(parent, text="System Health")
        health_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Health indicators grid
        health_indicators = [
            ("CPU Load", "cpu_health"),
            ("Memory Usage", "memory_health"),
            ("Disk Space", "disk_health"),
            ("Temperature", "temp_health"),
        ]
        
        self.health_vars = {}
        self.health_bars = {}
        
        # Create inner frame for grid layout
        grid_frame = ttk.Frame(health_frame)
        grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure column widths
        grid_frame.columnconfigure(0, weight=1)  # Label column
        grid_frame.columnconfigure(1, weight=3)  # Progress bar column
        grid_frame.columnconfigure(2, weight=1)  # Status column
        
        for i, (label_text, key) in enumerate(health_indicators):
            ttk.Label(grid_frame, text=f"{label_text}:", style="Card.TLabel").grid(
                row=i, column=0, sticky="w", padx=5, pady=6
            )
            self.health_vars[key] = tk.DoubleVar(value=0)
            progress = ttk.Progressbar(
                grid_frame,
                variable=self.health_vars[key],
                length=180,
                mode="determinate",
                maximum=100,
            )
            progress.grid(row=i, column=1, sticky="ew", padx=5, pady=6)
            self.health_bars[key] = progress
            
            # Status label
            self.health_vars[f"{key}_status"] = tk.StringVar(value="N/A")
            status_label = ttk.Label(grid_frame, textvariable=self.health_vars[f"{key}_status"], style="Card.TLabel")
            status_label.grid(row=i, column=2, sticky="w", padx=5, pady=6)
    
    def load_system_info(self):
        """Load system information."""
        # Update UI to show loading state
        for key in self.system_info_vars:
            self.system_info_vars[key].set("Loading...")
            
        # Run in a separate thread to avoid blocking the UI
        threading.Thread(target=self._load_system_info_thread, daemon=True).start()
    
    def _load_system_info_thread(self):
        """Background thread for loading system information with caching support."""
        try:
            # Check if we have valid cached data
            cache_ttl = self.shared_state.get("_cache_config", {}).get("ttl", 300)  # 5 minutes default
            cache_enabled = self.shared_state.get("_cache_config", {}).get("enabled", True)
            
            current_time = datetime.datetime.now()
            cached_info = self.shared_state.get("system_info", {})
            last_refresh = self.shared_state.get("_timestamps", {}).get("system_info")
            
            # Determine if cache is valid
            cache_valid = False
            if cache_enabled and last_refresh and cached_info:
                # Check if cache is still valid based on TTL
                elapsed_seconds = (current_time - last_refresh).total_seconds()
                cache_valid = elapsed_seconds < cache_ttl
            
            if cache_valid:
                # Use cached data
                logging.info(f"Using cached system information (age: {elapsed_seconds:.1f} seconds)")
                self.after(0, lambda: self.update_status("Loading cached system information..."))
                system_info = cached_info
                # Still update UI but skip the API call
                self.after(0, self._on_system_info_complete)
                return
            
            # Update status while loading fresh data
            self.after(0, lambda: self.update_status("Loading system information..."))
            
            # Register callback for progressive updates
            register_info_callback(self._on_system_info_update)
            self.callback_registered = True
            
            # Get fresh system information (only when needed)
            logging.info("Fetching fresh system information...")
            system_info = get_system_info(force_refresh=True)
            
            # Store initial system info
            self.system_info = system_info
            
            # Do an initial UI update with what we have now
            self.after(0, lambda: self._update_system_info_ui(system_info))
            
            # Update data source indicator
            self.after(0, lambda: self.data_source_var.set("Data Source: Local System"))
            
            # Store in shared state and broadcast the change
            self.shared_state["system_info"] = system_info
            if hasattr(self.parent, "master") and hasattr(self.parent.master, "update_shared_state"):
                self.after(0, lambda: self.parent.master.update_shared_state("system_info", system_info))
            
            # Update refresh time
            self.last_refresh_time = datetime.datetime.now()
            
            # Log success
            logging.info("System information loading started")
            self.after(0, lambda: self.update_status("Loading system components..."))
            
        except Exception as e:
            logging.error(f"Error loading system info: {e}")
            self.after(0, lambda: self.data_source_var.set("Data Source: Error"))
            self.after(0, lambda: messagebox.showerror(
                "Error", f"Failed to load system information: {str(e)}"
            ))
            self.after(0, lambda: self.update_status("Error loading system information"))
            
            # Make sure to unregister callback on error
            if self.callback_registered:
                unregister_info_callback(self._on_system_info_update)
                self.callback_registered = False
                
    def _on_system_info_update(self, key, value):
        """Callback for progressive updates from system_utils.
        
        Args:
            key: The key that was updated
            value: The new value
        """
        try:
            # Only handle specific completion events to avoid too many UI updates
            if key in ["basic_info_loaded", "hardware_info_loaded", "drives_scan_complete", "network_info_loaded", "health_metrics_loaded"]:
                # Update our copy with the latest data
                system_info = self.system_info
                
                # Update UI based on completion stage
                if key == "basic_info_loaded":
                    self.after(0, lambda: self.update_status("Basic system information loaded, getting hardware details..."))
                    self.after(0, lambda: self._update_system_info_ui(system_info))
                    
                elif key == "hardware_info_loaded":
                    self.after(0, lambda: self.update_status("Hardware information loaded, scanning drives..."))
                    self.after(0, lambda: self._update_system_info_ui(system_info))
                    
                elif key == "drives_scan_complete" and "drives" in system_info:
                    self.after(0, lambda: self.update_status("Drive information loaded, checking network..."))
                    self.after(0, lambda: self._update_drives_list(system_info["drives"]))
                    
                elif key == "network_info_loaded":
                    self.after(0, lambda: self.update_status("Network information loaded, checking system health..."))
                    
                elif key == "health_metrics_loaded" and "health" in system_info:
                    self.after(0, lambda: self.update_status("System information loaded successfully"))
                    self.after(0, lambda: self._update_health_indicators(system_info["health"]))
                    
                # Share updates with the rest of the application
                self.shared_state["system_info"] = system_info
                if hasattr(self.parent, "master") and hasattr(self.parent.master, "update_shared_state"):
                    self.after(0, lambda: self.parent.master.update_shared_state("system_info", system_info))
                    
                # If all information is loaded, unregister the callback
                if all(system_info.get(k, False) for k in ["basic_info_loaded", "hardware_info_loaded", "drives_scan_complete", "network_info_loaded", "health_metrics_loaded"]):
                    self.after(0, lambda: self.update_status("All system information loaded successfully"))
                    if self.callback_registered:
                        unregister_info_callback(self._on_system_info_update)
                        self.callback_registered = False
                        
        except Exception as e:
            logging.error(f"Error in system info update callback: {e}")
            
    def _on_destroy(self, event):
        """Clean up callbacks when the frame is destroyed.
        
        Args:
            event: The destroy event
        """
        # Unregister our callback to prevent memory leaks
        if self.callback_registered:
            try:
                unregister_info_callback(self._on_system_info_update)
                self.callback_registered = False
            except Exception as e:
                logging.error(f"Error unregistering system info callback: {e}")
    
    def _update_drives_list(self, drives_data):
        """Update the drives list with new data.
        
        Args:
            drives_data: List of drive dictionaries
        """
        try:
            # Only proceed if the widget exists and is properly initialized
            if not hasattr(self, 'data_frame') or not self.data_frame.winfo_exists():
                logging.warning("Storage devices table widget not ready for update")
                return
            
            # Clear existing rows
            for widget in self.data_frame.winfo_children():
                widget.destroy()
            
            # Reset row counter
            self.current_row = 0
            
            # Add drives from system info
            for drive in drives_data:
                # Extract drive information with fallbacks
                model = (
                    drive.get("model", "") or 
                    drive.get("name", "") or
                    drive.get("device", "") or
                    "Unknown"
                )
                
                # Format the model name - truncate if too long
                if len(model) > 30:
                    model = model[:27] + "..."
                    
                # Handle size - try multiple formats and convert to consistent format
                size_raw = (
                    drive.get("size_gb") or
                    drive.get("total_size") or
                    drive.get("size") or
                    0
                )
                
                # Format the size value for display
                if isinstance(size_raw, (int, float)):
                    size_gb = f"{float(size_raw):.1f}"
                elif isinstance(size_raw, str):
                    # Try to convert to float and format
                    try:
                        size_gb = f"{float(size_raw):.1f}"
                    except ValueError:
                        size_gb = size_raw  # Keep as is if conversion fails
                else:
                    size_gb = str(size_raw)
                
                # Get drive type
                drive_type = drive.get("type", "Unknown")
                
                # Handle used percentage - consolidate multiple possible field names
                used_percent = (
                    drive.get("used_percent") or
                    drive.get("used") or
                    ""
                )
                
                # Handle status - try multiple possible field names
                status = (
                    drive.get("smart_status") or
                    drive.get("status") or
                    drive.get("health") or
                    "Unknown"
                )
                
                # Format status with checkmark for healthy drives
                if status.lower() in ["healthy", "good", "ok", "passed"]:
                    status_text = "Healthy ✓"
                    status_bg = "#e8ffe8"  # Light green background
                    status_fg = "green"
                else:
                    status_text = status
                    status_bg = "white"
                    status_fg = "black"
                
                # Create a tall row - 50 pixels high for better visibility
                row_frame = ttk.Frame(self.data_frame, height=50)
                row_frame.pack(fill="x", expand=True)
                row_frame.pack_propagate(False)  # Keep the fixed height
                
                # Alternate row background color for better readability
                row_bg = "#f5f5f5" if self.current_row % 2 == 0 else "white"
                
                # Add cells for this row
                values = [model, size_gb, drive_type, used_percent, status_text]
                
                for i, col in enumerate(self.storage_columns):
                    # Create cell with proper styling
                    cell_bg = status_bg if i == 4 and "healthy" in status.lower() else row_bg
                    cell_fg = status_fg if i == 4 and "healthy" in status.lower() else "black"
                    
                    cell = ttk.Label(
                        row_frame,
                        text=values[i],
                        background=cell_bg,
                        foreground=cell_fg,
                        font=("Arial", 11),
                        anchor=col["anchor"],
                        borderwidth=1,
                        relief="solid",
                        padding=(10, 10)
                    )
                    
                    # Place cell at correct position and with correct width
                    cell.place(
                        x=sum([c["width"] for c in self.storage_columns[:i]]),
                        y=0,
                        width=col["width"],
                        height=50
                    )
                
                # Increment row counter
                self.current_row += 1
                
        except Exception as e:
            logging.error(f"Error updating drives list: {e}")
            import traceback
            traceback.print_exc()
            # Don't re-raise the exception - continue execution
        
    def _update_health_indicators(self, health):
        """Update the system health indicators.
        
        Args:
            health: Dictionary containing health metrics
        """
        for key, value in health.items():
            if key in self.health_vars:
                # Update progress bar
                self.health_vars[key].set(value.get("value", 0))
                
                # Update status text
                if f"{key}_status" in self.health_vars:
                    status = value.get("status", "N/A")
                    self.health_vars[f"{key}_status"].set(status)
                    
                    # Update progress bar color based on status
                    if key in self.health_bars:
                        if status == "Critical":
                            self.health_bars[key].configure(style="Danger.Horizontal.TProgressbar")
                        elif status == "Moderate":
                            self.health_bars[key].configure(style="Warning.Horizontal.TProgressbar")
                        else:  # Good or Unknown
                            self.health_bars[key].configure(style="Success.Horizontal.TProgressbar")
    
    def upload_system_info_to_repairdesk(self):
        """Upload system information to RepairDesk ticket."""
        # Get ticket number
        ticket_number = self.ticket_entry.get().strip()
        if not ticket_number:
            messagebox.showwarning(
                "Input Error", 
                "Please enter a valid RepairDesk Ticket number."
            )
            return
        
        # Save ticket to shared state and broadcast the change
        self.shared_state["current_ticket"] = ticket_number
        if hasattr(self.parent, "master") and hasattr(self.parent.master, "update_shared_state"):
            self.parent.master.update_shared_state("current_ticket", ticket_number)
        
        # Get system info
        if not self.system_info:
            messagebox.showinfo(
                "No Data", 
                "No system information available. Please refresh first."
            )
            return
        
        # Format for upload using snapshot logger
        technician_name = self.shared_state.get("current_user", {}).get("name", "Unknown")
        system_info_text = self.snapshot_logger.format_system_info(
            self.system_info,
            technician_name=technician_name
        )
        
        # Format the ticket number with T- prefix for consistency in UI
        if isinstance(ticket_number, str) and ticket_number.startswith('T-'):
            numeric_part = ticket_number[2:]
        else:
            numeric_part = ticket_number
        
        # Create properly formatted ticket ID with T- prefix
        formatted_ticket_id = f"T-{numeric_part}"
        
        # Confirm upload with properly formatted ticket ID
        if not messagebox.askyesno(
            "Confirm Upload", 
            f"Upload system information to RepairDesk ticket {formatted_ticket_id}?"
        ):
            return
        
        # Update data source indicator with properly formatted ticket ID
        self.data_source_var.set(f"Data Source: RepairDesk Ticket {formatted_ticket_id}")
        
        # Upload to RepairDesk
        self.after(0, lambda: self.update_status(f"Uploading to RepairDesk ticket {formatted_ticket_id}..."))
        threading.Thread(
            target=self._upload_thread,
            args=(ticket_number, "System Information", system_info_text),
            daemon=True
        ).start()
    
    def _upload_thread(self, ticket_number, title, content):
        """Background thread for uploading to RepairDesk.
        
        Args:
            ticket_number: RepairDesk ticket number
            title: Report title
            content: Report content
        """
        try:
            # Use ticket context to upload
            result = self.ticket_context.upload_to_ticket(
                ticket_number=ticket_number,
                title=title,
                content=content
            )
            
            if result.get("success"):
                self.after(0, lambda: messagebox.showinfo(
                    "Success", 
                    "System information successfully uploaded to RepairDesk."
                ))
                self.after(0, lambda: self.update_status("Ready"))
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Upload Error", 
                    f"Failed to upload to RepairDesk: {result.get('message', 'Unknown error')}"
                ))
                self.after(0, lambda: self.update_status("Error uploading to RepairDesk"))
        except Exception as e:
            logging.error(f"Error uploading to RepairDesk: {e}")
            self.after(0, lambda: messagebox.showerror(
                "Upload Error", 
                f"An error occurred during upload: {str(e)}"
            ))
            self.after(0, lambda: self.update_status("Error uploading to RepairDesk"))
    
    def update_status(self, message):
        """Update status bar with a message.
        
        Args:
            message: Status message
        """
        # Update status in parent if available
        if hasattr(self.parent, "master") and hasattr(self.parent.master, "update_status"):
            self.parent.master.update_status(message)
    
    def refresh_if_needed(self):
        """Refresh system info if necessary."""
        # Check if we need to refresh
        if not self.last_refresh_time:
            # Never loaded, load now
            self.load_system_info()
            return
        
        # Check if it's been more than 5 minutes
        now = datetime.datetime.now()
        if (now - self.last_refresh_time).total_seconds() > 300:  # 5 minutes
            # Ask user if they want to refresh
            if messagebox.askyesno(
                "Refresh System Info", 
                "System information is over 5 minutes old. Refresh now?"
            ):
                self.load_system_info()
    
    def on_system_info_updated(self):
        """Handle updates to system info in shared state."""
        system_info = self.shared_state.get("system_info", {})
        if not system_info:
            return
            
        # Update local copy
        self.system_info = system_info
        
        # Update UI
        self._update_system_info_ui(system_info)
    
    def _update_system_info_ui(self, system_info):
        """Update the UI with system information.
        
        Args:
            system_info: Dictionary containing system information
        """
        # Update each field
        for key, value in system_info.items():
            if key in self.system_info_vars:
                self.system_info_vars[key].set(value)
        
        # Format BIOS details in a single line similar to RAM details
        bios_vendor = system_info.get('bios_vendor', self.bios_info.get('vendor', 'Unknown'))
        bios_version = system_info.get('bios_version', self.bios_info.get('version', 'Unknown'))
        bios_date = system_info.get('bios_release_date', self.bios_info.get('release_date', 'Unknown'))
        bios_mode = system_info.get('bios_mode', self.bios_info.get('mode', 'Unknown'))
        
        # Format as: Vendor | Version | Release Date | Mode
        bios_details = f"{bios_vendor} | {bios_version} | {bios_date} | {bios_mode}"
        if 'bios_details' in self.system_info_vars:
            self.system_info_vars['bios_details'].set(bios_details)
            
        # Combine memory size and RAM details into a single line
        memory_size = system_info.get('memory', 'Unknown')
        ram_details = system_info.get('ram_details', 'Unknown')
        combined_memory_details = f"{memory_size} | {ram_details}"
        if 'memory_details' in self.system_info_vars:
            self.system_info_vars['memory_details'].set(combined_memory_details)
        
        # Combine boot time and boot analysis into a single boot_info field
        boot_time = system_info.get('boot_time', 'Unknown')
        boot_total = system_info.get('boot_analysis', {}).get('total', 'Unknown')
        
        # Combine the boot time and total boot time values
        boot_info = f"{boot_time} | Total: {boot_total}"
        
        if 'boot_info' in self.system_info_vars:
            self.system_info_vars['boot_info'].set(boot_info)
        
        # Format battery information if available
        if 'battery_info' in system_info:
            battery_info = system_info['battery_info']
            model = battery_info.get('model', 'Unknown')
            health = battery_info.get('health', 'Unknown')
            replacement = battery_info.get('replacement_recommended', False)
            
            # Format with warning indicator if replacement is recommended
            if replacement:
                battery_details = f"{model} | Health: {health} | ⚠️ Replacement Recommended"
            else:
                battery_details = f"{model} | Health: {health}"
            
            if 'battery_details' in self.system_info_vars:
                self.system_info_vars['battery_details'].set(battery_details)
        
        # Format available updates information
        if 'available_updates' in system_info:
            updates_count = system_info['available_updates']
            
            # Format with warning indicator if updates are available
            if updates_count > 0:
                updates_text = f"{updates_count} updates available | ⚠️ System update recommended"
            else:
                updates_text = "System up to date"
            
            if 'updates_available' in self.system_info_vars:
                self.system_info_vars['updates_available'].set(updates_text)
        
        # Update drives data if available
        if 'drives' in system_info:
            self._update_drives_list(system_info['drives'])
        
        # Update health indicators if available
        if 'health' in system_info:
            self._update_health_indicators(system_info['health'])
    
    def on_ticket_updated(self):
        """Handle updates to ticket in shared state."""
        ticket_number = self.shared_state.get("current_ticket")
        if ticket_number:
            # Update ticket entry
            self.ticket_entry.delete(0, tk.END)
            self.ticket_entry.insert(0, ticket_number)


# For direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create test app
    root = tk.Tk()
    root.title("System Info Tab Test")
    root.geometry("800x600")
    
    # Create tab with sample shared state
    shared_state = {
        "system_info": {},
        "current_ticket": "T-1234",
        "current_user": {"name": "Test User"}
    }
    
    app = SystemInfoTab(root, shared_state)
    app.pack(fill="both", expand=True)
    
    root.mainloop()
