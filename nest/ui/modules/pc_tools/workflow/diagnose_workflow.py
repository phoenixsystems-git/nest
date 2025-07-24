# nest/ui/modules/pc_tools/workflow/diagnose_workflow.py
import tkinter as tk
from tkinter import ttk
import platform
import asyncio
import threading
import logging
from typing import Dict, Any, Optional, Callable

from nest.ui.modules.pc_tools.components.system_gauge import SystemGauge
from nest.utils.diagnostics.storage_health import StorageHealthAnalyzer
from nest.utils.feature_detection import FeatureDetection


class DiagnoseWorkflow:
    """Cross-platform diagnostic workflow manager for PC Tools
    
    This class manages the diagnostic workflow UI and functionality,
    with platform-specific optimizations while maintaining a consistent API.
    """
    
    def __init__(self, parent, shared_state):
        """Initialize the diagnostic workflow
        
        Args:
            parent: Parent frame for this workflow
            shared_state: Shared state dictionary for the PC Tools module
        """
        self.parent = parent
        self.shared_state = shared_state
        self.system = platform.system().lower()
        self.feature_detection = FeatureDetection()
        
        # Initialize analyzers
        self.storage_analyzer = StorageHealthAnalyzer()
        
        # Setup UI states
        self.current_component = tk.StringVar(value="system")
        self.analysis_running = False
        self.analysis_results = {}
        
        # Create UI components
        self.create_ui()
        
    def create_ui(self):
        """Create the diagnostic workflow UI with platform-specific optimizations"""
        container = ttk.Frame(self.parent, padding=10)
        container.pack(fill="both", expand=True)
        
        # Left panel - Component selection
        left_panel = ttk.Frame(container, width=200)
        left_panel.pack(side="left", fill="y", padx=(0, 15))
        left_panel.pack_propagate(False)
        
        ttk.Label(
            left_panel, 
            text="System Components",
            style="Subheading.TLabel"
        ).pack(anchor="w", pady=(0, 10))
        
        # Component selection list
        components = [
            ("system", "System Overview"),
            ("cpu", "Processor"),
            ("memory", "Memory"),
            ("storage", "Storage"),
            ("network", "Network")
        ]
        
        # Add battery component only on laptops/mobile devices
        if self._is_battery_present():
            components.append(("battery", "Battery"))
        
        # Add OS-specific components
        if self.system == "windows":
            components.append(("windows", "Windows"))
        elif self.system == "linux":
            components.append(("linux", "Linux"))
        
        for id, label in components:
            rb = ttk.Radiobutton(
                left_panel,
                text=label,
                value=id,
                variable=self.current_component,
                command=self._on_component_selected
            )
            rb.pack(anchor="w", pady=3)
        
        # Add diagnostic buttons
        ttk.Separator(left_panel, orient="horizontal").pack(fill="x", pady=10)
        
        ttk.Button(
            left_panel,
            text="Run Quick Scan",
            command=self.run_quick_scan,
            style="Secondary.TButton"
        ).pack(fill="x", pady=(0, 5))
        
        ttk.Button(
            left_panel,
            text="Run Full Diagnostics",
            command=self.run_full_diagnostics,
            style="Primary.TButton"
        ).pack(fill="x")
        
        # Right panel - Component details and actions
        self.details_panel = ttk.Frame(container)
        self.details_panel.pack(side="right", fill="both", expand=True)
        
        # Progress indicator (initially hidden)
        self.progress_frame = ttk.Frame(self.details_panel)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_label = ttk.Label(self.progress_frame, text="Running diagnostics...")
        self.progress_label.pack(pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            mode="determinate", 
            variable=self.progress_var,
            length=300
        )
        self.progress_bar.pack(fill="x")
        
        # Initial view is the dashboard
        self.create_dashboard_view()
        
    def create_dashboard_view(self):
        """Create the dashboard view with system health visualization"""
        # Clear details panel except progress frame
        for widget in self.details_panel.winfo_children():
            if widget != self.progress_frame:
                widget.destroy()
        
        # Dashboard container
        dashboard = ttk.Frame(self.details_panel)
        dashboard.pack(fill="both", expand=True)
        
        # Dashboard title
        ttk.Label(
            dashboard, 
            text="System Health Dashboard",
            style="Heading.TLabel"
        ).pack(anchor="w", pady=(0, 15))
        
        # System health overview
        health_frame = ttk.Frame(dashboard)
        health_frame.pack(fill="x", pady=(0, 20))
        
        # Get system data from shared state or compute it
        system_data = self.shared_state.get("system_info", {})
        
        # Calculate health scores (default values if not available)
        cpu_health = system_data.get("cpu_health", 75)
        memory_health = system_data.get("memory_health", 80)
        storage_health = system_data.get("storage_health", 85)
        network_health = system_data.get("network_health", 90)
        
        # Weighted overall health
        weights = {"cpu": 0.25, "memory": 0.25, "storage": 0.4, "network": 0.1}
        overall_health = int(
            (cpu_health * weights["cpu"] + 
             memory_health * weights["memory"] + 
             storage_health * weights["storage"] + 
             network_health * weights["network"]) / sum(weights.values())
        )
        
        # Create gauge grid with platform-specific layout adjustment
        gauges_frame = ttk.Frame(health_frame)
        gauges_frame.pack(fill="x")
        
        # Adjust layout based on platform
        if self.system == "windows":
            pad_x, pad_y = 15, 15
        else:  # Linux may need slightly different spacing
            pad_x, pad_y = 12, 12
        
        # Overall system health (larger)
        overall_gauge = SystemGauge(gauges_frame, "Overall Health")
        overall_gauge.grid(row=0, column=0, columnspan=2, padx=pad_x, pady=pad_y)
        overall_gauge.draw_gauge(overall_health)
        
        # Component health gauges
        cpu_gauge = SystemGauge(gauges_frame, "CPU")
        cpu_gauge.grid(row=1, column=0, padx=pad_x, pady=pad_y)
        cpu_gauge.draw_gauge(cpu_health)
        
        memory_gauge = SystemGauge(gauges_frame, "Memory")
        memory_gauge.grid(row=1, column=1, padx=pad_x, pady=pad_y)
        memory_gauge.draw_gauge(memory_health)
        
        storage_gauge = SystemGauge(gauges_frame, "Storage")
        storage_gauge.grid(row=1, column=2, padx=pad_x, pady=pad_y)
        storage_gauge.draw_gauge(storage_health)
        
        network_gauge = SystemGauge(gauges_frame, "Network")
        network_gauge.grid(row=1, column=3, padx=pad_x, pady=pad_y)
        network_gauge.draw_gauge(network_health)
        
        # Key system specifications
        specs_frame = ttk.LabelFrame(dashboard, text="System Specifications", padding=10)
        specs_frame.pack(fill="x", pady=(0, 15))
        
        # Two-column grid for specs with platform-specific content
        specs_data = [
            ("Processor:", system_data.get("cpu_model", "Unknown")),
            ("Memory:", f"{system_data.get('memory_total_gb', 0)} GB"),
            ("Operating System:", self._get_os_name()),
            ("System Model:", system_data.get("system_model", "Unknown")),
            ("Storage:", f"{system_data.get('storage_total_gb', 0)} GB"),
            ("Last Scan:", system_data.get("last_scan_time", "Never"))
        ]
        
        for i, (label, value) in enumerate(specs_data):
            ttk.Label(specs_frame, text=label, font=("Segoe UI" if self.system == "windows" else "Noto Sans", 10, "bold")).grid(
                row=i//2, column=(i%2)*2, sticky="e", padx=(10, 5), pady=5
            )
            ttk.Label(specs_frame, text=value).grid(
                row=i//2, column=(i%2)*2+1, sticky="w", padx=(0, 20), pady=5
            )
        
        # Issues and recommendations
        issues_frame = ttk.LabelFrame(dashboard, text="Issues & Recommendations", padding=10)
        issues_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Scrollable issues list with platform-specific scrollbar behavior
        if self.system == "windows":
            # Windows-specific scrollbar styling
            issues_canvas = tk.Canvas(issues_frame, highlightthickness=0)
            scrollbar = ttk.Scrollbar(issues_frame, orient="vertical", command=issues_canvas.yview)
            scrollable_frame = ttk.Frame(issues_canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: issues_canvas.configure(scrollregion=issues_canvas.bbox("all"))
            )
            
            issues_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            issues_canvas.configure(yscrollcommand=scrollbar.set)
            
            issues_canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
        else:
            # Linux simpler scrollbar approach to avoid rendering inconsistencies
            scrollable_frame = ttk.Frame(issues_frame)
            scrollable_frame.pack(fill="both", expand=True)
        
        # Sample issues (would be populated from actual diagnostics)
        issues = system_data.get("issues", [
            {"type": "warning", "component": "storage", "message": "Disk space low (15% remaining)"},
            {"type": "critical", "component": "memory", "message": "Memory usage consistently high"},
            {"type": "info", "component": "os", "message": "System updates available"}
        ])
        
        # Issue icons - using text-based icons for cross-platform compatibility
        icons = {
            "critical": "⚠️",
            "warning": "⚡",
            "info": "ℹ️"
        }
        
        # Add issues to scrollable frame
        if not issues:
            ttk.Label(
                scrollable_frame,
                text="No issues detected. System appears to be healthy.",
                foreground="#4CAF50"
            ).pack(pady=10)
        else:
            for i, issue in enumerate(issues):
                issue_type = issue.get("type", "info")
                issue_frame = ttk.Frame(scrollable_frame)
                issue_frame.pack(fill="x", pady=5)
                
                # Icon and type
                ttk.Label(
                    issue_frame, 
                    text=icons.get(issue_type, "•"),
                    font=("Segoe UI" if self.system == "windows" else "Noto Sans", 12)
                ).pack(side="left", padx=(0, 5))
                
                # Issue description
                ttk.Label(
                    issue_frame,
                    text=issue.get("message", "Unknown issue"),
                    wraplength=500
                ).pack(side="left", fill="x", expand=True)
                
                # Fix button if actionable
                if issue.get("fixable", False):
                    ttk.Button(
                        issue_frame,
                        text="Fix",
                        command=lambda i=i: self._fix_issue(issues[i])
                    ).pack(side="right")
                
                # Add separator except for last item
                if i < len(issues) - 1:
                    ttk.Separator(scrollable_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Actions panel
        actions_frame = ttk.Frame(dashboard)
        actions_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(
            actions_frame,
            text="Refresh Dashboard",
            command=self.refresh_dashboard
        ).pack(side="left")
        
        ttk.Button(
            actions_frame,
            text="View Detailed Report",
            command=self.view_detailed_report
        ).pack(side="left", padx=(10, 0))
        
        ttk.Button(
            actions_frame,
            text="Save Diagnostics",
            command=self.save_diagnostics
        ).pack(side="right")
    
    def create_component_view(self, component_id):
        """Create view for a specific component
        
        Args:
            component_id: ID of the component to display
        """
        # Clear details panel except progress frame
        for widget in self.details_panel.winfo_children():
            if widget != self.progress_frame:
                widget.destroy()
        
        # Component container
        component_frame = ttk.Frame(self.details_panel)
        component_frame.pack(fill="both", expand=True)
        
        # Get component info
        components = {
            "system": {"title": "System Overview", "function": self._create_system_view},
            "cpu": {"title": "Processor Information", "function": self._create_cpu_view},
            "memory": {"title": "Memory Analysis", "function": self._create_memory_view},
            "storage": {"title": "Storage Health", "function": self._create_storage_view},
            "network": {"title": "Network Status", "function": self._create_network_view},
            "battery": {"title": "Battery Health", "function": self._create_battery_view},
            "windows": {"title": "Windows Information", "function": self._create_windows_view},
            "linux": {"title": "Linux Information", "function": self._create_linux_view}
        }
        
        if component_id in components:
            component_info = components[component_id]
            
            # Title
            ttk.Label(
                component_frame, 
                text=component_info["title"],
                style="Heading.TLabel"
            ).pack(anchor="w", pady=(0, 15))
            
            # Create component-specific view
            component_info["function"](component_frame)
        else:
            # Unknown component
            ttk.Label(
                component_frame,
                text=f"Unknown component: {component_id}",
                foreground="red"
            ).pack(pady=20)
    
    def _on_component_selected(self):
        """Handle component selection change"""
        component_id = self.current_component.get()
        self.create_component_view(component_id)
    
    def run_quick_scan(self):
        """Run a quick diagnostic scan"""
        if self.analysis_running:
            return
            
        self.analysis_running = True
        
        # Show progress frame
        self.progress_frame.pack(pady=20)
        self.progress_label.config(text="Running quick diagnostic scan...")
        self.progress_var.set(0)
        
        # Start scan in background thread
        threading.Thread(
            target=self._run_quick_scan_thread,
            daemon=True
        ).start()
    
    def _run_quick_scan_thread(self):
        """Background thread for quick scan"""
        try:
            # Simulate progress updates
            for i in range(1, 101):
                # Update progress on main thread
                self.parent.after(
                    10, 
                    lambda v=i: self.progress_var.set(v)
                )
                # Simulate work
                import time
                time.sleep(0.05)
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run storage health analysis (as an example of actual diagnostic)
            storage_results = loop.run_until_complete(self.storage_analyzer.analyze_all_drives())
            
            # Store results in shared state
            # In a real implementation, we would run all diagnostics and gather results
            self.shared_state["system_info"] = {
                "last_scan_time": self._get_current_time(),
                "scan_type": "quick",
                "storage_health": self._calculate_storage_health(storage_results)
            }
            
            # Complete the scan
            self.parent.after(0, self._complete_scan)
            
        except Exception as e:
            logging.error(f"Error in quick scan: {e}")
            self.parent.after(0, lambda: self._show_scan_error(str(e)))
    
    def _calculate_storage_health(self, storage_results):
        """Calculate overall storage health score from analysis results
        
        Args:
            storage_results: Storage analysis results from StorageHealthAnalyzer
            
        Returns:
            Overall health score (0-100)
        """
        drives = storage_results.get("drives", {})
        if not drives:
            return 50  # Default if no drives found
            
        total_score = 0
        
        for device, info in drives.items():
            health_status = info.get("health_status", "unknown")
            health_score = self._convert_health_status_to_score(health_status)
            total_score += health_score
            
        return int(total_score / len(drives)) if drives else 50
    
    def _convert_health_status_to_score(self, status):
        """Convert health status string to numeric score"""
        return {
            "healthy": 100,
            "good": 90,
            "fair": 70,
            "failing": 40,
            "failed": 0,
            "unknown": 50
        }.get(status.lower(), 50)
    
    def run_full_diagnostics(self):
        """Run comprehensive system diagnostics"""
        if self.analysis_running:
            return
            
        self.analysis_running = True
        
        # Show progress frame
        self.progress_frame.pack(pady=20)
        self.progress_label.config(text="Running full system diagnostics...")
        self.progress_var.set(0)
        
        # Start diagnostics in background thread
        threading.Thread(
            target=self._run_full_diagnostics_thread,
            daemon=True
        ).start()
    
    def _run_full_diagnostics_thread(self):
        """Background thread for full diagnostics"""
        try:
            # In a real implementation, this would run all available diagnostics
            # For this example, we'll simulate the process
            
            # Simulate progress updates
            for i in range(1, 101):
                # Update progress on main thread
                self.parent.after(
                    20, 
                    lambda v=i: self.progress_var.set(v)
                )
                # Simulate work
                import time
                time.sleep(0.1)
            
            # Complete the scan
            self.parent.after(0, self._complete_scan)
            
        except Exception as e:
            logging.error(f"Error in full diagnostics: {e}")
            self.parent.after(0, lambda: self._show_scan_error(str(e)))
    
    def _complete_scan(self):
        """Complete the diagnostic scan"""
        self.analysis_running = False
        self.progress_frame.pack_forget()
        
        # Refresh dashboard view with new results
        self.create_dashboard_view()
    
    def _show_scan_error(self, error_message):
        """Show error message for failed scan
        
        Args:
            error_message: Error message to display
        """
        self.analysis_running = False
        self.progress_frame.pack_forget()
        
        from tkinter import messagebox
        messagebox.showerror(
            "Diagnostic Error",
            f"An error occurred during diagnostics:\n{error_message}"
        )
    
    def refresh_dashboard(self):
        """Refresh the dashboard view"""
        self.create_dashboard_view()
    
    def view_detailed_report(self):
        """View detailed diagnostic report"""
        # This would open a detailed report view
        # For now, just show a message
        from tkinter import messagebox
        messagebox.showinfo(
            "Detailed Report",
            "This would show a detailed diagnostic report."
        )
    
    def save_diagnostics(self):
        """Save diagnostic results to file"""
        # This would save results to a file
        # For now, just show a message
        from tkinter import messagebox
        messagebox.showinfo(
            "Save Diagnostics",
            "Diagnostic results would be saved to file."
        )
    
    def _is_battery_present(self):
        """Check if a battery is present in the system
        
        Returns:
            True if battery is present, False otherwise
        """
        try:
            import psutil
            if hasattr(psutil, "sensors_battery"):
                battery = psutil.sensors_battery()
                return battery is not None
        except:
            pass
            
        return False
    
    def _get_os_name(self):
        """Get OS name with platform-specific details
        
        Returns:
            String with OS name and version
        """
        system = platform.system()
        
        if system == "Windows":
            return f"Windows {platform.release()} {platform.version()}"
        elif system == "Linux":
            try:
                import distro
                return f"{distro.name()} {distro.version()}"
            except ImportError:
                # Fallback if distro module not available
                return f"Linux {platform.release()}"
        else:
            return f"{system} {platform.release()}"
    
    def _get_current_time(self):
        """Get current time in a readable format
        
        Returns:
            Current time string
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Component-specific view creators
    def _create_system_view(self, parent):
        """Create system overview view
        
        Args:
            parent: Parent frame for the view
        """
        # For brevity, this is a simplified implementation
        ttk.Label(
            parent,
            text="System overview content would be displayed here.",
            foreground="#757575"
        ).pack(pady=20)
    
    def _create_cpu_view(self, parent):
        """Create processor view
        
        Args:
            parent: Parent frame for the view
        """
        # For brevity, this is a simplified implementation
        ttk.Label(
            parent,
            text="CPU information would be displayed here.",
            foreground="#757575"
        ).pack(pady=20)
    
    def _create_memory_view(self, parent):
        """Create memory view
        
        Args:
            parent: Parent frame for the view
        """
        # For brevity, this is a simplified implementation
        ttk.Label(
            parent,
            text="Memory analysis would be displayed here.",
            foreground="#757575"
        ).pack(pady=20)
    
    def _create_storage_view(self, parent):
        """Create storage health view
        
        Args:
            parent: Parent frame for the view
        """
        # For brevity, this is a simplified implementation
        ttk.Label(
            parent,
            text="Storage health information would be displayed here.",
            foreground="#757575"
        ).pack(pady=20)
    
    def _create_network_view(self, parent):
        """Create network view
        
        Args:
            parent: Parent frame for the view
        """
        # For brevity, this is a simplified implementation
        ttk.Label(
            parent,
            text="Network status would be displayed here.",
            foreground="#757575"
        ).pack(pady=20)
    
    def _create_battery_view(self, parent):
        """Create battery health view
        
        Args:
            parent: Parent frame for the view
        """
        # For brevity, this is a simplified implementation
        ttk.Label(
            parent,
            text="Battery health information would be displayed here.",
            foreground="#757575"
        ).pack(pady=20)
    
    def _create_windows_view(self, parent):
        """Create Windows-specific view
        
        Args:
            parent: Parent frame for the view
        """
        # Only show if on Windows, otherwise show message
        if self.system == "windows":
            ttk.Label(
                parent,
                text="Windows-specific information would be displayed here.",
                foreground="#757575"
            ).pack(pady=20)
        else:
            ttk.Label(
                parent,
                text="Windows-specific information is not available on this platform.",
                foreground="red"
            ).pack(pady=20)
    
    def _create_linux_view(self, parent):
        """Create Linux-specific view
        
        Args:
            parent: Parent frame for the view
        """
        # Only show if on Linux, otherwise show message
        if self.system == "linux":
            ttk.Label(
                parent,
                text="Linux-specific information would be displayed here.",
                foreground="#757575"
            ).pack(pady=20)
        else:
            ttk.Label(
                parent,
                text="Linux-specific information is not available on this platform.",
                foreground="red"
            ).pack(pady=20)
    
    def _fix_issue(self, issue):
        """Fix a detected issue
        
        Args:
            issue: Issue dictionary containing information about the issue
        """
        # This would implement issue-specific fixes
        # For now, just show a message
        from tkinter import messagebox
        messagebox.showinfo(
            "Fix Issue",
            f"This would fix the issue: {issue.get('message', 'Unknown issue')}"
        )