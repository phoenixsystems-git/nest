#!/usr/bin/env python3
"""
PC Tools Module - Workflow-Oriented Implementation

This module implements a workflow-oriented approach to PC diagnostics and repair
with cross-platform compatibility for Windows and Linux.
"""

import tkinter as tk
from tkinter import ttk
import platform
import logging
from typing import Dict, Any, Optional
import os
from pathlib import Path

from nest.ui.modules.pc_tools.workflow.diagnose_workflow import DiagnoseWorkflow
from nest.ui.modules.pc_tools.workflow.repair_workflow import RepairWorkflow
from nest.utils.feature_detection import FeatureDetection


class PCTools:
    """PC Tools module with workflow-oriented design and cross-platform support
    
    This class manages the PC Tools interface, implementing a workflow-based approach
    to system diagnosis and repair with cross-platform compatibility.
    """
    
    def __init__(self, parent, shared_state=None):
        """Initialize PC Tools module
        
        Args:
            parent: Parent frame for the module
            shared_state: Optional initial shared state
        """
        self.parent = parent
        self.system = platform.system().lower()
        self.feature_detection = FeatureDetection()
        
        # Initialize shared state
        self.shared_state = shared_state or {}
        
        # Add RepairDesk colors to shared state if not present
        if "colors" not in self.shared_state:
            self.shared_state["colors"] = {
                "primary": "#017E84",  # RepairDesk teal
                "primary_dark": "#016169",
                "primary_light": "#E6F7F7",
                "secondary": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "info": "#2196F3",
                "background": "#F5F5F5",
                "card_bg": "#FFFFFF",
                "text_primary": "#212121",
                "text_secondary": "#757575",
                "border": "#E0E0E0"
            }
        
        # Create UI components
        self.create_ui()
    
    def create_ui(self):
        """Create the PC Tools user interface with workflow-oriented design"""
        # Main container with RepairDesk styling
        main_frame = ttk.Frame(self.parent, padding=15)
        main_frame.pack(fill="both", expand=True)
        
        # Top section - Quick actions and context
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 15))
        
        # System summary card (always visible)
        self.system_summary = ttk.LabelFrame(top_frame, text="System Overview", padding=10)
        self.system_summary.pack(side="left", fill="x", expand=True)
        
        # Create system summary content
        self.create_system_summary()
        
        # Quick action buttons along top-right
        actions_frame = ttk.Frame(top_frame)
        actions_frame.pack(side="right", padx=(15, 0))
        
        ttk.Button(
            actions_frame, 
            text="Run Quick Analysis", 
            command=self.run_quick_analysis,
            style="Primary.TButton"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            actions_frame, 
            text="Create Repair Report", 
            command=self.create_repair_report
        ).pack(side="left", padx=(0, 5))
        
        # Create workflow notebook instead of regular tabs
        self.workflow_notebook = ttk.Notebook(main_frame)
        self.workflow_notebook.pack(fill="both", expand=True)
        
        # Workflow stages instead of disconnected tabs
        self.workflow_frames = {}
        workflows = [
            ("diagnose", "1. Diagnose", self.create_diagnose_workflow),
            ("repair", "2. Repair", self.create_repair_workflow),
            ("verify", "3. Verify", self.create_verify_workflow),
            ("report", "4. Report", self.create_report_workflow)
        ]
        
        for id, label, creator_func in workflows:
            frame = ttk.Frame(self.workflow_notebook)
            self.workflow_notebook.add(frame, text=label)
            self.workflow_frames[id] = frame
            creator_func(frame)
        
        # Bottom section - Current context and status
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x", pady=(15, 0))
        
        # Status indicators for workflow progress
        self.workflow_progress = ttk.Frame(bottom_frame)
        self.workflow_progress.pack(side="top", fill="x")
        
        # Update workflow progress indicators
        self.update_workflow_progress()
        
        # Status line
        self.status_var = tk.StringVar(value="Ready to diagnose system")
        status_label = ttk.Label(
            bottom_frame, 
            textvariable=self.status_var,
            anchor="w"
        )
        status_label.pack(fill="x", pady=(5, 0))
        
        # Bind notebook tab change
        self.workflow_notebook.bind("<<NotebookTabChanged>>", self.on_workflow_changed)
    
    def create_system_summary(self):
        """Create the system summary information"""
        # Clear existing content
        for widget in self.system_summary.winfo_children():
            widget.destroy()
        
        # Get system info from shared state or detect it
        system_info = self.shared_state.get("system_info", {})
        
        if not system_info:
            # Basic system information when no diagnostics run yet
            import platform
            import psutil
            
            try:
                # Get CPU info
                cpu_info = f"{platform.processor()}"
                if not cpu_info or cpu_info == "":
                    # Fallback for Linux
                    try:
                        with open('/proc/cpuinfo') as f:
                            for line in f:
                                if line.startswith('model name'):
                                    cpu_info = line.split(':', 1)[1].strip()
                                    break
                    except:
                        cpu_info = "Unknown CPU"
                
                # Get memory info
                memory = psutil.virtual_memory()
                memory_total = round(memory.total / (1024**3), 1)
                
                # Get OS info
                if self.system == "windows":
                    os_info = f"Windows {platform.release()}"
                else:
                    try:
                        import distro
                        os_info = f"{distro.name()} {distro.version()}"
                    except ImportError:
                        os_info = f"Linux {platform.release()}"
                
                # Basic system info
                system_info = {
                    "cpu_model": cpu_info,
                    "memory_total_gb": memory_total,
                    "os_name": os_info,
                    "system_model": "Unknown"  # Would require platform-specific detection
                }
                
            except Exception as e:
                logging.error(f"Error getting system info: {e}")
                system_info = {
                    "cpu_model": "Unknown",
                    "memory_total_gb": 0,
                    "os_name": "Unknown",
                    "system_model": "Unknown"
                }
        
        # Create summary grid using pathlib for cross-platform paths
        summary_frame = ttk.Frame(self.system_summary)
        summary_frame.pack(fill="both", expand=True)
        
        # Two-column grid for system info
        labels = [
            ("CPU:", system_info.get("cpu_model", "Unknown")),
            ("Memory:", f"{system_info.get('memory_total_gb', 0)} GB"),
            ("OS:", system_info.get("os_name", "Unknown")),
            ("System:", system_info.get("system_model", "Unknown"))
        ]
        
        # Platform-specific font selection
        font_family = "Segoe UI" if self.system == "windows" else "Noto Sans"
        if self.system == "linux":
            # Check if Noto Sans is available, otherwise use system default
            try:
                from tkinter import font
                available_fonts = font.families()
                if "Noto Sans" not in available_fonts:
                    font_family = "TkDefaultFont"
            except:
                font_family = "TkDefaultFont"
        
        for i, (label, value) in enumerate(labels):
            ttk.Label(
                summary_frame, 
                text=label, 
                font=(font_family, 9, "bold")
            ).grid(row=i//2, column=(i%2)*2, sticky="e", padx=(10, 5), pady=2)
            
            ttk.Label(
                summary_frame, 
                text=value,
                font=(font_family, 9)
            ).grid(row=i//2, column=(i%2)*2+1, sticky="w", padx=(0, 10), pady=2)
        
        # Add diagnostic status if available
        if "last_scan_time" in system_info:
            ttk.Separator(summary_frame, orient="horizontal").grid(
                row=len(labels)//2 + 1, column=0, columnspan=4, sticky="ew", pady=5
            )
            
            ttk.Label(
                summary_frame, 
                text="Last Scan:", 
                font=(font_family, 9, "bold")
            ).grid(row=len(labels)//2 + 2, column=0, sticky="e", padx=(10, 5), pady=2)
            
            ttk.Label(
                summary_frame, 
                text=system_info.get("last_scan_time", "Never"),
                font=(font_family, 9)
            ).grid(row=len(labels)//2 + 2, column=1, sticky="w", padx=(0, 10), pady=2)
            
            ttk.Label(
                summary_frame, 
                text="Issues:", 
                font=(font_family, 9, "bold")
            ).grid(row=len(labels)//2 + 2, column=2, sticky="e", padx=(10, 5), pady=2)
            
            issue_count = len(system_info.get("issues", []))
            ttk.Label(
                summary_frame, 
                text=str(issue_count),
                foreground="#F44336" if issue_count > 0 else "#4CAF50",
                font=(font_family, 9, "bold")
            ).grid(row=len(labels)//2 + 2, column=3, sticky="w", padx=(0, 10), pady=2)
    
    def create_diagnose_workflow(self, parent):
        """Create the diagnostic workflow view
        
        Args:
            parent: Parent frame for the workflow
        """
        # Create the diagnostic workflow
        self.diagnose_workflow = DiagnoseWorkflow(parent, self.shared_state)
    
    def create_repair_workflow(self, parent):
        """Create the repair workflow view
        
        Args:
            parent: Parent frame for the workflow
        """
        # Create the repair workflow
        self.repair_workflow = RepairWorkflow(parent, self.shared_state)
    
    def create_verify_workflow(self, parent):
        """Create the verification workflow view
        
        Args:
            parent: Parent frame for the workflow
        """
        # For brevity, this is a simplified implementation
        # Platform-specific font selection
        font_family = "Segoe UI" if self.system == "windows" else "Noto Sans"
        
        ttk.Label(
            parent,
            text="Verification workflow would be implemented here.",
            foreground="#757575",
            font=(font_family, 10)
        ).pack(pady=20)
    
    def create_report_workflow(self, parent):
        """Create the reporting workflow view
        
        Args:
            parent: Parent frame for the workflow
        """
        # For brevity, this is a simplified implementation
        # Platform-specific font selection
        font_family = "Segoe UI" if self.system == "windows" else "Noto Sans"
        
        ttk.Label(
            parent,
            text="Reporting workflow would be implemented here.",
            foreground="#757575",
            font=(font_family, 10)
        ).pack(pady=20)
    
    def run_quick_analysis(self):
        """Run a quick system analysis"""
        # Switch to diagnose tab
        self.workflow_notebook.select(0)
        
        # Run quick scan in diagnose workflow
        if hasattr(self, "diagnose_workflow"):
            self.diagnose_workflow.run_quick_scan()
            
            # Update status
            self.status_var.set("Running quick analysis...")
    
    def create_repair_report(self):
        """Create a comprehensive repair report"""
        # Switch to report tab
        self.workflow_notebook.select(3)
        
        # Update status
        self.status_var.set("Creating repair report...")
    
    def on_workflow_changed(self, event):
        """Handle workflow tab change
        
        Args:
            event: Event object
        """
        # Get selected tab index
        tab_index = self.workflow_notebook.index("current")
        tab_id = list(self.workflow_frames.keys())[tab_index]
        
        # Update shared state with current workflow
        self.shared_state["current_workflow"] = tab_id
        
        # Update workflow progress indicators
        self.update_workflow_progress()
        
        # Update status
        workflow_names = ["diagnostic", "repair", "verification", "reporting"]
        self.status_var.set(f"Ready for {workflow_names[tab_index]} workflow")
    
    def update_workflow_progress(self):
        """Update the workflow progress indicators"""
        # Clear existing progress indicators
        for widget in self.workflow_progress.winfo_children():
            widget.destroy()
        
        # Get current workflow
        current_workflow = self.shared_state.get("current_workflow", "diagnose")
        workflow_order = ["diagnose", "repair", "verify", "report"]
        current_index = workflow_order.index(current_workflow) if current_workflow in workflow_order else 0
        
        # Create progress indicators with platform-specific styling
        pad_x = 5 if self.system == "linux" else 5
        
        for i, workflow_id in enumerate(workflow_order):
            # Determine indicator state
            if i < current_index:
                state = "completed"
                color = self.shared_state["colors"]["secondary"]
                text_color = "white"
            elif i == current_index:
                state = "current"
                color = self.shared_state["colors"]["primary"]
                text_color = "white"
            else:
                state = "pending"
                color = self.shared_state["colors"]["border"]
                text_color = self.shared_state["colors"]["text_secondary"]
            
            # Create indicator frame
            indicator_frame = ttk.Frame(self.workflow_progress)
            indicator_frame.pack(side="left", fill="y", padx=pad_x)
            
            # Step number circle using Canvas
            canvas = tk.Canvas(indicator_frame, width=30, height=30, highlightthickness=0)
            canvas.create_oval(2, 2, 28, 28, fill=color, outline="")
            
            # Platform-specific font selection
            font_family = "Segoe UI" if self.system == "windows" else "Noto Sans"
            
            canvas.create_text(15, 15, text=str(i+1), fill=text_color, 
                             font=(font_family, 10, "bold"))
            canvas.pack()
            
            # Step name
            workflow_names = ["Diagnose", "Repair", "Verify", "Report"]
            ttk.Label(
                indicator_frame,
                text=workflow_names[i],
                foreground=color,
                font=(font_family, 9, 
                    "bold" if state == "current" else "normal")
            ).pack()
            
            # Connector line (except for last step)
            if i < len(workflow_order) - 1:
                line_canvas = tk.Canvas(self.workflow_progress, width=20, height=30, highlightthickness=0)
                line_color = self.shared_state["colors"]["secondary"] if state == "completed" else self.shared_state["colors"]["border"]
                line_canvas.create_line(0, 15, 20, 15, fill=line_color, width=2)
                line_canvas.pack(side="left")
    
    def activate_tab(self, tab_id):
        """Activate a specific workflow tab
        
        Args:
            tab_id: ID of the tab to activate
        """
        if tab_id in self.workflow_frames:
            tab_index = list(self.workflow_frames.keys()).index(tab_id)
            self.workflow_notebook.select(tab_index)
    
    def update_shared_state(self, updates):
        """Update the shared state
        
        Args:
            updates: Dictionary of updates to apply to shared state
        """
        self.shared_state.update(updates)
        
        # Update UI elements that depend on shared state
        self.create_system_summary()
        self.update_workflow_progress()


# For direct testing
if __name__ == "__main__":
    # Simple test app
    root = tk.Tk()
    root.title("PC Tools Module Test")
    root.geometry("1024x768")
    
    app = PCTools(root, {"name": "Test User"})
    
    root.mainloop()
