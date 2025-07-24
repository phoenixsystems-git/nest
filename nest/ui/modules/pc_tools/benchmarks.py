#!/usr/bin/env python3
"""
Benchmarks Tab for PC Tools Module

This module implements the Benchmarks tab for the PC Tools module,
providing performance testing functionality for various hardware components.
"""

import os
import sys
import time
import json
import tkinter as tk
import logging
import platform
import threading
import subprocess
import tempfile
import random
from tkinter import ttk, messagebox, scrolledtext, filedialog
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Import visualization libraries carefully to avoid errors
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    matplotlib_available = True
except ImportError:
    logging.warning("Matplotlib not available. Charts will be disabled.")
    matplotlib_available = False

# Import PIL carefully to avoid errors
try:
    from PIL import Image, ImageTk
    pil_available = True
except ImportError:
    logging.warning("PIL ImageTk not available. Some UI elements will be disabled.")
    pil_available = False

# Import OS-specific diagnostics modules
if platform.system() == 'Linux':
    from nest.utils import linux_diagnostics
elif platform.system() == 'Windows':
    # We'll implement Windows-specific benchmarks later
    pass

class BenchmarksTab(ttk.Frame):
    """Benchmarks tab for PC Tools module."""

    def __init__(self, parent, shared_state):
        """Initialize the Benchmarks tab.
        
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
        self.is_running_benchmark = False
        self.benchmark_results = {}
        self.previous_results = {}
        self.last_refresh_time = 0
        self.comparison_mode = False
        
        # Initialize benchmark categories
        self.categories = {
            'cpu': {
                'name': 'CPU Performance',
                'icon': '🔄',
                'tests': ['Single Core', 'Multi Core', 'Integer Math', 'Floating Point']  
            },
            'memory': {
                'name': 'Memory Speed',
                'icon': '💻',
                'tests': ['Read Speed', 'Write Speed', 'Copy Speed', 'Latency']
            },
            'disk': {
                'name': 'Disk Speed',
                'icon': '💽',
                'tests': ['Sequential Read', 'Sequential Write', 'Random Read', 'Random Write']
            },
            'graphics': {
                'name': 'Graphics Performance',
                'icon': '🖼️',
                'tests': ['2D Performance', '3D Performance', 'Compute', 'Video Encoding']
            }
        }
        
        # Create the tab UI
        self.create_ui()
    
    def create_ui(self):
        """Create the Benchmarks tab user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)
        
        # Heading and description
        heading_frame = ttk.Frame(main_frame)
        heading_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(heading_frame, text="Benchmarks", font=("Arial", 16, "bold")).pack(side="left")
        
        # Info text
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            info_frame, 
            text="The benchmarks tool will allow you to measure and compare system performance metrics.",
            wraplength=600
        ).pack(anchor="w")
        
        # Create notebook with tabs for different benchmark categories
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(5, 10))
        
        # Create frames for each category
        self.overview_frame = ttk.Frame(self.notebook)
        self.cpu_frame = ttk.Frame(self.notebook)
        self.memory_frame = ttk.Frame(self.notebook)
        self.disk_frame = ttk.Frame(self.notebook)
        self.graphics_frame = ttk.Frame(self.notebook)
        self.results_frame = ttk.Frame(self.notebook)  # New dedicated tab for results
        
        # Add frames to notebook
        self.notebook.add(self.overview_frame, text="Overview")
        self.notebook.add(self.cpu_frame, text="CPU Tests")
        self.notebook.add(self.memory_frame, text="Memory Tests")
        self.notebook.add(self.disk_frame, text="Disk Tests")
        self.notebook.add(self.graphics_frame, text="Graphics Tests")
        self.notebook.add(self.results_frame, text="Results Summary")
        
        # Create content for each tab
        self.create_overview_tab()
        self.create_cpu_tab()
        self.create_memory_tab()
        self.create_disk_tab()
        self.create_graphics_tab()
        self.create_results_tab()
        
        # Bottom action frame
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(10, 0))
        
        # Comparison mode checkbox
        self.comparison_var = tk.BooleanVar(value=False)
        self.comparison_checkbox = ttk.Checkbutton(
            action_frame,
            text="Before/After Comparison Mode",
            variable=self.comparison_var,
            command=self.toggle_comparison_mode
        )
        self.comparison_checkbox.pack(side="left")
        
        # Add a save report button
        self.save_button = ttk.Button(
            action_frame, 
            text="Save Benchmark Report", 
            command=self.save_benchmark_report,
            state="disabled"
        )
        self.save_button.pack(side="right", padx=(5, 0))
        
        # Add a run benchmarks button
        self.run_button = ttk.Button(
            action_frame, 
            text="Run All Benchmarks", 
            command=self.run_all_benchmarks
        )
        self.run_button.pack(side="right")

    def create_overview_tab(self):
        """Create the Overview tab content."""
        # Create a canvas with scrollbar to make everything scrollable
        canvas = tk.Canvas(self.overview_frame)
        scrollbar = ttk.Scrollbar(self.overview_frame, orient="vertical", command=canvas.yview)
        
        # Main scrollable frame
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create window in canvas
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Overview frame with padding inside the scrollable area
        frame = ttk.Frame(scrollable_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Create header section
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(
            header_frame,
            text="System Performance Benchmarks",
            font=("Arial", 16, "bold")
        ).pack(side="left")
        
        # Add main Run All Benchmarks button to header
        run_all_btn = ttk.Button(
            header_frame,
            text="Run All Benchmarks",
            command=self.run_all_benchmarks
        )
        run_all_btn.pack(side="right")
        
        # Create a frame for system info
        sys_info_frame = ttk.LabelFrame(frame, text="System Information")
        sys_info_frame.pack(fill="x", expand=False, pady=(0, 15), padx=5)
        
        # Extract key system information
        cpu_info = self.system_info.get('cpu', {})
        memory_info = self.system_info.get('memory', {})
        storage_info = self.system_info.get('storage', {})
        
        # Display system info in 2 columns
        sys_details = [
            ("CPU", cpu_info.get('model', 'Unknown')),
            ("CPU Cores", f"{cpu_info.get('cores', 'Unknown')} cores / {cpu_info.get('threads', 'Unknown')} threads"),
            ("Memory", f"{memory_info.get('total', 'Unknown')} {memory_info.get('type', '')}"),
            ("Storage", storage_info.get('primary_drive', {}).get('model', 'Unknown')),
            ("OS", f"{platform.system()} {platform.release()}"),
        ]
        
        for i, (label, value) in enumerate(sys_details):
            row = i // 2
            col = i % 2
            
            info_frame = ttk.Frame(sys_info_frame)
            info_frame.grid(row=row, column=col, sticky="w", padx=10, pady=5)
            
            ttk.Label(
                info_frame,
                text=f"{label}:",
                font=("Arial", 10, "bold")
            ).pack(side="left")
            
            ttk.Label(
                info_frame,
                text=f" {value}",
                font=("Arial", 10)
            ).pack(side="left")
        
        # Create benchmark categories section
        categories_frame = ttk.LabelFrame(frame, text="Benchmark Categories")
        categories_frame.pack(fill="both", expand=True, pady=(0, 10), padx=5)
        
        # Configure grid to expand properly
        categories_frame.grid_columnconfigure(0, weight=1)
        categories_frame.grid_columnconfigure(1, weight=1)
        
        # For each category create a card with more vertical space
        for i, (cat_id, cat_info) in enumerate(self.categories.items()):
            card_frame = ttk.Frame(categories_frame, relief="solid", borderwidth=1)
            card_frame.grid(row=i//2, column=i%2, sticky="nsew", padx=5, pady=5)
            
            # Category icon and name
            header_frame = ttk.Frame(card_frame)
            header_frame.pack(fill="x", pady=5, padx=5)
            
            ttk.Label(
                header_frame,
                text=cat_info['icon'] + " " + cat_info['name'],
                font=("Arial", 12, "bold")
            ).pack(side="left")
            
            # Run button for this category
            run_btn = ttk.Button(
                header_frame,
                text="Run Tests",
                command=lambda c=cat_id: self.run_category_benchmark(c)
            )
            run_btn.pack(side="right")
            
            # Add test list in a more compact two-column layout
            test_frame = ttk.Frame(card_frame)
            test_frame.pack(fill="x", padx=5, pady=2)
            
            # Use grid layout for better space utilization
            for i, test in enumerate(cat_info['tests']):
                row = i // 2  # Two columns
                col = i % 2
                
                ttk.Label(
                    test_frame, 
                    text=f"• {test}",
                    font=("Arial", 9)  # Slightly smaller font
                ).grid(row=row, column=col, sticky="w", padx=2, pady=1)
                
            # Create a results section with guaranteed minimum height
            results_frame = ttk.Frame(card_frame, height=30)  # Minimum height to prevent cutoff
            results_frame.pack(fill="x", padx=5, pady=5)
            results_frame.pack_propagate(False)  # Prevent the frame from shrinking below minimum height
            
            # Store reference to update later
            setattr(self, f"overview_{cat_id}_results", results_frame)
        
        # We've moved the summary to its own dedicated tab
            
    def create_cpu_tab(self):
        """Create the CPU Tests tab content."""
        # CPU frame
        frame = ttk.Frame(self.cpu_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Create placeholder content
        self._create_placeholder_content(frame, "CPU Performance", self.categories['cpu']['tests'])
    
    def create_memory_tab(self):
        """Create the Memory Tests tab content."""
        # Memory frame
        frame = ttk.Frame(self.memory_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Create placeholder content
        self._create_placeholder_content(frame, "Memory Speed", self.categories['memory']['tests'])
    
    def create_disk_tab(self):
        """Create the Disk Tests tab content."""
        # Disk frame
        frame = ttk.Frame(self.disk_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Create placeholder content
        self._create_placeholder_content(frame, "Disk Speed", self.categories['disk']['tests'])
    
    def create_graphics_tab(self):
        """Create the Graphics Tests tab content."""
        # Graphics frame
        frame = ttk.Frame(self.graphics_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)
        
        # Create placeholder content
        self._create_placeholder_content(frame, "Graphics Performance", self.categories['graphics']['tests'])
    
    def _create_placeholder_content(self, parent, title, tests):
        """Create placeholder content for benchmark tabs.
        
        Args:
            parent: Parent widget
            title: Tab title
            tests: List of tests for this category
        """
        # Store the parent reference for later updates
        category_key = title.lower().split()[0]  # cpu, memory, disk, or graphics
        setattr(self, f"{category_key}_parent", parent)
        
        # Create a frame for test controls
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill="x", pady=(0, 10))
        
        # Header
        ttk.Label(
            controls_frame,
            text=title,
            font=("Arial", 16, "bold")
        ).pack(side="left", pady=(0, 10))
        
        # Test list frame
        test_frame = ttk.LabelFrame(parent, text="Select Tests to Run")
        test_frame.pack(fill="x", expand=False, pady=(0, 10), padx=5)
        
        # Create test selection checkbuttons
        check_vars = []
        for i, test in enumerate(tests):
            var = tk.BooleanVar(value=True)
            check_vars.append(var)
            
            check = ttk.Checkbutton(
                test_frame,
                text=test,
                variable=var
            )
            row = i // 2
            col = i % 2
            check.grid(row=row, column=col, sticky="w", padx=10, pady=2)
        
        # Create results frame - initially empty
        results_frame = ttk.LabelFrame(parent, text="Benchmark Results")
        results_frame.pack(fill="both", expand=True, pady=(0, 10), padx=5)
        
        # Add a placeholder message
        placeholder = ttk.Label(
            results_frame,
            text="Run benchmarks to see results here",
            font=("Arial", 10, "italic"),
            foreground="gray"
        )
        placeholder.pack(pady=20)
        
        # Store references to update later
        setattr(self, f"{category_key}_results_frame", results_frame)
        setattr(self, f"{category_key}_placeholder", placeholder)
        
        # Add a Run button for this specific test category
        run_button = ttk.Button(
            controls_frame,
            text=f"Run {title} Tests",
            command=lambda: self.run_category_benchmark(category_key)
        )
        run_button.pack(side="right", pady=(10, 0))
    
    def toggle_comparison_mode(self):
        """Toggle before/after comparison mode."""
        self.comparison_mode = self.comparison_var.get()
        if self.comparison_mode:
            # Store current results as previous for comparison
            if self.benchmark_results:
                self.previous_results = self.benchmark_results.copy()
                self.benchmark_results = {}
                self.run_button.configure(text="Run Comparison Benchmark")
                logging.info("Benchmark comparison mode activated")
        else:
            # Reset to normal mode
            self.run_button.configure(text="Run All Benchmarks")
            logging.info("Benchmark comparison mode deactivated")
    
    def run_all_benchmarks(self):
        """Run all selected benchmark tests."""
        if self.is_running_benchmark:
            messagebox.showinfo("Benchmark in Progress", "Please wait for the current benchmark to complete.")
            return
            
        self.is_running_benchmark = True
        self.run_button.configure(state="disabled")
        
        # Start benchmarks in a separate thread to avoid freezing the UI
        threading.Thread(target=self._run_benchmarks_thread, daemon=True).start()
    
    def _run_benchmarks_thread(self):
        """Background thread for running benchmarks."""
        try:
            # Clear previous results if not in comparison mode
            if not self.comparison_mode:
                self.benchmark_results = {}
            
            # Run each category of benchmarks
            categories = ['cpu', 'memory', 'disk', 'graphics']
            for category in categories:
                # Simulate running benchmarks for now
                time.sleep(0.5)  # Simulate work
                
                # Generate simulated results
                self.benchmark_results[category] = self._simulate_benchmark_results(category)
            
            # Store results in shared state
            self.shared_state['benchmark_results'] = self.benchmark_results
            
            # Update UI with results
            self.after(100, self._update_ui_with_results)
            
        except Exception as e:
            logging.error(f"Error in benchmarks: {e}")
            # Update UI on error
            self.after(100, lambda: self._update_ui_with_error(str(e)))
        finally:
            # Re-enable UI
            self.after(100, lambda: self.run_button.configure(state="normal"))
            self.is_running_benchmark = False
    
    def _simulate_benchmark_results(self, category):
        """Generate simulated benchmark results for demo purposes.
        
        Args:
            category: The benchmark category
            
        Returns:
            Dictionary with simulated benchmark results
        """
        results = {}
        for test in self.categories[category]['tests']:
            # Generate a random score between 50-100 for demo
            score = random.randint(50, 100)
            results[test] = {
                'score': score,
                'unit': self._get_unit_for_test(category, test),
                'comparison': None  # Will be filled if in comparison mode
            }
            
            # If in comparison mode, compare with previous results
            if self.comparison_mode and category in self.previous_results and test in self.previous_results[category]:
                prev_score = self.previous_results[category][test]['score']
                change_pct = ((score - prev_score) / prev_score) * 100
                results[test]['comparison'] = {
                    'previous_score': prev_score,
                    'change_percent': change_pct,
                    'improved': change_pct > 0
                }
                
        return results
    
    def _get_unit_for_test(self, category, test):
        """Get the appropriate unit for a benchmark test.
        
        Args:
            category: Benchmark category
            test: Specific test name
            
        Returns:
            String representing the unit of measurement
        """
        if category == 'cpu':
            return 'score' if 'Math' in test else 'MIPS'
        elif category == 'memory':
            return 'ns' if 'Latency' in test else 'MB/s'
        elif category == 'disk':
            return 'MB/s'
        elif category == 'graphics':
            return 'FPS' if '3D' in test or '2D' in test else 'score'
        return 'score'
    
    def _update_ui_with_results(self):
        """Update UI with benchmark results."""
        # Enable the save report button
        self.save_button.configure(state="normal")
        
        # Update each category's results display
        for category in self.benchmark_results:
            self._display_category_results(category, self.benchmark_results[category])
            
        # Update the overview tab with summary results
        self._update_overview_results()
        
        # Update status
        logging.info("Benchmark completed successfully")
        logging.debug("Refreshed Benchmarks tab successfully")
        
        # Show a notification of completion
        messagebox.showinfo("Benchmark Complete", "All benchmark tests have completed successfully.")
    
    def _update_ui_with_error(self, error_message):
        """Show error message when benchmarks fail.
        
        Args:
            error_message: Error message to display
        """
        messagebox.showerror(
            "Benchmark Error", 
            f"An error occurred during benchmarking:\n{error_message}"
        )
        logging.error(f"Benchmark error: {error_message}")
    
    def run_category_benchmark(self, category):
        """Run benchmarks for a specific category.
        
        Args:
            category: Category to benchmark
        """
        if self.is_running_benchmark:
            messagebox.showinfo("Benchmark in Progress", "Please wait for the current benchmark to complete.")
            return
            
        self.is_running_benchmark = True
        
        # Start category benchmark in a separate thread
        threading.Thread(
            target=self._run_category_benchmark_thread, 
            args=(category,),
            daemon=True
        ).start()
    
    def _run_category_benchmark_thread(self, category):
        """Background thread for running category-specific benchmarks.
        
        Args:
            category: Category to benchmark
        """
        try:
            # Simulate running benchmarks
            time.sleep(1)  # Simulate work
            
            # Generate simulated results
            self.benchmark_results[category] = self._simulate_benchmark_results(category)
            
            # Store results in shared state
            self.shared_state['benchmark_results'] = self.benchmark_results
            
            # Update UI with results
            self.after(100, lambda: self._update_category_results(category))
            
        except Exception as e:
            logging.error(f"Error in {category} benchmark: {e}")
            # Update UI on error
            self.after(100, lambda: self._update_ui_with_error(str(e)))
        finally:
            # Re-enable UI
            self.is_running_benchmark = False
    
    def _update_category_results(self, category):
        """Update UI with category-specific benchmark results.
        
        Args:
            category: Category that was benchmarked
        """
        # Enable the save report button
        self.save_button.configure(state="normal")
        
        # Display the results for this category
        if category in self.benchmark_results:
            self._display_category_results(category, self.benchmark_results[category])
        
        # Show a notification of completion
        messagebox.showinfo(
            "Category Benchmark Complete", 
            f"The {self.categories[category]['name']} benchmark tests have completed successfully."
        )
    
    def save_benchmark_report(self):
        """Save the benchmark report to a file."""
        if not self.benchmark_results:
            messagebox.showinfo("No Report Available", "Please run benchmarks first to generate a report.")
            return
            
        # Get the current date and time for the filename
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        default_filename = f"benchmark_report_{current_time}.txt"
        
        # Ask the user where to save the file
        filename = tk.filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=default_filename,
            title="Save Benchmark Report"
        )
        
        if not filename:
            # User cancelled
            return
            
        try:
            with open(filename, 'w') as f:
                f.write("===== NEST PC TOOLS BENCHMARK REPORT =====\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Technician: {self.current_user.get('name', 'Unknown')}\n\n")
                
                # Write system information
                f.write("===== SYSTEM INFORMATION =====\n")
                for key, value in self.system_info.items():
                    if isinstance(value, dict):
                        f.write(f"{key.title()}:\n")
                        for subkey, subvalue in value.items():
                            f.write(f"  {subkey}: {subvalue}\n")
                    else:
                        f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # Write benchmark results
                f.write("===== BENCHMARK RESULTS =====\n")
                for category, tests in self.benchmark_results.items():
                    cat_name = self.categories[category]['name']
                    f.write(f"{cat_name}:\n")
                    
                    for test_name, result in tests.items():
                        score = result['score']
                        unit = result['unit']
                        f.write(f"  {test_name}: {score} {unit}")
                        
                        # Add comparison info if available
                        if result['comparison']:
                            prev = result['comparison']['previous_score']
                            change = result['comparison']['change_percent']
                            direction = 'up' if change > 0 else 'down'
                            f.write(f" ({prev} -> {score}, {abs(change):.1f}% {direction})")
                        
                        f.write("\n")
                    f.write("\n")
                
            messagebox.showinfo(
                "Report Saved", 
                f"Benchmark report saved to {filename}"
            )
        except Exception as e:
            messagebox.showerror(
                "Error Saving Report", 
                f"An error occurred while saving the report: {str(e)}"
            )
            logging.error(f"Error saving benchmark report: {e}")
    
    def refresh_if_needed(self):
        """Refresh tab data if needed."""
        logging.info(f"Refreshing Benchmarks tab")
        self.last_refresh_time = time.time()
        logging.debug("Refreshed Benchmarks tab successfully")
    
    def _display_category_results(self, category, results):
        """Display benchmark results for a specific category.
        
        Args:
            category: The benchmark category (cpu, memory, disk, graphics)
            results: Dictionary of benchmark results for this category
        """
        # Get the results frame for this category
        results_frame = getattr(self, f"{category}_results_frame", None)
        if not results_frame:
            logging.error(f"Results frame not found for {category}")
            return
            
        # Clear any placeholder or previous results
        placeholder = getattr(self, f"{category}_placeholder", None)
        if placeholder and placeholder.winfo_exists():
            placeholder.destroy()
            
        # Clear all widgets in the results frame
        for widget in results_frame.winfo_children():
            widget.destroy()
            
        # Create a canvas for results display
        results_canvas = tk.Canvas(results_frame, borderwidth=0, highlightthickness=0)
        results_canvas.pack(fill="both", expand=True)
        
        # Add a scrollbar if needed
        scrollbar = ttk.Scrollbar(results_canvas, orient="vertical", command=results_canvas.yview)
        scrollable_frame = ttk.Frame(results_canvas)
        
        # Configure canvas to scroll with frame
        scrollable_frame.bind(
            "<Configure>",
            lambda e: results_canvas.configure(scrollregion=results_canvas.bbox("all"))
        )
        
        # Create window in canvas for scrollable frame
        results_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        results_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Organize results in a grid
        row = 0
        for test_name, result in results.items():
            # Create a frame for this result
            result_frame = ttk.Frame(scrollable_frame)
            result_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
            row += 1
            
            # Add test name
            ttk.Label(
                result_frame, 
                text=test_name,
                font=("Arial", 12, "bold")
            ).grid(row=0, column=0, sticky="w", padx=5, pady=2)
            
            # Add score with appropriate unit
            score = result['score']
            unit = result['unit']
            
            # Create score display with color coding
            score_frame = ttk.Frame(result_frame)
            score_frame.grid(row=0, column=1, padx=5, pady=2)
            
            # Calculate a color based on score (green=good, yellow=medium, red=poor)
            # For this demo we'll just use score directly (50-100)
            if score >= 80:
                color = "#4CAF50"  # Green
            elif score >= 65:
                color = "#FF9800"  # Orange
            else:
                color = "#F44336"  # Red
            
            # Score display
            score_label = ttk.Label(
                score_frame,
                text=f"{score}",
                font=("Arial", 12, "bold"),
                foreground=color
            )
            score_label.pack(side="left")
            
            # Unit display
            ttk.Label(
                score_frame,
                text=f" {unit}",
                font=("Arial", 10)
            ).pack(side="left", padx=(2, 0))
            
            # Add comparison info if available
            if result['comparison']:
                prev = result['comparison']['previous_score']
                change = result['comparison']['change_percent']
                improved = result['comparison']['improved']
                
                # Create a frame for the comparison
                compare_frame = ttk.Frame(result_frame)
                compare_frame.grid(row=0, column=2, padx=5, pady=2)
                
                # Show the previous score
                ttk.Label(
                    compare_frame,
                    text=f"Previous: {prev} {unit}",
                    font=("Arial", 9)
                ).pack(side="left")
                
                # Show the change with an arrow and color
                arrow = "↑" if improved else "↓"
                arrow_color = "#4CAF50" if improved else "#F44336"  # Green if improved, red if worse
                
                ttk.Label(
                    compare_frame,
                    text=f" {arrow} {abs(change):.1f}%",
                    font=("Arial", 9, "bold"),
                    foreground=arrow_color
                ).pack(side="left")
            
            # Add a horizontal separator
            ttk.Separator(scrollable_frame, orient="horizontal").grid(
                row=row, column=0, sticky="ew", padx=5, pady=5)
            row += 1
    
    def _update_overview_results(self):
        """Update the benchmark results display in both the category cards and Results Summary tab."""
        # First, update each category card in the overview tab
        for category, results in self.benchmark_results.items():
            if not results:
                continue
                
            # Calculate average score
            scores = [result['score'] for result in results.values()]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            # Get color based on score
            color = "#4CAF50" if avg_score >= 80 else "#FF9800" if avg_score >= 65 else "#F44336"
            
            # Update the category card in the overview
            overview_results_frame = getattr(self, f"overview_{category}_results", None)
            if overview_results_frame:
                # Clear any existing results
                for widget in overview_results_frame.winfo_children():
                    widget.destroy()
                    
                # Add a condensed results display
                result_label = ttk.Label(
                    overview_results_frame,
                    text=f"Average Score: {avg_score:.1f}",
                    font=("Arial", 10, "bold"),
                    foreground=color
                )
                result_label.pack(pady=5)
                
                # If we're in comparison mode, add the comparison info
                if self.comparison_mode and category in self.previous_results:
                    # Calculate previous average
                    prev_scores = [result['score'] for result in self.previous_results[category].values()]
                    prev_avg = sum(prev_scores) / len(prev_scores) if prev_scores else 0
                    
                    # Calculate change percentage
                    change_pct = ((avg_score - prev_avg) / prev_avg) * 100 if prev_avg else 0
                    improved = change_pct > 0
                    
                    # Determine arrow and color
                    arrow = "↑" if improved else "↓"  # Up or down arrow
                    arrow_color = "#4CAF50" if improved else "#F44336"
                    
                    # Add to the overview card
                    ttk.Label(
                        overview_results_frame,
                        text=f"Change: {arrow} {abs(change_pct):.1f}%",
                        font=("Arial", 9),
                        foreground=arrow_color
                    ).pack()
        
        # Now update the Results Summary tab
        self._update_results_summary_tab()
    
    def _update_results_summary_tab(self):
        """Update the Results Summary tab with current benchmark results."""
        # Clear the placeholder if it exists
        if hasattr(self, 'results_placeholder') and self.results_placeholder.winfo_exists():
            self.results_placeholder.destroy()
        
        # Clear existing results
        for widget in self.results_container.winfo_children():
            widget.destroy()
        
        # Check if we have results to display
        if not self.benchmark_results:
            # No results yet, show placeholder
            self.results_placeholder = ttk.Label(
                self.results_container,
                text="Run benchmarks to see results summary",
                font=("Arial", 11, "italic"),
                foreground="gray"
            )
            self.results_placeholder.pack(pady=50)
            return
        
        # Create a results grid
        row = 0
        for category, results in self.benchmark_results.items():
            if not results:
                continue
                
            # Get category display name
            cat_name = self.categories[category]['name']
            
            # Calculate average score
            scores = [result['score'] for result in results.values()]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            # Create a row frame with alternating background color
            row_bg = "#f5f5f5" if row % 2 == 0 else "white"
            row_frame = ttk.Frame(self.results_container)
            row_frame.pack(fill="x", expand=False)
            
            # Category name cell
            cat_frame = ttk.Frame(row_frame, width=200)
            cat_frame.pack(side="left", fill="y", padx=1, pady=1)
            cat_frame.pack_propagate(False)
            
            ttk.Label(
                cat_frame,
                text=cat_name,
                font=("Arial", 10),
                background=row_bg,
                padding="10 5"
            ).pack(fill="both", expand=True)
            
            # Score cell with color coding
            score_frame = ttk.Frame(row_frame, width=150)
            score_frame.pack(side="left", fill="y", padx=1, pady=1)
            score_frame.pack_propagate(False)
            
            # Color based on score
            color = "#4CAF50" if avg_score >= 80 else "#FF9800" if avg_score >= 65 else "#F44336"
            
            ttk.Label(
                score_frame,
                text=f"{avg_score:.1f}",
                font=("Arial", 10, "bold"),
                foreground=color,
                background=row_bg,
                padding="10 5"
            ).pack(fill="both", expand=True)
            
            # Change cell if in comparison mode
            if self.comparison_mode and category in self.previous_results:
                change_frame = ttk.Frame(row_frame, width=150)
                change_frame.pack(side="left", fill="y", padx=1, pady=1)
                change_frame.pack_propagate(False)
                
                # Calculate previous average
                prev_scores = [result['score'] for result in self.previous_results[category].values()]
                prev_avg = sum(prev_scores) / len(prev_scores) if prev_scores else 0
                
                # Calculate change percentage
                change_pct = ((avg_score - prev_avg) / prev_avg) * 100 if prev_avg else 0
                improved = change_pct > 0
                
                # Determine arrow and color
                arrow = "↑" if improved else "↓"  # Up or down arrow
                arrow_color = "#4CAF50" if improved else "#F44336"
                
                ttk.Label(
                    change_frame,
                    text=f"{arrow} {abs(change_pct):.1f}%",
                    font=("Arial", 10, "bold"),
                    foreground=arrow_color,
                    background=row_bg,
                    padding="10 5"
                ).pack(fill="both", expand=True)
            
            row += 1
    
    def create_results_tab(self):
        """Create the Results Summary tab content."""
        # Summary frame with padding
        frame = ttk.Frame(self.results_frame, padding="20 20 20 20")
        frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(
            header_frame,
            text="Benchmark Results Summary",
            font=("Arial", 16, "bold")
        ).pack(side="left")
        
        # Create main content area
        content_frame = ttk.Frame(frame)
        content_frame.pack(fill="both", expand=True)
        
        # Create summary table with headers
        table_frame = ttk.Frame(content_frame, relief="solid", borderwidth=1)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Table headers
        header_frame = ttk.Frame(table_frame, padding="5 5 5 5")
        header_frame.pack(fill="x")
        
        # Create column headers with background color
        header_style = ttk.Style()
        header_style.configure("Header.TLabel", background=self.colors.get("primary", "#017E84"), foreground="white")
        
        columns = ["Category", "Average Score", "Change"]
        column_widths = [200, 150, 150]  # Widths for each column
        
        for i, column in enumerate(columns):
            column_frame = ttk.Frame(header_frame, width=column_widths[i], height=30)
            column_frame.pack(side="left", padx=1)
            column_frame.pack_propagate(False)  # Prevent the frame from shrinking
            
            ttk.Label(
                column_frame,
                text=column,
                font=("Arial", 11, "bold"),
                anchor="center"
            ).pack(fill="both", expand=True)
        
        # Create the results container where actual results will be displayed
        self.results_container = ttk.Frame(table_frame)
        self.results_container.pack(fill="both", expand=True)
        
        # Add placeholder message
        self.results_placeholder = ttk.Label(
            self.results_container,
            text="Run benchmarks to see results summary",
            font=("Arial", 11, "italic"),
            foreground="gray"
        )
        self.results_placeholder.pack(pady=50)
    
    def refresh(self):
        """Refresh the tab data."""
        logging.info(f"Refreshing Benchmarks tab")
        self.last_refresh_time = time.time()
        logging.debug("Refreshed Benchmarks tab successfully")
