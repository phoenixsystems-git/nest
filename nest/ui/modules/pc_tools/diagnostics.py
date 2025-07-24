#!/usr/bin/env python3
"""
Diagnostics Tab for PC Tools Module

This module implements the Diagnostics tab for the PC Tools module,
providing hardware and software diagnostics functionality.
"""

import os
import sys
import time
import json
import socket
import tkinter as tk
import logging
import platform
import threading
import subprocess
from tkinter import ttk, messagebox, scrolledtext
from tkinter import filedialog
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import OS-specific diagnostics modules
if platform.system() == 'Linux':
    from nest.utils import linux_diagnostics
elif platform.system() == 'Windows':
    # We'll implement Windows-specific diagnostics later
    pass

class DiagnosticsTab(ttk.Frame):
    """Diagnostics tab for PC Tools module."""

    def __init__(self, parent, shared_state):
        """Initialize the Diagnostics tab.
        
        Args:
            parent: Parent widget
            shared_state: Shared state dictionary
        """
        super().__init__(parent)
        self.parent = parent
        self.shared_state = shared_state
        self.colors = shared_state.get('colors', {})
        self.system_info = shared_state.get('system_info', {})
        self.current_user = shared_state.get('current_user', {})
        
        # Initialize state variables
        self.is_running_diagnostics = False
        self.diagnostics_results = {}
        self.last_refresh_time = 0
        
        # Technician name (if available)
        self.technician_name = self.current_user.get('name', 'Unknown')
        
        # Create the tab UI
        self.create_ui()
    
    def create_ui(self):
        """Create the Diagnostics tab user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)
        
        # Heading
        heading_frame = ttk.Frame(main_frame)
        heading_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(heading_frame, text="Diagnostics", font=("Arial", 16, "bold")).pack(side="left")
        
        # Info text
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            info_frame, 
            text="The diagnostics tool will analyze your system and identify potential hardware or software issues.",
            wraplength=600
        ).pack(anchor="w")
        
        # Create notebook with tabs for different diagnostic categories
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(5, 10))
        
        # Create frames for each category
        self.quick_scan_frame = ttk.Frame(self.notebook)
        self.hardware_frame = ttk.Frame(self.notebook)
        self.storage_frame = ttk.Frame(self.notebook)
        self.network_frame = ttk.Frame(self.notebook)
        
        # Add frames to notebook
        self.notebook.add(self.quick_scan_frame, text="Quick Scan")
        self.notebook.add(self.hardware_frame, text="Hardware Tests")
        self.notebook.add(self.storage_frame, text="Storage Tests")
        self.notebook.add(self.network_frame, text="Network Tests")
        
        # Create content for each tab
        self.create_quick_scan_tab()
        self.create_hardware_tab()
        self.create_storage_tab()
        self.create_network_tab()
        
        # Bottom action area
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(10, 0))
        
        # Add a save report button
        self.save_button = ttk.Button(
            action_frame, 
            text="Save Diagnostic Report", 
            command=self.export_diagnostic_report,
            state="disabled"
        )
        self.save_button.pack(side="right", padx=(5, 0))
        
        # Add a run diagnostics button
        self.run_button = ttk.Button(
            action_frame, 
            text="Run Full Diagnostics", 
            command=self.run_full_diagnostics
        )
        self.run_button.pack(side="right", padx=(5, 0))
    
    def create_quick_scan_tab(self):
        """Create the Quick Scan tab content."""
        frame = ttk.Frame(self.quick_scan_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Description
        ttk.Label(
            frame,
            text="Quick Scan performs basic diagnostics on your system to identify common issues.",
            wraplength=600
        ).pack(anchor="w", pady=(0, 10))
        
        # Status area
        self.status_frame = ttk.LabelFrame(frame, text="System Status")
        self.status_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Initialize with placeholder or loading indicator
        self.status_label = ttk.Label(
            self.status_frame,
            text="Click 'Run Quick Scan' to check system status",
            justify="center"
        )
        self.status_label.pack(anchor="center", pady=50)
        
        # Results area (initially hidden)
        self.results_frame = ttk.Frame(frame)
        self.results_frame.pack(fill="both", expand=True, pady=(0, 10))
        self.results_frame.pack_forget()  # Hide initially
        
        # Progress bar
        self.progress_frame = ttk.Frame(frame)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_status = ttk.Label(self.progress_frame, text="")
        self.progress_status.pack(side="left", padx=(10, 0))
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.progress_frame.pack_forget()  # Hide initially
        
        # Action buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x")
        
        self.quick_scan_button = ttk.Button(
            button_frame,
            text="Run Quick Scan",
            command=self.run_quick_scan
        )
        self.quick_scan_button.pack(side="right")
    
    def create_hardware_tab(self):
        """Create the Hardware Tests tab content."""
        frame = ttk.Frame(self.hardware_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(
            frame,
            text="Hardware diagnostics for CPU, memory, and other components.",
            wraplength=600
        ).pack(anchor="w", pady=(0, 10))
        
        # Create hardware test categories
        self.hw_notebook = ttk.Notebook(frame)
        self.hw_notebook.pack(fill="both", expand=True, pady=(5, 10))
        
        # Create frames for each hardware component
        self.cpu_frame = ttk.Frame(self.hw_notebook)
        self.memory_frame = ttk.Frame(self.hw_notebook)
        self.motherboard_frame = ttk.Frame(self.hw_notebook)
        
        # Add frames to notebook
        self.hw_notebook.add(self.cpu_frame, text="CPU")
        self.hw_notebook.add(self.memory_frame, text="Memory")
        self.hw_notebook.add(self.motherboard_frame, text="Motherboard")
        
        # Create content for each component tab
        self._create_cpu_tab()
        self._create_memory_tab()
        self._create_motherboard_tab()
        
        # Progress frame for hardware tests
        self.hw_progress_frame = ttk.Frame(frame)
        self.hw_progress_var = tk.DoubleVar()
        self.hw_progress_bar = ttk.Progressbar(
            self.hw_progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            variable=self.hw_progress_var
        )
        self.hw_progress_bar.pack(side="left", fill="x", expand=True)
        self.hw_progress_status = ttk.Label(self.hw_progress_frame, text="")
        self.hw_progress_status.pack(side="left", padx=(10, 0))
        self.hw_progress_frame.pack(fill="x", pady=(10, 10))
        self.hw_progress_frame.pack_forget()  # Hide initially
        
        # Bottom button area
        hw_btn_frame = ttk.Frame(frame)
        hw_btn_frame.pack(fill="x", pady=(10, 0))
        
        self.run_hw_tests_btn = ttk.Button(
            hw_btn_frame,
            text="Run Hardware Tests",
            command=self.run_hardware_tests
        )
        self.run_hw_tests_btn.pack(side="right", padx=(5, 0))
    
    def _create_cpu_tab(self):
        """Create the CPU test tab content."""
        frame = ttk.Frame(self.cpu_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # CPU info area
        self.cpu_info_frame = ttk.LabelFrame(frame, text="CPU Information")
        self.cpu_info_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Initialize with placeholder
        self.cpu_info_label = ttk.Label(
            self.cpu_info_frame,
            text="Click 'Run Hardware Tests' to analyze CPU",
            justify="center"
        )
        self.cpu_info_label.pack(anchor="center", pady=20)
        
        # CPU test results area (initially hidden)
        self.cpu_results_frame = ttk.Frame(frame)
        self.cpu_results_frame.pack(fill="both", expand=True)
        self.cpu_results_frame.pack_forget()  # Hide initially
        
    def _create_memory_tab(self):
        """Create the Memory test tab content."""
        frame = ttk.Frame(self.memory_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Memory info area
        self.memory_info_frame = ttk.LabelFrame(frame, text="Memory Information")
        self.memory_info_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Initialize with placeholder
        self.memory_info_label = ttk.Label(
            self.memory_info_frame,
            text="Click 'Run Hardware Tests' to analyze memory",
            justify="center"
        )
        self.memory_info_label.pack(anchor="center", pady=20)
        
        # Memory test results area (initially hidden)
        self.memory_results_frame = ttk.Frame(frame)
        self.memory_results_frame.pack(fill="both", expand=True)
        self.memory_results_frame.pack_forget()  # Hide initially
        
    def _create_motherboard_tab(self):
        """Create the Motherboard test tab content."""
        frame = ttk.Frame(self.motherboard_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Motherboard info area
        self.mobo_info_frame = ttk.LabelFrame(frame, text="Motherboard Information")
        self.mobo_info_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Initialize with placeholder
        self.mobo_info_label = ttk.Label(
            self.mobo_info_frame,
            text="Click 'Run Hardware Tests' to analyze motherboard",
            justify="center"
        )
        self.mobo_info_label.pack(anchor="center", pady=20)
        
        # Motherboard test results area (initially hidden)
        self.mobo_results_frame = ttk.Frame(frame)
        self.mobo_results_frame.pack(fill="both", expand=True)
        self.mobo_results_frame.pack_forget()  # Hide initially
        
    def run_hardware_tests(self):
        """Run detailed hardware tests for CPU, memory, and motherboard."""
        if self.is_running_diagnostics:
            return
            
        self.is_running_diagnostics = True
        self.run_hw_tests_btn.configure(state="disabled")
        
        # Reset and show progress indicator
        self.hw_progress_var.set(0)
        self.hw_progress_status.configure(text="Starting hardware tests...")
        self.hw_progress_frame.pack(fill="x", pady=(0, 10))
        
        # Start hardware tests in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._run_hardware_tests_thread)
        thread.daemon = True
        thread.start()
        
    def _run_hardware_tests_thread(self):
        """Background thread for running detailed hardware tests."""
        try:
            # Gather hardware information based on the OS platform
            if platform.system() == 'Linux':
                # CPU Tests
                self.hw_progress_var.set(10)
                self._update_hw_progress_status("Analyzing CPU...")
                cpu_info = linux_diagnostics.get_cpu_info()
                system_load = linux_diagnostics.get_system_load()
                self.after(100, lambda: self._update_cpu_info(cpu_info, system_load))
                
                # Memory Tests
                self.hw_progress_var.set(40)
                self._update_hw_progress_status("Analyzing memory...")
                memory_info = linux_diagnostics.get_memory_info()
                self.after(100, lambda: self._update_memory_info(memory_info))
                
                # Motherboard Tests
                self.hw_progress_var.set(70)
                self._update_hw_progress_status("Analyzing motherboard...")
                mobo_info = linux_diagnostics.get_motherboard_info()
                self.after(100, lambda: self._update_motherboard_info(mobo_info))
                
                # Final Check
                self.hw_progress_var.set(90)
                self._update_hw_progress_status("Checking hardware health...")
                
                # Get health data
                health_data = linux_diagnostics.check_hardware_health()
                
                # Complete
                self.hw_progress_var.set(100)
                self._update_hw_progress_status("Complete")
                
                # Update health status in UI
                self.after(100, lambda: self._finalize_hardware_tests(health_data))
                
            elif platform.system() == 'Windows':
                # Just a placeholder for Windows
                for progress in range(10, 101, 10):
                    self.hw_progress_var.set(progress)
                    self._update_hw_progress_status(f"Simulating hardware tests ({progress}%)...")
                    time.sleep(0.3)  # Simulate work being done
                
                # Complete with dummy data
                self.after(100, lambda: self._finalize_hardware_tests({
                    'cpu': {'status': 'Healthy', 'issues': []},
                    'memory': {'status': 'Healthy', 'issues': []},
                    'overall': 'Healthy'
                }))
            else:
                # Unsupported OS
                self.hw_progress_var.set(100)
                self._update_hw_progress_status("Unsupported OS")
                self.after(100, lambda: self._show_hardware_test_error(f"Platform {platform.system()} is not supported"))
                
        except Exception as e:
            logging.error(f"Error in hardware tests: {e}")
            # Update UI on error
            self.after(100, lambda: self._show_hardware_test_error(str(e)))
        
    def _update_hw_progress_status(self, text):
        """Update hardware test progress status text from a background thread."""
        self.after(0, lambda: self.hw_progress_status.configure(text=text))
        
    def _update_cpu_info(self, cpu_info, system_load):
        """Update the CPU information tab with detailed CPU data."""
        # Clear previous content
        for widget in self.cpu_info_frame.winfo_children():
            widget.destroy()
            
        # Create a frame for CPU details
        cpu_details = ttk.Frame(self.cpu_info_frame)
        cpu_details.pack(fill="both", expand=True, padx=10, pady=10)
        
        # CPU model
        ttk.Label(cpu_details, text="CPU Model:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(cpu_details, text=cpu_info['model']).grid(row=0, column=1, sticky="w", pady=2)
        
        # CPU cores/threads
        ttk.Label(cpu_details, text="Cores/Threads:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(cpu_details, text=f"{cpu_info['cores']} / {cpu_info['threads']}").grid(row=1, column=1, sticky="w", pady=2)
        
        # CPU speed
        ttk.Label(cpu_details, text="Speed:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(cpu_details, text=cpu_info['speed']).grid(row=2, column=1, sticky="w", pady=2)
        
        # CPU temperature
        ttk.Label(cpu_details, text="Temperature:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", pady=2)
        temp_color = "black"
        if cpu_info['temperature'] != 'Unknown':
            temp_value = float(cpu_info['temperature'].rstrip('°C'))
            if temp_value > 80:
                temp_color = "red"
            elif temp_value > 70:
                temp_color = "orange"
        ttk.Label(cpu_details, text=cpu_info['temperature'], foreground=temp_color).grid(row=3, column=1, sticky="w", pady=2)
        
        # Current CPU load
        ttk.Label(cpu_details, text="Current Load:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", pady=2)
        load_color = "black"
        if system_load['cpu_percent'] > 90:
            load_color = "red"
        elif system_load['cpu_percent'] > 70:
            load_color = "orange"
        ttk.Label(cpu_details, text=f"{system_load['cpu_percent']}%", foreground=load_color).grid(row=4, column=1, sticky="w", pady=2)
        
        # Load average (1, 5, 15 min)
        ttk.Label(cpu_details, text="Load Average:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="w", pady=2)
        ttk.Label(cpu_details, text=f"{system_load['load_avg'][0]:.2f}, {system_load['load_avg'][1]:.2f}, {system_load['load_avg'][2]:.2f}").grid(row=5, column=1, sticky="w", pady=2)
        
        # Process count
        ttk.Label(cpu_details, text="Active Processes:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="w", pady=2)
        ttk.Label(cpu_details, text=f"{system_load['processes']}").grid(row=6, column=1, sticky="w", pady=2)
        
    def _update_memory_info(self, memory_info):
        """Update the Memory information tab with detailed memory data."""
        # Clear previous content
        for widget in self.memory_info_frame.winfo_children():
            widget.destroy()
            
        # Create a frame for memory details
        mem_details = ttk.Frame(self.memory_info_frame)
        mem_details.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Total RAM
        ttk.Label(mem_details, text="Total RAM:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(mem_details, text=f"{memory_info['total']:.2f} GB").grid(row=0, column=1, sticky="w", pady=2)
        
        # Used RAM
        ttk.Label(mem_details, text="Used RAM:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(mem_details, text=f"{memory_info['used']:.2f} GB ({memory_info['percent_used']:.1f}%)").grid(row=1, column=1, sticky="w", pady=2)
        
        # Available RAM
        ttk.Label(mem_details, text="Available RAM:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(mem_details, text=f"{memory_info['available']:.2f} GB").grid(row=2, column=1, sticky="w", pady=2)
        
        # Swap Total
        ttk.Label(mem_details, text="Swap Total:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Label(mem_details, text=f"{memory_info['swap_total']:.2f} GB").grid(row=3, column=1, sticky="w", pady=2)
        
        # Swap Used
        ttk.Label(mem_details, text="Swap Used:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", pady=2)
        swap_color = "black"
        if memory_info['swap_percent'] > 80:
            swap_color = "red"
        elif memory_info['swap_percent'] > 50:
            swap_color = "orange"
        ttk.Label(mem_details, text=f"{memory_info['swap_used']:.2f} GB ({memory_info['swap_percent']:.1f}%)", foreground=swap_color).grid(row=4, column=1, sticky="w", pady=2)
        
        # Create a canvas for memory usage visualization
        canvas_frame = ttk.Frame(mem_details)
        canvas_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 2))
        
        mem_canvas = tk.Canvas(canvas_frame, height=30, width=300, bg="white")
        mem_canvas.pack(fill="x", expand=True)
        
        # Draw the memory usage bar
        used_width = int((memory_info['percent_used'] / 100) * 300)
        mem_color = "green"
        if memory_info['percent_used'] > 90:
            mem_color = "red"
        elif memory_info['percent_used'] > 70:
            mem_color = "orange"
        mem_canvas.create_rectangle(0, 0, used_width, 30, fill=mem_color, outline="")
        
        # Add label
        ttk.Label(mem_details, text=f"RAM Usage: {memory_info['percent_used']:.1f}%").grid(row=6, column=0, columnspan=2, sticky="w", pady=2)
        
    def _update_motherboard_info(self, mobo_info):
        """Update the Motherboard information tab with detailed motherboard data."""
        # Clear previous content
        for widget in self.mobo_info_frame.winfo_children():
            widget.destroy()
            
        # Create a frame for motherboard details
        mobo_details = ttk.Frame(self.mobo_info_frame)
        mobo_details.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Manufacturer
        ttk.Label(mobo_details, text="Manufacturer:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(mobo_details, text=mobo_info['manufacturer']).grid(row=0, column=1, sticky="w", pady=2)
        
        # Model
        ttk.Label(mobo_details, text="Model:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(mobo_details, text=mobo_info['model']).grid(row=1, column=1, sticky="w", pady=2)
        
        # BIOS Version
        ttk.Label(mobo_details, text="BIOS Version:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(mobo_details, text=mobo_info['bios_version']).grid(row=2, column=1, sticky="w", pady=2)
        
        # BIOS Date
        ttk.Label(mobo_details, text="BIOS Date:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Label(mobo_details, text=mobo_info['bios_date']).grid(row=3, column=1, sticky="w", pady=2)
        
    def _finalize_hardware_tests(self, health_data):
        """Complete hardware tests and display overall health information."""
        # Hide progress indicator
        self.hw_progress_frame.pack_forget()
        
        # Display health summary at the bottom of each tab
        # CPU health summary
        cpu_health_frame = ttk.LabelFrame(self.cpu_frame, text="CPU Health")
        cpu_health_frame.pack(fill="x", padx=10, pady=10)
        
        status_icon = "✅" if health_data['cpu']['status'] == 'Healthy' else "⚠️" if health_data['cpu']['status'] == 'Warning' else "❌"
        status_color = "green" if health_data['cpu']['status'] == 'Healthy' else "orange" if health_data['cpu']['status'] == 'Warning' else "red"
        
        cpu_status_frame = ttk.Frame(cpu_health_frame)
        cpu_status_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(cpu_status_frame, text=status_icon, font=("Arial", 12)).pack(side="left")
        ttk.Label(
            cpu_status_frame, 
            text=f"Status: {health_data['cpu']['status']}",
            foreground=status_color,
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=(5, 0))
        
        if health_data['cpu']['issues']:
            issues_frame = ttk.Frame(cpu_health_frame)
            issues_frame.pack(fill="x", padx=10, pady=5)
            ttk.Label(issues_frame, text="Issues:", font=("Arial", 10, "bold")).pack(anchor="w")
            
            for issue in health_data['cpu']['issues']:
                ttk.Label(issues_frame, text=f"• {issue}", foreground="red").pack(anchor="w", padx=(10, 0))
        
        # Memory health summary
        memory_health_frame = ttk.LabelFrame(self.memory_frame, text="Memory Health")
        memory_health_frame.pack(fill="x", padx=10, pady=10)
        
        status_icon = "✅" if health_data['memory']['status'] == 'Healthy' else "⚠️" if health_data['memory']['status'] == 'Warning' else "❌"
        status_color = "green" if health_data['memory']['status'] == 'Healthy' else "orange" if health_data['memory']['status'] == 'Warning' else "red"
        
        mem_status_frame = ttk.Frame(memory_health_frame)
        mem_status_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(mem_status_frame, text=status_icon, font=("Arial", 12)).pack(side="left")
        ttk.Label(
            mem_status_frame, 
            text=f"Status: {health_data['memory']['status']}",
            foreground=status_color,
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=(5, 0))
        
        if health_data['memory']['issues']:
            issues_frame = ttk.Frame(memory_health_frame)
            issues_frame.pack(fill="x", padx=10, pady=5)
            ttk.Label(issues_frame, text="Issues:", font=("Arial", 10, "bold")).pack(anchor="w")
            
            for issue in health_data['memory']['issues']:
                ttk.Label(issues_frame, text=f"• {issue}", foreground="red").pack(anchor="w", padx=(10, 0))
                
        # Re-enable the Run Hardware Tests button
        self.run_hw_tests_btn.configure(state="normal")
        self.is_running_diagnostics = False
        
    def _show_hardware_test_error(self, error_message):
        """Show error message when hardware tests fail."""
        # Hide progress
        self.hw_progress_frame.pack_forget()
        
        # Show error in CPU tab
        for widget in self.cpu_info_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(
            self.cpu_info_frame,
            text=f"Error running hardware tests:\n{error_message}",
            foreground="red",
            justify="center"
        ).pack(anchor="center", pady=50)
        
        # Show error in memory tab
        for widget in self.memory_info_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(
            self.memory_info_frame,
            text=f"Error running hardware tests:\n{error_message}",
            foreground="red",
            justify="center"
        ).pack(anchor="center", pady=50)
        
        # Show error in motherboard tab
        for widget in self.mobo_info_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(
            self.mobo_info_frame,
            text=f"Error running hardware tests:\n{error_message}",
            foreground="red",
            justify="center"
        ).pack(anchor="center", pady=50)
        
        # Re-enable the Run Hardware Tests button
        self.run_hw_tests_btn.configure(state="normal")
        self.is_running_diagnostics = False
        
    def create_storage_tab(self):
        """Create the Storage Tests tab content."""
        frame = ttk.Frame(self.storage_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(
            frame,
            text="Storage diagnostics for checking drive health and performance.",
            wraplength=600
        ).pack(anchor="w", pady=(0, 10))
        
        # Storage info area
        self.storage_info_frame = ttk.LabelFrame(frame, text="Storage Overview")
        self.storage_info_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Initialize with placeholder
        self.storage_info_label = ttk.Label(
            self.storage_info_frame,
            text="Click 'Run Storage Diagnostics' to analyze storage devices",
            justify="center"
        )
        self.storage_info_label.pack(anchor="center", pady=20)
        
        # Drive details area - will contain individual frames for each drive
        self.drives_frame = ttk.Frame(frame)
        self.drives_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Progress frame for storage tests
        self.storage_progress_frame = ttk.Frame(frame)
        self.storage_progress_var = tk.DoubleVar()
        self.storage_progress_bar = ttk.Progressbar(
            self.storage_progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            variable=self.storage_progress_var
        )
        self.storage_progress_bar.pack(side="left", fill="x", expand=True)
        self.storage_progress_status = ttk.Label(self.storage_progress_frame, text="")
        self.storage_progress_status.pack(side="left", padx=(10, 0))
        self.storage_progress_frame.pack(fill="x", pady=(10, 10))
        self.storage_progress_frame.pack_forget()  # Hide initially
        
        # Bottom button area
        storage_btn_frame = ttk.Frame(frame)
        storage_btn_frame.pack(fill="x", pady=(10, 0))
        
        self.run_storage_tests_btn = ttk.Button(
            storage_btn_frame,
            text="Run Storage Diagnostics",
            command=self.run_storage_tests
        )
        self.run_storage_tests_btn.pack(side="right", padx=(5, 0))
    
    def run_storage_tests(self):
        """Run detailed storage tests to analyze drive health and performance."""
        if self.is_running_diagnostics:
            return
            
        self.is_running_diagnostics = True
        self.run_storage_tests_btn.configure(state="disabled")
        
        # Reset UI elements
        for widget in self.storage_info_frame.winfo_children():
            widget.destroy()
            
        for widget in self.drives_frame.winfo_children():
            widget.destroy()
            
        # Show a loading message
        ttk.Label(
            self.storage_info_frame,
            text="Scanning storage devices...",
            justify="center"
        ).pack(anchor="center", pady=20)
        
        # Reset and show progress indicator
        self.storage_progress_var.set(0)
        self.storage_progress_status.configure(text="Initializing storage diagnostics...")
        self.storage_progress_frame.pack(fill="x", pady=(0, 10))
        
        # Start storage tests in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._run_storage_tests_thread)
        thread.daemon = True
        thread.start()
        
    def _run_storage_tests_thread(self):
        """Background thread for running detailed storage tests."""
        try:
            if platform.system() == 'Linux':
                # Get storage information
                self.storage_progress_var.set(10)
                self._update_storage_progress_status("Enumerating storage devices...")
                storage_info = linux_diagnostics.get_storage_info()
                
                # Update progress
                self.storage_progress_var.set(30)
                
                # Check if we have storage devices to analyze
                if not storage_info:
                    self.after(100, lambda: self._show_storage_error("No storage devices found"))
                    return
                    
                # Run SMART tests on each drive (if available)
                drive_health = {}
                total_drives = len(storage_info)
                for i, drive in enumerate(storage_info):
                    # Update progress based on the current drive
                    progress = 30 + int((i / total_drives) * 60)
                    self.storage_progress_var.set(progress)
                    self._update_storage_progress_status(f"Analyzing {drive['device']} ({drive['model']})")
                    
                    # Run SMART check if device is a physical drive (not a virtual device)
                    if drive['device'].startswith('/dev/') and not any(x in drive['device'] for x in ['loop', 'ram']):
                        try:
                            # Special handling for NVMe drives
                            if 'nvme' in drive['device']:
                                self._update_storage_progress_status(f"Running NVMe diagnostics on {drive['device']}")
                                
                            # Run SMART diagnostics
                            smart_result = linux_diagnostics.run_smart_check(drive['device'])
                            drive_health[drive['device']] = smart_result
                        except Exception as e:
                            logging.warning(f"SMART check failed for {drive['device']}: {e}")
                            drive_health[drive['device']] = {
                                'health': 'Unknown',
                                'temperature': None,
                                'power_on_hours': None,
                                'errors': [f"SMART check failed: {str(e)}"]
                            }
                            
                # Complete
                self.storage_progress_var.set(100)
                self._update_storage_progress_status("Storage analysis complete")
                
                # Update UI with results
                self.after(100, lambda: self._update_storage_info(storage_info, drive_health))
                
            elif platform.system() == 'Windows':
                # Placeholder for Windows
                for progress in range(10, 101, 10):
                    self.storage_progress_var.set(progress)
                    self._update_storage_progress_status(f"Simulating storage diagnostics ({progress}%)...")
                    time.sleep(0.3)  # Simulate work being done
                    
                # Complete with dummy data
                self.after(100, lambda: self._update_storage_info([
                    {
                        'device': 'C:',
                        'model': 'Windows System Drive',
                        'size_gb': 500,
                        'type': 'SSD',
                        'used_percent': 65,
                        'partitions': []
                    }
                ], {}))
            else:
                # Unsupported OS
                self.storage_progress_var.set(100)
                self._update_storage_progress_status("Unsupported OS")
                self.after(100, lambda: self._show_storage_error(f"Platform {platform.system()} is not supported"))
                
        except Exception as e:
            logging.error(f"Error in storage tests: {e}")
            self.after(100, lambda: self._show_storage_error(str(e)))
            
    def _update_storage_progress_status(self, text):
        """Update storage test progress status text from a background thread."""
        self.after(0, lambda: self.storage_progress_status.configure(text=text))
        
    def _update_storage_info(self, storage_info, drive_health):
        """Update the Storage information tab with detailed drive data."""
        # Hide progress
        self.storage_progress_frame.pack_forget()
        
        # Clear previous content
        for widget in self.storage_info_frame.winfo_children():
            widget.destroy()
            
        for widget in self.drives_frame.winfo_children():
            widget.destroy()
            
        # Create storage overview title
        ttk.Label(
            self.storage_info_frame,
            text=f"Found {len(storage_info)} storage device{'' if len(storage_info) == 1 else 's'}",
            font=("Arial", 12, "bold"),
            anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 5))
        
        # Calculate totals for overview
        total_space = sum(drive['size_gb'] for drive in storage_info)
        total_used = sum(drive['size_gb'] * (drive['used_percent'] / 100) for drive in storage_info if drive['used_percent'] > 0)
        total_used_percent = (total_used / total_space * 100) if total_space > 0 else 0
        
        # Create overview frame with storage summary
        overview_frame = ttk.Frame(self.storage_info_frame)
        overview_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Total storage
        ttk.Label(overview_frame, text="Total Space:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(overview_frame, text=f"{total_space:.1f} GB").grid(row=0, column=1, sticky="w", pady=2)
        
        # Used storage
        ttk.Label(overview_frame, text="Used Space:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(overview_frame, text=f"{total_used:.1f} GB ({total_used_percent:.1f}%)").grid(row=1, column=1, sticky="w", pady=2)
        
        # Drive count by type
        ssd_count = sum(1 for drive in storage_info if drive['type'] == 'SSD')
        hdd_count = sum(1 for drive in storage_info if drive['type'] == 'HDD')
        nvme_count = sum(1 for drive in storage_info if 'nvme' in drive['device'].lower())
        
        ttk.Label(overview_frame, text="Drive Types:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(overview_frame, text=f"{ssd_count} SSD(s), {hdd_count} HDD(s), {nvme_count} NVMe").grid(row=2, column=1, sticky="w", pady=2)
        
        # Display individual drive info
        for i, drive in enumerate(storage_info):
            # Create a frame for this drive with a clearer title
            drive_title = f"{drive['model']}"
            if 'nvme' in drive['device'].lower():
                drive_title = f"{drive['model']} (NVMe SSD)"
                
            drive_frame = ttk.LabelFrame(
                self.drives_frame, 
                text=f"{drive_title} - {drive['device']}"
            )
            drive_frame.pack(fill="x", expand=False, padx=5, pady=5)
            
            # Create a frame for drive details
            details_frame = ttk.Frame(drive_frame)
            details_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Drive type displayed more clearly
            row = 0
            ttk.Label(details_frame, text="Type:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
            drive_type = f"{drive['type']}"
            if 'nvme' in drive['device'].lower():
                drive_type = "SSD (NVMe)"
            ttk.Label(details_frame, text=drive_type).grid(row=row, column=1, sticky="w", pady=2)
            
            # Drive capacity
            row += 1
            ttk.Label(details_frame, text="Capacity:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Label(details_frame, text=f"{drive['size_gb']:.1f} GB").grid(row=row, column=1, sticky="w", pady=2)
            
            # Drive usage
            row += 1
            ttk.Label(details_frame, text="Usage:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
            usage_color = "black"
            if drive['used_percent'] > 90:
                usage_color = "red"
            elif drive['used_percent'] > 75:
                usage_color = "orange"
            ttk.Label(details_frame, text=f"{drive['used_percent']:.1f}%", foreground=usage_color).grid(row=row, column=1, sticky="w", pady=2)
            
            # SMART health status if available
            if drive['device'] in drive_health:
                row += 1
                ttk.Label(details_frame, text="Health:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
                
                health_status = drive_health[drive['device']]['health']
                health_color = "green" if health_status == 'Healthy' else "red" if health_status == 'Failing' else "black"
                ttk.Label(details_frame, text=health_status, foreground=health_color).grid(row=row, column=1, sticky="w", pady=2)
                
                # Temperature if available
                if drive_health[drive['device']]['temperature']:
                    row += 1
                    ttk.Label(details_frame, text="Temperature:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
                    
                    temp = drive_health[drive['device']]['temperature']
                    temp_color = "black"
                    if temp > 55:
                        temp_color = "red"
                    elif temp > 45:
                        temp_color = "orange"
                    ttk.Label(details_frame, text=f"{temp}°C", foreground=temp_color).grid(row=row, column=1, sticky="w", pady=2)
                    
                # Power-on hours if available
                if drive_health[drive['device']]['power_on_hours']:
                    row += 1
                    ttk.Label(details_frame, text="Power-On Hours:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
                    
                    hours = drive_health[drive['device']]['power_on_hours']
                    # Format as days if more than 24 hours
                    if hours > 24:
                        ttk.Label(details_frame, text=f"{hours} hours ({hours/24:.1f} days)").grid(row=row, column=1, sticky="w", pady=2)
                    else:
                        ttk.Label(details_frame, text=f"{hours} hours").grid(row=row, column=1, sticky="w", pady=2)
                    
                # Any errors
                if drive_health[drive['device']]['errors']:
                    row += 1
                    ttk.Label(details_frame, text="Issues:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
                    
                    issues_text = '; '.join(drive_health[drive['device']]['errors'])
                    ttk.Label(details_frame, text=issues_text, foreground="red", wraplength=400).grid(row=row, column=1, sticky="w", pady=2)
            
            # If the drive has partitions, show them
            if drive['partitions']:
                row += 1
                ttk.Label(details_frame, text="Partitions:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2)
                
                partitions_frame = ttk.Frame(details_frame)
                partitions_frame.grid(row=row, column=1, sticky="w", pady=2)
                
                for j, part in enumerate(drive['partitions']):
                    mount_info = f"→ {part['mountpoint']}" if part['mounted'] and part['mountpoint'] else "(not mounted)"
                    fs_info = f" ({part['fstype']})" if part['fstype'] else ""
                    
                    ttk.Label(partitions_frame, text=f"{part['device']} {mount_info}{fs_info}").grid(row=j, column=0, sticky="w")
        
        # Re-enable the Run Storage Tests button
        self.run_storage_tests_btn.configure(state="normal")
        self.is_running_diagnostics = False
        
    def _show_storage_error(self, error_message):
        """Show error message when storage tests fail."""
        # Hide progress
        self.storage_progress_frame.pack_forget()
        
        # Show error in storage info frame
        for widget in self.storage_info_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(
            self.storage_info_frame,
            text=f"Error running storage diagnostics:\n{error_message}",
            foreground="red",
            justify="center"
        ).pack(anchor="center", pady=50)
        
        # Re-enable the Run Storage Tests button
        self.run_storage_tests_btn.configure(state="normal")
        self.is_running_diagnostics = False
    
    def create_network_tab(self):
        """Create the Network Tests tab content."""
        # Create main frame
        frame = ttk.Frame(self.network_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(
            frame,
            text="Network diagnostics for connectivity and performance testing.",
            wraplength=600
        ).pack(anchor="w", pady=(0, 10))
        
        # Network interfaces area
        self.interfaces_frame = ttk.LabelFrame(frame, text="Network Interfaces")
        self.interfaces_frame.pack(fill="both", pady=(0, 10), ipady=5)
        self.interfaces_frame.configure(height=150)  # Fixed height
        
        # Initialize with placeholder
        self.interfaces_label = ttk.Label(
            self.interfaces_frame,
            text="Click 'Run Network Diagnostics' to analyze network interfaces",
            justify="center"
        )
        self.interfaces_label.pack(anchor="center", pady=20)
        
        # Connectivity tests area
        self.connectivity_frame = ttk.LabelFrame(frame, text="Connectivity Tests")
        self.connectivity_frame.pack(fill="both", pady=(0, 10), ipady=5)
        self.connectivity_frame.configure(height=150)  # Fixed height
        
        # Initialize with placeholder
        self.connectivity_label = ttk.Label(
            self.connectivity_frame,
            text="Run diagnostics to test internet connectivity",
            justify="center"
        )
        self.connectivity_label.pack(anchor="center", pady=20)
        
        # DNS tests area
        self.dns_frame = ttk.LabelFrame(frame, text="DNS Resolution")
        self.dns_frame.pack(fill="both", pady=(0, 10), ipady=5)
        self.dns_frame.configure(height=100)  # Fixed height
        
        # Initialize with placeholder
        self.dns_label = ttk.Label(
            self.dns_frame,
            text="Run diagnostics to test DNS resolution",
            justify="center"
        )
        self.dns_label.pack(anchor="center", pady=20)
        
        # Progress frame for network tests
        self.network_progress_frame = ttk.Frame(frame)
        self.network_progress_var = tk.DoubleVar()
        self.network_progress_bar = ttk.Progressbar(
            self.network_progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            variable=self.network_progress_var
        )
        self.network_progress_bar.pack(side="left", fill="x", expand=True)
        self.network_progress_status = ttk.Label(self.network_progress_frame, text="")
        self.network_progress_status.pack(side="left", padx=(10, 0))
        self.network_progress_frame.pack(fill="x", pady=(10, 10))
        self.network_progress_frame.pack_forget()  # Hide initially
        
        # Bottom button area
        network_btn_frame = ttk.Frame(frame)
        network_btn_frame.pack(fill="x", pady=(10, 0))
        
        self.run_network_tests_btn = ttk.Button(
            network_btn_frame,
            text="Run Network Diagnostics",
            command=self.run_network_tests
        )
        self.run_network_tests_btn.pack(side="right", padx=(5, 0))
    
    def run_network_tests(self):
        """Run network diagnostics including interface info, connectivity and DNS tests."""
        if self.is_running_diagnostics:
            return
            
        self.is_running_diagnostics = True
        self.run_network_tests_btn.configure(state="disabled")
        
        # Reset UI elements
        for widget in self.interfaces_frame.winfo_children():
            widget.destroy()
            
        for widget in self.connectivity_frame.winfo_children():
            widget.destroy()
            
        for widget in self.dns_frame.winfo_children():
            widget.destroy()
            
        # Show loading messages
        ttk.Label(
            self.interfaces_frame,
            text="Analyzing network interfaces...",
            justify="center"
        ).pack(anchor="center", pady=20)
        
        ttk.Label(
            self.connectivity_frame,
            text="Testing connectivity...",
            justify="center"
        ).pack(anchor="center", pady=20)
        
        ttk.Label(
            self.dns_frame,
            text="Testing DNS resolution...",
            justify="center"
        ).pack(anchor="center", pady=20)
        
        # Reset and show progress indicator
        self.network_progress_var.set(0)
        self.network_progress_status.configure(text="Initializing network diagnostics...")
        self.network_progress_frame.pack(fill="x", pady=(0, 10))
        
        # Start network tests in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._run_network_tests_thread)
        thread.daemon = True
        thread.start()
        
    def _run_network_tests_thread(self):
        """Background thread for running detailed network tests."""
        try:
            # 1. Get Network Interface Information
            self.network_progress_var.set(10)
            self._update_network_progress_status("Gathering network interfaces information...")
            interfaces = linux_diagnostics.get_network_info()
            
            # Update progress
            self.network_progress_var.set(25)
            self._update_network_progress_status("Testing interface connectivity...")
            
            # 2. Test Connectivity
            connectivity_results = self._test_connectivity()
            
            # Update progress
            self.network_progress_var.set(60)
            self._update_network_progress_status("Testing DNS resolution...")
            
            # 3. Test DNS Resolution
            dns_results = self._test_dns_resolution()
            
            # Complete
            self.network_progress_var.set(100)
            self._update_network_progress_status("Network diagnostics complete")
            
            # Update UI with results
            self.after(100, lambda: self._update_network_info(interfaces, connectivity_results, dns_results))
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error in network tests: {error_msg}")
            self.after(100, lambda error=error_msg: self._show_network_error(error))
            
    def _update_network_progress_status(self, text):
        """Update network test progress status text from a background thread."""
        self.after(0, lambda: self.network_progress_status.configure(text=text))
        
    def _test_connectivity(self):
        """Test connectivity to important destinations."""
        results = []
        
        # List of important destinations to test
        destinations = [
            {"name": "Google DNS", "host": "8.8.8.8", "port": 53},
            {"name": "Cloudflare DNS", "host": "1.1.1.1", "port": 53},
            {"name": "Google.com", "host": "google.com", "port": 80},
            {"name": "Default Gateway", "host": self._get_default_gateway(), "port": None}
        ]
        
        # Test each destination
        for dest in destinations:
            if not dest["host"]:
                results.append({"name": dest["name"], "status": "Skipped", "latency": None, "error": "Unable to determine address"})
                continue
                
            result = {"name": dest["name"], "host": dest["host"]}
            
            # Try pinging the destination
            try:
                start_time = time.time()
                if dest["port"]:
                    # Socket connection test
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)  # 2 second timeout
                    sock.connect((dest["host"], dest["port"]))
                    sock.close()
                else:
                    # Simple ICMP ping
                    ping_param = "-c 1 -W 2" if platform.system() == "Linux" else "-n 1 -w 2000"
                    subprocess.check_call(f"ping {ping_param} {dest['host']}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to ms
                
                result["status"] = "Success"
                result["latency"] = latency
                result["error"] = None
            except (socket.error, subprocess.CalledProcessError, Exception) as e:
                result["status"] = "Failed"
                result["latency"] = None
                result["error"] = str(e)
                
            results.append(result)
            
        return results
    
    def _test_dns_resolution(self):
        """Test DNS resolution for several domains."""
        results = []
        
        # List of domains to test resolution
        domains = [
            "google.com",
            "amazon.com",
            "microsoft.com",
            "apple.com",
            "repairdesk.co"
        ]
        
        # Test each domain
        for domain in domains:
            result = {"domain": domain}
            
            try:
                # Try to resolve the domain
                start_time = time.time()
                addresses = socket.getaddrinfo(domain, 80)
                end_time = time.time()
                
                # Extract the IP addresses from the result
                unique_ips = set(addr[4][0] for addr in addresses if addr[4][0])
                
                result["status"] = "Success"
                result["ips"] = str(list(unique_ips))
                result["latency"] = str((end_time - start_time) * 1000)  # Convert to ms
                result["error"] = ""
            except socket.gaierror as e:
                result["status"] = "Failed"
                result["ips"] = "[]"
                result["latency"] = ""
                result["error"] = f"DNS resolution failed: {e}"
                
            results.append(result)
            
        return results
    
    def _get_default_gateway(self):
        """Get the default gateway IP address."""
        try:
            if platform.system() == "Linux":
                # Parse /proc/net/route for default gateway
                with open("/proc/net/route", "r") as f:
                    for line in f.readlines()[1:]:  # Skip header line
                        fields = line.strip().split()
                        if fields[1] == "00000000":  # Default route
                            gateway = int(fields[2], 16)  # Convert hex to int
                            # Convert to IP address format
                            return socket.inet_ntoa(gateway.to_bytes(4, byteorder="little"))
            elif platform.system() == "Windows":
                # For Windows we would use the 'route print' command
                # Return None for now as this requires more parsing
                return None
        except Exception:
            pass
            
        return None
        
    def _update_network_info(self, interfaces, connectivity_results, dns_results):
        """Update the Network tab with detailed test results."""
        # Hide progress
        self.network_progress_frame.pack_forget()
        
        # Clear previous content
        for widget in self.interfaces_frame.winfo_children():
            widget.destroy()
            
        for widget in self.connectivity_frame.winfo_children():
            widget.destroy()
            
        for widget in self.dns_frame.winfo_children():
            widget.destroy()
            
        # 1. Update Network Interfaces section
        if interfaces:
            # Create a scrollable frame for interfaces
            canvas = tk.Canvas(self.interfaces_frame, borderwidth=0)
            scrollbar = ttk.Scrollbar(self.interfaces_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Add each interface
            for i, interface in enumerate(interfaces):
                # Create a frame for this interface
                if_frame = ttk.LabelFrame(
                    scrollable_frame, 
                    text=f"{interface['name']} ({interface['type']})"
                )
                if_frame.pack(fill="x", expand=False, padx=5, pady=5, ipadx=5, ipady=5)
                
                # Status with color
                status_color = "green" if interface["status"] == "Up" else "red"
                status_frame = ttk.Frame(if_frame)
                status_frame.pack(fill="x", padx=5, pady=2)
                ttk.Label(status_frame, text="Status:", width=15, anchor="w").pack(side="left")
                ttk.Label(status_frame, text=interface["status"], foreground=status_color).pack(side="left")
                
                # MAC Address
                mac_frame = ttk.Frame(if_frame)
                mac_frame.pack(fill="x", padx=5, pady=2)
                ttk.Label(mac_frame, text="MAC Address:", width=15, anchor="w").pack(side="left")
                ttk.Label(mac_frame, text=interface["mac"]).pack(side="left")
                
                # IP Addresses
                if interface["ipv4"]:
                    ip_frame = ttk.Frame(if_frame)
                    ip_frame.pack(fill="x", padx=5, pady=2)
                    ttk.Label(ip_frame, text="IPv4 Address:", width=15, anchor="w").pack(side="left")
                    ttk.Label(ip_frame, text=", ".join(interface["ipv4"])).pack(side="left")
                    
                if interface["ipv6"]:
                    ip6_frame = ttk.Frame(if_frame)
                    ip6_frame.pack(fill="x", padx=5, pady=2)
                    ttk.Label(ip6_frame, text="IPv6 Address:", width=15, anchor="w").pack(side="left")
                    ipv6_text = interface["ipv6"][0]
                    if len(interface["ipv6"]) > 1:
                        ipv6_text += f" (+{len(interface['ipv6'])-1} more)"
                    ttk.Label(ip6_frame, text=ipv6_text).pack(side="left")
        else:
            ttk.Label(
                self.interfaces_frame,
                text="No network interfaces found",
                foreground="red"
            ).pack(anchor="center", pady=20)
            
        # 2. Update Connectivity Tests section
        if connectivity_results:
            # Create a results table
            results_frame = ttk.Frame(self.connectivity_frame)
            results_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Headers
            ttk.Label(results_frame, text="Destination", font=("Arial", 10, "bold"), width=15).grid(row=0, column=0, sticky="w", padx=5, pady=5)
            ttk.Label(results_frame, text="Host", font=("Arial", 10, "bold"), width=20).grid(row=0, column=1, sticky="w", padx=5, pady=5)
            ttk.Label(results_frame, text="Status", font=("Arial", 10, "bold"), width=10).grid(row=0, column=2, sticky="w", padx=5, pady=5)
            ttk.Label(results_frame, text="Latency", font=("Arial", 10, "bold"), width=10).grid(row=0, column=3, sticky="w", padx=5, pady=5)
            
            # Results
            for i, result in enumerate(connectivity_results):
                row = i + 1
                ttk.Label(results_frame, text=result["name"]).grid(row=row, column=0, sticky="w", padx=5, pady=2)
                ttk.Label(results_frame, text=result["host"]).grid(row=row, column=1, sticky="w", padx=5, pady=2)
                
                status_color = "green" if result["status"] == "Success" else "red"
                ttk.Label(results_frame, text=result["status"], foreground=status_color).grid(row=row, column=2, sticky="w", padx=5, pady=2)
                
                if result["latency"]:
                    latency_text = f"{result['latency']:.1f} ms"
                    latency_color = "black"
                    if result["latency"] < 50:
                        latency_color = "green"
                    elif result["latency"] > 200:
                        latency_color = "red"
                    elif result["latency"] > 100:
                        latency_color = "orange"
                        
                    ttk.Label(results_frame, text=latency_text, foreground=latency_color).grid(row=row, column=3, sticky="w", padx=5, pady=2)
                else:
                    ttk.Label(results_frame, text="N/A").grid(row=row, column=3, sticky="w", padx=5, pady=2)
                    
            # Overall assessment
            success_count = sum(1 for r in connectivity_results if r["status"] == "Success")
            total_count = len(connectivity_results)
            
            assessment_text = "Internet connectivity looks good" if success_count >= total_count - 1 else \
                            "Some connectivity issues detected" if success_count >= total_count // 2 else \
                            "Major connectivity issues detected"
                            
            assessment_color = "green" if success_count >= total_count - 1 else \
                            "orange" if success_count >= total_count // 2 else \
                            "red"
                            
            ttk.Label(
                self.connectivity_frame,
                text=f"Assessment: {assessment_text}",
                foreground=assessment_color,
                font=("Arial", 10, "bold")
            ).pack(anchor="w", padx=10, pady=(10, 5))
            
        else:
            ttk.Label(
                self.connectivity_frame,
                text="No connectivity test results available",
                foreground="red"
            ).pack(anchor="center", pady=20)
            
        # 3. Update DNS Resolution section
        if dns_results:
            # Create a results table
            results_frame = ttk.Frame(self.dns_frame)
            results_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Headers
            ttk.Label(results_frame, text="Domain", font=("Arial", 10, "bold"), width=15).grid(row=0, column=0, sticky="w", padx=5, pady=5)
            ttk.Label(results_frame, text="Status", font=("Arial", 10, "bold"), width=10).grid(row=0, column=1, sticky="w", padx=5, pady=5)
            ttk.Label(results_frame, text="IP Addresses", font=("Arial", 10, "bold"), width=30).grid(row=0, column=2, sticky="w", padx=5, pady=5)
            ttk.Label(results_frame, text="Latency", font=("Arial", 10, "bold"), width=10).grid(row=0, column=3, sticky="w", padx=5, pady=5)
            
            # Results
            for i, result in enumerate(dns_results):
                row = i + 1
                ttk.Label(results_frame, text=result["domain"]).grid(row=row, column=0, sticky="w", padx=5, pady=2)
                
                status_color = "green" if result["status"] == "Success" else "red"
                ttk.Label(results_frame, text=result["status"], foreground=status_color).grid(row=row, column=1, sticky="w", padx=5, pady=2)
                
                if result["ips"]:
                    ips_text = ", ".join(result["ips"][:2])
                    if len(result["ips"]) > 2:
                        ips_text += f" (+{len(result['ips'])-2} more)"
                    ttk.Label(results_frame, text=ips_text).grid(row=row, column=2, sticky="w", padx=5, pady=2)
                else:
                    ttk.Label(results_frame, text="None").grid(row=row, column=2, sticky="w", padx=5, pady=2)
                    
                if result["latency"]:
                    ttk.Label(results_frame, text=f"{result['latency']:.1f} ms").grid(row=row, column=3, sticky="w", padx=5, pady=2)
                else:
                    ttk.Label(results_frame, text="N/A").grid(row=row, column=3, sticky="w", padx=5, pady=2)
                    
            # Overall assessment
            success_count = sum(1 for r in dns_results if r["status"] == "Success")
            total_count = len(dns_results)
            
            assessment_text = "DNS resolution looks good" if success_count == total_count else \
                            "Some DNS resolution issues detected" if success_count >= total_count // 2 else \
                            "Major DNS resolution issues detected"
                            
            assessment_color = "green" if success_count == total_count else \
                            "orange" if success_count >= total_count // 2 else \
                            "red"
                            
            ttk.Label(
                self.dns_frame,
                text=f"Assessment: {assessment_text}",
                foreground=assessment_color,
                font=("Arial", 10, "bold")
            ).pack(anchor="w", padx=10, pady=(10, 5))
            
            # Configured DNS servers (if we can get them)
            dns_servers = self._get_configured_dns_servers()
            if dns_servers:
                ttk.Label(
                    self.dns_frame,
                    text=f"Configured DNS Servers: {', '.join(dns_servers)}",
                    font=("Arial", 9)
                ).pack(anchor="w", padx=10, pady=(0, 5))
                
        else:
            ttk.Label(
                self.dns_frame,
                text="No DNS resolution test results available",
                foreground="red"
            ).pack(anchor="center", pady=20)
            
        # Re-enable the Run Network Tests button
        self.run_network_tests_btn.configure(state="normal")
        self.is_running_diagnostics = False
        
    def _get_configured_dns_servers(self):
        """Get the DNS servers configured on the system."""
        dns_servers = []
        
        try:
            if platform.system() == "Linux":
                # Try to read from /etc/resolv.conf
                if os.path.exists("/etc/resolv.conf"):
                    with open("/etc/resolv.conf", "r") as f:
                        for line in f:
                            if line.startswith("nameserver"):
                                parts = line.strip().split()
                                if len(parts) > 1:
                                    dns_servers.append(parts[1])
            elif platform.system() == "Windows":
                # For Windows, we'd use the 'ipconfig /all' command
                # Return empty list for now as this requires more parsing
                pass
        except Exception as e:
            logging.warning(f"Error getting DNS servers: {e}")
            
        return dns_servers
        
    def _show_network_error(self, error_message):
        """Show error message when network tests fail."""
        # Hide progress
        self.network_progress_frame.pack_forget()
        
        # Show error in all frames
        for frame in [self.interfaces_frame, self.connectivity_frame, self.dns_frame]:
            for widget in frame.winfo_children():
                widget.destroy()
                
            ttk.Label(
                frame,
                text=f"Error running network diagnostics: {error_message}",
                foreground="red",
                justify="center",
                wraplength=400
            ).pack(anchor="center", pady=20)
            
        # Re-enable the Run Network Tests button
        self.run_network_tests_btn.configure(state="normal")
        self.is_running_diagnostics = False
    
    def run_quick_scan(self):
        """Run a quick diagnostic scan."""
        if self.is_running_diagnostics:
            return
            
        self.is_running_diagnostics = True
        self.quick_scan_button.configure(state="disabled")
        self.run_button.configure(state="disabled")
        
        # Show progress indicator
        self.status_frame.pack_forget()
        self.results_frame.pack_forget()
        self.progress_var.set(0)
        self.progress_status.configure(text="Starting diagnostics...")
        self.progress_frame.pack(fill="x", pady=(0, 10))
        
        # Start diagnostics in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._run_quick_scan_thread)
        thread.daemon = True
        thread.start()
        
    def _run_quick_scan_thread(self):
        """Background thread for running quick diagnostics."""
        try:
            # Update progress status
            self.progress_var.set(10)
            self._update_progress_status("Checking system status...")
            
            # Run basic diagnostics based on the OS platform
            if platform.system() == 'Linux':
                results = linux_diagnostics.run_diagnostics_tests()
            elif platform.system() == 'Windows':
                # Placeholder for Windows implementation
                results = {
                    'passed': True,
                    'tests': [
                        {'name': 'Placeholder', 'passed': True, 'value': 'N/A', 'message': 'Windows diagnostics not yet implemented'}
                    ]
                }
                # Simulate a delay for testing
                time.sleep(1)
            else:
                results = {
                    'passed': False,
                    'tests': [
                        {'name': 'Platform Support', 'passed': False, 'value': 'Unsupported', 'message': f'Platform {platform.system()} is not supported'}
                    ]
                }
            
            # Update progress
            self.progress_var.set(50)
            self._update_progress_status("Processing results...")
            
            # Store results
            self.diagnostics_results = results
            self.shared_state['diagnostic_results'] = results
            
            # Update UI with results
            self.progress_var.set(100)
            self._update_progress_status("Complete")
            
            # Call UI update on the main thread
            self.after(100, self._update_ui_with_results)
            
        except Exception as e:
            logging.error(f"Error in diagnostics: {e}")
            # Update UI on error
            self.after(100, lambda: self._update_ui_with_error(str(e)))
    
    def export_diagnostic_report(self):
        """Save the diagnostic report to a file."""
        if not self.diagnostics_results or 'report' not in self.diagnostics_results:
            messagebox.showinfo("No Report Available", "Please run diagnostics first to generate a report.")
            return
            
        # Get the current date and time for the filename
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        default_filename = f"diagnostic_report_{current_time}.txt"
        
        # Ask the user where to save the file
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=default_filename,
            title="Save Diagnostic Report"
        )
        
        if not filename:
            # User cancelled
            return
            
        try:
            with open(filename, 'w') as f:
                f.write(self.diagnostics_results['report'])
                
            messagebox.showinfo(
                "Report Saved", 
                f"Diagnostic report saved to {filename}"
            )
        except Exception as e:
            messagebox.showerror(
                "Error Saving Report", 
                f"An error occurred while saving the report: {str(e)}"
            )
            logging.error(f"Error saving diagnostic report: {e}")
    
    def _update_progress_status(self, text):
        """Update progress status text from a background thread."""
        self.after(0, lambda: self.progress_status.configure(text=text))
    
    def _update_ui_with_results(self):
        """Update the UI with diagnostic results."""
        # Hide progress
        self.progress_frame.pack_forget()
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        # Display results
        results_title = ttk.Label(
            self.results_frame,
            text="Diagnostic Results",
            font=("Arial", 12, "bold")
        )
        results_title.pack(anchor="w", pady=(0, 10))
        
        # Display overall status
        overall_frame = ttk.Frame(self.results_frame)
        overall_frame.pack(fill="x", pady=(0, 10))
        
        overall_status = "✅ All tests passed" if self.diagnostics_results.get('passed', False) else "❌ Some tests failed"
        overall_color = "green" if self.diagnostics_results.get('passed', False) else "red"
        
        ttk.Label(
            overall_frame, 
            text=overall_status,
            foreground=overall_color,
            font=("Arial", 11, "bold")
        ).pack(anchor="w")
        
        # Display individual test results
        if 'tests' in self.diagnostics_results:
            for test in self.diagnostics_results['tests']:
                test_frame = ttk.Frame(self.results_frame)
                test_frame.pack(fill="x", pady=(5, 0))
                
                status_icon = "✅" if test.get('passed', False) else "❌"
                status_color = "green" if test.get('passed', False) else "red"
                
                ttk.Label(
                    test_frame,
                    text=status_icon,
                    foreground=status_color
                ).pack(side="left", padx=(0, 5))
                
                ttk.Label(
                    test_frame,
                    text=f"{test.get('name', 'Unknown')}: "
                ).pack(side="left")
                
                ttk.Label(
                    test_frame,
                    text=test.get('value', 'N/A'),
                    foreground=status_color if not test.get('passed', False) else "black"
                ).pack(side="left", padx=(5, 5))
                
                if 'message' in test:
                    ttk.Label(
                        test_frame,
                        text=f"({test['message']})",
                        foreground="gray"
                    ).pack(side="left")
        
        # Show the results frame
        self.results_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Enable buttons
        self.quick_scan_button.configure(state="normal")
        self.run_button.configure(state="normal")
        self.save_button.configure(state="normal")
        self.is_running_diagnostics = False
    
    def _update_ui_with_error(self, error_message):
        """Update the UI when an error occurs during diagnostics."""
        # Hide progress
        self.progress_frame.pack_forget()
        
        # Show error message
        self.status_frame.pack(fill="both", expand=True, pady=(0, 10))
        for widget in self.status_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(
            self.status_frame,
            text=f"Error running diagnostics:\n{error_message}",
            foreground="red",
            justify="center"
        ).pack(anchor="center", pady=50)
        
        # Enable buttons
        self.quick_scan_button.configure(state="normal")
        self.run_button.configure(state="normal")
        self.is_running_diagnostics = False
        
    def run_full_diagnostics(self):
        """Run a full comprehensive diagnostic scan."""
        if self.is_running_diagnostics:
            return
            
        self.is_running_diagnostics = True
        self.quick_scan_button.configure(state="disabled")
        self.run_button.configure(state="disabled")
        
        # Show progress indicator
        self.status_frame.pack_forget()
        self.results_frame.pack_forget()
        self.progress_var.set(0)
        self.progress_status.configure(text="Starting comprehensive diagnostics...")
        self.progress_frame.pack(fill="x", pady=(0, 10))
        
        # Start diagnostics in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._run_full_diagnostics_thread)
        thread.daemon = True
        thread.start()
        
    def _run_full_diagnostics_thread(self):
        """Background thread for running full system diagnostics."""
        try:
            # Update progress status
            self.progress_var.set(5)
            self._update_progress_status("Collecting system information...")
            
            # Gather comprehensive diagnostics based on the OS platform
            if platform.system() == 'Linux':
                # Gather the diagnostics data
                self.progress_var.set(10)
                self._update_progress_status("Running hardware diagnostics...")
                diagnostics_data = linux_diagnostics.gather_linux_diagnostics(self.technician_name)
                
                # Format the report
                self.progress_var.set(80)
                self._update_progress_status("Generating diagnostic report...")
                formatted_report = linux_diagnostics.format_diagnostics_report(diagnostics_data)
                
                # Create a results dictionary with both raw data and formatted report
                results = {
                    'passed': diagnostics_data['health']['overall'] == 'Healthy',
                    'raw_data': diagnostics_data,
                    'report': formatted_report,
                    'tests': []  # We'll convert health data to test format below
                }
                
                # Convert health data to the tests format for display in the UI
                # CPU health
                results['tests'].append({
                    'name': 'CPU',
                    'passed': diagnostics_data['health']['cpu']['status'] == 'Healthy',
                    'value': diagnostics_data['health']['cpu']['status'],
                    'message': '; '.join(diagnostics_data['health']['cpu']['issues']) if diagnostics_data['health']['cpu']['issues'] else 'No issues detected'
                })
                
                # Memory health
                results['tests'].append({
                    'name': 'Memory',
                    'passed': diagnostics_data['health']['memory']['status'] == 'Healthy',
                    'value': diagnostics_data['health']['memory']['status'],
                    'message': '; '.join(diagnostics_data['health']['memory']['issues']) if diagnostics_data['health']['memory']['issues'] else 'No issues detected'
                })
                
                # Network health
                results['tests'].append({
                    'name': 'Network',
                    'passed': diagnostics_data['health']['network']['status'] == 'Healthy',
                    'value': diagnostics_data['health']['network']['status'],
                    'message': '; '.join(diagnostics_data['health']['network']['issues']) if diagnostics_data['health']['network']['issues'] else 'No issues detected'
                })
                
                # Storage health for each drive
                for drive in diagnostics_data['health']['storage']:
                    results['tests'].append({
                        'name': f"Storage: {drive['model']}",
                        'passed': drive['status'] == 'Healthy',
                        'value': drive['status'],
                        'message': '; '.join(drive['issues']) if drive['issues'] else 'No issues detected'
                    })
                    
            elif platform.system() == 'Windows':
                # Placeholder for Windows implementation
                # We'll simulate a full diagnostics with a delay
                for progress in range(10, 100, 10):
                    self.progress_var.set(progress)
                    self._update_progress_status(f"Simulating Windows diagnostics ({progress}%)...")
                    time.sleep(0.5)  # Simulate work being done
                    
                results = {
                    'passed': True,
                    'report': "Windows diagnostics simulation complete.",
                    'tests': [
                        {'name': 'CPU', 'passed': True, 'value': 'Healthy', 'message': 'Windows diagnostics not yet implemented'},
                        {'name': 'Memory', 'passed': True, 'value': 'Healthy', 'message': 'Windows diagnostics not yet implemented'},
                        {'name': 'Storage', 'passed': True, 'value': 'Healthy', 'message': 'Windows diagnostics not yet implemented'},
                        {'name': 'Network', 'passed': True, 'value': 'Healthy', 'message': 'Windows diagnostics not yet implemented'}
                    ]
                }
            else:
                results = {
                    'passed': False,
                    'report': f"Unsupported platform: {platform.system()}",
                    'tests': [
                        {'name': 'Platform Support', 'passed': False, 'value': 'Unsupported', 'message': f'Platform {platform.system()} is not supported'}
                    ]
                }
            
            # Update progress
            self.progress_var.set(95)
            self._update_progress_status("Finalizing results...")
            
            # Store results
            self.diagnostics_results = results
            self.shared_state['diagnostic_results'] = results
            
            # Update UI with results
            self.progress_var.set(100)
            self._update_progress_status("Complete")
            
            # Call UI update on the main thread
            self.after(100, self._update_ui_with_results)
            
        except Exception as e:
            logging.error(f"Error in full diagnostics: {e}")
            self.after(100, lambda: self._update_ui_with_error(str(e)))
        """Save the diagnostic report to a file."""
        if not self.diagnostics_results or 'report' not in self.diagnostics_results:
            messagebox.showinfo("No Report Available", "Please run diagnostics first to generate a report.")
            return
            
        # Get the current date and time for the filename
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        default_filename = f"diagnostic_report_{current_time}.txt"
        
        # Ask the user where to save the file
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=default_filename,
            title="Save Diagnostic Report"
        )
        
        if not filename:
            # User cancelled
            return
            
        try:
            with open(filename, 'w') as f:
                f.write(self.diagnostics_results['report'])
                
            messagebox.showinfo(
                "Report Saved", 
                f"Diagnostic report saved to {filename}"
            )
        except Exception as e:
            messagebox.showerror(
                "Error Saving Report", 
                f"An error occurred while saving the report: {str(e)}"
            )
            logging.error(f"Error saving diagnostic report: {e}")

