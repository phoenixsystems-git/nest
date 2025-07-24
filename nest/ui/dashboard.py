import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import json
import logging
import threading
import queue
from typing import Dict, List, Optional, Any, Tuple, Callable
from tkinter import font as tkfont

# Local imports
from ..utils.config import get_config, get_repairdesk_key
from ..api.api_client import RepairDeskClient



from ..ui.widgets import HoverButton, ScrollableFrame, ToolTip
from .styles import get_style

# Import our custom Treeview
from ..main import FixedHeaderTreeview

# Load config
CONFIG = get_config()

# Set up logging
logger = logging.getLogger(__name__)

# Define file paths
# Import cache utilities for centralized cache management
from nest.utils.cache_utils import get_ticket_cache_path

# Use the central cache utility to get the ticket cache path
CACHE_FILE_PATH = get_ticket_cache_path()
from nest.utils.platform_paths import PlatformPaths
_platform_paths = PlatformPaths()
LAST_LOGIN_FILE_PATH = str(_platform_paths.ensure_dir_exists(_platform_paths.get_user_data_dir()) / "last_login.json")

def log_message(message):
    """Log a message to the console and to the log file."""
    logging.info(message)

# RepairDesk Brand Colors
REPAIRDESK_GREEN = "#2ecc71"
DARK_GREEN = "#27ae60"
LIGHT_GREEN = "#a3f7bf"
BG_COLOR = "#f9f9f9"
TEXT_COLOR = "#333333"
BORDER_COLOR = "#dddddd"


def save_to_cache(data):
    try:
        with open(CACHE_FILE_PATH, "w") as file:
            json.dump(data, file)
        log_message("Tickets data cached successfully.")
    except Exception as e:
        log_message(f"Error saving cache: {e}")


def load_from_cache():
    try:
        if os.path.exists(CACHE_FILE_PATH):
            with open(CACHE_FILE_PATH, "r") as file:
                log_message("Loaded tickets from cache.")
                return json.load(file)
        log_message("No cached tickets found.")
    except Exception as e:
        log_message(f"Error loading cache: {e}")
    return None


def save_last_login():
    try:
        with open(LAST_LOGIN_FILE_PATH, "w") as file:
            json.dump({"last_login": datetime.now().timestamp()}, file)
        log_message("Last login time saved.")
    except Exception as e:
        log_message(f"Error saving last login: {e}")


def load_last_login():
    try:
        if os.path.exists(LAST_LOGIN_FILE_PATH):
            with open(LAST_LOGIN_FILE_PATH, "r") as file:
                log_message("Loaded last login time.")
                return json.load(file).get("last_login", None)
        log_message("No last login time found.")
    except Exception as e:
        log_message(f"Error loading last login: {e}")
    return None


def format_date(timestamp: float) -> str:
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%B %d, %Y")


def format_timestamp(ts) -> str:
    if ts is None:
        return "N/A"
    try:
        return format_date(float(ts))
    except Exception:
        return "N/A"


def map_job_status(raw_status: str) -> str:
    mapping = {
        "Open": "Open",
        "In Progress": "In Progress",
        "Repaired": "Repaired",
        "Waiting For Parts": "Waiting For Parts",
        "Pending recycle": "Pending Recycle",
        "B2B Outsourced": "B2B Outsourced",
    }
    return mapping.get(raw_status, raw_status)


def create_error_ticket(error_type):
    """Create a placeholder ticket with error information.
    
    Args:
        error_type: Description of the error
        
    Returns:
        Dictionary with placeholder ticket information
    """
    return {
        "ticket_id": "Error",
        "customer_name": error_type, 
        "customer_mobile": "-",
        "device_type": "-",
        "repair_type": "-",
        "job_status": "Error",
        "assigned_to": "-",
        "quoted_price": "-",
        "booked_in": "-",
        "due_date": "-",
        "days_open": "-"
    }


def normalize_ticket(ticket) -> dict:
    """Convert a raw RepairDesk ticket into a normalized format for display"""
    # Handle case where ticket is a string (JSON string)
    if isinstance(ticket, str):
        # Handle empty strings or whitespace
        if not ticket.strip():
            logging.error("Empty ticket string encountered")
            return create_error_ticket("Empty String")
            
        # If it's a string starting with 'ticketData' or 'pagination', it's likely metadata
        if ticket.startswith("ticketData") or ticket.startswith("pagination"):
            logging.warning(f"Skipping metadata string: {ticket[:20]}...")
            return create_error_ticket("Metadata")
        
        # Try to parse as JSON
        try:
            ticket = json.loads(ticket)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse ticket string as JSON: {e}")
            # Return a placeholder ticket with minimal information
            return create_error_ticket(f"Parse Error: {str(e)[:30]}")

    
    # Ensure ticket is a dictionary
    if not isinstance(ticket, dict):
        logging.error(f"Ticket is not a dictionary: {type(ticket)}")
        # Return a placeholder ticket with minimal information
        return {
            "ticket_id": "Error",
            "customer_name": f"Type Error: {type(ticket)}", 
            "customer_mobile": "-",
            "device_type": "-",
            "repair_type": "-",
            "job_status": "Error",
            "assigned_to": "-",
            "quoted_price": "-",
            "booked_in": "-",
            "due_date": "-",
            "days_open": "-"
        }
        
    summary = ticket.get("summary", {})
    devices = ticket.get("devices", [])
    order_id = summary.get("order_id", "N/A")
    customer_name = summary.get("customer", {}).get("fullName", "N/A")
    customer_mobile = summary.get("customer", {}).get("mobile", "N/A")
    device_type = devices[0].get("device", {}).get("name", "N/A") if devices else "N/A"
    repair_type = (
        devices[0].get("repairProdItems", [{}])[0].get("name", "N/A") if devices else "N/A"
    )
    job_status = (
        map_job_status(devices[0].get("status", {}).get("name", "Open")) if devices else "Open"
    )
    assigned_to = devices[0].get("assigned_to", {}).get("fullname", "N/A") if devices else "N/A"
    quoted_price = summary.get("total", "N/A")
    due_date = format_timestamp(devices[0].get("due_on")) if devices else "N/A"
    try:
        created_ts = float(summary.get("created_date", 0))
        booked_in = format_timestamp(created_ts)
        days_open = (datetime.now() - datetime.fromtimestamp(created_ts)).days
    except Exception:
        booked_in = "N/A"
        days_open = "N/A"
    return {
        "ticket_id": order_id,
        "customer_name": customer_name,
        "customer_mobile": customer_mobile,
        "device_type": device_type,
        "repair_type": repair_type,
        "job_status": job_status,
        "assigned_to": assigned_to,
        "quoted_price": quoted_price,
        "booked_in": booked_in,
        "due_date": due_date,
        "days_open": days_open,
    }


class DashboardModule(ttk.Frame):
    def __init__(self, parent, current_user):
        # Apply padding to the frame with RepairDesk styling
        super().__init__(parent, padding=15, style="RepairDesk.TFrame")
        
        # Set up the RepairDesk theme
        self._setup_styles()
        
        # Process user information
        if isinstance(current_user, str):
            current_user = {"fullname": current_user, "pin_code": "N/A"}
        self.current_user = current_user
        
        # Set up API access
        self.api_key = get_repairdesk_key()
        self.client = RepairDeskClient(api_key=self.api_key)
        
        # Initialize config
        self.config = get_config()
        
        # Initialize data storage
        self.all_tickets = []
        self.tech_tickets = []
        self.last_login = load_last_login()
        self.loading = False
        
        # Create UI and load data
        self.create_widgets()
        self._load_data_async()
        save_last_login()

    def _setup_styles(self):
        """Configure the RepairDesk theme styling"""
        style = ttk.Style()
        
        # Configure frame styles
        style.configure("RepairDesk.TFrame", background=BG_COLOR)
        style.configure("RepairDesk.TLabelframe", background=BG_COLOR)
        style.configure("RepairDesk.TLabelframe.Label", 
                       background=BG_COLOR, 
                       foreground=DARK_GREEN,
                       font=("Segoe UI", 9, "bold"))
        
        # Configure card style for dashboard metrics
        style.configure("Card.TFrame", 
                       background="white",
                       relief="solid", 
                       borderwidth=1)
        
        # Configure detail section style
        style.configure("DetailSection.TLabelframe", 
                       background=BG_COLOR,
                       relief="solid", 
                       borderwidth=1)
        
        # Configure table header styles
        style.configure("Header.TFrame",
                       background=REPAIRDESK_GREEN,
                       borderwidth=0)
                       
        style.configure("Header.TLabel",
                       background=REPAIRDESK_GREEN,
                       foreground="white",
                       font=("Segoe UI", 10, "bold"))
        
        # Configure table row styles
        style.configure("Row.TFrame",
                       background="white",
                       borderwidth=0)
                       
        style.configure("Row.TLabel",
                       background="white",
                       foreground=TEXT_COLOR,
                       font=("Segoe UI", 9))
        
        # Configure button styles
        style.configure("RepairDesk.TButton", 
                       background=REPAIRDESK_GREEN, 
                       foreground="white", 
                       font=("Segoe UI", 9),
                       padding=(8, 4))
        style.map("RepairDesk.TButton",
                 background=[("active", DARK_GREEN), ("disabled", "#cccccc")],
                 foreground=[("disabled", "#666666")])
        
        # Configure the treeview (table) styles
        style.configure("RepairDesk.Treeview", 
                       background="white",
                       foreground=TEXT_COLOR,
                       rowheight=30,
                       fieldbackground="white",
                       borderwidth=1,
                       relief="solid")
                       
        # Enhanced heading styles with better visibility
        style.configure("RepairDesk.Treeview.Heading", 
                       background="#E6E6E6",  # Light gray background
                       foreground="#333333",    # Dark text
                       font=("Segoe UI", 10, "bold"),  # Larger bold font
                       relief="raised",  # Raised effect for better visibility
                       borderwidth=1)  # Add border
                       
        # Add hover effect for headings
        style.map("RepairDesk.Treeview.Heading",
                 background=[
                    ("active", "#D9D9D9"),  # Darker gray when active
                    ("hover", "#D9D9D9")  # Same on hover
                 ])
        
        style.map("RepairDesk.Treeview",
                 background=[("selected", LIGHT_GREEN)],
                 foreground=[("selected", TEXT_COLOR)])
        
        # Configure label styles
        style.configure("RepairDesk.TLabel", 
                       background=BG_COLOR,
                       foreground=TEXT_COLOR,
                       font=("Segoe UI", 8))
        
        # Configure entry field styles
        style.configure("RepairDesk.TEntry", 
                       padding=(5, 5),
                       fieldbackground="white")

    def create_widgets(self):
        """Create the dashboard UI components"""
        # Create a frame for the dashboard title
        title_frame = ttk.Frame(self, style="RepairDesk.TFrame")
        title_frame.pack(fill="x", pady=(0, 10))
        
        # Use the current user's name in the dashboard title
        user_name = self.current_user.get("fullname", "User").strip()
        
        # Create header with RepairDesk green color
        self.header_text = tk.Label(
            title_frame, 
            text=f"Dashboard – Tickets Assigned to {user_name} ({len(self.tech_tickets) if hasattr(self, 'tech_tickets') else 0} Tickets)",
            font=("Segoe UI", 11, "bold"),
            fg=REPAIRDESK_GREEN,
            bg=BG_COLOR,
            anchor="w"
        )
        self.header_text.pack(anchor="w", fill="x", pady=5)
        
        # Create refresh button with improved style
        self.refresh_btn = ttk.Button(
            title_frame,
            text="↻ Refresh",
            style="Action.TButton",
            command=self._load_data_async
        )
        self.refresh_btn.pack(side="right", padx=5)
        
        # Add dashboard summary section with key metrics
        self.summary_frame = ttk.LabelFrame(
            self,
            text="Repair Status Summary",
            style="DetailSection.TLabelframe"
        )
        self.summary_frame.pack(fill="x", padx=5, pady=(0, 10))
        
        # Create a grid layout for the summary metrics
        summary_grid = ttk.Frame(self.summary_frame)
        summary_grid.pack(fill="x", padx=10, pady=10)
        
        # Configure the grid columns
        for i in range(4):
            summary_grid.columnconfigure(i, weight=1, uniform="metrics")
            
        # Create metric cards for different statuses
        self._create_metric_card(summary_grid, 0, "Pending", "#F0AD4E")  # Yellow/orange
        self._create_metric_card(summary_grid, 1, "In Progress", "#5BC0DE")  # Blue
        self._create_metric_card(summary_grid, 2, "Waiting for Parts", "#D9534F")  # Red
        self._create_metric_card(summary_grid, 3, "Completed", "#5CB85C")  # Green
        
        # Create the table section with RepairDesk styling
        self.table_section = ttk.LabelFrame(
            self, 
            text="Your Assigned Tickets",
            style="RepairDesk.TLabelframe"
        )
        self.table_section.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create a frame for the tickets table with padding
        self.table_frame = ttk.Frame(self.table_section, style="RepairDesk.TFrame")
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Define columns with their properties
        self.columns = [
            {"name": "Ticket ID", "width": 80, "align": "center"},
            {"name": "Customer Name", "width": 150, "align": "w"},
            {"name": "Customer Mobile", "width": 120, "align": "center"},
            {"name": "Device Type", "width": 120, "align": "w"},
            {"name": "Repair Type", "width": 140, "align": "w"},
            {"name": "Job Status", "width": 100, "align": "center"},
            {"name": "Quoted Price", "width": 90, "align": "e"},
            {"name": "Booked In", "width": 90, "align": "center"},
            {"name": "Due Date", "width": 90, "align": "center"},
            {"name": "Days Open", "width": 80, "align": "center"},
        ]
        
        # Define columns for the treeview
        columns = (
            "Ticket ID",
            "Customer Name",
            "Customer Mobile",
            "Device Type",
            "Repair Type",
            "Job Status",
            "Quoted Price",
            "Booked In",
            "Due Date",
            "Days Open",
        )
        
        # Create a scrollbar for the table
        scrollbar = ttk.Scrollbar(self.table_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Create the treeview with our custom FixedHeaderTreeview
        self.tree = FixedHeaderTreeview(
            self.table_frame, 
            columns=columns, 
            show="headings",  # Show only headings, no icons
            selectmode="browse",  # Single row selection
            yscrollcommand=scrollbar.set,
            height=10  # Set a fixed number of visible rows
        )
        self.tree.pack(fill="both", expand=True)
        
        # Connect scrollbar to the treeview
        scrollbar.config(command=self.tree.yview)
        
        # Configure the column headings with proper styling
        for i, col in enumerate(columns):
            # Set column heading text and sort command
            self.tree.heading(
                col, 
                text=col.upper(),  # Uppercase text for better visibility
                command=lambda _col=col: self.sort_by_column(_col, False)
            )
            
            # Set appropriate width and alignment
            width = 100  # Default width
            alignment = "center"  # Default alignment
            
            if col == "Ticket ID":
                width = 80
                alignment = "center"
            elif col == "Customer Name":
                width = 150
                alignment = "w"  # Left-align names
            elif col == "Customer Mobile":
                width = 120
                alignment = "center"
            elif col == "Device Type":
                width = 120
                alignment = "w"  # Left-align text
            elif col == "Repair Type":
                width = 140
                alignment = "w"  # Left-align text
            elif col == "Job Status":
                width = 100
                alignment = "center"
            elif col == "Quoted Price":
                width = 90
                alignment = "e"  # Right-align prices
            elif col == "Booked In" or col == "Due Date":
                width = 90
                alignment = "center"  # Center dates
            elif col == "Days Open":
                width = 80
                alignment = "center"
            
            # Apply column configuration
            self.tree.column(col, anchor=alignment, width=width, stretch=tk.NO)

        
        # Bind events for the treeview
        self.tree.bind("<ButtonRelease-1>", self.on_single_click)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)  # Right-click context menu

        # Create style tags for different ticket statuses
        self.tree.tag_configure("pending", background="#fff9c4")  # Light yellow
        self.tree.tag_configure("completed", background="#c8e6c9")  # Light green
        self.tree.tag_configure("waiting", background="#ffccbc")  # Light red
        self.tree.tag_configure("in_progress", background="#bbdefb")  # Light blue
        self.tree.tag_configure("priority", foreground="#d32f2f")  # Red text
        self.tree.tag_configure("overdue", foreground="#d32f2f", font=("Segoe UI", 9, "bold"))  # Bold red
        # Create right-click context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self.view_details)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Mark as Complete", 
                                     command=lambda: self.mark_as("Repaired"))
        self.context_menu.add_command(label="Mark as Waiting for Parts", 
                                     command=lambda: self.mark_as("Waiting For Parts"))
        # Will bind right-click later after tree is created

        # Create a more compact stats bar at the bottom
        stats_frame = ttk.Frame(self, style="RepairDesk.TFrame")
        stats_frame.pack(fill="x", side="bottom", pady=(5, 0), padx=0)
        
        # Create a horizontal layout for stats (more compact)
        stats_inner = ttk.Frame(stats_frame, style="RepairDesk.TFrame", padding=(5, 2))
        stats_inner.pack(fill="x", expand=True)
        
        # Stats formatted as a compact horizontal status bar
        self.user_stats_label = tk.Label(
            stats_inner, 
            text="", 
            font=("Segoe UI", 8),  # Smaller font
            justify="left",
            bg=BG_COLOR,
            anchor="w",
            padx=8,
            pady=2  # Reduced padding
        )
        self.user_stats_label.pack(anchor="w", padx=5)

    def status_message(self, message, message_type="info"):
        """Display a status message in the UI"""
        # Log the message
        log_message(message)
        
        # Update the status label with the message
        # Set color based on message type
        colors = {
            "info": "#333333",     # Dark gray
            "success": "#18a383",  # Green
            "warning": "#ff9800",  # Orange
            "error": "#e74c3c"     # Red
        }
        color = colors.get(message_type, colors["info"])
        
        # Set message in status bar
        self.user_stats_label.config(text=message, fg=color)
        
        # Schedule reset after 5 seconds if not an error
        if message_type != "error":
            self.after(5000, self.load_stats)
    
    def _create_metric_card(self, parent_frame, column, status, color):
        """Create a metric card for the dashboard summary section."""
        # Create a frame for the metric card with a border
        card_frame = ttk.Frame(parent_frame, style="Card.TFrame")
        card_frame.grid(row=0, column=column, padx=10, pady=5, sticky="nsew")
        
        # Status label
        status_label = ttk.Label(
            card_frame, 
            text=status,
            font=("Segoe UI", 9, "bold"),
            foreground=color
        )
        status_label.pack(pady=(5, 0))
        
        # Count value - will be updated later
        count_var = tk.StringVar(value="0")
        count_label = ttk.Label(
            card_frame,
            textvariable=count_var,
            font=("Segoe UI", 16, "bold"),
        )
        count_label.pack(pady=(0, 5))
        
        # Store references to update later
        if not hasattr(self, 'metric_counts'):
            self.metric_counts = {}
        self.metric_counts[status] = count_var
    
    def load_stats(self):
        """Update statistics display"""
        stats = [f"Tickets Assigned: {len(self.tech_tickets)}"]
        
        # Add status breakdown
        status_counts = {}
        for ticket in self.tech_tickets:
            status = ticket.get("job_status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
        # Update the metric cards in the summary section
        if hasattr(self, 'metric_counts'):
            # Map various statuses to our dashboard categories
            pending_count = status_counts.get("Pending", 0)
            self.metric_counts["Pending"].set(str(pending_count))
            
            in_progress_count = status_counts.get("In Progress", 0)
            self.metric_counts["In Progress"].set(str(in_progress_count))
            
            waiting_count = status_counts.get("Waiting for Parts", 0) + status_counts.get("Waiting", 0)
            self.metric_counts["Waiting for Parts"].set(str(waiting_count))
            
            completed_count = status_counts.get("Completed", 0) + status_counts.get("Repaired", 0)
            self.metric_counts["Completed"].set(str(completed_count))
        
        # Add status counts to stats bar
        for status, count in status_counts.items():
            stats.append(f"  - {status}: {count}")
            
        # Join stats into a single string and update label
        stats_text = " | ".join(stats)
        self.user_stats_label.config(text=stats_text, fg="#333333")
            
        # Update the header text with the current ticket count
        if hasattr(self, 'header_text') and hasattr(self, 'current_user'):
            user_name = self.current_user.get("fullname", "User").strip()
            self.header_text.config(text=f"Dashboard – Tickets Assigned to {user_name} ({len(self.tech_tickets)} Tickets)")
            
        log_message(f"Dashboard stats: {stats}")

    def sort_by_column(self, col, reverse):
        """Sort treeview by a specific column"""
        data_list = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]

        def try_convert(val):
            try:
                return float(val.replace("$", "").replace(",", ""))
            except:
                return val.lower()

        data_list.sort(key=lambda t: try_convert(t[0]), reverse=reverse)
        for idx, (_, child) in enumerate(data_list):
            self.tree.move(child, "", idx)
        self.tree.heading(col, command=lambda: self.sort_by_column(col, not reverse))

    def on_single_click(self, event):
        """Handle single-click on a row"""
        selected_item = self.tree.focus()
        if not selected_item:
            return
        vals = self.tree.item(selected_item, "values")
        log_message(f"Selected row: {vals}")

    def on_double_click(self, event):
        """Handle double-click on a row"""
        self.view_details()

    def on_right_click(self, event):
        """Handle right-click for context menu"""
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.tree.focus(row)
            self.context_menu.post(event.x_root, event.y_root)

    def mark_as(self, status):
        """Mark selected ticket with a new status and update via RepairDesk API"""
        item = self.tree.focus()
        if not item:
            messagebox.showerror("Error", "No ticket selected.")
            return
        vals = self.tree.item(item, "values")
        ticket_id = vals[0]
        ticket = next((t for t in self.all_tickets if str(t["ticket_id"]) == str(ticket_id)), None)
        if not ticket:
            messagebox.showerror("Error", f"Ticket {ticket_id} not found.")
            return
        
        # Show a "Processing" message
        self.status_message(f"Updating ticket {ticket_id} status to {status}...", "info")
        
        # Use a background thread to avoid UI freezing during API call
        def update_ticket_thread():
            try:
                # Make the API call to update the ticket status
                # Call the client's update_ticket_status method
                result = self.client.update_ticket_status(ticket_id, status)
                
                # Check if there was an error in the response
                if isinstance(result, dict) and "error" in result:
                    # Show error message using the error from the API
                    error_msg = result["error"]
                    # Use the safer method to update UI from background thread
                    self._safe_update_ui(
                        lambda: messagebox.showerror("Error", f"Failed to update ticket status: {error_msg}"),
                        lambda: self.status_message(f"Error updating ticket: {error_msg}", "error")
                    )
                    return
                    
                # Update local data after successful API call
                ticket["job_status"] = status
                
                # Use the safer method to update UI from background thread
                self._safe_update_ui(
                    lambda: messagebox.showinfo("Success", f"Ticket {ticket_id} marked as {status}."),
                    self._update_tree,
                    lambda: self.status_message(f"Ticket {ticket_id} updated successfully.", "success")
                )
            except Exception as e:
                # Capture the error message in a local variable
                error_msg = str(e)
                # Use the safer method to update UI from background thread
                self._safe_update_ui(
                    lambda: messagebox.showerror("Error", f"Failed to update ticket status: {error_msg}"),
                    lambda: self.status_message(f"Error updating ticket: {error_msg}", "error")
                )
        
        # Start the update in a background thread
        import threading
        threading.Thread(target=update_ticket_thread, daemon=True).start()
        
    def _safe_update_ui(self, *funcs):
        """Safely schedule UI updates from background threads.
        
        This method ensures that UI updates only occur if the widget still exists,
        preventing many common Tkinter threading errors.
        
        Args:
            funcs: Functions to be executed on the UI thread
        """
        def execute_when_exists():
            # Check if widget still exists first
            if not self.winfo_exists():
                return  # Widget has been destroyed, don't proceed
                
            # Execute each function in sequence, safely catching any errors
            for func in funcs:
                try:
                    if callable(func):
                        func()
                except Exception as e:
                    logging.error(f"Error in _safe_update_ui: {e}")
        
        # Schedule the execution on the main thread
        try:
            self.after(0, execute_when_exists)
        except Exception as e:
            # This could happen if the widget is being destroyed
            logging.error(f"Could not schedule UI update: {e}")

    def view_details(self):
        """View detailed information for the selected ticket"""
        item = self.tree.focus()
        if not item:
            messagebox.showerror("Error", "No ticket selected.")
            return
        vals = self.tree.item(item, "values")
        ticket_id = vals[0]
        ticket = next((t for t in self.all_tickets if str(t["ticket_id"]) == str(ticket_id)), None)
        if ticket:
            self.show_ticket_details(ticket)
        else:
            messagebox.showerror("Error", f"Ticket {ticket_id} not found.")

    def show_ticket_details(self, ticket):
        """Display a dialog with detailed ticket information"""
        win = tk.Toplevel(self)
        win.title(f"Ticket Details: {ticket['ticket_id']}")
        win.geometry("600x500")
        win.resizable(False, False)
        win.configure(background=BG_COLOR)
        
        # Configure the detail window style
        win.grid_columnconfigure(0, weight=1)
        
        # Title at the top
        title_frame = tk.Frame(win, bg=BG_COLOR, padx=15, pady=10)
        title_frame.grid(row=0, column=0, sticky="ew")
        
        tk.Label(
            title_frame, 
            text=f"Ticket: {ticket['ticket_id']}",
            font=("Segoe UI", 11, "bold"),
            fg=REPAIRDESK_GREEN,
            bg=BG_COLOR
        ).pack(anchor="w")
        
        # Define sections with field groups
        sections = {
            "Customer Information": [
                ("Customer Name", "customer_name"), 
                ("Mobile", "customer_mobile")
            ],
            "Device Information": [
                ("Device Type", "device_type"), 
                ("Repair Type", "repair_type")
            ],
            "Job Details": [
                ("Job Status", "job_status"),
                ("Quoted Price", "quoted_price"),
                ("Booked In", "booked_in"),
                ("Due Date", "due_date"),
                ("Days Open", "days_open"),
            ],
        }
        
        # Add each section to the dialog
        row_idx = 1
        for section_title, fields in sections.items():
            section = tk.LabelFrame(
                win, 
                text=section_title,
                font=("Segoe UI", 9, "bold"),
                fg=DARK_GREEN,
                bg=BG_COLOR,
                padx=10,
                pady=10
            )
            section.grid(row=row_idx, column=0, sticky="ew", padx=15, pady=5)
            
            # Add each field to the section
            for i, (label, key) in enumerate(fields):
                field_frame = tk.Frame(section, bg=BG_COLOR)
                field_frame.pack(fill="x", pady=5)
                
                # Label on left
                tk.Label(
                    field_frame, 
                    text=f"{label}:",
                    width=15,
                    anchor="w",
                    font=("Segoe UI", 9, "bold"),
                    bg=BG_COLOR,
                    fg=TEXT_COLOR
                ).pack(side="left")
                
                # Value on right
                value_var = tk.StringVar(value=ticket.get(key, "N/A"))
                entry = tk.Entry(
                    field_frame,
                    textvariable=value_var,
                    readonlybackground="white",
                    relief="solid",
                    bd=1,
                    font=("Segoe UI", 9)
                )
                entry.config(state="readonly")
                entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
            
            row_idx += 1
            
        # Bottom buttons
        btn_frame = tk.Frame(win, bg=BG_COLOR, padx=15, pady=15)
        btn_frame.grid(row=row_idx, column=0, sticky="ew")
        
        # Create close button with RepairDesk styling
        close_btn = tk.Button(
            btn_frame,
            text="Close",
            font=("Segoe UI", 9),
            bg=REPAIRDESK_GREEN,
            fg="white",
            padx=15,
            pady=5,
            relief="flat",
            command=win.destroy
        )
        close_btn.pack(side="right")

    def _load_data_async(self, force_refresh=True):
        """Load data asynchronously to prevent UI freezing"""
        # Check if already loading
        if hasattr(self, 'loading') and self.loading:
            return
            
        self.loading = True
        
        # Clear the tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Show loading message
        self.tree.insert("", "end", values=("Loading tickets...",) + ("",) * 9)
        
        # Disable refresh button during load
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.config(state="disabled")
        
        # Start a thread to fetch the data
        threading.Thread(target=lambda: self._fetch_tickets_data(force_refresh), daemon=True).start()
    
    def _fetch_tickets_data(self, force_refresh=False):
        """Fetch ticket data from API or cache"""
        try:
            log_message("Loading tickets from API...")
            
            # If force_refresh is True, always get tickets from API
            # Otherwise try to load from cache first
            if force_refresh:
                tickets = []
            else:
                tickets = load_from_cache() or []
                
            # If no tickets in cache or force_refresh is True, fetch from API
            if not tickets:
                try:
                    log_message("Fetching tickets from RepairDesk API...")
                    
                    # Use our updated RepairDeskClient to get all tickets with force_refresh
                    try:
                        # The updated client handles pagination and error handling internally
                        tickets = self.client.get_all_tickets(force_refresh=force_refresh)
                        log_message(f"Successfully retrieved {len(tickets)} tickets from API")
                    except Exception as e:
                        log_message(f"Error fetching tickets from API: {e}")
                        error_message = str(e)  # Capture the error message
                        self.after(0, lambda error=error_message: messagebox.showerror(
                            "API Error", 
                            f"Could not fetch tickets: {error}"
                        ))
                        # Fall back to cache if available and we're not forcing refresh
                        if not force_refresh:
                            tickets = load_from_cache() or []
                            if tickets:
                                log_message("Falling back to cached tickets")
                        else:
                            tickets = []
                    
                    # Save fetched tickets to cache
                    if tickets:
                        save_to_cache(tickets)
                        log_message(f"Cached {len(tickets)} tickets successfully")
                        
                except Exception as e:
                    log_message(f"Critical error loading tickets: {e}")
                    self.after(0, lambda: messagebox.showerror(
                        "Error", 
                        f"Failed to load tickets: {e}"
                    ))
            
            # Process tickets for display
            self.all_tickets = [normalize_ticket(t) for t in tickets]
            uname = self.current_user.get("fullname", "").strip().lower()
            self.tech_tickets = [
                t for t in self.all_tickets if t["assigned_to"].strip().lower() == uname
            ]
            
            # Update UI on the main thread
            self.after(0, self._update_tree)
            
        finally:
            # Always re-enable the refresh button with error handling for widget destruction
            def safe_enable_button():
                try:
                    # Check if widget still exists and is valid before configuring
                    if hasattr(self, 'refresh_btn') and self.refresh_btn.winfo_exists():
                        self.refresh_btn.config(state="normal")
                except (tk.TclError, RuntimeError, AttributeError) as e:
                    # Silently handle widget destruction errors
                    logging.debug(f"Widget access error (normal during module switching): {e}")
            
            self.after(0, safe_enable_button)
            self.loading = False

    def _update_tree(self):
        """Update the treeview with current ticket data and apply styling"""
        # Ensure we're on the main thread by checking if the widget exists
        if not self.winfo_exists():
            return  # Widget has been destroyed, don't proceed
            
        try:
            # Update the header text with ticket count
            if hasattr(self, 'header_text') and hasattr(self, 'current_user'):
                self.header_text.config(
                    text=f"Dashboard – Tickets Assigned to {self.current_user['fullname']} ({len(self.tech_tickets)} Tickets)"
                )
            
            # Update user stats
            self.load_stats()
            
            # Clear the tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # If no tickets, show message
            if not self.tech_tickets:
                self.tree.insert("", "end", values=("No tickets found",) + ("",) * 9)
                return
            
            # Process each ticket
            for ticket in self.tech_tickets:
                # Extract values with safe defaults
                ticket_id = ticket.get("ticket_id", "")
                customer_name = ticket.get("customer_name", "")
                customer_mobile = ticket.get("contact_mobile", "")
                device_type = ticket.get("device_type", "")
                repair_type = ticket.get("repair_type", "")
                job_status = ticket.get("job_status", "")
                quoted_price = f"${float(ticket.get('price', 0)):.2f}" if ticket.get('price') else "$0.00"
                
                # Format dates
                booked_in = self._format_date(ticket.get("created_at"))
                due_date = self._format_date(ticket.get("due_date"))
                
                # Calculate days open
                days_open = self._calculate_days_open(ticket.get("created_at"))
                
                # Determine tags based on status
                tags = []
                status_lower = job_status.lower() if job_status else ""
                
                # Add status tag
                if "pending" in status_lower:
                    tags.append("pending")
                elif "complete" in status_lower or "repaired" in status_lower:
                    tags.append("completed")
                elif "waiting" in status_lower:
                    tags.append("waiting")
                elif "progress" in status_lower:
                    tags.append("in_progress")
                
                # Check for priority flag
                if ticket.get("priority", "0") == "1":
                    tags.append("priority")
                    
                # Check for overdue
                if due_date and self._is_overdue(due_date):
                    tags.append("overdue")
                
                # Insert row with all values
                item_id = self.tree.insert("", "end", values=(
                    ticket_id,
                    customer_name,
                    customer_mobile,
                    device_type,
                    repair_type,
                    job_status,
                    quoted_price,
                    booked_in,
                    due_date,
                    days_open
                ), tags=tags)
            
            # Re-enable the refresh button with robust error handling
            try:
                if hasattr(self, 'refresh_btn') and self.refresh_btn.winfo_exists():
                    self.refresh_btn.config(state="normal")
            except (tk.TclError, RuntimeError, AttributeError) as e:
                # Silently handle widget destruction errors
                logging.debug(f"Widget access error (normal during module switching): {e}")
                
            # Mark loading complete
            self.loading = False
        except Exception as e:
            logging.error(f"Error updating dashboard: {e}")
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.config(state="normal")
            self.loading = False
                
    def _on_row_click(self, ticket_id):
        """Handle clicking on a row in our custom table"""
        # Find the ticket with this ID
        for ticket in self.tech_tickets:
            if ticket.get("ticket_id") == ticket_id:
                # Show ticket details
                self.show_ticket_details(ticket)
                break
    
    def _on_row_double_click(self, ticket_id):
        """Handle double-clicking on a row in our custom table"""
        # Find the ticket with this ID
        for ticket in self.tech_tickets:
            if ticket.get("ticket_id") == ticket_id:
                # Open ticket in full view
                self.view_ticket_details(ticket)
                break
    
    def _on_treeview_motion(self, event):
        """Handle mouse movement over the treeview"""
        # Kept for compatibility with old code, but not used anymore
        pass
    
    def _on_treeview_leave(self, event):
        """Handle mouse leaving the treeview"""
        # Kept for compatibility with old code, but not used anymore
        pass
        
    def _format_date(self, date_str):
        """Format a date string for display"""
        if not date_str:
            return ""
        
        try:
            # Handle different date formats
            if "T" in date_str:
                # ISO format (e.g., 2025-05-14T10:30:00)
                date_obj = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
            elif "-" in date_str:
                # YYYY-MM-DD format
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            elif any(month in date_str for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                # Month name format (e.g., May 17, 2025)
                try:
                    date_obj = datetime.strptime(date_str, '%b %d, %Y')
                except ValueError:
                    date_obj = datetime.strptime(date_str, '%B %d, %Y')
            else:
                # Attempt to parse as timestamp
                date_obj = datetime.fromtimestamp(float(date_str))
                
            # Format as MMM DD, YYYY
            return date_obj.strftime('%b %d, %Y')
        except Exception as e:
            logging.warning(f"Error formatting date {date_str}: {e}")
            return date_str
    
    def _calculate_days_open(self, created_date):
        """Calculate number of days a ticket has been open"""
        if not created_date:
            return 0
            
        try:
            # Parse the creation date
            if "T" in created_date:
                # ISO format
                date_obj = datetime.strptime(created_date.split('T')[0], '%Y-%m-%d')
            elif "-" in created_date:
                # YYYY-MM-DD format
                date_obj = datetime.strptime(created_date, '%Y-%m-%d')
            else:
                # Attempt to parse as timestamp
                date_obj = datetime.fromtimestamp(float(created_date))
                
            # Calculate days difference
            delta = datetime.now() - date_obj
            return delta.days
        except Exception as e:
            logging.warning(f"Error calculating days open: {e}")
            return 0
            
    def _is_overdue(self, due_date):
        """Check if a ticket is overdue"""
        if not due_date:
            return False
            
        try:
            # Parse the due date
            if "T" in due_date:
                # ISO format
                date_obj = datetime.strptime(due_date.split('T')[0], '%Y-%m-%d')
            elif "-" in due_date:
                # YYYY-MM-DD format
                date_obj = datetime.strptime(due_date, '%Y-%m-%d')
            elif any(month in due_date for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                # Month name format (e.g., May 17, 2025)
                try:
                    date_obj = datetime.strptime(due_date, '%b %d, %Y')
                except ValueError:
                    date_obj = datetime.strptime(due_date, '%B %d, %Y')
            else:
                # Attempt to parse as timestamp
                date_obj = datetime.fromtimestamp(float(due_date))
                
            # Check if due date is in the past
            return date_obj.date() < datetime.now().date()
        except Exception as e:
            logging.warning(f"Error checking if overdue: {e}")
            return False

    def _get_status_id_from_name(self, status_name):
        """Convert a status name to a status ID for the RepairDesk API
        
        Args:
            status_name: The human-readable status name
            
        Returns:
            The status ID if found, None otherwise
        """
        # Common status mappings in RepairDesk
        # These are standard status mappings, but actual IDs may vary by store
        status_map = {
            "Pending": 1,
            "In Progress": 2,
            "Waiting For Parts": 3,
            "Completed": 4,
            "Ready For Pickup": 5,
            "Waiting For Customer": 6,
            "Waiting For Quote": 7,
            "Waiting For Deposit": 8,
            "Cancelled": 9,
            "On Hold": 10
        }
        
        # Try to match the exact name
        if status_name in status_map:
            return status_map[status_name]
            
        # Try case-insensitive search
        status_lower = status_name.lower()
        for name, id in status_map.items():
            if name.lower() == status_lower:
                return id
                
        # Try partial matching
        for name, id in status_map.items():
            if status_lower in name.lower() or name.lower() in status_lower:
                return id
                
        # If all else fails, return None and let the caller handle it
        return None
