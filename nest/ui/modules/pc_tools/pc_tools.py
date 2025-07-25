#!/usr/bin/env python3
"""
PC Tools Module - Main Coordinator

This module serves as the entry point and main controller for the PC Tools module.
It creates the tabbed interface, manages shared state between tabs, and coordinates
communication between different components.
"""

import os
import sys
import time
import json
import math
import tkinter as tk
from tkinter import ttk
import platform
import logging
from typing import Dict, Any, Optional
import os
from pathlib import Path

# Import DiagnoseWorkflow locally to avoid circular imports
# Import workflow modules locally to avoid missing modules and circular imports
from nest.utils.feature_detection import FeatureDetection
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional

# Import the PC Tools components
from nest.ui.modules.pc_tools.system_info import SystemInfoTab
from nest.ui.modules.pc_tools.styles import PCToolsStyles
from nest.ui.modules.pc_tools.diagnostics import DiagnosticsTab
from nest.ui.modules.pc_tools.benchmarks import BenchmarksTab
from nest.ui.modules.pc_tools.utilities import UtilitiesTab
from nest.ui.modules.pc_tools.data_recovery import DataRecoveryTab


class PCToolsModule(ttk.Frame):
    """PC Tools module for Nest application."""

    def __init__(self, parent, current_user=None, app=None):
        """Initialize the PC Tools module with enhanced caching and performance tracking.
        
        Args:
            parent: Parent widget
            current_user: Dictionary containing current user information
            app: The main application instance for NestBot integration
        """
        super().__init__(parent, padding=10)
        self.parent = parent
        self.current_user = current_user or {}
        self.app = app
        
        # Session start time for performance tracking
        self.session_start_time = time.time()
        
        # Initialize performance metrics
        self.performance_metrics = {
            'startup_time': 0,
            'tab_switch_times': [],
            'data_load_times': {}
        }
        
        # Initialize styling
        styling_start = time.time()
        try:
            self.styles = PCToolsStyles(self)
            self.colors = self.styles.get_colors()
        except Exception as e:
            logging.error(f"Error initializing PC Tools styles: {e}")
            # Fallback to default colors if styles fail to load
            self.colors = {
                "primary": "#017E84",  # RepairDesk teal (official brand color)
                "primary_dark": "#016169", # Darker teal for hover states
                "secondary": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "background": "#F5F5F5",
                "card_bg": "#FFFFFF",
                "text_primary": "#212121",
                "text_secondary": "#757575",
                "border": "#E0E0E0",
                "highlight": "#E6F7F7",
                "accent": "#00B8D4"
            }
        
        # Record styling initialization time
        self.performance_metrics['styling_time'] = time.time() - styling_start
        
        # Initialize shared state with additional metadata
        self.shared_state = {
            # User and system information
            "current_user": current_user,
            "system_info": {},
            "diagnostic_results": {},
            "benchmark_results": {},
            "colors": self.colors,
            
            # Metadata and tracking
            "_session_id": f"pc_tools_session_{int(time.time())}",
            "_timestamps": {},
            "_performance": self.performance_metrics,
            "_cache_config": {
                "enabled": True,
                "ttl": 300,  # 5 minutes default cache lifetime
                "refresh_on_tab_switch": True
            }
        }
        
        # Cache configuration
        self.cache_config = self.shared_state["_cache_config"]
        
        # Initialize tab instances
        self.tab_instances = {}
        
        # Create the PC Tools interface
        self.create_ui()
        
        # Record startup time
        self.performance_metrics['startup_time'] = time.time() - self.session_start_time
        self.shared_state["_performance"] = self.performance_metrics
    
    def create_ui(self):
        """Create the PC Tools user interface."""
        # Main frame for PC Tools
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)
        
        # Create header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=5)
        
        # Module title with styled heading
        ttk.Label(
            header_frame, 
            text="PC Tools", 
            style="Heading.TLabel"
        ).pack(side="left", padx=10)
        
        # Add info about current technician
        tech_name = self.current_user.get("name", "Unknown Technician")
        ttk.Label(
            header_frame, 
            text=f"Technician: {tech_name}"
        ).pack(side="right", padx=10)
        
        # Add separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", padx=10, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Initialize tabs
        self.init_tabs()
        
        # Status frame at the bottom
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", side="bottom")
        
        ttk.Separator(status_frame, orient="horizontal").pack(fill="x")
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            foreground=self.colors["text_secondary"]
        )
        self.status_label.pack(side="left", padx=10, pady=5)
    
    def init_tabs(self):
        """Initialize the tabs for PC Tools."""
        try:
            system_info_frame = ttk.Frame(self.notebook)
            self.notebook.add(system_info_frame, text="System Info")
            system_info_tab = SystemInfoTab(system_info_frame, self.shared_state)
            system_info_tab.pack(fill="both", expand=True)
            self.tab_instances["system_info"] = system_info_tab
            logging.info("System Info tab initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing System Info tab: {e}")
            # Create a placeholder as fallback in case of error
            system_info_frame = ttk.Frame(self.notebook)
            self.notebook.add(system_info_frame, text="System Info")
            self._create_error_tab(system_info_frame, "System Information", str(e))
        
        # Initialize Diagnostics tab with our new implementation
        try:
            diagnostics_frame = ttk.Frame(self.notebook)
            self.notebook.add(diagnostics_frame, text="Diagnostics")
            diagnostics_tab = DiagnosticsTab(diagnostics_frame, self.shared_state)
            diagnostics_tab.pack(fill="both", expand=True)
            self.tab_instances["diagnostics"] = diagnostics_tab
            logging.info("Diagnostics tab initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing Diagnostics tab: {e}")
            # Create a placeholder as fallback in case of error
            diagnostics_frame = ttk.Frame(self.notebook)
            self.notebook.add(diagnostics_frame, text="Diagnostics")
            self._create_error_tab(diagnostics_frame, "Diagnostics", str(e))
        
        # Benchmarks Tab
        try:
            benchmarks_frame = ttk.Frame(self.notebook)
            self.notebook.add(benchmarks_frame, text="Benchmarks")
            benchmarks_tab = BenchmarksTab(benchmarks_frame, self.shared_state)
            benchmarks_tab.pack(fill="both", expand=True)
            self.tab_instances["benchmarks"] = benchmarks_tab
            logging.info("Benchmarks tab initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing Benchmarks tab: {e}")
            benchmarks_frame = ttk.Frame(self.notebook)
            self.notebook.add(benchmarks_frame, text="Benchmarks")
            self._create_error_tab(benchmarks_frame, "Benchmarks", str(e))
        
        # Initialize Utilities tab with real implementation
        try:
            utilities_frame = ttk.Frame(self.notebook)
            self.notebook.add(utilities_frame, text="Utilities")
            utilities_tab = UtilitiesTab(utilities_frame, self.shared_state)
            utilities_tab.pack(fill="both", expand=True)
            self.tab_instances["utilities"] = utilities_tab
            logging.info("Utilities tab initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing Utilities tab: {e}")
            utilities_frame = ttk.Frame(self.notebook)
            self.notebook.add(utilities_frame, text="Utilities")
            self._create_error_tab(utilities_frame, "Utilities", str(e))
        
        # Initialize Data Recovery tab
        try:
            data_recovery_frame = ttk.Frame(self.notebook)
            self.notebook.add(data_recovery_frame, text="Data Recovery")
            data_recovery_tab = DataRecoveryTab(data_recovery_frame, self.shared_state)
            data_recovery_tab.pack(fill="both", expand=True)
            self.tab_instances["data_recovery"] = data_recovery_tab
            logging.info("Data Recovery tab initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing Data Recovery tab: {e}")
            data_recovery_frame = ttk.Frame(self.notebook)
            self.notebook.add(data_recovery_frame, text="Data Recovery")
            self._create_error_tab(data_recovery_frame, "Data Recovery", str(e))
        
        # Initialize remaining placeholder tabs using our PlaceholderTab class
        placeholder_tabs = [
            {"name": "Manufacturer", "id": "manufacturer"}
        ]
        
        # Create each placeholder tab
        for tab in placeholder_tabs:
            try:
                frame = ttk.Frame(self.notebook)
                self.notebook.add(frame, text=tab["name"])
                placeholder = PlaceholderTab(frame, tab["name"], self.shared_state)
                placeholder.pack(fill="both", expand=True)
                self.tab_instances[tab["id"]] = placeholder
                logging.info(f"{tab['name']} tab initialized as placeholder")
            except Exception as e:
                logging.error(f"Error initializing {tab['name']} tab: {e}")
                frame = ttk.Frame(self.notebook)
                self.notebook.add(frame, text=tab["name"])
                self._create_error_tab(frame, tab["name"], str(e))
        
        # Add Analytics tab (hidden by default for technicians)
        if self.current_user.get("role") == "admin" or "debug" in self.shared_state:
            try:
                analytics_frame = ttk.Frame(self.notebook)
                self.notebook.add(analytics_frame, text="Analytics")
                self.create_analytics_tab(analytics_frame)
                logging.info("Analytics tab initialized successfully")
            except Exception as e:
                logging.error(f"Error initializing Analytics tab: {e}")
                frame = ttk.Frame(self.notebook)
                self.notebook.add(frame, text="Analytics")
                self._create_error_tab(frame, "Analytics", str(e))
        
        # Set up tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
    def create_analytics_tab(self, parent):
        """Create the Analytics tab with performance metrics.
        
        Args:
            parent: Parent frame for the tab
        """
        # Main frame for analytics
        main_frame = ttk.Frame(parent, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Header with title
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="PC Tools Analytics",
            style="Heading.TLabel"
        ).pack(side="left", padx=5)
        
        # Session info
        session_id = self.shared_state.get("_session_id", "Unknown")
        session_time = time.strftime("Started: %Y-%m-%d %H:%M:%S", time.localtime(self.session_start_time))
        ttk.Label(
            header_frame,
            text=f"{session_time}",
            foreground=self.colors["text_secondary"]
        ).pack(side="right", padx=5)
        
        # Create notebook for analytics sections
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=10)
        
        # Performance Metrics tab
        perf_frame = ttk.Frame(notebook, padding=10)
        notebook.add(perf_frame, text="Performance")
        
        # App startup metrics
        startup_frame = ttk.LabelFrame(perf_frame, text="Application Startup")
        startup_frame.pack(fill="x", pady=10)
        
        startup_time = self.performance_metrics.get('startup_time', 0) * 1000  # Convert to ms
        styling_time = self.performance_metrics.get('styling_time', 0) * 1000  # Convert to ms
        
        metrics_frame = ttk.Frame(startup_frame)
        metrics_frame.pack(fill="x", padx=10, pady=10)
        
        # Create a canvas for the startup time gauge
        startup_canvas = tk.Canvas(metrics_frame, width=200, height=100, bg=self.colors["card_bg"])
        startup_canvas.grid(row=0, column=0, padx=10, pady=10)
        
        # Draw startup time gauge with RepairDesk teal color
        self._draw_gauge(
            canvas=startup_canvas, 
            value=min(startup_time, 2000) / 2000 * 100,  # Cap at 2000ms for viz
            label=f"Total Startup: {startup_time:.1f}ms", 
            color=self.colors["primary"],
            threshold_good=500,
            threshold_warn=1000
        )
        
        # Create a canvas for styling time gauge
        styling_canvas = tk.Canvas(metrics_frame, width=200, height=100, bg=self.colors["card_bg"])
        styling_canvas.grid(row=0, column=1, padx=10, pady=10)
        
        # Draw styling time gauge with RepairDesk teal color
        self._draw_gauge(
            canvas=styling_canvas, 
            value=min(styling_time, 500) / 500 * 100,  # Cap at 500ms for viz
            label=f"UI Styling: {styling_time:.1f}ms", 
            color=self.colors["primary"],
            threshold_good=100,
            threshold_warn=250
        )
        
        # Data loading metrics
        data_frame = ttk.LabelFrame(perf_frame, text="Data Loading Times")
        data_frame.pack(fill="x", pady=10)
        
        # Create data loading metrics table
        data_table = ttk.Frame(data_frame)
        data_table.pack(fill="x", padx=10, pady=10)
        
        # Table headers
        ttk.Label(data_table, text="Data Type", width=20, style="Subheading.TLabel").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(data_table, text="Load Time", width=15, style="Subheading.TLabel").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(data_table, text="Status", width=15, style="Subheading.TLabel").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Table separator
        separator = ttk.Separator(data_table, orient="horizontal")
        separator.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Add data load times
        data_load_times = self.performance_metrics.get('data_load_times', {})
        if data_load_times:
            row = 2
            for data_type, metrics in data_load_times.items():
                load_time = (metrics.get('completion_time', 0) - metrics.get('start_time', 0)) * 1000  # ms
                
                # Determine status based on load time
                if load_time < 1000:  # Less than 1 second
                    status = "Good"
                    status_style = "Good.TLabel"
                elif load_time < 3000:  # Less than 3 seconds
                    status = "Acceptable"
                    status_style = "Warning.TLabel"
                else:
                    status = "Slow"
                    status_style = "Critical.TLabel"
                
                # Add row to table
                ttk.Label(data_table, text=data_type.title(), width=20).grid(row=row, column=0, padx=5, pady=5, sticky="w")
                ttk.Label(data_table, text=f"{load_time:.1f} ms", width=15).grid(row=row, column=1, padx=5, pady=5, sticky="w")
                ttk.Label(data_table, text=status, width=15, style=status_style).grid(row=row, column=2, padx=5, pady=5, sticky="w")
                row += 1
        else:
            ttk.Label(data_table, text="No data loading metrics available yet.", foreground=self.colors["text_secondary"]).grid(row=2, column=0, columnspan=3, padx=5, pady=20)
        
        # Cache Management tab
        cache_frame = ttk.Frame(notebook, padding=10)
        notebook.add(cache_frame, text="Cache Management")
        
        # Cache configuration section
        config_frame = ttk.LabelFrame(cache_frame, text="Cache Configuration")
        config_frame.pack(fill="x", pady=10)
        
        config_grid = ttk.Frame(config_frame)
        config_grid.pack(fill="x", padx=10, pady=10)
        
        # Cache enabled switch
        ttk.Label(config_grid, text="Cache Enabled:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        cache_enabled_var = tk.BooleanVar(value=self.cache_config.get("enabled", True))
        ttk.Checkbutton(config_grid, variable=cache_enabled_var, command=lambda: self._update_cache_config("enabled", cache_enabled_var.get())).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Cache TTL (Time to Live)
        ttk.Label(config_grid, text="Cache TTL (seconds):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttl_options = ["60", "300", "600", "1800", "3600"]
        ttl_var = tk.StringVar(value=str(self.cache_config.get("ttl", 300)))
        ttl_dropdown = ttk.Combobox(config_grid, textvariable=ttl_var, values=ttl_options, width=10, state="readonly")
        ttl_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttl_dropdown.bind("<<ComboboxSelected>>", lambda e: self._update_cache_config("ttl", int(ttl_var.get())))
        
        # Refresh on tab switch
        ttk.Label(config_grid, text="Refresh on Tab Switch:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        tab_refresh_var = tk.BooleanVar(value=self.cache_config.get("refresh_on_tab_switch", True))
        ttk.Checkbutton(config_grid, variable=tab_refresh_var, command=lambda: self._update_cache_config("refresh_on_tab_switch", tab_refresh_var.get())).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Cache statistics section
        stats_frame = ttk.LabelFrame(cache_frame, text="Cache Statistics")
        stats_frame.pack(fill="x", pady=10)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill="x", padx=10, pady=10)
        
        # Count timestamps to get cached item count
        timestamps = self.shared_state.get('_timestamps', {})
        cache_count = len([k for k in timestamps.keys() if not k.startswith('_')])
        
        ttk.Label(stats_grid, text="Cached Items:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(stats_grid, text=str(cache_count)).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Button to clear all caches
        ttk.Button(
            cache_frame,
            text="Clear All Caches",
            command=self._clear_all_caches,
            style="Danger.TButton"
        ).pack(side="right", padx=10, pady=10)
    
    def _draw_gauge(self, canvas, value, label, color, threshold_good=50, threshold_warn=75):
        """Draw a semi-circular gauge on a canvas with RepairDesk styling.
        
        Args:
            canvas: The canvas to draw on
            value: Value between 0-100 to display
            label: Text label for the gauge
            color: Primary color for the gauge (should be RepairDesk teal)
            threshold_good: Upper bound for good values (green)
            threshold_warn: Upper bound for warning values (yellow)
        """
        # Clear the canvas
        canvas.delete("all")
        
        # Calculate gauge parameters
        width = canvas.winfo_reqwidth()
        height = canvas.winfo_reqheight()
        center_x = width // 2
        center_y = height - 10
        radius = min(width, height) - 20
        
        # Draw background arc
        canvas.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=180, extent=180,
            outline=self.colors["border"], width=10,
            style=tk.ARC
        )
        
        # Determine color based on value
        if value <= threshold_good:
            gauge_color = self.colors["secondary"]  # Green
        elif value <= threshold_warn:
            gauge_color = self.colors["warning"]  # Yellow
        else:
            gauge_color = self.colors["danger"]  # Red
        
        # Draw value arc
        extent = min(value, 100) / 100 * 180
        canvas.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=180, extent=extent,
            outline=gauge_color, width=10,
            style=tk.ARC
        )
        
        # Draw indicator line
        angle = math.radians(180 - extent)
        x = center_x + (radius * math.cos(angle))
        y = center_y - (radius * math.sin(angle))
        canvas.create_line(center_x, center_y, x, y, fill=gauge_color, width=2)
        
        # Draw text for value and label
        canvas.create_text(center_x, height - 15, text=label, fill=self.colors["text_primary"], font=("Segoe UI", 10))
        
    def _update_cache_config(self, key, value):
        """Update the cache configuration.
        
        Args:
            key: Config key to update
            value: New value
        """
        self.cache_config[key] = value
        self.shared_state["_cache_config"] = self.cache_config
        logging.info(f"Cache config updated: {key} = {value}")
        self.update_status(f"Cache configuration updated: {key} = {value}")
        
    def _clear_all_caches(self):
        """Clear all cached data."""
        # Clear timestamps
        self.shared_state["_timestamps"] = {}
        
        # Log and notify
        logging.info("All caches cleared")
        self.update_status("All caches cleared")
    
    def _create_error_tab(self, parent, tab_name, error_message):
        """Create an error tab when a tab fails to initialize.
        
        Args:
            parent: Parent frame
            tab_name: Name of the tab that failed
            error_message: Error message to display
        """
        error_frame = ttk.Frame(parent)
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(
            error_frame,
            text=f"Error Loading {tab_name} Tab",
            font=("Segoe UI", 14, "bold"),
            foreground=self.colors["danger"]
        ).pack(pady=(20, 10))
        
        ttk.Label(
            error_frame,
            text=f"An error occurred while loading this tab: {error_message}",
            wraplength=400
        ).pack(pady=10)
        
        ttk.Button(
            error_frame,
            text="Retry",
            command=lambda: self.update_status(f"Retry not yet implemented for {tab_name}")
        ).pack(pady=20)
    
    def on_tab_changed(self, event):
        """Handle tab change event with intelligent cache refresh policy.
        
        Args:
            event: Tab change event
        """
        # Get the currently selected tab
        tab_id = self.notebook.select()
        if not tab_id:
            return
        
        # Get the tab name
        tab_name = self.notebook.tab(tab_id, 'text')
        if not tab_name:
            return
        
        # Start timing tab switch performance
        tab_switch_start = time.time()
        
        # Get the tab instance based on name (lowercase with underscore)
        instance_key = tab_name.lower().replace(' ', '_')
        
        # Update the status
        self.update_status(f"Switched to {tab_name} tab")
        
        # Check if we should refresh based on cache config
        should_refresh = self.cache_config.get("refresh_on_tab_switch", True)
        
        # Get tab instance and refresh if needed
        tab_instance = self.tab_instances.get(instance_key)
        if tab_instance and hasattr(tab_instance, 'refresh') and should_refresh:
            # Check if the tab has data that needs refreshing based on cache timestamps
            needs_refresh = False
            if instance_key == "system_info":
                system_info = self.shared_state.get("system_info", {})
                timestamps = self.shared_state.get("_timestamps", {})
                
                # Get timestamp for system_info
                sys_info_timestamp = timestamps.get("system_info", 0)
                ttl = self.cache_config.get("ttl", 300)  # 5 minutes default
                
                # Check if cache expired
                if time.time() - sys_info_timestamp > ttl:
                    needs_refresh = True
                    logging.debug(f"Cache expired for {instance_key}, refreshing")
            else:
                # For other tabs, always refresh on switch if the setting is enabled
                needs_refresh = True
            
            # Refresh if needed
            if needs_refresh:
                try:
                    tab_instance.refresh()
                    logging.debug(f"Refreshed {tab_name} tab successfully")
                except Exception as e:
                    logging.error(f"Error refreshing {tab_name} tab: {e}")
            else:
                logging.debug(f"Using cached data for {tab_name} tab")
        
        # Record tab switch performance
        tab_switch_time = time.time() - tab_switch_start
        self.performance_metrics['tab_switch_times'].append({
            'tab': tab_name,
            'time': tab_switch_time * 1000,  # Convert to ms
            'timestamp': time.time()
        })
        
        # Keep only the most recent 20 tab switches
        if len(self.performance_metrics['tab_switch_times']) > 20:
            self.performance_metrics['tab_switch_times'] = self.performance_metrics['tab_switch_times'][-20:]
    
    def update_status(self, message):
        """Update status bar with a message."""
        self.status_var.set(message)

    def update_shared_state(self, key: str, value: Any) -> None:
        """Update shared state dictionary with timestamp tracking and efficient change detection.
        
        Args:
            key: The key to update
            value: The new value
        """
        old_value = self.shared_state.get(key)
        
        # Only process if value has changed (using deep comparison for collections)
        if isinstance(old_value, dict) and isinstance(value, dict):
            # For dictionaries, we can do partial updates to avoid unnecessary notifications
            has_changes = False
            for k, v in value.items():
                if k not in old_value or old_value[k] != v:
                    old_value[k] = v
                    has_changes = True
                    
            # If we made changes, update the timestamp
            if has_changes:
                # Add timestamp for tracking when data was last updated
                self.shared_state.setdefault('_timestamps', {})[key] = time.time()
                self._notify_state_change(key, self.shared_state[key])
        elif old_value != value:
            # Regular value update
            self.shared_state[key] = value
            
            # Add timestamp for tracking when data was last updated
            self.shared_state.setdefault('_timestamps', {})[key] = time.time()
            
            # Track performance for data loading if applicable
            if key == "system_info" and isinstance(value, dict) and value.get("basic_info_loaded", False):
                if not self.performance_metrics['data_load_times'].get("system_info"):
                    # First time loading system info in this session, record metrics
                    self.performance_metrics['data_load_times']["system_info"] = {
                        'start_time': time.time() - value.get('_load_start_time', 0),
                        'completion_time': time.time()
                    }
                    # Update the performance metrics in shared state
                    self.shared_state["_performance"] = self.performance_metrics
            
            # Notify of the change
            self._notify_state_change(key, value)
    
    def get_cached_data(self, key: str, default=None, max_age_seconds=None) -> Any:
        """Get data from shared state with optional cache validation.
        
        Args:
            key: The key to retrieve
            default: Default value if key doesn't exist or cache is invalid
            max_age_seconds: Maximum age of cached data in seconds (None for no limit)
            
        Returns:
            The cached value if valid, otherwise the default value
        """
        # Check if caching is enabled
        if not self.cache_config.get("enabled", True):
            return default
            
        # Get the value from shared state
        value = self.shared_state.get(key)
        if value is None:
            return default
            
        # If no max age specified, use the default TTL from cache config
        if max_age_seconds is None:
            max_age_seconds = self.cache_config.get("ttl", 300)  # Default 5 minutes
            
        # Check if the data is still valid based on timestamp
        timestamps = self.shared_state.get('_timestamps', {})
        if key in timestamps:
            age = time.time() - timestamps[key]
            if age > max_age_seconds:
                logging.debug(f"Cache for {key} expired (age: {age:.1f}s, max: {max_age_seconds}s)")
                return default
        
        return value
    
    def _notify_state_change(self, key, value):
        """Notify tabs of state changes with improved error handling and performance tracking.
        
        Args:
            key: The key that changed
            value: The new value
        """
        # Record notification start time for performance tracking
        notification_start = time.time()
        
        # Track successful and failed notifications
        notification_stats = {
            'total': 0,
            'successful': 0,
            'failed': 0
        }
        
        # Map of keys to handler methods
        handler_map = {
            "system_info": "on_system_info_updated",
            "current_ticket": "on_ticket_updated",
            "diagnostic_results": "on_diagnostic_results_updated",
            "benchmark_results": "on_benchmark_results_updated"
        }
        
        # Get the specific handler for this key, if any
        handler_name = handler_map.get(key)
        
        # If we have a specific handler for this key
        if handler_name:
            # For all tabs, call their specific handler if they have one
            for tab_id, tab_instance in self.tab_instances.items():
                if hasattr(tab_instance, handler_name):
                    notification_stats['total'] += 1
                    try:
                        # Call the specific handler method
                        getattr(tab_instance, handler_name)()
                        notification_stats['successful'] += 1
                    except Exception as e:
                        notification_stats['failed'] += 1
                        logging.error(f"Error notifying {tab_id} tab of {key} update: {e}")
        
        # Special case for current_ticket - update window title
        if key == "current_ticket" and value and hasattr(self.parent, "title"):
            try:
                # Update window title with ticket information
                self.parent.title(f"Nest PC Tools - Ticket #{value}")
            except Exception as e:
                logging.error(f"Error updating window title: {e}")
        
        # Generic handlers for all state changes
        for tab_id, tab_instance in self.tab_instances.items():
            # If the tab has a generic handler for all state changes
            if hasattr(tab_instance, "on_shared_state_updated"):
                notification_stats['total'] += 1
                try:
                    tab_instance.on_shared_state_updated(key, value)
                    notification_stats['successful'] += 1
                except Exception as e:
                    notification_stats['failed'] += 1
                    logging.error(f"Error calling generic handler for {tab_id} tab: {e}")
        
        # Track performance if this is a significant update
        notification_time = time.time() - notification_start
        if notification_time > 0.05:  # Only log if it took more than 50ms
            logging.debug(f"State notification for {key} took {notification_time*1000:.1f}ms "
                         f"({notification_stats['successful']}/{notification_stats['total']} successful)")
        
        # Update performance metrics if this is a key we're tracking
        if key in ['system_info', 'diagnostic_results', 'benchmark_results']:
            if '_notification_times' not in self.performance_metrics:
                self.performance_metrics['_notification_times'] = {}
            
            # Store the notification time for this key
            self.performance_metrics['_notification_times'][key] = notification_time


# Placeholder implementation for tabs until real implementations are ready
class PlaceholderTab(ttk.Frame):
    """Placeholder tab for PC Tools module with support for future module integrations."""
    
    def __init__(self, parent, name, shared_state):
        """Initialize a placeholder tab with modern RepairDesk styling.
        
        Args:
            parent: Parent widget
            name: Tab name
            shared_state: Shared state dictionary
        """
        super().__init__(parent)
        self.parent = parent
        self.name = name
        self.shared_state = shared_state
        
        # Track when this tab was last refreshed
        self.last_refresh_time = None
        
        # Get RepairDesk colors from shared state
        self.colors = shared_state.get("colors", {
            "primary": "#017E84",   # RepairDesk teal
            "background": "#F5F5F5", 
            "card_bg": "#FFFFFF",
            "text_primary": "#212121"
        })
        
        # Determine the icon and description based on tab name
        tab_info = self._get_tab_info()
        
        # Create a card-style UI for the placeholder
        card_frame = ttk.Frame(self, style="Card.TFrame")
        card_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Add header with tab name
        header_frame = ttk.Frame(card_frame)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(
            header_frame, 
            text=f"{self.name}",
            style="Heading.TLabel"
        ).pack(anchor="w")
        
        ttk.Separator(card_frame, orient="horizontal").pack(fill="x", padx=20, pady=10)
        
        # Content area
        content_frame = ttk.Frame(card_frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Icon and description
        ttk.Label(
            content_frame,
            text=tab_info["icon"],
            font=("Segoe UI", 36),
            foreground=self.colors["primary"]
        ).pack(pady=(20, 10))
        
        ttk.Label(
            content_frame,
            text="Coming Soon",
            font=("Segoe UI", 18, "bold"),
            foreground=self.colors["text_primary"]
        ).pack(pady=(0, 10))
        
        ttk.Label(
            content_frame,
            text=tab_info["description"],
            wraplength=400,
            justify="center"
        ).pack(padx=40, pady=10)
        
        # Feature list if available
        if tab_info.get("features"):
            features_frame = ttk.Frame(content_frame)
            features_frame.pack(fill="x", padx=40, pady=10)
            
            ttk.Label(
                features_frame,
                text="Key Features:",
                font=("Segoe UI", 12, "bold")
            ).pack(anchor="w", pady=(10, 5))
            
            for feature in tab_info["features"]:
                ttk.Label(
                    features_frame,
                    text=f"• {feature}",
                    wraplength=400,
                    justify="left"
                ).pack(anchor="w", pady=2)
        
        # Button area at bottom
        button_frame = ttk.Frame(card_frame)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        ttk.Button(
            button_frame,
            text="Refresh",
            command=self.refresh_if_needed
        ).pack(side="right", padx=5)
    
    def _get_tab_info(self):
        """Get tab-specific information for display.
        
        Returns:
            Dictionary with tab information including icon, description, and features
        """
        tab_name_lower = self.name.lower()
        
        # Default info
        info = {
            "icon": "🔧",  # Default tools icon
            "description": "This feature is coming soon to the PC Tools module.",
            "features": []
        }
        
        # Tab-specific customizations
        if "diagnostics" in tab_name_lower:
            info["icon"] = "🔍"
            info["description"] = "The Diagnostics tab will provide automated testing and troubleshooting tools for hardware and software issues."
            info["features"] = [
                "Hardware component testing",
                "Memory diagnostics",
                "Storage health analysis",
                "Network connectivity tests",
                "Automated diagnostic reporting"
            ]
        elif "benchmarks" in tab_name_lower:
            info["icon"] = "📊"
            info["description"] = "The Benchmarks tab will allow you to measure and compare system performance metrics."
            info["features"] = [
                "CPU performance testing",
                "Memory speed benchmarks",
                "Disk read/write speed tests",
                "Graphics performance analysis",
                "Before/after comparison reports"
            ]
        elif "utilities" in tab_name_lower:
            info["icon"] = "🧰"
            info["description"] = "The Utilities tab will provide helpful tools for system maintenance and repair."
            info["features"] = [
                "System cleanup tools",
                "Boot repair utilities",
                "Driver management",
                "File recovery options",
                "Windows update troubleshooting"
            ]
        elif "manufacturer" in tab_name_lower:
            info["icon"] = "🏭"
            info["description"] = "The Manufacturer tab will provide brand-specific diagnostics and repair tools."
            info["features"] = [
                "Dell SupportAssist integration",
                "HP Support Assistant tools",
                "Lenovo Vantage utilities",
                "ASUS diagnostics",
                "Manufacturer warranty lookup"
            ]
        
        return info
    
    def refresh_if_needed(self):
        """Refresh tab data if needed."""
        logging.info(f"Refreshing {self.name} tab")
        self.last_refresh_time = time.time()
    
    def refresh(self):
        """Refresh the tab data."""
        logging.info(f"Refreshing {self.name} tab")
        self.last_refresh_time = time.time()
    
    def refresh_with_context(self, context):
        """Refresh tab with context information about data freshness.
        
        Args:
            context: Dictionary containing data age and other context information
        """
        logging.info(f"Context-aware refresh for {self.name} tab")
        
        # Check data age for relevant information
        data_age = context.get('data_age', {})
        
        # Log some diagnostic information about data freshness
        for key, age in data_age.items():
            if isinstance(age, (int, float)) and age > 300:  # Older than 5 minutes
                logging.info(f"{self.name} tab: Data '{key}' is {int(age)} seconds old")
        
        # Update last refresh time
        self.last_refresh_time = time.time()
    
    def on_system_info_updated(self):
        """Handle update to system info in shared state."""
        logging.info(f"{self.name} tab: System info updated")
        
    def on_ticket_updated(self):
        """Handle update to ticket in shared state."""
        logging.info(f"{self.name} tab: Ticket updated")


# For direct testing
if __name__ == "__main__":
    # Simple test app
    root = tk.Tk()
    root.title("PC Tools Module Test")
    root.geometry("1024x768")
    
    app = PCToolsModule(root, {"name": "Test User"})
    app.pack(fill="both", expand=True)
    
    root.mainloop()
