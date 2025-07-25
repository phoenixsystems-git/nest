#!/usr/bin/env python3
"""
Utilities Tab for PC Tools - Linux-focused

Provides system maintenance and repair utilities specifically optimized for Linux systems.
Includes features like system cleanup, driver management, and disk utilities with enhanced
NVMe support.
"""

# Standard library imports
import os
import sys
import time
import json
import logging
import threading
import datetime
import subprocess
import shutil
from pathlib import Path

# Third-party imports - move inside functions where possible to avoid circular imports
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional, Union
from nest.main import FixedHeaderTreeview

# Try to import optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available, system monitoring features will be limited")

# Try to import Linux-specific modules
try:
    import pyudev
    PYUDEV_AVAILABLE = True
except ImportError:
    PYUDEV_AVAILABLE = False
    logging.warning("pyudev not available, some hardware detection features will be limited")

class UtilitiesTab(ttk.Frame):
    """Utilities tab for PC Tools module with Linux focus."""
    
    def __init__(self, parent, shared_state):
        """Initialize the Utilities tab.
        
        Args:
            parent: Parent widget
            shared_state: Shared state dictionary
        """
        super().__init__(parent)
        self.parent = parent
        self.shared_state = shared_state
        
        # Initialize state variables
        self.temp_stats = {}
        self.running_tasks = {}
        self.task_results = {}
        self.last_refresh_time = None
        
        # Initialize all method attributes to prevent attribute errors
        # These will be replaced by real implementations later but prevent attribute errors
        self.cleanup_temp_files = self._placeholder_method
        self.cleanup_package_cache = self._placeholder_method
        self.refresh_drives_info = self._placeholder_method
        self.refresh_module_list = self._placeholder_method
        self.show_module_details = self._placeholder_method
        self.analyze_selected_drive = self._placeholder_method
        self.show_nvme_details = self._placeholder_method
        
        # Initialize colors
        self.colors = self.get_colors_from_shared_state()
        
        # Create UI components
        self.create_widgets()
        
        # Bind destroy event to clean up any ongoing processes
        self.bind("<Destroy>", self._on_destroy)
        
        # Initialize data
        self.load_data()
        
        # Now replace placeholder methods with real implementations
        self._setup_methods()
        
        # Pack self to fill entire parent frame
        self.pack(fill="both", expand=True)
    
    def get_colors_from_shared_state(self):
        """Get colors from shared state or use defaults."""
        if "colors" in self.shared_state:
            return self.shared_state["colors"]
        else:
            # Default colors (similar to SystemInfoTab)
            return {
                "primary": "#1976D2",  # Blue
                "primary_dark": "#0D47A1",
                "primary_light": "#BBDEFB",
                "secondary": "#43A047",  # Green
                "secondary_dark": "#2E7D32",
                "secondary_light": "#C8E6C9",
                "warning": "#F57C00",    # Orange
                "danger": "#D32F2F",      # Red
                "background": "#F5F5F5",
                "card_bg": "#FFFFFF",
                "text_primary": "#212121",
                "text_secondary": "#757575",
                "border": "#E0E0E0",
                "highlight": "#E3F2FD",
            }
    
    def create_widgets(self):
        """Create the UI components for the Utilities tab."""
        # Main container with scrolling support
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Create a canvas for scrolling
        self.canvas = tk.Canvas(self.main_container, bg=self.colors["background"])
        scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create a frame inside the canvas for content
        self.content_frame = ttk.Frame(self.canvas)
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        # Configure canvas scrolling
        self.content_frame.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # ===== Create Utility Sections =====
        self.create_header(self.content_frame)
        self.create_storage_utilities_section(self.content_frame)
        self.create_system_cleanup_section(self.content_frame)
        self.create_driver_management_section(self.content_frame)
    
    def on_canvas_configure(self, event):
        """Update canvas scrollregion when the content frame changes size."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_resize(self, event):
        """Resize the canvas window when the canvas is resized."""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def create_header(self, parent):
        """Create header section."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        # Title and description
        ttk.Label(
            header_frame, 
            text="Linux System Utilities", 
            font=("Arial", 16, "bold"),
            foreground=self.colors["primary_dark"]
        ).pack(anchor="w")
        
        ttk.Label(
            header_frame,
            text="Maintenance and repair tools for Linux systems",
            foreground=self.colors["text_secondary"]
        ).pack(anchor="w")
        
        ttk.Separator(header_frame).pack(fill="x", pady=10)
    
    def create_storage_utilities_section(self, parent):
        """Create storage utilities section with enhanced NVMe support."""
        frame = self.create_section_frame(parent, "Storage Utilities", "💾")
        
        # Storage devices frame
        storage_frame = ttk.Frame(frame)
        storage_frame.pack(fill="x", padx=10, pady=5)
        
        # Create a treeview for storage devices
        columns = ("device", "mountpoint", "size", "used", "free", "fstype")
        self.drives_tree = FixedHeaderTreeview(storage_frame, columns=columns, show="headings", height=6)
        
        # Define column headings
        self.drives_tree.heading("device", text="Device")
        self.drives_tree.heading("mountpoint", text="Mount Point")
        self.drives_tree.heading("size", text="Size")
        self.drives_tree.heading("used", text="Used")
        self.drives_tree.heading("free", text="Free")
        self.drives_tree.heading("fstype", text="Filesystem Type")
        
        # Define column widths
        self.drives_tree.column("device", width=80)
        self.drives_tree.column("mountpoint", width=120)
        self.drives_tree.column("size", width=80)
        self.drives_tree.column("used", width=100)
        self.drives_tree.column("free", width=80)
        self.drives_tree.column("fstype", width=80)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(storage_frame, orient="vertical", command=self.drives_tree.yview)
        self.drives_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.drives_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        # Add action buttons
        refresh_btn = ttk.Button(
            buttons_frame,
            text="Refresh Drives",
            command=self._real_refresh_drives_info
        )
        refresh_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        analyze_btn = ttk.Button(
            buttons_frame,
            text="Analyze Selected Drive",
            command=self._real_analyze_selected_drive
        )
        analyze_btn.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Additional NVMe-specific button
        nvme_info_btn = ttk.Button(
            buttons_frame,
            text="NVMe Drive Details",
            command=self._real_show_nvme_details
        )
        nvme_info_btn.grid(row=0, column=2, padx=5, pady=5, sticky="w")
    
    def create_system_cleanup_section(self, parent):
        """Create system cleanup section."""
        frame = self.create_section_frame(parent, "System Cleanup", "🧹")
        
        # Add action buttons
        actions_frame = ttk.Frame(frame)
        actions_frame.pack(fill="x", padx=10, pady=5)
        
        # Temp Files Cleanup
        temp_cleanup_btn = ttk.Button(
            actions_frame,
            text="Clean Temporary Files",
            command=self._real_cleanup_temp_files
        )
        temp_cleanup_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Package Cache Cleanup
        pkg_cleanup_btn = ttk.Button(
            actions_frame,
            text="Clean Package Cache",
            command=self._real_cleanup_package_cache
        )
        pkg_cleanup_btn.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Status frame for displaying cleanup results
        self.cleanup_status_frame = ttk.LabelFrame(frame, text="Cleanup Status")
        self.cleanup_status_frame.pack(fill="x", padx=10, pady=5)
        
        # Status text
        self.cleanup_status_text = tk.Text(self.cleanup_status_frame, height=3, wrap="word")
        self.cleanup_status_text.pack(fill="x", padx=5, pady=5)
        self.cleanup_status_text.config(state="disabled")
    
    def create_driver_management_section(self, parent):
        """Create driver management section."""
        frame = self.create_section_frame(parent, "Driver Management", "🔧")
        
        # Driver info frame
        driver_frame = ttk.Frame(frame)
        driver_frame.pack(fill="x", padx=10, pady=5)
        
        # Create a treeview for kernel modules/drivers
        columns = ("module", "size", "used_by", "status")
        self.driver_tree = FixedHeaderTreeview(driver_frame, columns=columns, show="headings", height=5)
        
        # Define column headings
        self.driver_tree.heading("module", text="Module Name")
        self.driver_tree.heading("size", text="Size")
        self.driver_tree.heading("used_by", text="Used By")
        self.driver_tree.heading("status", text="Status")
        
        # Define column widths
        self.driver_tree.column("module", width=150)
        self.driver_tree.column("size", width=80)
        self.driver_tree.column("used_by", width=150)
        self.driver_tree.column("status", width=80)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(driver_frame, orient="vertical", command=self.driver_tree.yview)
        self.driver_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.driver_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        # Add action buttons
        refresh_btn = ttk.Button(
            buttons_frame,
            text="Refresh Module List",
            command=self._real_refresh_module_list
        )
        refresh_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        info_btn = ttk.Button(
            buttons_frame,
            text="Module Details",
            command=self._real_show_module_details
        )
        info_btn.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    
    def create_section_frame(self, parent, title, icon=None):
        """Helper to create a consistent section frame."""
        # Create a frame with a border and background
        section_frame = ttk.LabelFrame(
            parent,
            text=f"{icon} {title}" if icon else title
        )
        section_frame.pack(fill="x", padx=10, pady=5)
        
        return section_frame
    
    def _on_destroy(self, event):
        """Clean up on tab destruction."""
        # Cancel any running tasks
        for task_id, task_info in self.running_tasks.items():
            if "process" in task_info and task_info["process"] is not None:
                try:
                    task_info["process"].terminate()
                except Exception as e:
                    logging.error(f"Error terminating process: {e}")
    
    def load_data(self):
        """Load initial data for the tab."""
        # Refresh drives information
        self.refresh_drives_info()
        
        # Load kernel modules list
        self.refresh_module_list()
        
        # Update last refresh time
        self.last_refresh_time = datetime.datetime.now()
        
    def _placeholder_method(self, *args, **kwargs):
        """Placeholder method to avoid attribute errors during initialization."""
        logging.info("Placeholder method called - real implementation not yet available")
    
    def _setup_methods(self):
        """Set up all the real methods after initialization is complete."""
        # This allows us to prevent attribute errors during initialization
        # while still implementing the real methods eventually
        
        # Define all the real method implementations
        self.cleanup_temp_files = self._real_cleanup_temp_files
        self.cleanup_package_cache = self._real_cleanup_package_cache
        self.refresh_drives_info = self._real_refresh_drives_info
        self.refresh_module_list = self._real_refresh_module_list
        self.show_module_details = self._real_show_module_details
        self.analyze_selected_drive = self._real_analyze_selected_drive
        self.show_nvme_details = self._real_show_nvme_details
    
    def update_status(self, message):
        """Update status bar with a message."""
        # Update status in parent if available
        if hasattr(self.parent, "master") and hasattr(self.parent.master, "update_status"):
            self.parent.master.update_status(message)
    
    def _real_refresh_drives_info(self):
        """Refresh the storage drives information."""
        try:
            # Clear existing items
            for item in self.drives_tree.get_children():
                self.drives_tree.delete(item)
            
            if PSUTIL_AVAILABLE:
                # Get disk partitions using psutil (preferred method)
                partitions = psutil.disk_partitions(all=True)
                
                # Add each partition to the treeview
                for partition in partitions:
                    # Get usage statistics
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        size = f"{usage.total / (1024**3):.2f} GB"
                        used = f"{usage.used / (1024**3):.2f} GB ({usage.percent}%)"
                        free = f"{usage.free / (1024**3):.2f} GB"
                    except PermissionError:
                        size = "N/A"
                        used = "N/A"
                        free = "N/A"
                        
                    # Add to tree
                    self.drives_tree.insert(
                        "", "end",
                        values=(partition.device, partition.mountpoint, size, used, free, partition.fstype)
                    )
            else:
                # Fallback method using df command if psutil is not available
                try:
                    # Run df command to get filesystem information
                    result = subprocess.run(["df", "-h"], capture_output=True, text=True, check=True)
                    lines = result.stdout.strip().split('\n')
                    
                    # Skip the header line
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 6:
                            device = parts[0]
                            size = parts[1]
                            used = parts[2]  # Used space
                            free = parts[3]  # Available space
                            use_percent = parts[4]  # Use percentage
                            mount_point = parts[5]  # Mount point
                            
                            # Get filesystem type using mount command
                            fs_type = "Unknown"
                            try:
                                mount_result = subprocess.run(["mount"], capture_output=True, text=True, check=True)
                                mount_lines = mount_result.stdout.strip().split('\n')
                                for mount_line in mount_lines:
                                    if device in mount_line and f" on {mount_point} " in mount_line:
                                        # Extract filesystem type
                                        type_index = mount_line.find("type")
                                        if type_index > 0:
                                            fs_type = mount_line[type_index + 5:].split()[0]
                                            break
                            except Exception as mount_err:
                                logging.warning(f"Error getting filesystem type: {mount_err}")
                            
                            # Add to tree
                            self.drives_tree.insert(
                                "", "end",
                                values=(device, mount_point, size, f"{used} ({use_percent})", free, fs_type)
                            )
                            
                except subprocess.SubprocessError as cmd_err:
                    logging.error(f"Error running df command: {cmd_err}")
                    self.drives_tree.insert("", "end", values=("Error", "Failed to get drive information", "", "", "", ""))
                    
            self.update_status("Drives information refreshed successfully")
        except Exception as e:
            logging.error(f"Error refreshing drives info: {e}")
            self.update_status(f"Error refreshing drives info: {e}")
    
    def _real_refresh_module_list(self):
        """Refresh the kernel modules/drivers list."""
        try:
            # Clear existing items
            for item in self.driver_tree.get_children():
                self.driver_tree.delete(item)
                
            # Run lsmod command to get module information
            try:
                result = subprocess.run(["lsmod"], capture_output=True, text=True, check=True)
                module_info = result.stdout.strip().split('\n')
                
                # Skip the header line
                for line in module_info[1:]:
                    parts = line.split()
                    if len(parts) >= 3:
                        module_name = parts[0]
                        size = parts[1]
                        used_count = parts[2]
                        used_by = "" if len(parts) < 4 else " ".join(parts[3:])
                        
                        # Add to tree
                        self.driver_tree.insert(
                            "", "end",
                            values=(module_name, f"{int(size):,} bytes", used_by, "Loaded")
                        )
                        
                self.update_status("Module list refreshed successfully")
            except subprocess.CalledProcessError as e:
                logging.error(f"Error running lsmod: {e}")
                self.update_status(f"Error obtaining module list: {e}")
        except Exception as e:
            logging.error(f"Error refreshing module list: {e}")
            self.update_status(f"Error refreshing module list: {e}")
    
    def _real_show_module_details(self):
        """Show detailed information about the selected module."""
        # Get selected module
        selection = self.driver_tree.selection()
        if not selection:
            messagebox.showinfo("Module Details", "Please select a module first.")
            return
            
        # Get module name from the selected item
        item = self.driver_tree.item(selection[0])
        module_name = item['values'][0]
        
        try:
            # Run modinfo command to get detailed information
            result = subprocess.run(["modinfo", module_name], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Create a new window to display the information
                info_window = tk.Toplevel(self)
                info_window.title(f"Module Details: {module_name}")
                info_window.geometry("600x400")
                
                # Create a text widget to display the information
                text = tk.Text(info_window, wrap="word")
                text.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Insert the information
                text.insert("1.0", result.stdout)
                text.config(state="disabled")
                
                # Add a close button
                close_btn = ttk.Button(info_window, text="Close", command=info_window.destroy)
                close_btn.pack(pady=10)
                
                self.update_status(f"Showing details for module {module_name}")
            else:
                messagebox.showerror("Error", f"Could not get information for module {module_name}: {result.stderr}")
        except Exception as e:
            logging.error(f"Error showing module details: {e}")
            messagebox.showerror("Error", f"Error showing module details: {e}")
    
    def _real_cleanup_temp_files(self):
        """Clean up temporary files on the system."""
        try:
            # Update status
            self.cleanup_status_text.config(state="normal")
            self.cleanup_status_text.delete("1.0", tk.END)
            self.cleanup_status_text.insert("1.0", "Cleaning temporary files...\n")
            self.cleanup_status_text.update()
            
            # Common temp directories to clean
            temp_dirs = [
                "/tmp",
                f"/home/{os.getlogin()}/.cache",
                f"/home/{os.getlogin()}/Downloads"
            ]
            
            total_cleaned = 0
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                    try:
                        # Get size before cleaning
                        dir_size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                                     for dirpath, dirnames, filenames in os.walk(temp_dir) 
                                     for filename in filenames 
                                     if os.path.exists(os.path.join(dirpath, filename)))
                        
                        # For system directories like /tmp, we'll only remove files older than 1 day
                        if temp_dir == "/tmp":
                            cutoff_time = time.time() - (86400)  # 24 hours
                            cleaned = 0
                            
                            # Don't traverse too deep in system directories
                            for item in os.listdir(temp_dir):
                                item_path = os.path.join(temp_dir, item)
                                # Skip if it's not a file or if it's a system file
                                if not os.path.isfile(item_path) or item.startswith('.'):
                                    continue
                                    
                                # Check if the file is older than cutoff time
                                try:
                                    if os.path.getmtime(item_path) < cutoff_time:
                                        try:
                                            file_size = os.path.getsize(item_path)
                                            os.remove(item_path)
                                            cleaned += file_size
                                        except (PermissionError, OSError):
                                            # Skip files we don't have permission to remove
                                            pass
                                except OSError:
                                    # Skip files with access issues
                                    pass
                                    
                            total_cleaned += cleaned
                            self.cleanup_status_text.insert(tk.END, 
                                                        f"Cleaned {cleaned / (1024**2):.2f} MB from {temp_dir}\n")
                                
                        # For user directories, ask for confirmation before removing all files
                        elif temp_dir.startswith(f"/home/{os.getlogin()}"):
                            self.cleanup_status_text.insert(tk.END, 
                                                      f"User directory {temp_dir} requires manual confirmation.\n")
                            
                    except Exception as e:
                        logging.error(f"Error cleaning {temp_dir}: {e}")
                        self.cleanup_status_text.insert(tk.END, f"Error cleaning {temp_dir}: {str(e)}\n")
                        
            # Show summary
            self.cleanup_status_text.insert(tk.END, 
                                         f"Total cleaned: {total_cleaned / (1024**2):.2f} MB\n")
            self.cleanup_status_text.config(state="disabled")
            self.update_status("Temporary files cleanup completed")
            
        except Exception as e:
            logging.error(f"Error cleaning temporary files: {e}")
            self.cleanup_status_text.config(state="normal")
            self.cleanup_status_text.insert(tk.END, f"Error: {str(e)}\n")
            self.cleanup_status_text.config(state="disabled")
            self.update_status(f"Error cleaning temporary files: {e}")
            
    def _real_cleanup_package_cache(self):
        """Clean up package cache based on the detected package manager."""
        try:
            # Determine the package manager
            package_managers = [
                {"cmd": "apt", "check": ["apt", "--version"], "clean": ["apt", "clean"]},
                {"cmd": "dnf", "check": ["dnf", "--version"], "clean": ["dnf", "clean", "all"]},
                {"cmd": "pacman", "check": ["pacman", "--version"], "clean": ["pacman", "-Sc", "--noconfirm"]}
            ]
            
            # Find available package manager
            pkg_manager = None
            for pm in package_managers:
                try:
                    subprocess.run(pm["check"], capture_output=True, check=True)
                    pkg_manager = pm
                    break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
            
            if not pkg_manager:
                messagebox.showinfo("Cleanup", "No supported package manager detected.")
                return
                
            # Update status
            self.cleanup_status_text.config(state="normal")
            self.cleanup_status_text.delete("1.0", tk.END)
            self.cleanup_status_text.insert("1.0", f"Using {pkg_manager['cmd']} package manager...\n")
            self.cleanup_status_text.update()
            
            # Run the clean command with sudo
            clean_cmd = ["sudo"] + pkg_manager["clean"]
            process = subprocess.Popen(
                clean_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Show ongoing status
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.cleanup_status_text.insert(tk.END, "Package cache cleaned successfully!\n")
                if stdout.strip():
                    self.cleanup_status_text.insert(tk.END, f"Output: {stdout.strip()}\n")
            else:
                self.cleanup_status_text.insert(tk.END, f"Error cleaning package cache: {stderr.strip()}\n")
                
            self.cleanup_status_text.config(state="disabled")
            self.update_status("Package cache cleanup completed")
            
        except Exception as e:
            logging.error(f"Error cleaning package cache: {e}")
            self.cleanup_status_text.config(state="normal")
            self.cleanup_status_text.insert(tk.END, f"Error: {str(e)}\n")
            self.cleanup_status_text.config(state="disabled")
            self.update_status(f"Error cleaning package cache: {e}")
            
    def _real_analyze_selected_drive(self):
        """Analyze the selected drive with smart data."""
        # Get selected drive
        selection = self.drives_tree.selection()
        if not selection:
            messagebox.showinfo("Drive Analysis", "Please select a drive first.")
            return
            
        # Get drive device from the selected item
        item = self.drives_tree.item(selection[0])
        device = item['values'][0]
        
        try:
            # Create a new window for drive analysis
            analysis_window = tk.Toplevel(self)
            analysis_window.title(f"Drive Analysis: {device}")
            analysis_window.geometry("700x500")
            
            # Create a notebook for different analysis tabs
            notebook = ttk.Notebook(analysis_window)
            notebook.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Create Smart Data tab
            smart_frame = ttk.Frame(notebook)
            notebook.add(smart_frame, text="SMART Data")
            
            # Create Usage Statistics tab
            usage_frame = ttk.Frame(notebook)
            notebook.add(usage_frame, text="Usage Statistics")
            
            # Try to get SMART data
            smart_text = tk.Text(smart_frame, wrap="word")
            smart_text.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Run smartctl command if available
            try:
                result = subprocess.run(["sudo", "smartctl", "-a", device], 
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    smart_text.insert("1.0", result.stdout)
                else:
                    smart_text.insert("1.0", f"Error getting SMART data: {result.stderr}\n")
                    smart_text.insert(tk.END, "Note: SMART data may not be available for all devices.")
            except Exception as e:
                smart_text.insert("1.0", f"Error: Unable to run SMART diagnostics: {str(e)}\n")
                smart_text.insert(tk.END, "Install smartmontools with: sudo apt install smartmontools")
                
            smart_text.config(state="disabled")
            
            # Add usage statistics
            usage_text = tk.Text(usage_frame, wrap="word")
            usage_text.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Get drive usage with df command
            try:
                result = subprocess.run(["df", "-h", device], capture_output=True, text=True)
                usage_text.insert("1.0", "Disk Usage:\n")
                usage_text.insert(tk.END, result.stdout)
                usage_text.insert(tk.END, "\n\n")
                
                # Get filesystem info with tune2fs for ext partitions
                result = subprocess.run(["sudo", "tune2fs", "-l", device], 
                                       capture_output=True, text=True, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    usage_text.insert(tk.END, "Filesystem Information:\n")
                    usage_text.insert(tk.END, result.stdout)
            except Exception as e:
                usage_text.insert(tk.END, f"\nError getting usage information: {str(e)}")
                
            usage_text.config(state="disabled")
            
            # Add close button
            close_btn = ttk.Button(analysis_window, text="Close", command=analysis_window.destroy)
            close_btn.pack(pady=10)
            
            self.update_status(f"Analyzing drive {device}")
            
        except Exception as e:
            logging.error(f"Error analyzing drive: {e}")
            messagebox.showerror("Error", f"Error analyzing drive: {e}")
    
    def _real_show_nvme_details(self):
        """Show detailed information about NVMe drives."""
        try:
            # Create a new window for NVMe information
            nvme_window = tk.Toplevel(self)
            nvme_window.title("NVMe Drive Details")
            nvme_window.geometry("700x500")
            
            # Create a text widget for displaying NVMe information
            text = tk.Text(nvme_window, wrap="word")
            text.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Check if nvme-cli is installed
            try:
                # Try to run nvme list command
                result = subprocess.run(["nvme", "list"], capture_output=True, text=True)
                
                if result.returncode == 0:
                    text.insert("1.0", "=== NVMe Drive List ===\n\n")
                    text.insert(tk.END, result.stdout)
                    text.insert(tk.END, "\n\n")
                    
                    # Try to get detailed info for each drive
                    try:
                        # Get list of NVMe devices
                        nvme_devices = []
                        lines = result.stdout.strip().split('\n')
                        for line in lines[2:]:  # Skip header lines
                            parts = line.split()
                            if parts and '/dev/' in parts[0]:
                                nvme_devices.append(parts[0])
                        
                        # Get info for each device
                        for device in nvme_devices:
                            text.insert(tk.END, f"\n=== Detailed info for {device} ===\n\n")
                            
                            # Get device info
                            info_result = subprocess.run(["sudo", "nvme", "smart-log", device], 
                                                       capture_output=True, text=True)
                            if info_result.returncode == 0:
                                text.insert(tk.END, info_result.stdout)
                            else:
                                text.insert(tk.END, f"Error getting info: {info_result.stderr}\n")
                    except Exception as e:
                        text.insert(tk.END, f"\nError getting detailed NVMe info: {str(e)}\n")
                else:
                    text.insert("1.0", f"Error listing NVMe drives: {result.stderr}\n")
                    text.insert(tk.END, "No NVMe drives detected or nvme-cli cannot access them.")
            except FileNotFoundError:
                text.insert("1.0", "nvme-cli tool not found. Please install it to get NVMe details:\n")
                text.insert(tk.END, "sudo apt install nvme-cli\n\n")
                text.insert(tk.END, "NVMe (Non-Volatile Memory Express) is a specification for accessing solid-state drives (SSDs) attached through the PCI Express (PCIe) bus. The nvme-cli tool provides management and monitoring capabilities for these high-performance storage devices.")
            
            text.config(state="disabled")
            
            # Add a scrollbar
            scrollbar = ttk.Scrollbar(nvme_window, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)
            
            # Add close button
            close_btn = ttk.Button(nvme_window, text="Close", command=nvme_window.destroy)
            close_btn.pack(pady=10)
            
            self.update_status("Displaying NVMe drive details")
            
        except Exception as e:
            logging.error(f"Error showing NVMe details: {e}")
            messagebox.showerror("Error", f"Error showing NVMe details: {e}")
