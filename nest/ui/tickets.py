"""
Tickets module for Nest - Computer Repair Shop Management System

Handles ticket creation, viewing, and management for repair services.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import json
import logging
import os
import webbrowser
import threading
import queue
import time
from typing import Dict, List, Optional, Any, Tuple, Callable

# Local imports
from ..utils.config import get_config, load_config
from ..api.api_client import RepairDeskClient
from ..utils.cache_utils import get_ticket_cache_path
from ..utils.ui_threading import ThreadSafeUIUpdater


from ..ui.widgets import HoverButton, ScrollableFrame, ToolTip
from .styles import get_style

# Import our custom Treeview
from ..main import FixedHeaderTreeview

# Load config
CONFIG = get_config()

# Set up logging
logger = logging.getLogger(__name__)

def log_message(message):
    """Log a message to the console and to the log file."""
    logging.info(message)

def normalize_ticket(ticket: dict) -> dict:
    """Convert API ticket format to a consistent display format."""
    summary = ticket.get("summary", {})
    devices = ticket.get("devices", [])

    ticket_id = summary.get("order_id", "N/A")
    if ticket_id != "N/A" and not str(ticket_id).startswith("T-"):
        ticket_id = f"T-{ticket_id}"

    customer_name = summary.get("customer", {}).get("fullName", "N/A")
    customer_phone = summary.get("customer", {}).get("mobile", "N/A")

    device_name = "N/A"
    repair_type = "N/A"
    if devices and isinstance(devices, list) and len(devices) > 0:
        device_name = devices[0].get("device", {}).get("name", "N/A")
        if "repairProdItems" in devices[0] and len(devices[0]["repairProdItems"]) > 0:
            repair_type = devices[0]["repairProdItems"][0].get("name", "N/A")

    status = "Open"
    if devices and isinstance(devices, list) and len(devices) > 0:
        status = devices[0].get("status", {}).get("name", "Open")

    assigned_to = "Unassigned"
    if devices and isinstance(devices, list) and len(devices) > 0:
        assigned_to = devices[0].get("assigned_to", {}).get("fullname", "Unassigned")
        if assigned_to == "":
            assigned_to = "Unassigned"

    created_date = "N/A"
    try:
        ts = float(summary.get("created_date", 0))
        created_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception as e:
        log_message(f"Error formatting created_date: {e}")

    last_updated = created_date  # Default to same as created date
    try:
        # Try to get last updated date from ticket
        update_ts = summary.get("updated_at")
        if update_ts:
            last_updated = datetime.fromtimestamp(float(update_ts)).strftime("%Y-%m-%d")
    except Exception:
        pass

    return {
        "id": ticket_id,
        "customer": customer_name,
        "phone": customer_phone,
        "device": device_name,
        "issue": repair_type,
        "status": status,
        "technician": assigned_to,
        "date_created": created_date,
        "date_updated": last_updated,
        "raw_data": ticket,  # Store the original data for reference
    }


class TicketsModule(ttk.Frame):
    """Module for managing repair tickets."""

    REFRESH_INTERVAL = 30000  # Refresh interval in milliseconds (30 seconds)
    LOADING_TEXT = "Loading ticket details..."

    def __del__(self):
        """Ensure resources are properly cleaned up."""
        self._cleanup_resources()

    def __init__(self, parent, current_user=None, action=None):
        """Initialize the tickets module.

        Args:
            parent: The parent widget
            current_user: Dictionary with current user information
            action: Action to perform ('new', 'view', etc.)
        """
        super().__init__(parent)
        self.parent = parent
        self.current_user = current_user
        self.action = action

        # Get colors from parent if available
        self.colors = getattr(
            parent.master,
            "colors",
            {
                "primary": "#2196F3",
                "secondary": "#4CAF50",
                "warning": "#F44336",
                "background": "#FAFAE0",  # Slight yellow tint
                "card_bg": "#FFFFFF",
                "text_primary": "#212121",
                "text_secondary": "#757575",
            },
        )

        # Initialize tracking variables
        self.ticket_data = []
        self.filtered_tickets = []
        self.current_ticket = None
        self.refresh_timer_id = None

        # Initialize API client
        config = load_config()
        self.api_key = config.get("repairdesk", {}).get("api_key", "")
        self.client = RepairDeskClient(api_key=self.api_key)

        # Set up the UI based on the action
        self.setup_ui()

    def setup_ui(self):
        """Set up the module UI."""
        # Import styling
        from nest.ui.theme.styles import apply_styles
        
        # Apply custom styling to the module
        self.style_data = apply_styles(self)
        
        # Create main content frame with padding for better appearance
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Choose UI based on action
        if self.action == "new":
            self.setup_new_ticket_ui()
        else:
            self.setup_tickets_list_ui()

    def setup_tickets_list_ui(self):
        """Set up the UI for listing tickets."""
        # Top controls frame - enhanced with better spacing and borders
        self.controls_frame = ttk.LabelFrame(self.content_frame, text="Ticket Controls")
        self.controls_frame.pack(fill="x", padx=5, pady=5, ipady=5)
        
        # Add padding inside the controls frame for better appearance
        controls_inner = ttk.Frame(self.controls_frame)
        controls_inner.pack(fill="x", padx=12, pady=8, expand=True)

        # Header with action buttons
        header_frame = ttk.Frame(controls_inner, style="Content.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))

        # Title
        title = ttk.Label(header_frame, text="Repair Tickets", style="Title.TLabel")
        title.pack(side="left")

        # Action buttons with improved styling
        buttons_frame = ttk.Frame(header_frame, style="Content.TFrame")
        buttons_frame.pack(side="right")

        # Refresh button with icon-like appearance
        refresh_button = ttk.Button(
            buttons_frame, 
            text="↻ Refresh", 
            style="Action.TButton",
            command=lambda: self.load_tickets(force_refresh=True)
        )
        refresh_button.pack(side="right", padx=5)

        # New ticket button with more prominent style
        new_button = ttk.Button(
            buttons_frame,
            text="+ New Ticket",
            style="Action.TButton",
            command=lambda: self.change_action("new"),
        )
        new_button.pack(side="right", padx=5)

        # Search and filter frame - enhanced with better styling
        filter_frame = ttk.LabelFrame(self.content_frame, text="Search & Filters", style="DetailSection.TLabelframe")
        filter_frame.pack(fill="x", pady=(0, 10), padx=5)

        # Search input with better spacing and layout
        search_container = ttk.Frame(filter_frame)
        search_container.pack(side="left", fill="y", padx=12, pady=10)

        ttk.Label(search_container, text="Search:", font=("Segoe UI", 9, "bold")).pack(
            side="left"
        )

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_container, width=30, textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<Return>", self.search_tickets_callback)

        search_btn = ttk.Button(
            search_container, 
            text="🔍 Search", 
            style="Action.TButton", 
            command=self.search_tickets_callback
        )
        search_btn.pack(side="left", padx=(5, 0))

        # Status filter with improved styling
        filter_container = ttk.Frame(filter_frame)
        filter_container.pack(side="right", fill="y", padx=10, pady=10)

        ttk.Label(filter_container, text="Status:", font=("Segoe UI", 9, "bold")).pack(
            side="left"
        )

        self.status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(
            filter_container,
            width=15,
            textvariable=self.status_var,
            values=["All", "Open", "In Progress", "Pending", "Waiting for Parts", "Completed"],
            state="readonly",
        )
        status_combo.pack(side="left", padx=10)
        status_combo.bind("<<ComboboxSelected>>", self.filter_by_status)
        
        # Apply button for filters
        apply_btn = ttk.Button(
            filter_container,
            text="Apply Filters",
            style="Action.TButton",
            command=self.apply_filters
        )
        apply_btn.pack(side="left", padx=(5, 0))

        # Create split view - top for table, bottom for details with improved styling
        self.paned_window = ttk.PanedWindow(self.content_frame, orient=tk.VERTICAL)
        self.paned_window.pack(fill="both", expand=True, padx=5, pady=5)

        # Top pane - tickets table with better visual appearance
        table_frame = ttk.LabelFrame(self.paned_window, text="Ticket List")
        self.paned_window.add(table_frame, weight=3)  # Give more weight to the table

        # Create table with scrollbar and better padding
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill="both", expand=True, padx=12, pady=12)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_container)
        scrollbar.pack(side="right", fill="y")

        # Tickets table
        columns = (
            "id",
            "customer",
            "device",
            "issue",
            "status",
            "technician",
            "date_created",
            "date_updated",
        )
        self.tickets_table = FixedHeaderTreeview(
            table_container,
            columns=columns,
            show="headings",
            height=12,  # Better height for more ticket visibility
            selectmode="browse",
            yscrollcommand=scrollbar.set,
        )

        # Configure the scrollbar
        scrollbar.config(command=self.tickets_table.yview)

        # Configure columns with better sizing and alignment
        self.tickets_table.column("id", width=80, anchor="w")
        self.tickets_table.column("customer", width=160, anchor="w")
        self.tickets_table.column("device", width=140, anchor="w")
        self.tickets_table.column("issue", width=180, anchor="w")
        self.tickets_table.column("status", width=120, anchor="center")
        self.tickets_table.column("technician", width=140, anchor="w")
        self.tickets_table.column("date_created", width=100, anchor="center")
        self.tickets_table.column("date_updated", width=100, anchor="center")

        # Configure headers
        self.tickets_table.heading(
            "id", text="Ticket #", command=lambda: self.sort_by_column("id", False)
        )
        self.tickets_table.heading(
            "customer", text="Customer", command=lambda: self.sort_by_column("customer", False)
        )
        self.tickets_table.heading(
            "device", text="Device", command=lambda: self.sort_by_column("device", False)
        )
        self.tickets_table.heading(
            "issue", text="Issue", command=lambda: self.sort_by_column("issue", False)
        )
        self.tickets_table.heading(
            "status", text="Status", command=lambda: self.sort_by_column("status", False)
        )
        self.tickets_table.heading(
            "technician",
            text="Technician",
            command=lambda: self.sort_by_column("technician", False),
        )
        self.tickets_table.heading(
            "date_created",
            text="Created",
            command=lambda: self.sort_by_column("date_created", False),
        )
        self.tickets_table.heading(
            "date_updated",
            text="Updated",
            command=lambda: self.sort_by_column("date_updated", False),
        )

        self.tickets_table.pack(fill="both", expand=True)

        # Bind events to the table
        self.tickets_table.bind("<ButtonRelease-1>", self.on_ticket_select)
        self.tickets_table.bind("<Double-1>", self.on_double_click)

        # Bottom pane - details view
        details_frame = ttk.LabelFrame(
            self.paned_window, text="Ticket Details", style="Card.TLabelframe"
        )
        self.paned_window.add(details_frame, weight=1)  # Less weight for details

        # Main details container - full width without scrollbars
        details_container = ttk.Frame(details_frame, style="Card.TFrame")
        details_container.pack(fill="both", expand=True, padx=15, pady=10)

        # Create a fixed layout with three columns for better organization
        details_container.columnconfigure(0, weight=1)  # Customer info
        details_container.columnconfigure(1, weight=1)  # Device info
        details_container.columnconfigure(2, weight=1)  # Status info

        # Customer info section (left column)
        details_left = ttk.Frame(details_container, style="Card.TFrame")
        details_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Device info section (middle column)
        details_middle = ttk.Frame(details_container, style="Card.TFrame")
        details_middle.grid(row=0, column=1, sticky="nsew", padx=10)
        
        # Status info section (right column)
        details_right = ttk.Frame(details_container, style="Card.TFrame")
        details_right.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        
        # Customer info section - Left Column
        customer_section = ttk.LabelFrame(details_left, text="Customer Information", style="DetailSection.TLabelframe")
        customer_section.pack(fill="x", expand=False, pady=(0, 10))
        
        # Grid for customer details
        customer_grid = ttk.Frame(customer_section)
        customer_grid.pack(fill="x", padx=5, pady=5)
        
        # Customer name row
        ttk.Label(customer_grid, text="Name:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        self.customer_name = ttk.Label(customer_grid, text="-")
        self.customer_name.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # Customer phone row
        ttk.Label(customer_grid, text="Phone:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        self.customer_phone = ttk.Label(customer_grid, text="-")
        self.customer_phone.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # Customer email row
        ttk.Label(customer_grid, text="Email:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        self.customer_email = ttk.Label(customer_grid, text="-")
        self.customer_email.grid(row=2, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # Device Information section (middle-left)
        device_section = ttk.LabelFrame(details_middle, text="Device Information", style="DetailSection.TLabelframe")
        device_section.pack(fill="x", expand=False, pady=(0, 10))
        
        # Grid for device details
        device_grid = ttk.Frame(device_section)
        device_grid.pack(fill="x", padx=5, pady=5)
        
        # Device type row
        ttk.Label(device_grid, text="Device:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        self.device_type = ttk.Label(device_grid, text="-")
        self.device_type.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # Issue row
        ttk.Label(device_grid, text="Issue:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        self.device_issue = ttk.Label(device_grid, text="-")
        self.device_issue.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # IMEI/SN row
        ttk.Label(device_grid, text="IMEI/SN:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        self.device_imei = ttk.Label(device_grid, text="-")
        self.device_imei.grid(row=2, column=1, sticky="w", padx=(5, 0), pady=2)

        # Notes section (middle-bottom)
        notes_section = ttk.LabelFrame(details_middle, text="Notes", style="DetailSection.TLabelframe")
        notes_section.pack(fill="both", expand=True, pady=(0, 0))
        
        # Add note button
        notes_header = ttk.Frame(notes_section)
        notes_header.pack(fill="x", pady=(0, 5), padx=5)
        
        add_note_btn = ttk.Button(
            notes_header, text="+ Add Note", style="Action.TButton", command=self.add_note
        )
        add_note_btn.pack(side="right")

        # Notes text area with scrollbar
        notes_frame = ttk.Frame(notes_section)
        notes_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        notes_scrollbar = ttk.Scrollbar(notes_frame)
        notes_scrollbar.pack(side="right", fill="y")
        
        self.notes_text = tk.Text(notes_frame, height=4, width=40, wrap="word", yscrollcommand=notes_scrollbar.set, borderwidth=1, relief="solid")
        self.notes_text.pack(side="left", fill="both", expand=True)
        self.notes_text.config(state="disabled")
        notes_scrollbar.config(command=self.notes_text.yview)

        # Ticket status section (right-top)
        status_section = ttk.LabelFrame(details_right, text="Ticket Status", style="DetailSection.TLabelframe")
        status_section.pack(fill="x", expand=False, pady=(0, 10))
        
        # Grid for status details
        status_grid = ttk.Frame(status_section)
        status_grid.pack(fill="x", padx=5, pady=5)
        
        # Status row
        ttk.Label(status_grid, text="Status:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        self.status_label = ttk.Label(status_grid, text="-")
        self.status_label.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # Assigned row
        ttk.Label(status_grid, text="Assigned To:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        self.assigned_label = ttk.Label(status_grid, text="-")
        self.assigned_label.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=2)

        # Date created row
        ttk.Label(status_grid, text="Created:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        self.date_created = ttk.Label(status_grid, text="-")
        self.date_created.grid(row=2, column=1, sticky="w", padx=(5, 0), pady=2)

        # Date updated row
        ttk.Label(status_grid, text="Updated:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=2)
        self.date_updated = ttk.Label(status_grid, text="-")
        self.date_updated.grid(row=3, column=1, sticky="w", padx=(5, 0), pady=2)

        # Action buttons section (right-bottom)
        action_section = ttk.LabelFrame(details_right, text="Actions", style="DetailSection.TLabelframe")
        action_section.pack(fill="x", expand=True, pady=(0, 0))
        
        action_grid = ttk.Frame(action_section)
        action_grid.pack(fill="x", padx=5, pady=5)
        
        # Use a grid for better button layout with more spacing
        self.update_btn = ttk.Button(
            action_grid, text="Update Ticket", style="Action.TButton", command=self.update_ticket, state="disabled"
        )
        self.update_btn.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        self.print_btn = ttk.Button(
            action_grid, text="Print Invoice", style="Action.TButton", command=self.print_invoice, state="disabled"
        )
        self.print_btn.grid(row=1, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        self.complete_btn = ttk.Button(
            action_grid, text="Mark Complete", style="Action.TButton", command=self.mark_complete, state="disabled"
        )
        self.complete_btn.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        self.cancel_btn = ttk.Button(
            action_grid, text="Cancel Ticket", style="Action.TButton", command=self.cancel_ticket, state="disabled"
        )
        self.cancel_btn.grid(row=3, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        # Configure action grid column to expand buttons
        action_grid.columnconfigure(0, weight=1)

        # Status bar showing count
        self.status_label = ttk.Label(
            self.content_frame,
            text="Loading tickets...",
            foreground=self.colors["text_secondary"],
            style="TLabel",  # Use ttk style instead of direct background
        )
        self.status_label.pack(anchor="w", pady=(5, 0))

        # Load ticket data
        self.load_tickets()

    def destroy(self):
        """Clean up resources when widget is destroyed."""
        # Set the destroyed flag first to prevent new operations from starting
        self._is_destroyed = True
        
        try:
            # Cancel any in-progress loading operations
            self.loading_tickets = False
            
            # Call our cleanup resources method to ensure everything is properly released
            if hasattr(self, '_cleanup_resources'):
                self._cleanup_resources()
            
            # Wait for any existing threads to complete
            if hasattr(self, 'loader_thread') and self.loader_thread and self.loader_thread.is_alive():
                logging.info("Waiting for ticket loader thread to complete...")
                self.loader_thread.join(0.5)  # Wait max 0.5 seconds
                
            # Make sure any pending tkinter updates are canceled
            if hasattr(self, '_pending_updates'):
                for update_id in self._pending_updates:
                    try:
                        self.after_cancel(update_id)
                    except Exception:
                        pass
            
            # Cancel any refresh timer
            if hasattr(self, 'refresh_timer_id') and self.refresh_timer_id:
                try:
                    self.after_cancel(self.refresh_timer_id)
                    self.refresh_timer_id = None
                except Exception:
                    pass
            
            # Clear any queues
            if hasattr(self, 'ticket_queue'):
                while not self.ticket_queue.empty():
                    try:
                        self.ticket_queue.get_nowait()
                    except Exception:
                        pass
                        
            logging.info("TicketsModule resources cleaned up before destroy")
        except Exception as e:
            logging.error(f"Error during ticket module cleanup in destroy: {e}")
        
        # Clear references that might keep objects alive
        self.ticket_data = []
        self.filtered_tickets = []
        self.current_ticket = None
        
        # Finally destroy the widget
        try:
            super().destroy()
        except Exception as e:
            logging.error(f"Error destroying ticket module widget: {e}")

    def pack_forget(self):
        """Hide the module."""
        # Cancel any pending refresh when module is hidden
        if self.refresh_timer_id:
            self.after_cancel(self.refresh_timer_id)
            self.refresh_timer_id = None
            
        super().pack_forget()
            
    def load_tickets(self, force_refresh=False):
        """Initiate loading tickets from the API.
        
        Args:
            force_refresh (bool): Whether to force refresh from API instead of using cache
        """
        if hasattr(self, 'loading_tickets') and self.loading_tickets:
            # Already loading, don't start another operation
            return
            
        self.loading_tickets = True
        self.status_label.config(text="Loading tickets...")
        
        # Create a queue to safely pass data between threads
        self.ticket_queue = queue.Queue()
        
        # Start a background thread for API calls
        self.loader_thread = threading.Thread(
            target=lambda: self._load_tickets_thread(force_refresh=force_refresh), 
            daemon=True
        )
        self.loader_thread.start()
        
        # Schedule a check for results from the queue
        self.after(100, self._check_ticket_queue)
        
        # Start the periodic refresh timer
        self._schedule_ticket_refresh()
    
    def _load_tickets_thread(self, force_refresh=False, is_refresh=False):
        """Background thread to load tickets.
        
        Args:
            force_refresh (bool): Whether to bypass cache and get fresh data from API
            is_refresh (bool): Whether this is a periodic refresh or initial load
        """
        try:
            # Get tickets from the API
            if is_refresh:
                log_message("Refreshing tickets from API...")
            else:
                log_message("Fetching tickets from API...")
            
            # Try to get tickets from the API first
            raw_tickets = []
            try:
                # Pass the force_refresh parameter to the RepairDeskClient
                raw_tickets = self.client.get_all_tickets(force_refresh=force_refresh)
                if force_refresh:
                    log_message(f"Force-refreshed {len(raw_tickets)} tickets from API")
                else:
                    log_message(f"Loaded {len(raw_tickets)} tickets from API")
            except Exception as e:
                log_message(f"Error loading tickets from API: {e}")
                
                # Try to load from cache as fallback
                try:
                    # Use the centralized cache path
                    cache_path = get_ticket_cache_path()
                    if os.path.exists(cache_path):
                        with open(cache_path, "r") as f:
                            raw_tickets = json.load(f)
                            log_message(f"Loaded {len(raw_tickets)} tickets from cache")
                except Exception as cache_err:
                    log_message(f"Error loading tickets from cache: {cache_err}")
            
            # Clear existing tickets if this is a refresh
            if is_refresh:
                self.ticket_data = []
                
            # Process tickets
            for ticket in raw_tickets:
                try:
                    # Convert to consistent format
                    normalized = normalize_ticket(ticket)
                    self.ticket_data.append(normalized)
                except Exception as e:
                    log_message(f"Error processing ticket: {e}")
                    
            # Update the UI on the main thread
            ThreadSafeUIUpdater.safe_update(self, lambda: self.update_ticket_table())
            
            # Schedule the next refresh if this is a periodic refresh
            if is_refresh:
                self._schedule_ticket_refresh()
                
        except Exception as e:
            log_message(f"Error loading tickets: {e}")
            error_msg = str(e)
            ThreadSafeUIUpdater.safe_update(self, lambda: self.status_label.config(text=f"Error loading tickets: {error_msg}"))
            
            # Even if we fail, schedule another refresh
            if is_refresh:
                self._schedule_ticket_refresh()

        except Exception as e:
            log_message(f"Error loading tickets: {e}")
            error_msg = str(e)
            ThreadSafeUIUpdater.safe_update(self, lambda: self.status_label.config(text=f"Error loading tickets: {error_msg}"))

            # Even if we fail, schedule another refresh
            return
            
        self.loading_tickets = True
        self.status_label.config(text="Loading tickets...")
        
        # Create a queue to safely pass data between threads
        self.ticket_queue = queue.Queue()
        
        # Start a background thread for API calls
        self.loader_thread = threading.Thread(target=self._background_ticket_loader, daemon=True)
        self.loader_thread.start()
        
        # Schedule a check for results from the queue
        self.after(100, self._check_ticket_queue)
        
    def _load_tickets_thread(self, force_refresh=False, is_refresh=False):
        """Background thread that loads tickets from the API.
        
        Args:
            force_refresh (bool): Whether to bypass cache and force fresh data from API
            is_refresh (bool): Whether this is a periodic refresh or initial load
        """
        try:
            # Log whether we're force refreshing
            if force_refresh:
                log_message("Force refreshing ticket data from API...")
                
            # Log operation type
            if is_refresh:
                log_message("Refreshing tickets from API...")
            else:
                log_message("Loading tickets from API...")
                
            # Load tickets from API
            raw_tickets = []
            try:
                # Pass the force_refresh parameter to get fresh data when needed
                raw_tickets = self.client.get_all_tickets(force_refresh=force_refresh)
                self.ticket_queue.put(("success", raw_tickets))
            except Exception as e:
                logging.error(f"Error loading tickets from API: {e}")
                
                # Try to load from cache as fallback
                try:
                    # Use the centralized cache path
                    cache_path = get_ticket_cache_path()
                    if os.path.exists(cache_path):
                        with open(cache_path, "r") as f:
                            raw_tickets = json.load(f)
                            self.ticket_queue.put(("cache", raw_tickets))
                    else:
                        self.ticket_queue.put(("error", f"Error: {str(e)}. No cache available."))
                except Exception as cache_err:
                    logging.error(f"Error loading tickets from cache: {cache_err}")
                    self.ticket_queue.put(("error", f"API Error: {str(e)}\nCache Error: {str(cache_err)}"))
        except Exception as e:
            logging.exception(f"Unhandled exception in ticket loading: {e}")
            self.ticket_queue.put(("error", f"Unhandled error: {str(e)}"))
    
    def _check_ticket_queue(self):
        """Check for tickets in the queue and update the UI safely."""
        try:
            # Check if we've been destroyed
            if hasattr(self, '_is_destroyed') and self._is_destroyed:
                logging.debug("Ticket queue check aborted - widget destroyed")
                return
                
            # Initialize pending updates if not already created
            if not hasattr(self, '_pending_updates'):
                self._pending_updates = []
                
            if not hasattr(self, 'ticket_queue') or self.ticket_queue.empty():
                # Keep checking if thread is still running
                if hasattr(self, 'loader_thread') and self.loader_thread.is_alive():
                    # Store the after ID so we can cancel it if needed
                    after_id = self.after(100, self._check_ticket_queue)
                    self._pending_updates.append(after_id)
                    return
                else:
                    # Thread finished but no data in queue - likely an error
                    self.loading_tickets = False
                    try:
                        self.status_label.config(text="Error: No tickets loaded")
                    except (tk.TclError, RuntimeError):
                        # Widget might be destroyed
                        logging.debug("Failed to update status label - widget likely destroyed")
                    return
                    
            # Get data from the queue
            status, data = self.ticket_queue.get()
            
            if status == "success":
                # Process tickets on the main thread
                self.ticket_data = []
                processed = 0
                
                for ticket in data:
                    try:
                        processed += 1
                        normalized = normalize_ticket(ticket)
                        self.ticket_data.append(normalized)
                    except Exception as e:
                        logging.error(f"Error processing ticket: {e}")
                
                # Update the UI
                self.update_ticket_table()
                self.status_label.config(text=f"Loaded {processed} tickets from API")
                
                # Save cache for offline access
                try:
                    # Use the centralized cache path
                    cache_path = get_ticket_cache_path()
                    with open(cache_path, "w") as f:
                        json.dump(data, f)
                except Exception as e:
                    logging.error(f"Failed to save ticket cache: {e}")
                    
            elif status == "cache":
                # Process cached tickets
                self.ticket_data = []
                processed = 0
                
                for ticket in data:
                    try:
                        processed += 1
                        normalized = normalize_ticket(ticket)
                        self.ticket_data.append(normalized)
                    except Exception as e:
                        logging.error(f"Error processing cached ticket: {e}")
                
                # Update the UI
                self.update_ticket_table()
                self.status_label.config(text=f"Loaded {processed} tickets from cache")
                
            elif status == "error":
                # Show error in UI
                self.status_label.config(text=data)
                logging.error(f"Ticket loading error: {data}")
        except Exception as e:
            logging.exception(f"Error in _check_ticket_queue: {e}")
            self.status_label.config(text=f"Error: {str(e)}")
        finally:
            self.loading_tickets = False
            
            # Schedule the next auto-refresh if this was successful
            if hasattr(self, '_schedule_ticket_refresh'):
                self._schedule_ticket_refresh()
                
    def _schedule_ticket_refresh(self):
        """Schedule the next ticket refresh."""
        # Cancel any existing refresh timer
        if hasattr(self, 'refresh_timer_id') and self.refresh_timer_id:
            self.after_cancel(self.refresh_timer_id)
            self.refresh_timer_id = None
        
        # Schedule a new refresh
        self.refresh_timer_id = self.after(self.REFRESH_INTERVAL, self._refresh_tickets)
        
    def _refresh_tickets(self):
        """Refresh tickets from the API."""
        # Don't refresh if we're already loading or if we're destroyed
        if hasattr(self, 'loading_tickets') and self.loading_tickets:
            return
            
        if hasattr(self, '_is_destroyed') and self._is_destroyed:
            return
            
        # Force refresh using the force_refresh parameter
        self.load_tickets(force_refresh=True)
        
    def _fetch_detailed_ticket_info(self, ticket_id):
        """Fetch detailed ticket information from the API using the /tickets/{Ticket-Id} endpoint.
        
        Args:
            ticket_id: The display ID of the ticket (e.g., T-12661)
        """
        try:
            # Don't fetch if module is being destroyed or already loading
            if hasattr(self, '_is_destroyed') and self._is_destroyed:
                return
            
            # Find the ticket in our data to get the actual API ID
            selected_ticket = None
            actual_api_id = None
            
            # Try filtered tickets first
            for ticket in self.filtered_tickets:
                if str(ticket.get("id", "")) == str(ticket_id):
                    selected_ticket = ticket
                    break
                    
            # If not found, check all tickets
            if not selected_ticket:
                for ticket in self.ticket_data:
                    if str(ticket.get("id", "")) == str(ticket_id):
                        selected_ticket = ticket
                        break
            
            # Extract the actual API ID from the raw ticket data
            if selected_ticket and "raw_data" in selected_ticket:
                raw_data = selected_ticket["raw_data"]
                
                # Look for the actual ticket ID (not the order_id)
                if "id" in raw_data:
                    actual_api_id = raw_data["id"]
                elif "summary" in raw_data and "id" in raw_data["summary"]:
                    actual_api_id = raw_data["summary"]["id"]
                elif "summary" in raw_data and "ticket_id" in raw_data["summary"]:
                    actual_api_id = raw_data["summary"]["ticket_id"]
                    
                # If we still don't have the API ID, try devices section
                if not actual_api_id and "devices" in raw_data and raw_data["devices"] and isinstance(raw_data["devices"], list):
                    device = raw_data["devices"][0]
                    if "id" in device:
                        actual_api_id = device["id"]
                        
            # Log what we found
            if actual_api_id:
                log_message(f"Found actual API ID {actual_api_id} for display ticket ID {ticket_id}")
            else:
                log_message(f"Could not find actual API ID for display ticket ID {ticket_id}, using display ID")
                
            # Create API client
            api_client = RepairDeskClient()
            
            # Update status
            ThreadSafeUIUpdater.safe_update(self, lambda: self.status_label.config(text="Fetching detailed ticket information..."))
            
            # Fetch detailed ticket data using the actual API ID if found
            detailed_ticket = api_client.get_ticket_by_id(ticket_id, actual_api_id)
            
            if not detailed_ticket or not isinstance(detailed_ticket, dict):
                log_message(f"Failed to fetch detailed ticket info for {ticket_id}")
                # Update status in main thread
                ThreadSafeUIUpdater.safe_update(self, lambda: self.status_label.config(text="Failed to fetch ticket details"))
                return
                
            # Process and display ticket in the main thread
            ThreadSafeUIUpdater.safe_update(self, lambda: self._update_with_detailed_info(detailed_ticket, ticket_id))
            
        except Exception as e:
            log_message(f"Error fetching detailed ticket info: {e}")
            error_msg = str(e)[:50]
            ThreadSafeUIUpdater.safe_update(self, lambda: self.status_label.config(text=f"Error fetching ticket details: {error_msg}"))
        
    def _update_with_detailed_info(self, detailed_ticket, ticket_id):
        """Update the UI with detailed ticket information.
        
        Args:
            detailed_ticket: The detailed ticket data from API
            ticket_id: The ID of the ticket
        """
        # Update status
        self.status_label.config(text="Detailed ticket information loaded")
        
        # Store the detailed ticket data for future use
        if self.current_ticket and str(self.current_ticket.get("id", "")) == str(ticket_id):
            self.current_ticket["detailed_data"] = detailed_ticket
            
            # Update the details panel with the new detailed information
            self.update_details_panel(self.current_ticket)
            
            # If the ticket details window is open, update it too
            if hasattr(self, "active_details_window") and self.active_details_window and self.active_details_window.winfo_exists():
                # Close the existing window and open a new one with updated data
                self.active_details_window.destroy()
                self.show_ticket_details(ticket_id)
    
    def _manual_refresh(self):
        """Handle manual refresh button click."""
        # Don't refresh if we're already loading or if we're destroyed
        if hasattr(self, 'loading_tickets') and self.loading_tickets:
            log_message("Already loading tickets, ignoring manual refresh")
            return
            
        if hasattr(self, '_is_destroyed') and self._is_destroyed:
            log_message("Module destroyed, ignoring manual refresh")
            return
            
        try:
            # Update UI first
            self.status_label.config(text="Refreshing tickets...")
            self.loading_tickets = True
            
            # First update the UI
            self.update_idletasks()
            
            # Force refresh directly
            log_message("Manual refresh: Fetching tickets directly")
            setattr(self.client, '_force_refresh', True)
            
            # Get tickets directly - more reliable for manual refresh
            raw_tickets = self.client.get_all_tickets()
            log_message(f"Manual refresh: Loaded {len(raw_tickets)} tickets")
            
            # Process tickets
            self.ticket_data = []
            for ticket in raw_tickets:
                try:
                    normalized = normalize_ticket(ticket)
                    self.ticket_data.append(normalized)
                except Exception as e:
                    log_message(f"Error processing ticket: {e}")
            
            # Update UI
            self.update_ticket_table()
            self.status_label.config(text=f"Loaded {len(self.ticket_data)} tickets")
            
            # Schedule next refresh
            self._schedule_ticket_refresh()
            
        except (tk.TclError, RuntimeError) as e:
            # Widget might be destroyed
            log_message(f"Error during manual refresh (UI): {e}")
        except Exception as e:
            # Handle general errors
            log_message(f"Error during manual refresh: {e}")
            try:
                self.status_label.config(text=f"Error refreshing tickets: {str(e)}")
            except:
                pass
        finally:
            self.loading_tickets = False
        
    def update_ticket_table(self):
        """Update the ticket table with current data."""
        self.tickets_table.delete(*self.tickets_table.get_children())
        
        # Add tickets to the table
        self.filtered_tickets = self.ticket_data.copy()
        for ticket in self.filtered_tickets:
            self.tickets_table.insert(
                "",
                "end",
                values=(
                    ticket.get("id", ""),
                    ticket.get("customer", ""),
                    ticket.get("device", ""),
                    ticket.get("issue", ""),
                    ticket.get("status", ""),
                    ticket.get("technician", ""),
                    ticket.get("date_created", ""),
                    ticket.get("date_updated", ""),
                ),
            )

        # Update status
        self.status_label.config(text=f"{len(self.filtered_tickets)} tickets loaded")
        
    def search_tickets_callback(self, event=None):
        """Search for tickets based on the search input."""
        search_term = self.search_var.get().strip().lower()
        self.filter_tickets(self.status_var.get(), search_term)
        
    def filter_by_status(self, event=None):
        """Handle status filter selection."""
        # This method is called when the status combobox selection changes
        # We don't immediately filter to allow the user to make multiple filter selections first
        logging.info(f"Status filter selected: {self.status_var.get()}")
        
    def apply_filters(self):
        """Apply all active filters to the ticket list."""
        self._filter_tickets()
        status_filter = self.status_var.get()
        self.show_notification(f"Filtered tickets by status: {status_filter}", "info")
        
    def filter_tickets_callback(self, event=None):
        """Filter tickets based on selection (legacy method)."""
        self._filter_tickets() 
        status = self.status_var.get()
        search_term = self.search_var.get().strip().lower()
        self.filter_tickets(status, search_term)
        
    def filter_tickets(self, status="All", search_term=""):
        """Filter tickets by status and search term."""
        try:
            # Check if widget is already destroyed
            if hasattr(self, '_is_destroyed') and self._is_destroyed:
                logging.debug("Skipping ticket filtering - widget destroyed")
                return
                
            # Clear existing items
            for item in self.tickets_table.get_children():
                try:
                    self.tickets_table.delete(item)
                except (tk.TclError, RuntimeError) as e:
                    logging.debug(f"Error clearing table row: {e}")
                    # Widget might be destroyed, stop further processing
                    return
                    
            # Filter tickets
            self.filtered_tickets = []
            for ticket in self.ticket_data:
                # Status filter
                if status != "All" and ticket.get("status") != status:
                    continue
                    
                # Search filter
                if search_term and not (
                    search_term in str(ticket.get("id", "")).lower()
                    or search_term in str(ticket.get("customer", "")).lower()
                    or search_term in str(ticket.get("device", "")).lower()
                    or search_term in str(ticket.get("issue", "")).lower()
                    or search_term in str(ticket.get("technician", "")).lower()
                ):
                    continue
                    
                self.filtered_tickets.append(ticket)
                
            # Display filtered tickets
            for ticket in self.filtered_tickets:
                try:
                    values = [
                        ticket.get("id", ""),
                        ticket.get("customer", ""),
                        ticket.get("device", ""),
                        ticket.get("issue", ""),
                        ticket.get("status", ""),
                        ticket.get("technician", ""),
                        ticket.get("date_created", ""),
                    ]
                    self.tickets_table.insert("", "end", values=values)
                except (tk.TclError, RuntimeError) as e:
                    logging.debug(f"Error inserting row: {e}")
                    break
                    
            # Display filtered count in status bar
            try:
                if search_term and status != "All":
                    self.status_label.config(
                        text=f"{len(self.filtered_tickets)} tickets matching '{search_term}' with status '{status}'"
                    )
                elif search_term:
                    self.status_label.config(
                        text=f"{len(self.filtered_tickets)} tickets matching '{search_term}'"
                    )
                elif status != "All":
                    self.status_label.config(
                        text=f"{len(self.filtered_tickets)} tickets with status '{status}'"
                    )
                else:
                    self.status_label.config(text=f"{len(self.filtered_tickets)} tickets found")
            except (tk.TclError, RuntimeError) as e:
                logging.debug(f"Error updating status label: {e}")
        except Exception as e:
            logging.error(f"Error filtering tickets: {e}")
            try:
                self.status_label.config(text=f"Error filtering tickets: {e}")
            except:
                pass
            
    def on_ticket_select(self, event):
        """Handle ticket selection in the table."""
        selection = self.tickets_table.selection()
        if not selection:
            return

        # Get the ticket data for the selected row
        item = self.tickets_table.item(selection[0])
        ticket_id = item["values"][0]

        # Find the ticket in our local data
        selected_ticket = None
        for ticket in self.filtered_tickets:
            if str(ticket.get("id", "")) == str(ticket_id):
                selected_ticket = ticket
                break

        if not selected_ticket:
            return

        # Store the current ticket
        self.current_ticket = selected_ticket
        
        # Fetch complete detailed information for this ticket from API
        self.status_label.config(text="Fetching detailed ticket information...")
        self.update_details_panel(selected_ticket)  # Show basic info while fetching
        
        # Start a background thread to fetch detailed ticket info to avoid UI freezing
        threading.Thread(
            target=self._fetch_detailed_ticket_info,
            args=(ticket_id,),
            daemon=True
        ).start()
        
        # Enable update button
        self.update_btn.config(state="normal")
        
    def on_double_click(self, event):
        """Handle double-click on a ticket."""
        selection = self.tickets_table.selection()
        if not selection:
            return

        # Get the ticket data for the selected row
        item = self.tickets_table.item(selection[0])
        ticket_id = item["values"][0]

        # Show detailed view or edit form
        self.show_ticket_details(ticket_id)
        
    def update_details_panel(self, ticket):
        """Update the details panel with the selected ticket's information."""
        if not ticket:
            return

        # Store the current ticket
        self.current_ticket = ticket
        
        # Check if we have detailed data from the API (/tickets/{Ticket-Id} endpoint)
        detailed_data = ticket.get("detailed_data", {})
        has_detailed_data = detailed_data and isinstance(detailed_data, dict)

        # Update customer information
        self.customer_name.config(text=ticket.get('customer', 'N/A'))
        self.customer_phone.config(text=ticket.get('phone', 'N/A'))
        
        # Get customer info from the most detailed source available
        raw_data = ticket.get("raw_data", {})
        
        if has_detailed_data:
            # Handle case where API returns a list instead of dict
            if isinstance(detailed_data, list):
                # If it's a list, we'll use the first item if available
                if detailed_data and len(detailed_data) > 0:
                    detailed_data = detailed_data[0]
                else:
                    detailed_data = {}
                    
            # Get nested data with safety checks
            data_obj = detailed_data.get("data", {}) if isinstance(detailed_data, dict) else {}
            summary_obj = data_obj.get("summary", {}) if isinstance(data_obj, dict) else {}
            customer = summary_obj.get("customer", {}) if isinstance(summary_obj, dict) else {}
        else:
            # Fall back to raw data from the tickets list
            customer = raw_data.get("summary", {}).get("customer", {})
            
        self.customer_email.config(text=customer.get("email", "-"))

        # Update device information
        self.device_type.config(text=ticket.get('device', 'N/A'))
        self.device_issue.config(text=ticket.get('issue', 'N/A'))

        # IMEI/SN if available
        imei = "-"
        serial = "-"
        
        # Try to get device details from the most comprehensive source
        if has_detailed_data:
            # Use the data_obj we already processed to get devices
            data_obj = detailed_data.get("data", {}) if isinstance(detailed_data, dict) else {}
            devices = data_obj.get("devices", []) if isinstance(data_obj, dict) else []
        else:
            devices = raw_data.get("devices", [])
            
        if devices and len(devices) > 0:
            device = devices[0]
            if "imei" in device and device["imei"]:
                imei = device["imei"]
            # Try to get serial from device details    
            if "device" in device and "serial" in device["device"]:
                serial = device["device"]["serial"]
                
        self.device_imei.config(text=imei)
        
        # We'll just update the IMEI label to show both IMEI and Serial if available
        if serial != "-" and imei != "-":
            self.device_imei.config(text=f"{imei} / SN: {serial}")
        elif serial != "-":
            self.device_imei.config(text=f"SN: {serial}")
        else:
            self.device_imei.config(text=imei)
        
        # Update status and assignment labels
        self.status_label.config(text=ticket.get("status", "Unknown"))
        self.assigned_label.config(text=ticket.get("technician", "Unassigned"))
        
        # Update dates
        self.date_created.config(text=ticket.get("date_created", "-"))
        self.date_updated.config(text=ticket.get("date_updated", "-"))

        # Update notes
        self.notes_text.config(state="normal")
        self.notes_text.delete("1.0", tk.END)

        notes = "No notes available for this ticket."

        # Check for comments, notes, or activities in the ticket data
        comments_found = False
        
        # Look for comments directly in the data structure
        if has_detailed_data:
            # Check for comments in the API response
            data_obj = detailed_data.get("data", {}) if isinstance(detailed_data, dict) else {}
            
            # Try to find comments - check multiple possible locations
            comments = None
            
            # Check direct comments field
            if isinstance(data_obj, dict) and "comments" in data_obj:
                comments = data_obj["comments"]
                comments_found = True
            
            # Some APIs might have comments in the summary
            elif isinstance(data_obj, dict) and "summary" in data_obj and isinstance(data_obj["summary"], dict):
                if "comments" in data_obj["summary"]:
                    comments = data_obj["summary"]["comments"]
                    comments_found = True
            
            # Or sometimes in each device entry
            elif isinstance(data_obj, dict) and "devices" in data_obj and data_obj["devices"] and isinstance(data_obj["devices"][0], dict):
                if "comments" in data_obj["devices"][0]:
                    comments = data_obj["devices"][0]["comments"]
                    comments_found = True
            
            if comments_found and comments:
                note_entries = []
                for comment in comments:
                    timestamp = "N/A"
                    if "date" in comment:
                        timestamp = comment["date"]
                    elif "timestamp" in comment:
                        try:
                            ts = float(comment.get("timestamp", 0))
                            timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            pass
                    
                    # Try different field names for the comment text
                    text = comment.get("text", "")
                    if not text:
                        text = comment.get("note", "")
                    if not text:
                        text = comment.get("comment", "No comment text")
                    
                    # Add author if available
                    author = comment.get("author", comment.get("user", ""))
                    if author:
                        note_entries.append(f"{timestamp} - {author}: {text}")
                    else:
                        note_entries.append(f"{timestamp}: {text}")
                
                notes = "\n\n".join(note_entries)
        
        # If no comments found, check for activities
        if not comments_found and has_detailed_data:
            data_obj = detailed_data.get("data", {}) if isinstance(detailed_data, dict) else {}
            if isinstance(data_obj, dict) and "activities" in data_obj:
                activities = data_obj["activities"]
                if activities:
                    note_entries = []
                    for activity in activities:
                        timestamp = "N/A"
                        try:
                            ts = float(activity.get("timestamp", 0))
                            timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            pass
                        
                        note_text = activity.get("activity", "Unknown activity")
                        note_entries.append(f"{timestamp}: {note_text}")
                    
                    notes = "\n\n".join(note_entries)
                    comments_found = True
        elif "notes" in raw_data and raw_data["notes"]:
            notes = "\n\n".join(
                [f"{note.get('date', '')}: {note.get('text', '')}" for note in raw_data["notes"]]
            )
        elif raw_data.get("devices", []) and len(raw_data["devices"]) > 0:
            if "repairProdItems" in raw_data["devices"][0]:
                repair_items = [
                    item.get("name", "") for item in raw_data["devices"][0]["repairProdItems"]
                ]
                notes = "Repair items: " + ", ".join(repair_items)

        self.notes_text.insert("1.0", notes)
        self.notes_text.config(state="disabled")
        
        # Enable all action buttons
        self.update_btn.config(state="normal")
        self.print_btn.config(state="normal")
        self.complete_btn.config(state="normal")
        self.cancel_btn.config(state="normal")
        
    def show_ticket_details(self, ticket_id):
        """Show detailed ticket view using complete data from the /tickets/{Ticket-Id} endpoint."""
        # Find the ticket in our data
        selected_ticket = None
        for ticket in self.filtered_tickets:
            if str(ticket.get("id", "")) == str(ticket_id):
                selected_ticket = ticket
                break

        if not selected_ticket:
            # If not found in filtered tickets, try all tickets
            for ticket in self.ticket_data:
                if str(ticket.get("id", "")) == str(ticket_id):
                    selected_ticket = ticket
                    break
                    
        if not selected_ticket:
            messagebox.showerror("Error", f"Ticket {ticket_id} not found")
            return
            
        # Check if we have detailed data, and if not, try to fetch it first
        has_detailed_data = "detailed_data" in selected_ticket and selected_ticket["detailed_data"]
        if not has_detailed_data:
            # Show loading message
            messagebox.showinfo("Loading", "Fetching detailed ticket information...")
            
            # Initiate fetching of detailed data
            threading.Thread(
                target=self._fetch_and_show_details,
                args=(ticket_id,),
                daemon=True
            ).start()
            return
        
        # Use our custom TicketModal class to show ticket details
        from .ticket_modal import TicketModal
        ticket_modal = TicketModal(self, selected_ticket["detailed_data"]["data"], customer_folder_path=None)
        
        # Store reference to the window
        self.active_details_window = ticket_modal
    
    def _fetch_and_show_details(self, ticket_id):
        """Fetch detailed ticket info and show details window."""
        # Get the detailed ticket info - this runs in a background thread
        detailed_data = self._fetch_detailed_ticket_info(ticket_id)
        
        if not detailed_data:
            # Failed to get data
            messagebox.showerror("Error", f"Failed to retrieve detailed information for ticket {ticket_id}")
            return
            
        # Now find the ticket in our data and update it
        found = False
        for ticket in self.filtered_tickets:
            if str(ticket.get("id", "")) == str(ticket_id):
                ticket["detailed_data"] = detailed_data
                found = True
                break
                
        if not found:
            # If not in filtered tickets, try all tickets
            for ticket in self.ticket_data:
                if str(ticket.get("id", "")) == str(ticket_id):
                    ticket["detailed_data"] = detailed_data
                    found = True
                    break
        
        if not found:
            messagebox.showerror("Error", f"Ticket {ticket_id} not found in local data")
            return
        
        # Schedule showing the details window on the main thread
        self.after(10, lambda: self.show_ticket_details(ticket_id))
        
    def _fetch_detailed_ticket_info(self, ticket_id):
        """Fetch detailed ticket information from the API using the /tickets/{Ticket-Id} endpoint.
        
        Args:
            ticket_id: The display ID of the ticket (e.g., T-12661)
        """
        # First, find the actual API ID for this ticket
        api_ticket_id = None
        
        # Look for the ticket in our data to get the API ID
        for ticket in self.filtered_tickets:
            if str(ticket.get("id", "")) == str(ticket_id):
                # Get the original raw data
                raw_data = ticket.get("raw_data", {})
                # Extract the internal API ID from raw_data -> summary -> id
                if "summary" in raw_data and "id" in raw_data["summary"]:
                    api_ticket_id = raw_data["summary"]["id"]
                    log_message(f"Found API ID {api_ticket_id} for ticket {ticket_id}")
                break
                
        # If not found in filtered tickets, try all tickets
        if not api_ticket_id:
            for ticket in self.ticket_data:
                if str(ticket.get("id", "")) == str(ticket_id):
                    # Get the original raw data
                    raw_data = ticket.get("raw_data", {})
                    # Extract the internal API ID from raw_data -> summary -> id
                    if "summary" in raw_data and "id" in raw_data["summary"]:
                        api_ticket_id = raw_data["summary"]["id"]
                        log_message(f"Found API ID {api_ticket_id} for ticket {ticket_id} in full ticket list")
                    break
        
        # If we couldn't find the API ID, use the display ID as fallback
        if not api_ticket_id:
            api_ticket_id = ticket_id
            # Remove T- prefix if present
            if isinstance(api_ticket_id, str) and api_ticket_id.startswith("T-"):
                api_ticket_id = api_ticket_id[2:]
                
        # Create API client
        client = RepairDeskClient()
        
        try:
            # Get detailed ticket information
            detailed_ticket = client.get_ticket_by_id(ticket_id, actual_api_id=api_ticket_id)
            
            # Check if the response is empty or not a valid ticket response
            if not detailed_ticket or not isinstance(detailed_ticket, dict) or not detailed_ticket.get('data'):
                log_message(f"Failed to retrieve detailed information for ticket {ticket_id}")
                # Show a message to the user
                messagebox.showerror("Ticket Not Found", f"Could not find ticket {ticket_id}. It may have been deleted or is not accessible.")
                return None
                
            # Return the detailed ticket data
            return detailed_ticket
        except Exception as e:
            log_message(f"Error fetching ticket details: {e}")
            return None
    # All ticket display functionality has been moved to the TicketModal class
    
    def _update_with_detailed_info(self, detailed_ticket, ticket_id):
        """Update the UI with detailed ticket information.
        
        Args:
            detailed_ticket: The detailed ticket data from API
            ticket_id: The ID of the ticket
        """
        # Find the ticket in our data
        selected_ticket = None
        for ticket in self.filtered_tickets:
            if str(ticket.get("id", "")) == str(ticket_id):
                ticket["detailed_data"] = detailed_ticket
                selected_ticket = ticket
                break
        
        # If not found in filtered tickets, try all tickets
        if not selected_ticket:
            for ticket in self.ticket_data:
                if str(ticket.get("id", "")) == str(ticket_id):
                    ticket["detailed_data"] = detailed_ticket
                    break
                    
        # Show the details window
        self.after(10, lambda: self.show_ticket_details(ticket_id))
            
    # End of _update_with_detailed_info method
    def refresh_tickets(self, event=None):
        """Refresh the tickets list from the API"""
        self.load_tickets()

    # All ticket details display has been moved to ticket_modal.py
        
    def _fetch_and_show_details(self, ticket_id):
        """Fetch detailed ticket information and show it in a window.
        
        Args:
            ticket_id: The ID of the ticket to fetch and display
        """
        try:
            # Create API client
            api_client = RepairDeskClient()
            
            # Find the actual API ID for this ticket from raw data
            api_ticket_id = None
            
            # Look in filtered tickets first
            for ticket in self.filtered_tickets:
                if str(ticket.get("id", "")) == str(ticket_id):
                    raw_data = ticket.get("raw_data", {})
                    if "summary" in raw_data and "id" in raw_data["summary"]:
                        api_ticket_id = raw_data["summary"]["id"]
                        log_message(f"Found API ID {api_ticket_id} for ticket {ticket_id} in duplicate _fetch_and_show_details")
                    break
                    
            # If not found, try all tickets
            if not api_ticket_id:
                for ticket in self.ticket_data:
                    if str(ticket.get("id", "")) == str(ticket_id):
                        raw_data = ticket.get("raw_data", {})
                        if "summary" in raw_data and "id" in raw_data["summary"]:
                            api_ticket_id = raw_data["summary"]["id"]
                            log_message(f"Found API ID {api_ticket_id} for ticket {ticket_id} in duplicate method (all tickets)")
                        break
                        
            # Fetch detailed ticket data using the correct API ID
            detailed_ticket = api_client.get_ticket_by_id(ticket_id, actual_api_id=api_ticket_id)
            
            if not detailed_ticket or not isinstance(detailed_ticket, dict):
                ThreadSafeUIUpdater.safe_update(self, lambda: messagebox.showerror(
                    "Error", f"Failed to fetch detailed ticket info for {ticket_id}"
                ))
                return
                
            # Find the ticket in our data
            selected_ticket = None
            for ticket in self.filtered_tickets:
                if str(ticket.get("id", "")) == str(ticket_id):
                    selected_ticket = ticket
                    break

            if not selected_ticket:
                # If not found in filtered tickets, try all tickets
                for ticket in self.ticket_data:
                    if str(ticket.get("id", "")) == str(ticket_id):
                        selected_ticket = ticket
                        break
                        
            if selected_ticket:
                # Update the ticket with detailed data
                selected_ticket["detailed_data"] = detailed_ticket
                
                # Show the details window in the main thread
                ThreadSafeUIUpdater.safe_update(self, lambda: self.show_ticket_details(ticket_id))
            else:
                ThreadSafeUIUpdater.safe_update(self, lambda: messagebox.showerror(
                    "Error", f"Ticket {ticket_id} not found in local data"
                ))
                
        except Exception as e:
            log_message(f"Error fetching and showing ticket details: {e}")
            error_msg = str(e)[:100]
            ThreadSafeUIUpdater.safe_update(self, lambda: messagebox.showerror(
                "Error", f"Failed to load ticket details: {error_msg}"
            ))
        
    def show_update_form(self, ticket, details_window=None):
        """Show form to update a ticket."""
        # Create dialog for updating ticket
        update_window = tk.Toplevel(self)
        update_window.title(f"Update Ticket {ticket.get('id', '')}")
        update_window.geometry("400x300")
        update_window.resizable(False, False)

        frame = ttk.Frame(update_window, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text=f"Update Ticket {ticket.get('id', '')}", font=("" , 12, "bold")
        ).pack(anchor="w", pady=(0, 15))

        # Status update
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill="x", pady=5)

        ttk.Label(status_frame, text="Status:").pack(side="left", padx=(0, 10))

        update_status_var = tk.StringVar(value=ticket.get("status", "Open"))
        status_combo = ttk.Combobox(
            status_frame,
            textvariable=update_status_var,
            values=["Open", "In Progress", "Waiting for Parts", "Completed", "Pending"],
        )
        status_combo.pack(side="left", fill="x", expand=True)

        # Assigned technician
        tech_frame = ttk.Frame(frame)
        tech_frame.pack(fill="x", pady=5)

        ttk.Label(tech_frame, text="Assign to:").pack(side="left", padx=(0, 10))

        tech_var = tk.StringVar(value=ticket.get("technician", ""))
        tech_combo = ttk.Combobox(
            tech_frame, textvariable=tech_var, values=self.get_technician_list()
        )
        tech_combo.pack(side="left", fill="x", expand=True)

        # Add note
        ttk.Label(frame, text="Add Note:").pack(anchor="w", pady=(10, 5))
        note_text = tk.Text(frame, height=5, wrap="word")
        note_text.pack(fill="both", expand=True, pady=(0, 10))

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(button_frame, text="Cancel", command=update_window.destroy).pack(
            side="right", padx=5
        )

        ttk.Button(
            button_frame,
            text="Save Changes",
            style="Primary.TButton",
            command=lambda: self.save_ticket_update(
                ticket.get("id"),
                update_status_var.get(),
                tech_var.get(),
                note_text.get("1.0", "end-1c"),
                update_window,
            ),
        ).pack(side="right", padx=5)

        # Make modal
        update_window.transient(self)
        update_window.grab_set()
        update_window.wait_window()

    def print_invoice(self):
        """Print invoice for the selected ticket."""
        if not hasattr(self, 'current_ticket') or not self.current_ticket:
            self.show_notification("Please select a ticket first", "warning")
            return
        
        ticket_id = self.current_ticket.get('id', 'Unknown')
        
        # Show print options dialog
        print_window = tk.Toplevel(self)
        print_window.title(f"Print Invoice - Ticket #{ticket_id}")
        print_window.geometry("400x300")
        print_window.resizable(False, False)

        frame = ttk.Frame(print_window, padding=15)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(
            frame, text=f"Print Invoice for Ticket #{ticket_id}", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 15))
        
        # Print options
        options_frame = ttk.LabelFrame(frame, text="Print Options", padding=10, style="DetailSection.TLabelframe")
        options_frame.pack(fill="x", pady=(0, 15))
        
        # Include detailed items checkbox
        include_items_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Include detailed repair items", variable=include_items_var
        ).pack(anchor="w", pady=2)
        
        # Include notes checkbox
        include_notes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, text="Include service notes", variable=include_notes_var
        ).pack(anchor="w", pady=2)
        
        # Include customer signature line
        include_signature_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Include customer signature line", variable=include_signature_var
        ).pack(anchor="w", pady=2)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", side="bottom", pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancel", command=print_window.destroy).pack(
            side="right", padx=5
        )
        
        ttk.Button(
            button_frame,
            text="Print",
            style="Action.TButton",
            command=lambda: self.do_print_invoice(
                ticket_id,
                include_items_var.get(),
                include_notes_var.get(),
                include_signature_var.get(),
                print_window
            ),
        ).pack(side="right", padx=5)
        
        # Make modal
        print_window.transient(self)
        print_window.grab_set()
        print_window.wait_window()
        
    def do_print_invoice(self, ticket_id, include_items, include_notes, include_signature, window):
        """Perform the actual invoice printing."""
        # In a real app, this would generate and print an invoice
        msg = f"Printing invoice for ticket {ticket_id}\n"
        msg += f"Options: Items: {'Yes' if include_items else 'No'}, "
        msg += f"Notes: {'Yes' if include_notes else 'No'}, "
        msg += f"Signature: {'Yes' if include_signature else 'No'}"
        
        # Close the print window
        window.destroy()
        
        # Show success notification
        self.show_notification("Invoice sent to printer", "success")

    def save_ticket_update(self, ticket_id, status, technician, note, window):
        """Save ticket updates."""
        try:
            # Here you would call the API to update the ticket
            # For demonstration, we'll just update our local data

            logging.info(f"Updating ticket {ticket_id}: Status={status}, Tech={technician}")

            if note.strip():
                logging.info(f"Adding note to ticket {ticket_id}: {note}")

            # Update the current ticket in memory
            if self.current_ticket:
                self.current_ticket["status"] = status
                self.current_ticket["technician"] = technician

                # Update the UI
                self.status_label.config(text=status)
                self.assigned_label.config(text=technician)

                # Update the table
                for item_id in self.tickets_table.get_children():
                    item = self.tickets_table.item(item_id)
                    if str(item["values"][0]) == str(ticket_id):
                        values = list(item["values"])
                        values[4] = status  # Status column
                        values[5] = technician  # Technician column
                        values[7] = datetime.now().strftime("%Y-%m-%d")  # Updated date
                        self.tickets_table.item(item_id, values=tuple(values))
                        break

                # Update notes if provided
                if note.strip():
                    self.notes_text.config(state="normal")
                    current_notes = self.notes_text.get("1.0", tk.END).strip()
                    if current_notes:
                        self.notes_text.insert(
                            tk.END, f"\n\n{datetime.now().strftime('%Y-%m-%d %H:%M')}: {note}"
                        )
                    else:
                        self.notes_text.insert(
                            tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {note}"
                        )
                    self.notes_text.config(state="disabled")

            self.show_notification(f"Ticket {ticket_id} updated successfully", "success")

            # In a real implementation, this would update the API:
            # self.client.update_ticket(ticket_id, status=status, technician=technician)
            # if note:
            #     self.client.add_note_to_ticket(ticket_id, note)

            # Close the dialog if provided
            if window:
                window.destroy()
                
            # Refresh tickets to show updated data
            self.load_tickets(force_refresh=True)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update ticket: {str(e)}")
            
    def mark_complete(self):
        """Mark the selected ticket as complete."""
        if not hasattr(self, 'current_ticket') or not self.current_ticket:
            self.show_notification("Please select a ticket first", "warning")
            return
        
        ticket_id = self.current_ticket.get('id', 'Unknown')
        result = messagebox.askyesno("Confirm Action", 
                                 f"Are you sure you want to mark ticket #{ticket_id} as complete?\n"
                                 f"This will notify the customer that their repair is ready for pickup.")
        
        if result:
            # This would call the API to update the ticket status
            # For demonstration, we'll just update our local data
            if self.current_ticket:
                self.current_ticket["status"] = "Completed"
                
                # Update the UI
                self.status_label.config(text="Completed")
                
                # Update the table
                for item_id in self.tickets_table.get_children():
                    item = self.tickets_table.item(item_id)
                    if str(item["values"][0]) == str(ticket_id):
                        values = list(item["values"])
                        values[4] = "Completed"  # Status column
                        values[7] = datetime.now().strftime("%Y-%m-%d")  # Updated date
                        self.tickets_table.item(item_id, values=tuple(values))
                        break
                        
            self.show_notification(f"Ticket {ticket_id} marked as complete", "success")
            
            # Refresh tickets to show updated status
            self.load_tickets(force_refresh=True)
    
    def cancel_ticket(self):
        """Cancel the selected ticket."""
        if not hasattr(self, 'current_ticket') or not self.current_ticket:
            self.show_notification("Please select a ticket first", "warning")
            return
        
        ticket_id = self.current_ticket.get('id', 'Unknown')
        
        # Create a dialog to confirm and enter reason
        cancel_window = tk.Toplevel(self)
        cancel_window.title(f"Cancel Ticket #{ticket_id}")
        cancel_window.geometry("400x250")
        cancel_window.resizable(False, False)
        cancel_window.transient(self)
        cancel_window.grab_set()
        
        frame = ttk.Frame(cancel_window, padding=15)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(
            frame, text=f"Cancel Ticket #{ticket_id}", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 5))
        
        ttk.Label(
            frame, text="This action cannot be undone.", foreground="red"
        ).pack(anchor="w", pady=(0, 15))
        
        # Reason for cancellation
        ttk.Label(frame, text="Reason for cancellation:").pack(anchor="w", pady=(0, 5))
        
        reason_frame = ttk.Frame(frame)
        reason_frame.pack(fill="both", expand=True)
        
        reason_scrollbar = ttk.Scrollbar(reason_frame)
        reason_scrollbar.pack(side="right", fill="y")
        
        reason_text = tk.Text(reason_frame, height=3, wrap="word", yscrollcommand=reason_scrollbar.set)
        reason_text.pack(side="left", fill="both", expand=True)
        reason_scrollbar.config(command=reason_text.yview)
        reason_text.focus_set()
        
        # Notify customer checkbox
        notify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text="Send notification to customer", variable=notify_var
        ).pack(anchor="w", pady=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(
            button_frame, text="Back", command=cancel_window.destroy
        ).pack(side="right", padx=5)
        
        ttk.Button(
            button_frame,
            text="Confirm Cancellation",
            style="Action.TButton",
            command=lambda: self.do_cancel_ticket(
                ticket_id, reason_text.get("1.0", "end-1c"), notify_var.get(), cancel_window
            ),
        ).pack(side="right", padx=5)
    
    def do_cancel_ticket(self, ticket_id, reason, notify, window):
        """Process the ticket cancellation."""
        if not reason.strip():
            messagebox.showwarning("Reason Required", "Please provide a reason for cancellation")
            return
            
        window.destroy()
        
        # In a real app, this would communicate with the API to cancel the ticket
        # For demonstration, we'll just update our local data
        if self.current_ticket:
            self.current_ticket["status"] = "Cancelled"
            
            # Update the UI
            self.status_label.config(text="Cancelled")
            
            # Update the table
            for item_id in self.tickets_table.get_children():
                item = self.tickets_table.item(item_id)
                if str(item["values"][0]) == str(ticket_id):
                    values = list(item["values"])
                    values[4] = "Cancelled"  # Status column
                    values[7] = datetime.now().strftime("%Y-%m-%d")  # Updated date
                    self.tickets_table.item(item_id, values=tuple(values))
                    break
                    
        # Show notification with customer notification status
        notification_msg = f"Ticket {ticket_id} has been cancelled"
        if notify:
            notification_msg += " and customer has been notified"
            
        self.show_notification(notification_msg, "success")
        
        # Refresh tickets to show updated status
        self.load_tickets(force_refresh=True)
    def get_technician_list(self):
        """Get list of technicians."""
        # In a real app, this would come from the API
        return ["Unassigned", "John Smith", "Jane Doe", "Daniel Van Nattan", "Mei Ling"]
        
    def add_note(self):
        """Add a note to the selected ticket."""
        if not hasattr(self, 'current_ticket') or not self.current_ticket:
            messagebox.showwarning("No Ticket Selected", "Please select a ticket first")
            return

        # Create dialog for adding note
        note_window = tk.Toplevel(self)
        note_window.title(f"Add Note to Ticket {self.current_ticket.get('id', '')}")
        note_window.geometry("400x250")
        note_window.resizable(False, False)
        note_window.transient(self)  # Set to be on top of the parent window
        note_window.grab_set()  # Make it modal

        # Add content to the window
        frame = ttk.Frame(note_window, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=f"Add Note to Ticket {self.current_ticket.get('id', '')}").pack(
            anchor="w", pady=(0, 10)
        )

        # Note text area
        ttk.Label(frame, text="Note:").pack(anchor="w")
        note_text = tk.Text(frame, height=5, wrap="word")
        note_text.pack(fill="both", expand=True, pady=(5, 10))
        note_text.focus_set()

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="Cancel", command=note_window.destroy).pack(
            side="right", padx=(5, 0)
        )

        ttk.Button(
            button_frame,
            text="Add Note",
            style="Primary.TButton",
            command=lambda: self.save_note(
                self.current_ticket.get("id"), note_text.get("1.0", "end-1c"), note_window
            ),
        ).pack(side="right")

        # Make modal
        note_window.transient(self)
        note_window.grab_set()
        note_window.wait_window()
        
    def save_note(self, ticket_id, note_text, window=None):
        """Save a note to the ticket."""
        if not note_text.strip():
            messagebox.showwarning("Warning", "Please enter a note.")
            return

        try:
            # Here you would call the API to add the note
            # For now, we'll just show a success message
            log_message(f"Adding note to ticket {ticket_id}: {note_text}")

            # In a real implementation:
            # response = self.client.add_note_to_ticket(ticket_id, note_text)

            self.show_notification(f"Note added to ticket {ticket_id}")

            # Update the notes display
            if self.current_ticket:
                notes = self.notes_text.get("1.0", tk.END).strip()
                self.notes_text.config(state="normal")
                if notes:
                    self.notes_text.insert(
                        tk.END, f"\n\n{datetime.now().strftime('%Y-%m-%d %H:%M')}: {note_text}"
                    )
                else:
                    self.notes_text.insert(
                        tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {note_text}"
                    )
                self.notes_text.config(state="disabled")

            # Close the dialog if provided
            if window:
                window.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add note: {str(e)}")
            
    def update_ticket(self):
        """Open dialog to update the selected ticket."""
        if not self.current_ticket:
            self.show_notification("Please select a ticket first", "warning")
            return

        # Show dialog to update ticket status, etc.
        update_window = tk.Toplevel(self)
        update_window.title(f"Update Ticket {self.current_ticket.get('id', '')}")
        update_window.geometry("400x300")
        update_window.resizable(False, False)

        frame = ttk.Frame(update_window, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text=f"Update Ticket {self.current_ticket.get('id', '')}", font=("" , 12, "bold")
        ).pack(anchor="w", pady=(0, 15))

        # Status update
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill="x", pady=5)

        ttk.Label(status_frame, text="Status:").pack(side="left", padx=(0, 10))

        update_status_var = tk.StringVar(value=self.current_ticket.get("status", "Open"))
        status_combo = ttk.Combobox(
            status_frame,
            textvariable=update_status_var,
            values=["Open", "In Progress", "Waiting for Parts", "Completed", "Pending"],
        )
        status_combo.pack(side="left", fill="x", expand=True)

        # Assigned technician
        tech_frame = ttk.Frame(frame)
        tech_frame.pack(fill="x", pady=5)

        ttk.Label(tech_frame, text="Assign to:").pack(side="left", padx=(0, 10))

        tech_var = tk.StringVar(value=self.current_ticket.get("technician", ""))
        tech_combo = ttk.Combobox(
            tech_frame, textvariable=tech_var, values=self.get_technician_list()
        )
        tech_combo.pack(side="left", fill="x", expand=True)

        # Add note
        ttk.Label(frame, text="Add Note:").pack(anchor="w", pady=(10, 5))
        note_text = tk.Text(frame, height=5, wrap="word")
        note_text.pack(fill="both", expand=True, pady=(0, 10))

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(button_frame, text="Cancel", command=update_window.destroy).pack(
            side="right", padx=5
        )

        ttk.Button(
            button_frame,
            text="Save Changes",
            style="Primary.TButton",
            command=lambda: self.save_ticket_update(
                self.current_ticket.get("id"),
                update_status_var.get(),
                tech_var.get(),
                note_text.get("1.0", "end-1c"),
                update_window,
            ),
        ).pack(side="right", padx=5)

        # Make modal
        update_window.transient(self)
        update_window.grab_set()
        update_window.wait_window()

    def show_notification(self, message, level="info"):
        """Show a notification to the user."""
        # In a real app, this would be a toast or notification
        log_message(message)
        
        # For now, just update the status label
        if level == "warning":
            self.status_label.config(text=message, foreground="orange")
        elif level == "error":
            self.status_label.config(text=message, foreground="red")
        else:
            self.status_label.config(text=message, foreground="green")
            
        # Reset after 3 seconds
        self.after(3000, lambda: self.status_label.config(foreground="black"))
            
        # In a real app, this would call the API to create a ticket
        ticket_id = f"T-{1000 + len(self.ticket_data) + 1}"

        # Log the ticket data
        log_message(f"Creating new ticket {ticket_id}:")
        log_message(f"Customer: {self.customer_var.get()}")
        log_message(f"Phone: {self.phone_var.get()}")
        log_message(f"Device: {self.device_type_var.get()} - {self.model_var.get()}")
        log_message(f"Serial: {self.serial_var.get()}")
        log_message(f"Issue: {self.description_text.get('1.0', 'end-1c')}")

        # Show success message
        self.show_notification(f"Ticket {ticket_id} created successfully", "success")

        # Return to the list view
        self.change_action(None)

    def show_notification(self, message, message_type="info"):
        """Show a notification to the user."""
        # Log the message
        log_message(f"Notification ({message_type}): {message}")

        # Try to access the parent app's notification system
        try:
            if hasattr(self.parent.master, "show_notification"):
                self.parent.master.show_notification(message, message_type)
            else:
                # Fallback to messagebox
                if message_type == "error":
                    messagebox.showerror("Error", message)
                elif message_type == "warning":
                    messagebox.showwarning("Warning", message)
                else:
                    messagebox.showinfo("Information", message)
        except Exception as e:
            logging.error(f"Failed to show notification: {e}")
            # Final fallback
            print(f"Notification: {message}")

    def get_customer_list(self):
        """Return a list of customers."""
        # In a real app, this would come from the API
        return [
            "John Smith",
            "Sarah Johnson",
            "Mike Wilson",
            "Emily Davis",
            "Chris Martin",
            "Anna Lee",
            "David Brown",
            "Lisa White",
            "Kevin Johnson",
            "Barbara Hall",
            "Greg West",
            "Michelle Johnson",
            "Ray Brown",
        ]

    def get_technician_list(self):
        """Return a list of technicians."""
        # In a real app, this would come from the API
        current_user = self.current_user.get("fullname", "") if self.current_user else ""
        techs = [
            "Unassigned",
            "Tim Mijnout",
            "Codey O'Connor",
            "Isaac Wisnewski",
            "Reece Baldwin",
            "Lani Johnston",
        ]
        if current_user and current_user not in techs and current_user != "Admin":
            techs.append(current_user)
        return techs

    def get_device_types(self):
        """Return a list of device types."""
        return [
            "iPhone",
            "iPad",
            "MacBook",
            "iMac",
            "Desktop PC",
            "Laptop",
            "Android Phone",
            "Tablet",
            "Printer",
            "Gaming Console",
            "Network Device",
            "Other",
        ]

    def get_default_completion_date(self):
        """Return a default completion date (current date + 3 days)."""
        return (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

    def validate_decimal(self, value):
        """Validate a decimal input."""
        if value == "":
            return True

        try:
            float(value)
            return True
        except ValueError:
            return False

    def add_new_customer(self):
        """Show dialog to add a new customer."""
        customer_window = tk.Toplevel(self)
        customer_window.title("Add New Customer")
        customer_window.geometry("400x350")
        customer_window.resizable(False, False)

        frame = ttk.Frame(customer_window, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Add New Customer", font=("", 12, "bold")).pack(
            anchor="w", pady=(0, 15)
        )

        fields_frame = ttk.Frame(frame)
        fields_frame.pack(fill="x", pady=5)
        fields_frame.columnconfigure(1, weight=1)

        ttk.Label(fields_frame, text="First Name:*").grid(
            row=0, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        first_name_var = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=first_name_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(fields_frame, text="Last Name:*").grid(
            row=1, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        last_name_var = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=last_name_var).grid(row=1, column=1, sticky="ew")

        ttk.Label(fields_frame, text="Phone:*").grid(
            row=2, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        phone_var = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=phone_var).grid(row=2, column=1, sticky="ew")

        ttk.Label(fields_frame, text="Email:").grid(
            row=3, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        email_var = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=email_var).grid(row=3, column=1, sticky="ew")

        ttk.Label(fields_frame, text="Address:").grid(
            row=4, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        address_var = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=address_var).grid(row=4, column=1, sticky="ew")

        ttk.Label(frame, text="* Required fields", font=("", 8)).pack(anchor="w", pady=(5, 10))

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(button_frame, text="Cancel", command=customer_window.destroy).pack(
            side="right", padx=5
        )

        def save_customer():
            if not first_name_var.get().strip():
                messagebox.showerror("Validation Error", "First Name is required.")
                return
            if not last_name_var.get().strip():
                messagebox.showerror("Validation Error", "Last Name is required.")
                return
            if not phone_var.get().strip():
                messagebox.showerror("Validation Error", "Phone number is required.")
                return

            full_name = f"{first_name_var.get().strip()} {last_name_var.get().strip()}"
            new_customer_list = self.get_customer_list()
            new_customer_list.append(full_name)

            if hasattr(self, "customer_var"):
                self.customer_var.set(full_name)
            if hasattr(self, "phone_var"):
                self.phone_var.set(phone_var.get().strip())

            self.show_notification(f"Added new customer: {full_name}")
            customer_window.destroy()

        ttk.Button(button_frame, text="Save", style="Primary.TButton", command=save_customer).pack(
            side="right", padx=5
        )
        frame.after(100, lambda: fields_frame.winfo_children()[1].focus())


def fetch_tickets(self):
    """Fetch tickets from the API or database."""
    self.load_ticket_data()


def update_ticket_status(self, ticket_id, new_status):
    """Update the status of a ticket."""
    selected = self.tickets_table.selection()
    if not selected:
        self.show_notification("No ticket selected")
        return

    for i, ticket in enumerate(self.ticket_data):
        if ticket[0] == ticket_id:
            updated_ticket = list(ticket)
            updated_ticket[4] = new_status
            self.ticket_data[i] = tuple(updated_ticket)
            self.tickets_table.item(selected, values=updated_ticket)
            self.show_notification(f"Ticket {ticket_id} status updated to {new_status}")
            return
    self.show_notification(f"Ticket {ticket_id} not found")


def assign_ticket(self, ticket_id, technician):
    """Assign a ticket to a technician."""
    selected = self.tickets_table.selection()
    if not selected:
        self.show_notification("No ticket selected")
        return

    for i, ticket in enumerate(self.ticket_data):
        if ticket[0] == ticket_id:
            updated_ticket = list(ticket)
            updated_ticket[5] = technician
            self.ticket_data[i] = tuple(updated_ticket)
            self.tickets_table.item(selected, values=updated_ticket)
            self.show_notification(f"Ticket {ticket_id} assigned to {technician}")
            return
    self.show_notification(f"Ticket {ticket_id} not found")


def add_ticket_note(self, ticket_id, note):
    """Add a note to a ticket."""
    self.show_notification(f"Note added to ticket {ticket_id}")


def create_context_menu(self):
    """Create a context menu for the tickets table."""
    self.context_menu = tk.Menu(self, tearoff=0)
    self.context_menu.add_command(label="View Details", command=self.view_ticket)

    status_menu = tk.Menu(self.context_menu, tearoff=0)
    status_options = ["Open", "In Progress", "Waiting Parts", "Ready", "Completed"]
    for status in status_options:
        status_menu.add_command(
            label=status, command=lambda s=status: self.update_selected_ticket_status(s)
        )
    self.context_menu.add_cascade(label="Change Status", menu=status_menu)

    assign_menu = tk.Menu(self.context_menu, tearoff=0)
    for tech in self.get_technician_list():
        assign_menu.add_command(label=tech, command=lambda t=tech: self.assign_selected_ticket(t))
    self.context_menu.add_cascade(label="Assign To", menu=assign_menu)

    self.context_menu.add_command(label="Add Note", command=self.add_note_to_selected)
    self.context_menu.add_separator()
    self.context_menu.add_command(label="Delete", command=self.delete_selected_ticket)

    self.tickets_table.bind("<Button-3>", self.show_context_menu)


def show_context_menu(self, event):
    """Show the context menu at the cursor position."""
    iid = self.tickets_table.identify_row(event.y)
    if iid:
        self.tickets_table.selection_set(iid)
        self.context_menu.post(event.x_root, event.y_root)


def update_selected_ticket_status(self, status):
    """Update the status of the selected ticket."""
    selected = self.tickets_table.selection()
    if not selected:
        return
    ticket_id = self.tickets_table.item(selected, "values")[0]
    self.update_ticket_status(ticket_id, status)


def assign_selected_ticket(self, technician):
    """Assign the selected ticket to a technician."""
    selected = self.tickets_table.selection()
    if not selected:
        return
    ticket_id = self.tickets_table.item(selected, "values")[0]
    self.assign_ticket(ticket_id, technician)


def add_note_to_selected(self):
    """Add a note to the selected ticket."""
    selected = self.tickets_table.selection()
    if not selected:
        self.show_notification("No ticket selected")
        return

    ticket_id = self.tickets_table.item(selected, "values")[0]

    note_window = tk.Toplevel(self)
    note_window.title(f"Add Note to Ticket {ticket_id}")
    note_window.geometry("400x200")
    note_window.resizable(False, False)

    frame = ttk.Frame(note_window, padding=10)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=f"Add Note to Ticket {ticket_id}", font=("", 12, "bold")).pack(
        anchor="w", pady=(0, 10)
    )

    note_text = tk.Text(frame, height=5, width=40, wrap="word")
    note_text.pack(fill="both", expand=True, pady=5)

    button_frame = ttk.Frame(frame)
    button_frame.pack(fill="x", pady=(10, 0))

    ttk.Button(button_frame, text="Cancel", command=note_window.destroy).pack(side="right", padx=5)

    def save_note():
        note = note_text.get("1.0", "end-1c").strip()
        if not note:
            messagebox.showerror("Validation Error", "Note cannot be empty.")
            return
        self.add_ticket_note(ticket_id, note)
        note_window.destroy()

    ttk.Button(button_frame, text="Save", style="Primary.TButton", command=save_note).pack(
        side="right", padx=5
    )
    note_text.focus_set()


def delete_selected_ticket(self):
    """Delete the selected ticket."""
    selected = self.tickets_table.selection()
    if not selected:
        self.show_notification("No ticket selected")
        return

    ticket_id = self.tickets_table.item(selected, "values")[0]

    if not messagebox.askyesno(
        "Confirm Delete", f"Are you sure you want to delete ticket {ticket_id}?"
    ):
        return

    for i, ticket in enumerate(self.ticket_data):
        if ticket[0] == ticket_id:
            del self.ticket_data[i]
            self.tickets_table.delete(selected)
            self.show_notification(f"Ticket {ticket_id} deleted")
            return
    self.show_notification(f"Ticket {ticket_id} not found")


def get_device_types(self):
    """Return a list of device types."""
    return [
        "iPhone",
        "iPad",
        "MacBook",
        "iMac",
        "Desktop PC",
        "Laptop",
        "Android Phone",
        "Tablet",
        "Printer",
        "Gaming Console",
        "Network Device",
        "Other",
    ]
